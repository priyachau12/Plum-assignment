"""Tests for the AI-using steps, with a FAKE client (no network).

Proves the AI seam works: extraction uses validated model output, falls back /
degrades on failure, and explanation prefers the AI but keeps the built text
when the model fails.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.agents.extraction_agent import ExtractionAgent, ExtractionAgentConfig
from app.graph.nodes.classify import classify
from app.graph.nodes.explain import explain
from app.graph.nodes.extract import extract
from app.llm.client import DocumentClassification, LLMClient, LLMError
from app.models.claim import ClaimRequest, Document, DocumentQuality, DocumentType
from app.models.decision import Decision, DecisionResult, TraceStatus


def _agent(llm, **cfg) -> ExtractionAgent:
    """Wrap a fake client in an ExtractionAgent for extract-node tests."""
    base = dict(
        enabled=True,
        confidence_threshold=0.67,
        max_attempts=3,
        model_fast="fast",
        model_strong="strong",
    )
    base.update(cfg)
    return ExtractionAgent(llm, ExtractionAgentConfig(**base))


class FakeLLM(LLMClient):
    def __init__(
        self,
        fields: dict | None = None,
        explanation: str = "AI TEXT",
        fail: bool = False,
        classification: DocumentClassification | None = None,
    ):
        self._fields = fields or {"diagnosis": "Viral Fever"}
        self._explanation = explanation
        self._fail = fail
        self._classification = classification or DocumentClassification(
            document_type="PRESCRIPTION", readable=True, patient_name="Rajesh Kumar"
        )
        self.extract_calls: list[dict] = []  # records (model, prompt_hint) per call

    def classify_document(self, document: Document) -> DocumentClassification:
        if self._fail:
            raise LLMError("simulated classification failure")
        return self._classification

    def extract_document(
        self, document: Document, *, model: str | None = None, prompt_hint: str | None = None
    ) -> dict[str, Any]:
        self.extract_calls.append({"model": model, "prompt_hint": prompt_hint})
        if self._fail:
            raise LLMError("simulated extraction failure")
        return self._fields

    def generate_explanation(self, decision, approved_amount, reasons, fallback) -> str:
        if self._fail:
            raise LLMError("simulated explanation failure")
        return self._explanation


def _request_without_content() -> ClaimRequest:
    return ClaimRequest(
        member_id="EMP001",
        policy_id="PLUM_GHI_2024",
        claim_category="CONSULTATION",
        treatment_date="2024-11-01",
        claimed_amount=1500,
        documents=[Document(file_id="F1", actual_type="PRESCRIPTION")],  # no inline content
    )


def _request_with_content() -> ClaimRequest:
    return ClaimRequest(
        member_id="EMP001",
        policy_id="PLUM_GHI_2024",
        claim_category="CONSULTATION",
        treatment_date="2024-11-01",
        claimed_amount=1500,
        documents=[
            Document(file_id="F1", actual_type="PRESCRIPTION", content={"diagnosis": "Viral Fever"})
        ],
    )


def test_extract_uses_validated_ai_output():
    full = {"patient_name": "R", "date": "2024-11-01", "diagnosis": "Dengue"}
    out = extract({"request": _request_without_content()}, agent=_agent(FakeLLM(fields=full)))
    assert out["extracted_content"]["F1"]["diagnosis"] == "Dengue"
    assert not out.get("degraded")


def test_extract_inline_content_bypasses_agent():
    # Determinism guard: a document with inline content must NOT invoke the agent
    # (this is what keeps the injected-content eval reproducible).
    llm = FakeLLM(fields={"diagnosis": "SHOULD NOT BE USED"})
    out = extract({"request": _request_with_content()}, agent=_agent(llm))
    assert llm.extract_calls == []  # agent.run never reached the LLM
    assert "extracted_content" not in out  # the provided content is used directly
    assert not out.get("degraded")


def test_extract_simulate_failure_skips_agent():
    req = _request_without_content()
    req.simulate_component_failure = True
    llm = FakeLLM()
    out = extract({"request": req}, agent=_agent(llm))
    assert out["degraded"] is True
    assert llm.extract_calls == []  # short-circuited before the agent ran


def test_extract_degrades_on_ai_error():
    out = extract({"request": _request_without_content()}, agent=_agent(FakeLLM(fail=True)))
    assert out["degraded"] is True
    assert any(t.status == TraceStatus.FAILED for t in out["trace"])


def test_extract_degrades_without_ai():
    out = extract({"request": _request_without_content()}, agent=None)
    assert out["degraded"] is True
    assert any(t.status == TraceStatus.SKIPPED for t in out["trace"])


@pytest.fixture
def approved_result() -> DecisionResult:
    return DecisionResult(
        decision=Decision.APPROVED,
        approved_amount=1350,
        confidence=0.95,
        financial_breakdown={
            "is_network": False,
            "covered_base": 1500,
            "network_discount_percent": 0,
            "after_network_discount": 1500,
            "copay_percent": 10,
            "after_copay": 1350,
        },
    )


def test_explain_prefers_ai(approved_result):
    # Consistent AI text (mentions the approved amount) is used as-is.
    out = explain(
        {"adjudication_result": approved_result},
        llm=FakeLLM(explanation="Good news — Rs. 1,350 is approved and on its way."),
    )
    assert out["explanation"] == "Good news — Rs. 1,350 is approved and on its way."
    assert out["trace"][0].data["source"] == "llm"


def test_explain_guards_against_amount_drift(approved_result):
    # AI text that contradicts the approved amount (1350) is rejected; the node
    # falls back to the deterministic template, which carries the correct number.
    out = explain(
        {"adjudication_result": approved_result},
        llm=FakeLLM(explanation="Your claim is fully approved for Rs. 9,999."),
    )
    assert "1350" in out["explanation"]
    assert "9,999" not in out["explanation"]
    assert out["trace"][0].data["source"] == "template-guarded"


def test_explain_guard_does_not_trigger_on_rejection():
    rejected = DecisionResult(
        decision=Decision.REJECTED,
        approved_amount=0.0,
        confidence=0.95,
    )
    # No amount to match on a rejection — arbitrary AI text is accepted.
    out = explain({"adjudication_result": rejected}, llm=FakeLLM(explanation="Sorry, declined."))
    assert out["explanation"] == "Sorry, declined."
    assert out["trace"][0].data["source"] == "llm"


def test_explain_falls_back_to_built_text_on_failure(approved_result):
    out = explain({"adjudication_result": approved_result}, llm=FakeLLM(fail=True))
    assert "1350" in out["explanation"]  # deterministic built text still works


def test_explain_surfaces_degraded_caveat_on_an_approval():
    # A degraded APPROVAL (TC011) must not read as a clean success — the member
    # explanation has to carry the "manual review recommended" caveat.
    degraded_approval = DecisionResult(
        decision=Decision.APPROVED,
        approved_amount=4000,
        confidence=0.65,
        notes=[
            "A processing component failed and was skipped; manual review is "
            "recommended due to incomplete processing."
        ],
        financial_breakdown={
            "is_network": False,
            "covered_base": 4000,
            "network_discount_percent": 0,
            "after_network_discount": 4000,
            "copay_percent": 0,
            "after_copay": 4000,
        },
    )
    out = explain({"adjudication_result": degraded_approval}, llm=None)  # template path
    assert "manual review" in out["explanation"].lower()
    assert "4000" in out["explanation"]


# --- vision classification path (real uploads) -------------------------------


def _uploaded_doc() -> ClaimRequest:
    """A real upload: bytes attached, no declared type — vision must classify."""
    return ClaimRequest(
        member_id="EMP001",
        policy_id="PLUM_GHI_2024",
        claim_category="CONSULTATION",
        treatment_date="2024-11-01",
        claimed_amount=1500,
        documents=[
            # no actual_type: vision must classify it
            Document(file_id="F1", media_type="image/jpeg", data_base64="ZmFrZQ==")
        ],
    )


def test_classify_classifies_upload_with_vision():
    req = _uploaded_doc()
    classification = DocumentClassification(
        document_type="HOSPITAL_BILL", readable=True, patient_name="Asha Rao"
    )
    out = classify({"request": req}, llm=FakeLLM(classification=classification))

    # The vision findings are resolved onto the document so the gate can use them.
    doc = req.documents[0]
    assert doc.actual_type is DocumentType.HOSPITAL_BILL
    assert doc.patient_name_on_doc == "Asha Rao"
    assert out["classified_docs"]["F1"] == "HOSPITAL_BILL"
    assert any(t.status == TraceStatus.OK for t in out["trace"])


def test_classify_marks_unreadable_upload():
    req = _uploaded_doc()
    classification = DocumentClassification(document_type="PHARMACY_BILL", readable=False)
    classify({"request": req}, llm=FakeLLM(classification=classification))
    assert req.documents[0].quality is DocumentQuality.UNREADABLE


def test_classify_skips_when_no_ai_and_no_declared_type():
    req = _uploaded_doc()
    out = classify({"request": req}, llm=None)
    assert req.documents[0].actual_type is None
    assert any(t.status == TraceStatus.SKIPPED for t in out["trace"])


# --- Phase 4: extraction quality + schema validation -------------------------


def test_extract_full_fields_give_full_confidence():
    full = {"patient_name": "Rajesh Kumar", "date": "2024-11-01", "diagnosis": "Viral Fever"}
    out = extract({"request": _request_without_content()}, agent=_agent(FakeLLM(fields=full)))
    assert out["extraction_confidence"] == 1.0


def test_extract_partial_fields_lower_confidence():
    out = extract(
        {"request": _request_without_content()}, agent=_agent(FakeLLM(fields={"diagnosis": "X"}))
    )
    assert out["extraction_confidence"] < 1.0


def test_extract_document_validates_and_coerces_llm_json(monkeypatch):
    from app.llm.client import AnthropicLLMClient

    client = AnthropicLLMClient(model="x", api_key="dummy", timeout=1.0)
    monkeypatch.setattr(
        client,
        "_ask",
        lambda *a, **k: '{"patient_name": "Rajesh", "total": "1500"}',
    )
    fields = client.extract_document(Document(file_id="F1", actual_type="HOSPITAL_BILL"))
    assert fields["patient_name"] == "Rajesh"
    assert fields["total"] == 1500.0  # coerced from string to float


def test_extract_document_raises_on_bad_schema(monkeypatch):
    from app.llm.client import AnthropicLLMClient

    client = AnthropicLLMClient(model="x", api_key="dummy", timeout=1.0)
    monkeypatch.setattr(
        client,
        "_ask",
        lambda doc, prompt, max_tokens=1024, model=None: '{"total": "not-a-number"}',
    )
    with pytest.raises(LLMError):
        client.extract_document(Document(file_id="F1", actual_type="HOSPITAL_BILL"))


def test_extract_document_honors_model_override_and_prompt_hint(monkeypatch):
    from app.llm.client import AnthropicLLMClient

    client = AnthropicLLMClient(model="default-model", api_key="dummy", timeout=1.0)
    seen: dict = {}

    def fake_ask(doc, prompt, max_tokens=1024, model=None):
        seen["prompt"] = prompt
        seen["model"] = model
        return '{"patient_name": "Asha"}'

    monkeypatch.setattr(client, "_ask", fake_ask)
    client.extract_document(
        Document(file_id="F1", actual_type="HOSPITAL_BILL"),
        model="strong-model",
        prompt_hint="LOOK AGAIN at the footer.",
    )
    assert seen["model"] == "strong-model"  # override reached the API call
    assert "LOOK AGAIN at the footer." in seen["prompt"]  # hint appended to the prompt


def test_create_falls_back_to_default_model_without_override(monkeypatch):
    from app.llm.client import AnthropicLLMClient

    client = AnthropicLLMClient(model="default-model", api_key="dummy", timeout=1.0)
    seen: dict = {}

    class _Messages:
        def create(self, *, model, **kwargs):
            seen["model"] = model

            class _Resp:
                content = [type("B", (), {"text": "{}"})()]

            return _Resp()

    monkeypatch.setattr(client, "_client", type("C", (), {"messages": _Messages()})())
    client._create(max_tokens=10, messages=[])
    assert seen["model"] == "default-model"  # None override -> client default
