# Technical Documentation — Plum Claims Processing System

> **What this file is:** the single, running technical reference for the whole
> system. It is appended to at the end of **every phase**. It records the tech
> stack, a file-by-file reference, component contracts, configuration, how to
> run/test, the decision log, the risk register, and the test-case routing map.
>
> **Companion docs:** [`architecture.md`](./architecture.md) holds the
> high-level architecture (the deliverable). This file holds the *detailed,
> growing* reference.
>
> **Maintenance rule:** when a phase adds or changes a file, its row in
> §4 is added/updated and a dated entry is added to §1 (Phase log).

---

## 0. Plain-language guide: what we built, in simple words

> This section explains the whole system in everyday language — no jargon. If
> you read only one section, read this one.

### What the system does

A company's employee uploads medical documents (a doctor's prescription, a
hospital bill, a lab report) and says "please pay my claim." A human normally
reads those documents, checks them against the insurance rules, and decides:
**pay in full, pay part, reject, or send for a human to look closer.** Our
system does that automatically — and it always **shows its work** so anyone can
see *why* it decided what it did.

### The one big idea

We split the work into two kinds of jobs:

1. **Reading and writing** — messy, "human" work. Reading a blurry handwritten
   bill, or writing a friendly explanation. **AI (the LLM) is good at this**, so
   the AI does it.
2. **Deciding** — applying the insurance rulebook (waiting periods, limits,
   exclusions, the co-pay math). This must be **exactly the same every single
   time** and never "made up." So a plain, fixed **rulebook in code** does this
   — never the AI.

So: **the AI reads and explains; fixed code decides.** This is the most
important sentence in the whole project. It means decisions are reliable,
repeatable, and you can always trace them — while the AI handles the messy
parts. The AI is never allowed to decide a claim.

### A claim's journey, step by step (in plain words)

Think of an assembly line. The claim moves down the line; each station does one
small job and writes a note in a logbook (the "trace"). The logbook is what lets
anyone see exactly what happened.

1. **Intake** — "Who is this? Are they a real member?" Opens the logbook.
2. **Classify** — "What kind of document is each file?" (prescription? bill?)
3. **Verify (the gate)** — "Are the right documents here, are they readable, and
   are they all for the same patient?" **If something's wrong, the line STOPS
   here** and tells the member exactly what to fix. No decision is made on a bad
   set of documents.
4. **Extract** — "Pull the useful facts out of each document" (amounts,
   diagnosis, dates).
5. **Normalize the diagnosis** — "The doctor wrote 'Type 2 Diabetes Mellitus';
   the rulebook calls that 'diabetes'." Translates free text into the exact
   words the rulebook understands.
6. **Adjudicate (the rulebook)** — the real decision. Runs the rules in a fixed
   order and does the money math.
7. **Explain** — writes the decision in friendly language for the member.

If verification fails at step 3, steps 4–7 never run.

### The rulebook, in order (and why the order matters)

The rules run in a fixed order, because some reasons "win" over others. For each
claim it checks, in this sequence:

1. **Is the person actually a member?** If not → reject.
2. **Is this treatment excluded entirely?** (e.g. weight-loss / cosmetic) →
   reject. *(Checked early so an excluded claim is rejected for the right reason,
   not for a money reason.)*
3. **Is it too soon?** (a "waiting period" — some conditions aren't covered for
   the first 90/365 days) → reject, and tell them the date they become eligible.
4. **Did it need pre-approval they didn't get?** (e.g. an expensive MRI) →
   reject, and tell them to get pre-approval and resubmit.
5. **Is the amount over the per-claim limit?** → reject, stating the limit.
6. **For dental/vision: which line items are covered?** If some are excluded but
   others are fine → pay the good ones (a "partial" approval).
7. **Does it look suspicious?** (e.g. 4 claims on the same day) → don't reject;
   send to a **human** to review.
8. **Is it a very large amount?** → also send to a human.
9. **Otherwise, do the money math and approve.**

### The money math (the part people get wrong)

When a claim is approved, the order of the discount and the co-pay matters:

> **First** apply the network-hospital discount, **then** the co-pay.

Example (real test case): a ₹4,500 bill at a network hospital → 20% discount
first = ₹3,600 → then 10% co-pay = **₹3,240**. Doing it in the wrong order gives
a different (wrong) number, so we fixed the order and wrote a test that proves it.

### "Confidence" and handling failure

- Every decision comes with a **confidence score** (how sure the system is).
- If a part of the system breaks mid-way (say the document reader times out),
  the line **does not crash**. It writes "this step failed" in the logbook,
  **lowers the confidence**, adds a note saying "a human should double-check,"
  and keeps going with whatever it has. (Test case TC011 checks exactly this.)

### Why the test data lets us be exact

The provided test cases already include the "facts" that would normally be read
off the documents. So for grading we **skip the AI reading step and feed those
facts straight to the rulebook** — which means the 12 results are identical every
run and don't depend on the AI. The AI reading step still exists and is used for
real documents (and we test it separately with a stand-in AI).

### What got built in each phase (plain words)

- **Phase 1 — the plumbing.** Set up the project, the web server, the
  configuration, and the code that reads the insurance rulebook file. Added a
  `/health` page that says "I'm up and the rulebook loaded."
- **Phase 2 — the document gate.** The "stop early if the documents are wrong"
  check, with specific messages (wrong document / unreadable / different
  patients). Added the `POST /claims` entry point.
- **Phase 3 — the AI layer.** Plugged in the AI for reading documents and
  writing explanations, with safety nets so a failed AI call never crashes
  anything (it just lowers confidence and continues).
- **Phase 4 — the rulebook.** The deterministic decision engine: eligibility,
  exclusions, waiting periods, pre-approval, limits, fraud signals, and the
  money math. This is the brain.
- **Phase 5 — the web page.** A simple page where you pick one of the 12 test
  cases (or paste your own), click a button, and see the decision plus the full
  step-by-step logbook.
- **Phase 6 — the report card.** A script that runs all 12 test cases and writes
  a report (`docs/EVAL_REPORT.md`) showing, for each, what the system decided vs
  what was expected. Result: **12 out of 12 match.**

### How to run it (copy-paste)

```bash
cd "Plum Assignment - 12-04-2026"
uv venv .venv && uv pip install --python .venv -r requirements.txt
.venv/bin/uvicorn app.main:app --reload      # then open http://127.0.0.1:8000
.venv/bin/python -m pytest                    # run all tests
.venv/bin/python scripts/run_eval.py          # regenerate the eval report
```

---

## 1. Phase log

### Phase 1 — Skeleton (status: ✅ complete, verified)

**Scope delivered:** repository structure, FastAPI setup, LangGraph setup,
configuration system, policy loader, health-check endpoint. **No claim
processing.**

**Verification (run 2026-06-14):**
- `pytest` → **8 passed**.
- `uvicorn app.main:app` boots; `GET /health` → `status: ok`, policy
  `PLUM_GHI_2024` loaded with 6 categories and 12 members.

**Key decisions made this phase:** D1–D7 (see §6).

**Not in this phase (deferred):** claim/decision models, any graph node beyond
the `intake` placeholder, the rule engine, LLM clients, the UI.

### Phase 2 — Claim intake + document-verification gate (status: ✅ complete, verified)

**Scope delivered:** `ClaimRequest`/`Document`/`decision` models; the pure
`document_verifier` (required-docs, readability, patient-consistency checks);
the `intake` and `verify_documents` graph nodes; the **conditional early-stop
branch** (`verify_documents → {stop: END | continue: …}`); and the `POST /claims`
endpoint. Handles **TC001–TC003** (block with specific messages) and lets clean
claims (TC004) pass verification. **No LLM, no adjudication yet.**

**Verification (run 2026-06-14):**
- `pytest` → **23 passed**.
- Live `POST /claims`: TC001 → `BLOCKED`, message *"You uploaded: PRESCRIPTION,
  PRESCRIPTION. A CONSULTATION claim requires … HOSPITAL_BILL …"*, trace stops at
  the gate. TC004 → passes verification and continues down the pipeline.

**Decisions this phase:** D11 (pure verifier vs node adapter), D12 (200 + structured
blocking body, not 4xx), D13 (bind policy into nodes via `functools.partial`),
D14 (`operator.add` reducers for `trace`/`blocking_issues`), D15 (rename
`ClaimHistoryEntry.date` → `claim_date` to dodge a Py3.14 annotation shadowing bug).

**Security note:** moved a real API key out of the committable `.env.example`
into the gitignored `.env`; key should be rotated.

**Not in this phase (deferred):** LLM classify/extract/normalize/explain,
the rule engine, the UI.

### Phases 3–6 — LLM layer, rule engine, UI, eval (status: ✅ complete, verified)

**Scope delivered:**
- **P3 (LLM layer):** `app/llm/` (interface + `AnthropicLLMClient` + factory +
  prompts); `classify`, `extract`, `normalize_diagnosis`, `explain` nodes.
  Deterministic-first: declared type / inline content / template are used when
  available; the LLM runs only otherwise, with output validated and failures
  degrading gracefully (no crash).
- **P4 (rule engine):** `app/rules/` (`financials`, `normalization`, `engine`) —
  ordered deterministic rules (eligibility → exclusion → waiting → pre-auth →
  per-claim → line-items → fraud → high-value → money math), confidence scoring,
  and discount-before-co-pay computation.
- **P5 (UI):** `app/static/index.html` single-page UI + `routes_ui` (`GET /`,
  `GET /sample-claims`) to submit a claim (or load any of the 12 cases) and view
  the decision + trace.
- **P6 (eval):** `scripts/run_eval.py` → `docs/EVAL_REPORT.md`.

**Verification:**
- `pytest` → **67 passed** (offline; `USE_LLM=false`); `ruff check .` clean.
- `scripts/run_eval.py` → **12/12 cases match** every `system_must` requirement
  (message specificity, eligibility dates, confidence bounds, fraud signals,
  discount-before-co-pay), not just decision + amount.
- Live server: UI serves (HTTP 200), `/sample-claims` returns 12 cases, TC010
  decision shows discount-before-co-pay (₹4500 → ₹3600 → ₹3240); a live LLM call
  produced the member explanation (numbers unchanged — engine computed them).

### Phase 7 — Hardening, policy completeness, and the live vision demo (status: ✅ complete)

**Scope delivered:**
- **Policy completeness:** annual OPD limit (via `ytd_claims_amount`), minimum
  claim amount, and submission deadline (guarded by an optional `submission_date`)
  — all read from `policy_terms.json` (new reasons `ANNUAL_LIMIT_EXCEEDED`,
  `BELOW_MINIMUM`, `SUBMISSION_WINDOW_EXCEEDED`).
- **Composed confidence:** base − degraded − extraction-quality − ambiguity, with
  a < 0.50 gate that routes to MANUAL_REVIEW.
- **AI hardening:** `ExtractedDocument` Pydantic validation of LLM output;
  retries/backoff on the Anthropic client.
- **Live vision demo:** generated sample document images run through
  `POST /claims/upload` against real Claude vision → `docs/VISION_DEMO.md`.

**Decisions this phase:** D23 (annual-OPD cap in the financial `min`; reject when
exhausted), D24 (composed confidence + low-confidence → MANUAL_REVIEW routing),
D25 (Pydantic-validate LLM extraction; retry transient calls), D26 (keep diagnosis
normalization deterministic — the interface stays at exactly three LLM tasks).

**Decisions this phase:** D16 (LLM behind an injectable interface; fake in tests),
D17 (deterministic-first / LLM-fallback in every LLM node), D18 (deterministic
normalizer grounded in the policy vocabulary, word-boundary matching),
D19 (effective per-claim cap = max(per_claim_limit, category sub_limit) — explains
why dental ₹8000 is allowed but consultation ₹7500 is not), D20 (exclusion checked
before waiting period so obesity rejects as EXCLUDED_CONDITION, not WAITING_PERIOD),
D21 (per-claim checked on the *covered* amount, after line-item exclusions),
D22 (submission-window rule uses an optional submission date; absent ⇒ on-time, so
2024 test dates aren't falsely rejected against today).

**Bug fixed:** `hernia` alias matched "lumbar disc **hernia**tion" via substring →
wrongly triggered a waiting period on TC007. Fixed with whole-word matching.

---

## 2. Tech stack & dependencies

| Package | Role | Why this one |
|---|---|---|
| **fastapi** | HTTP framework | Async, Pydantic-native, free OpenAPI docs, dependency injection. |
| **uvicorn[standard]** | ASGI server | Standard way to run FastAPI locally and in prod. |
| **pydantic** (v2) | Data modeling + validation | Validates policy + (later) LLM output. Core to "structured & validated". |
| **pydantic-settings** | Typed settings | Env/.env → validated `Settings`; keeps `os.environ` out of the code. |
| **langgraph** | Orchestration | Graph of nodes with conditional edges + shared state → maps to the multi-agent pipeline and the early-stop branch. |
| **pytest** | Tests | Every significant component is tested (grading requirement). |
| **httpx** | Test HTTP client | Required by FastAPI's `TestClient`. |
| **ruff** | Lint/format | Fast, single-tool linting + import sorting. |

Pinned to **minimum** versions in `requirements.txt` (so it installs cleanly);
a hash-pinned lockfile is the production follow-up.

**Runtime note:** verified on CPython 3.14 via a `uv`-managed venv.

---

## 3. Configuration reference (`app/config.py`)

All settings come from environment variables (case-insensitive) or `.env`;
each maps 1:1 to a `Settings` field. Copy `.env.example` → `.env` to override.

| Env var | Field | Default | Used from |
|---|---|---|---|
| `APP_NAME` | `app_name` | `Plum Claims Processing System` | Phase 1 |
| `ENVIRONMENT` | `environment` | `development` | Phase 1 |
| `LOG_LEVEL` | `log_level` | `INFO` | Phase 1 |
| `POLICY_FILE_PATH` | `policy_file_path` | `<repo>/policy_terms.json` | Phase 1 |
| `LLM_PROVIDER` | `llm_provider` | `anthropic` | Phase 2 |
| `LLM_MODEL` | `llm_model` | `claude-sonnet-4-6` | Phase 2 |
| `LLM_TIMEOUT_SECONDS` | `llm_timeout_seconds` | `30.0` | Phase 2 |
| `LLM_MAX_ATTEMPTS` | `llm_max_attempts` | `2` | Phase 4 (retries) |
| `USE_LLM` | `use_llm` | `True` | master switch; `false` ⇒ deterministic/offline |
| `ANTHROPIC_API_KEY` | `anthropic_api_key` | `None` | Phase 2 |

`get_settings()` is `lru_cache`d → the env is read and validated exactly once
per process. Tests call `get_settings.cache_clear()` to re-read.

---

## 4. File-by-file reference

> Format: **purpose** · **why it exists** · **how it interacts**.

### Configuration & cross-cutting

- **`app/config.py`** — Typed settings (`Settings`, `get_settings()`,
  `PROJECT_ROOT`). · Single source of truth for tunables; validated at startup.
  · Read by `main.py` (startup), `routes_health.py` (via `app.state`),
  `policy_loader.py` (gets the policy path).
- **`app/logging_config.py`** — `configure_logging(level)`. · One consistent log
  format/level across all modules; idempotent (no duplicate handlers). · Called
  once by `main.py` at startup; every module uses `logging.getLogger(__name__)`.
- **`app/exceptions.py`** — `ClaimsSystemError` (base) + `PolicyLoadError`. ·
  Lets callers catch *our* errors precisely. · Raised by `loader.py`, caught by
  `main.py`.

### Domain models

- **`app/models/claim.py`** *(P2)* — input models: `ClaimRequest`, `Document`,
  `ClaimHistoryEntry`, and enums `ClaimCategory`/`DocumentType`/`DocumentQuality`.
  · The system's trust boundary; validated by FastAPI before the graph. ·
  Consumed by `routes_claims.py`, `state.py`, `document_verifier.py`.
- **`app/models/decision.py`** *(P2)* — output models: `Decision`,
  `TraceEntry`/`TraceStatus`, `BlockingIssue`/`BlockingReason`,
  `ProcessingStatus`, `ClaimProcessingResult`. · Types the trace + early-stop +
  response. · Produced by nodes, the verifier, and `routes_claims.py`.
- **`app/verification/document_verifier.py`** *(P2)* — pure checks
  (`verify_documents` → `DocumentVerificationResult`): required docs, readability,
  patient consistency. · The early-stop logic, LangGraph-free and unit-tested. ·
  Called by the `verify_documents` node.
- **`app/graph/nodes/intake.py`** *(P2)* — `intake_node`: opens the trace,
  resolves the member. · Bound to policy via `partial` in `builder.py`.
- **`app/graph/nodes/verify_documents.py`** *(P2)* — `verify_documents_node`:
  thin adapter over `document_verifier`; sets `status=BLOCKED` on failure.
- **`app/api/routes_claims.py`** *(P2/P4)* — `POST /claims`: validates body,
  invokes the graph, maps final state → `ClaimProcessingResult` (BLOCKED or
  DECIDED); 503 if policy/graph absent.
- **`app/rules/financials.py`** *(P4)* — bill-item collection + network detection
  + the `get_document_fields` (inline-or-extracted) helper, `effective_per_claim_cap`,
  and `compute_financials` (discount → co-pay → caps). · Used by the engine.
- **`app/models/extraction.py`** *(P4)* — `ExtractedDocument` (validated shape of
  LLM-extracted fields) + `extraction_completeness` (the confidence signal). ·
  Used by `llm/client.py` and the `extract` node.
- **`app/rules/normalization.py`** *(P4)* — deterministic diagnosis→policy-vocab
  mapping (word-boundary alias matching). · Used by the normalize node.
- **`app/rules/engine.py`** *(P4)* — `adjudicate()`: the ordered rules + money
  math + confidence. The brain; pure and unit-tested.
- **`app/llm/client.py`** *(P3)* — `LLMClient` interface, `AnthropicLLMClient`,
  `build_llm_client(settings)`, `LLMError`. · Injected into the LLM nodes.
- **`app/llm/prompts.py`** *(P3)* — classification/extraction/explanation prompts.
- **`app/graph/nodes/classify.py` / `extract.py` / `normalize_diagnosis.py` /
  `adjudicate.py` / `explain.py`** *(P3/P4)* — the five processing nodes; thin
  adapters over the rules/LLM modules.
- **`app/api/routes_ui.py`** *(P5)* — `GET /` (serves the SPA) + `GET
  /sample-claims` (the 12 cases for the UI).
- **`app/static/index.html`** *(P5)* — the submission + review UI (vanilla JS).
- **`scripts/run_eval.py`** *(P6)* — runs all 12 cases offline, asserts each
  case's `system_must` requirements, writes `EVAL_REPORT.md`.
- **`scripts/make_sample_docs.py`** *(P7)* — generates sample document images
  (Pillow) into `samples/` for the vision demo.
- **`scripts/run_vision_demo.py`** *(P7)* — uploads those images to
  `POST /claims/upload` with the live LLM, writes `docs/VISION_DEMO.md`.
- **`app/models/policy.py`** — Pydantic models for `policy_terms.json`
  (`Policy`, `Coverage`, `OpdCategory`, `WaitingPeriods`, `Exclusions`,
  `PreAuthorization`, `DocumentRequirement`, `FraudThresholds`, `Member`, …)
  plus lookups `get_member`, `get_category`, `document_requirement`. · Validates
  the policy and absorbs the file's casing/shape inconsistencies in one place.
  · Built by `loader.py`; consumed (later) by the rule engine.

### Policy loading

- **`app/policy/policy_loader.py`** — `load_policy(path) -> Policy`. · Isolates
  I/O + parse + validation; maps 3 failure modes to one `PolicyLoadError`. ·
  Called by `main.py`; returns a `Policy`; raises `PolicyLoadError`.

### Orchestration (LangGraph)

- **`app/graph/state.py`** — `ClaimState` (TypedDict, `total=False`). · The
  shared state every node reads/updates; `trace` is the observability backbone.
  · Used as the graph's schema in `builder.py`.
- **`app/graph/builder.py`** — `build_graph(policy, llm)`: registers the 7 nodes,
  binds `policy`/`llm` via `partial`, wires the edges + the early-stop conditional
  edge. · One place that constructs/compiles the graph. · Called by `main.py`;
  returns a compiled Runnable stored on `app.state.graph`.

### API

- **`app/api/routes_health.py`** — `GET /health` (+ `HealthResponse`,
  `PolicyStatus`). · Readiness probe that reports whether the policy loaded. ·
  Registered by `main.py`; reads `app.state.settings` / `app.state.policy`.

### Composition root

- **`app/main.py`** — `create_app()` factory + `lifespan`. · Wires logging,
  policy load, graph build, and routers; stashes shared resources on
  `app.state`. · Imports config/logging/loader/builder/routes; exposes
  module-level `app` for `uvicorn app.main:app`.

### Tests

- **`tests/conftest.py`** — `app` + `client` fixtures (`TestClient` as context
  manager so lifespan runs).
- **`tests/test_config.py`** — defaults + env override (cache-clear discipline).
- **`tests/test_policy_loader.py`** — parses the real policy; asserts numbers,
  category-specific fields, roster size, lookups; 3 failure modes raise
  `PolicyLoadError`.
- **`tests/test_health.py`** — `/health` returns ok + policy summary; graph
  compiles and runs (trace gets an `intake` entry).

### Project files

- **`requirements.txt`** — runtime + dev deps (min versions).
- **`pyproject.toml`** — tool config only (pytest, ruff). No packaging in P1.
- **`.env.example`** — template for `.env`.
- **`.gitignore`** — venv, `.env`, caches.

---

## 5. Component contracts

> Precise enough to reimplement any single component without reading its code.

### `load_policy(path: Path) -> Policy`
- **Input:** filesystem path to a policy JSON file.
- **Output:** a validated `Policy`.
- **Raises:** `PolicyLoadError` if the file is unreadable, not valid JSON, or
  does not match the schema (root cause chained via `from`).
- **Guarantees:** pure read; no mutation; logs start + summary.

### `Policy` lookups
- `get_member(member_id: str) -> Member | None` — exact id match.
- `get_category(category: str) -> OpdCategory | None` — case-insensitive
  (lowercases; file keys are lowercase).
- `document_requirement(category: str) -> DocumentRequirement | None` —
  case-insensitive (uppercases; file keys are uppercase).

### `build_graph(policy: Policy, llm: LLMClient | None = None) -> CompiledGraph`
- **Input:** the loaded `Policy` (bound into the deterministic nodes) and the
  optional `LLMClient` (bound into the AI nodes), both via `functools.partial`.
- **Output:** a compiled LangGraph with `.invoke(state) -> dict`.
- **Behavior:** `intake → classify → verify_documents → {stop: END | continue:
  extract → normalize_diagnosis → adjudicate → explain → END}`. The conditional
  edge `_after_document_verification` routes a claim with `blocking_issues` to END.

### `verify_documents(request: ClaimRequest, policy: Policy) -> DocumentVerificationResult`
- **Input:** a validated claim + the policy.
- **Output:** `DocumentVerificationResult{ passed: bool, blocking_issues:
  [BlockingIssue], trace_entries: [TraceEntry] }`. Every check emits a trace
  entry (pass or fail); all three checks (required docs / readability / patient
  consistency) run so multiple problems are reported together.
- **Raises:** nothing — verification is total.

### Graph nodes — each `(state: ClaimState, *, policy|llm) -> dict`
Every node returns only the state keys it sets; LangGraph merges them (`trace`
and `blocking_issues` concatenate via `operator.add`). None raise — AI nodes
catch `LLMError` and degrade.
- `intake(state, *, policy)` → `{member, trace}` — resolve member; open the trace.
- `classify(state, *, llm)` → `{classified_docs, trace}` — per document: trust a
  declared `actual_type`, else vision-classify (type/readability/patient written
  back onto the `Document`).
- `verify_documents(state, *, policy)` → `{trace, blocking_issues, status?}` —
  thin adapter over `document_verifier.verify_documents`; sets `status=BLOCKED`
  on any blocking issue.
- `extract(state, *, llm)` → `{extracted_content?, extraction_confidence?,
  degraded?, trace}` — use inline `content`, else `llm.extract_document`; honors
  `simulate_component_failure` by degrading (TC011).
- `normalize_diagnosis(state, *, policy)` → `{normalized_diagnosis, trace}`.
- `adjudicate(state, *, policy)` → `{adjudication_result, status=DECIDED, trace}`.
- `explain(state, *, llm)` → `{explanation, trace}`.

### `normalize_diagnosis(request, extracted_content, policy) -> DiagnosisMatch`
- **Input:** the claim, the extracted-content map, the policy.
- **Output:** `DiagnosisMatch{ raw_text, waiting_condition | None,
  excluded_condition | None }` — free text mapped to policy vocabulary via
  whole-word keyword matching (deterministic). **Raises:** nothing.

### `compute_financials(covered_base, cat, bill, policy, remaining_annual_opd) -> (float, dict)`
- **Input:** covered base amount, the `OpdCategory` (or None), `BillDetails`,
  the policy, and the remaining annual OPD allowance.
- **Output:** `(approved_amount, breakdown)`. Applies network discount FIRST,
  then co-pay, then caps at `min(after_copay, max(per_claim_limit, sub_limit),
  remaining_annual_opd)`. The breakdown dict carries every intermediate number.
- **Raises:** nothing.

### `POST /claims`
- **Input (body):** `ClaimRequest` (JSON). Documents may declare `actual_type`
  and carry pre-extracted `content`. Malformed → **422** automatically.
- **Output (200):** `ClaimProcessingResult{ claim_id, status, decision,
  approved_amount, rejection_reasons[], line_items[], confidence, degraded,
  blocking_issues[], explanation, financial_breakdown, note, trace[] }`. `status`
  is `BLOCKED` (verification stopped it) or `DECIDED`.
- **Errors:** **503** if the policy/graph is unavailable (degraded startup).

### `POST /claims/upload`
- **Input (multipart/form-data):** `files` (one or more images/PDFs) + form fields
  `member_id, policy_id, claim_category, treatment_date, claimed_amount` and the
  optionals `hospital_name, ytd_claims_amount, pre_authorization_obtained`. Each
  file's bytes are base64-attached to a `Document` with `actual_type` unset, so
  the pipeline classifies and extracts it with Claude vision.
- **Output (200):** identical `ClaimProcessingResult` shape as `POST /claims`.
- **Errors:** **422** if no non-empty file is supplied or a form field is invalid;
  **503** if the policy/graph is unavailable.

### `adjudicate(request, member, diagnosis, policy, bill, extracted_content, degraded, extraction_confidence=1.0) -> DecisionResult`
- **Input:** validated claim, resolved member (or None), `DiagnosisMatch`, policy,
  `BillDetails`, extracted-content map, degraded flag, and the average extraction
  confidence (1.0 on the inject-content path).
- **Output:** `DecisionResult{ decision, approved_amount, rejection_reasons[],
  line_items[], confidence, financial_breakdown, notes[], trace_entries[] }`.
  `rejection_reasons` ∈ {NOT_ELIGIBLE, BELOW_MINIMUM, SUBMISSION_WINDOW_EXCEEDED,
  WAITING_PERIOD, EXCLUDED_CONDITION, PRE_AUTH_MISSING, PER_CLAIM_EXCEEDED,
  ANNUAL_LIMIT_EXCEEDED}.
- **Guarantees:** pure + deterministic; every rule emits a trace entry; exclusion
  before waiting period; discount before co-pay; an otherwise-approvable claim
  with confidence < 0.50 is routed to MANUAL_REVIEW.
- **Raises:** nothing.

### `LLMClient` (interface) — `build_llm_client(settings) -> LLMClient | None`
- **Methods (the three LLM tasks):**
  - `classify_document(doc) -> DocumentClassification{document_type, readable,
    patient_name}` — vision classification + readability + patient name (feeds
    the early gate).
  - `extract_document(doc) -> dict` — vision structured extraction, **validated
    into `ExtractedDocument`** before return (a mis-typed field raises `LLMError`).
  - `generate_explanation(decision, approved_amount, reasons, fallback) -> str`.
- **Vision:** when `doc.data_base64`/`doc.media_type` are set, the call attaches an
  image or PDF content block so Claude reads the real document; otherwise it falls
  back to a filename-only prompt.
- **Resilience:** the Anthropic client retries up to `llm_max_attempts` times with
  backoff on transient failures before raising.
- **Raises:** `LLMError` on any provider/parse/validation failure (callers degrade,
  never crash).
- **Factory:** returns `None` when `use_llm` is false or no API key (offline mode).

### `GET /sample-claims`
- **Output (200):** list of `{case_id, case_name, input}` read from the read-only
  `test_cases.json` (powers the UI dropdown).

### `GET /` (UI)
- **Output (200):** the single-page submission + review UI (`app/static/index.html`).

### `GET /health`
- **Input:** none.
- **Output (200):** `{ status, app_name, environment, policy:{ loaded,
  policy_id, categories, members } }`. `status` is `ok` if the policy loaded,
  else `degraded`.

---

## 6. Decision log

| ID | Decision | Rationale | Alternative rejected |
|---|---|---|---|
| D1 | LLMs for perception/communication only; decisions are deterministic | Reproducible, testable, auditable; matches the brief | LLM-makes-decision (non-deterministic, unauditable) |
| D2 | LangGraph for orchestration | Conditional early-stop edge + shared trace + multi-agent framing (bonus) | Plain function chain (hides routing/observability) |
| D3 | Single `Policy` Pydantic tree from the file | "Don't hardcode policy"; validate once; typed access | Reading raw dicts everywhere |
| D4 | `TypedDict` for graph state, Pydantic for domain models | TypedDict is LangGraph's idiom for partial/incremental state; Pydantic gives validation where it matters | All-Pydantic state (awkward partial updates) |
| D5 | Policy load failure → DEGRADED, not crash | Graceful failure + observability are graded; `/health` reports it | Fail-fast exit (less observable) |
| D6 | Point config at the provided repo-root `policy_terms.json` | Single source of truth; no copy to drift | Copy into `data/` (duplication) |
| D7 | LLM provider = Anthropic Claude (`claude-sonnet-4-6`), configurable | Vision-capable for handwritten docs; strong default | Hardcoding a provider; unset until Phase 2 |
| D11 | Pure `document_verifier` + thin node adapter | Rules unit-testable without LangGraph; node is trivial | Verification logic inside the node (untestable in isolation) |
| D12 | Blocked claim → **200** + structured `blocking_issues` | It's a valid business outcome the UI renders, not a server/client error | 4xx (conflates with transport errors; awkward for the UI) |
| D13 | Bind `policy` into nodes via `functools.partial` | Nodes keep the clean `(state)->dict` signature; policy loaded once | Putting the whole policy into graph state (bloated state) |
| D14 | `operator.add` reducers for `trace`/`blocking_issues` | Nodes return only their new entries; correct if nodes parallelize | Read-modify-write the whole list in every node |
| D15 | Rename `ClaimHistoryEntry.date` → `claim_date` (alias `date`) | A field named after its type shadows it during Py3.14 annotation eval | Keep `date` (crashes on model build) |
| D16 | LLM behind an injectable `LLMClient` interface; fake in tests | LLM paths are tested offline, no network/key | Calling Anthropic directly in nodes (untestable, flaky) |
| D17 | Deterministic-first in every LLM node (bypass when data present) | Reproducible eval + no needless cost; LLM is the fallback | Always call the LLM (non-deterministic, costly) |
| D18 | Deterministic normalizer grounded in policy vocabulary, word-boundary match | Decisions stay reproducible; avoids substring false-positives | LLM-only normalization (non-deterministic) |
| D19 | Effective per-claim cap = max(per_claim_limit, category sub_limit) | Explains dental ₹8000 allowed yet consultation ₹7500 rejected (matches expected) | Flat ₹5000 for all (would wrongly reject dental TC006) |
| D20 | Check exclusion BEFORE waiting period | Obesity rejects as EXCLUDED_CONDITION not WAITING_PERIOD (TC012 expects the former) | Waiting first (wrong reason code) |
| D21 | Per-claim limit applied to the *covered* amount (post line-item exclusion) | Dental TC006 covered ₹8000 ≤ cap; only excluded line dropped | Apply to claimed total (would reject TC006) |
| D22 | Submission-window uses optional submission date; absent ⇒ on-time | The 2024 treatment dates aren't falsely rejected against today (2026) | Check vs today (rejects every test case) |
| D23 | Annual OPD limit caps the payout (`annual_opd_limit − ytd_claims_amount`); reject when exhausted | Applies a real policy rule that was modeled but unused; guarded so the 12 cases are unaffected | Ignoring the annual limit (approves claims the policy wouldn't) |
| D24 | Composed confidence (base − degraded − extraction-quality − ambiguity) + low-confidence (<0.50) → MANUAL_REVIEW | Confidence reflects real uncertainty and routes accordingly; matches the documented model | Flat `0.95 − 0.30·degraded` (doesn't reflect extraction quality) |
| D25 | Pydantic-validate LLM extraction; retry transient Anthropic calls | Contains hallucinated/mis-typed fields; survives a flaky call | Trusting raw LLM JSON; single-attempt calls |
| D26 | Keep diagnosis normalization deterministic (no 4th LLM method) | Reproducible decisions; the LLM interface stays at exactly three tasks | An LLM normalize method (non-deterministic; widens the interface) |

---

## 7. Risk register

| # | Risk | Mitigation |
|---|---|---|
| R1 | Inconsistent policy key casing | Normalized lookups in `Policy` (tested). |
| R2 | Per-category shape differences | One `OpdCategory`, category-specific fields optional. |
| R3 | LLM hallucination → bad decision | LLMs never decide; output Pydantic-validated. |
| R4 | LLM/timeout crashes pipeline (TC011) | Per-node try/except → trace + degrade, never 500. |
| R5 | Diagnosis text ≠ policy keys | `normalize_diagnosis` (deterministic, word-boundary); unmapped → no key, coverage still decided by category. |
| R6 | Non-deterministic eval | Inject test `content`; engine is pure. |
| R7 | Policy missing/corrupt | `PolicyLoadError` + `/health` degraded. |
| R8 | Concurrent trace mutation | Phase 2 uses `Annotated[list, add]` reducer. |

---

## 8. Test-case routing map (target system)

| TC | Stops/decides at | Mechanism | Expected |
|---|---|---|---|
| TC001 | verify→halt | required docs incomplete (2× prescription) | stop; name uploaded vs required type |
| TC002 | verify→halt | quality=UNREADABLE | stop; ask re-upload that file |
| TC003 | verify→halt | patient-name mismatch | stop; surface both names |
| TC004 | adjudicate | 10% co-pay on ₹1500 | APPROVED ₹1350, conf >0.85 |
| TC005 | adjudicate | diabetes 90-day waiting | REJECTED + eligible date |
| TC006 | adjudicate | line-item exclusion | PARTIAL ₹8000 + per-line reasons |
| TC007 | adjudicate | MRI>₹10k needs pre-auth | REJECTED PRE_AUTH_MISSING |
| TC008 | adjudicate | ₹7500 > ₹5000 | REJECTED PER_CLAIM_EXCEEDED |
| TC009 | adjudicate | 4 same-day > limit 2 | MANUAL_REVIEW + signals |
| TC010 | adjudicate | 20% discount then 10% co-pay | APPROVED ₹3240 + breakdown |
| TC011 | adjudicate (degraded) | simulate node failure | APPROVED, degraded note, no 500 |
| TC012 | adjudicate | obesity ∈ exclusions | REJECTED EXCLUDED_CONDITION, conf >0.90 |

---

## 9. How to run

```bash
cd "Plum Assignment - 12-04-2026"

# Option A — uv (used to verify this build)
uv venv .venv
uv pip install --python .venv -r requirements.txt

# Option B — stdlib venv + pip
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# Run the server
.venv/bin/uvicorn app.main:app --reload
# → http://127.0.0.1:8000/health   and   /docs (Swagger UI)

# Run the tests
.venv/bin/python -m pytest
```
