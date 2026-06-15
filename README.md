# Health Insurance Claims Processing System

An automated, explainable pipeline that takes a health-insurance claim plus its
documents, **catches document problems before any processing**, extracts the
data, **decides deterministically against the member's policy**, and returns the
decision with a **full step-by-step trace**.

> **Eval result: 12/12 test cases match the expected outcome** (run offline and
> deterministic). See [`docs/EVAL_REPORT.md`](docs/EVAL_REPORT.md).

This is my submission for the Plum AI Engineer assignment. The full problem
statement is in [`assignment.md`](assignment.md). Maintained by Priya Chau.

---

## Core idea

**LLMs do perception and communication. Deterministic code does cognition (the
decision).**

| Stage | Owner | Examples |
|---|---|---|
| **Perception** (messy → structured) | LLM | classify document type, extract fields, normalize `"Type 2 Diabetes Mellitus"` → `diabetes` |
| **Cognition** (structured → decision) | Deterministic rule engine | waiting periods, exclusions, pre-auth, limits, co-pay math, fraud |
| **Communication** (decision → human) | LLM | member-facing explanation generated *from the trace* |

The LLM **never decides**. Every LLM output is validated by a Pydantic schema
before the rule engine touches it, so the same validated input always produces
the same decision and the same trace — reproducible and auditable.

Why this matters: it makes decisions reproducible (System Design + Observability
are 50% of the grade), contains hallucination (a wrong extracted field still
goes through the same rules and lowers confidence), and keeps the 12-case eval
deterministic.

---

## The pipeline

The claim flows through a [LangGraph](https://langchain-ai.github.io/langgraph/)
graph of single-responsibility nodes (each a small "agent"). A conditional edge
at the verification gate is what lets bad-document claims **stop early**:

```
POST /claims  (JSON)   or   POST /claims/upload  (multipart: real images/PDFs)
  └─ intake        validate request, resolve member + policy, start the trace
  └─ classify (LLM vision)  on a real upload: read the image/PDF to identify the
                            document type, judge readability, and read the patient
                            name; on the JSON path the declared type is trusted
  └─ verify         required docs present? readable? same patient?
        ├─ blocking issue ─▶ halt ─▶ respond   (extract/adjudicate never run)
        └─ ok ─▶
  └─ extract (LLM vision)  read structured fields from each document image/PDF
                           (or use the pre-extracted `content` on the JSON path)
  └─ normalize      map free-text diagnosis → canonical policy key
  └─ adjudicate     ordered, pure rule engine → decision + amount + confidence
  └─ explain (LLM)  member-facing explanation generated from the trace
  └─ respond        assemble the final ClaimDecision + full trace
```

The **classify** and **extract** steps send the actual file bytes (base64 image
or PDF blocks) to Claude, so handwritten prescriptions, stamped bills, and phone
photos are read for real. The early-stop gate runs *after classify but before
extract*, so a wrong/unreadable/mismatched document is caught before the
expensive full extraction. The JSON path keeps a deterministic bypass (declared
type + injected `content`) that keeps the 12-case eval reproducible and offline.

Every node appends a structured entry to a single `trace` list, and the trace is
embedded in the response — so any decision is reconstructable step-by-step
without reading code. Any node failure becomes a `failed` trace entry plus a
confidence penalty (the claim degrades, it never returns a 500).

A detailed walk-through of the happy path, the early-stop path, the degraded
path, the rule engine, and the financial computation order is in
[`docs/architecture.md`](docs/architecture.md).

---

## Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| Web framework | FastAPI + Pydantic v2 |
| Server | uvicorn |
| Orchestration | LangGraph |
| LLM | Anthropic Claude (`claude-sonnet-4-6`, configurable; vision-capable) |
| Tests / lint | pytest + httpx, ruff |

---

## Quickstart

### 1. Set up the environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
```

The system runs **fully offline and deterministic** without any API key — the
LLM nodes fall back to deterministic behavior and the 12 test cases pass as-is.
To enable live LLM document understanding, set `ANTHROPIC_API_KEY` in `.env`
(keep `USE_LLM=true`). To force offline mode, set `USE_LLM=false`.

> `.env` is gitignored — never commit it.

### 3. Run the app

```bash
uvicorn app.main:app --reload
```

Then open **http://127.0.0.1:8000/** for the UI, or the auto-generated API docs
at **http://127.0.0.1:8000/docs**.

---

## Using the system

### UI

The page at `/` has two modes:

- **Upload documents** (default) — fill in the claim details, drag-and-drop one
  or more images/PDFs, and submit. The files are sent to `/claims/upload`, where
  Claude vision classifies and reads them. (Needs `ANTHROPIC_API_KEY`; without a
  key, an uploaded file can't be classified and the gate stops the claim with a
  specific message.)
- **JSON (advanced)** — paste a claim JSON, or load any of the 12 provided test
  cases as one-click examples (from `/sample-claims`). This is the deterministic
  path used by the eval.

Try a blocked case (TC001) to see the specific, actionable error message, and an
approved case (TC004/TC010) to see the full trace and financial breakdown.

### API endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/claims` | Submit a claim as **JSON** (documents may carry pre-extracted `content`); returns the decision (or blocking issues) + full trace |
| `POST` | `/claims/upload` | Submit a claim with **real uploaded files** (`multipart/form-data`, images/PDFs). The type is *not* supplied — the pipeline classifies and extracts each file with Claude vision |
| `GET` | `/health` | Readiness probe — reports `degraded` if the policy failed to load |
| `GET` | `/sample-claims` | The 12 test cases, for the UI dropdown |
| `GET` | `/` | The single-page UI |

`POST /claims` returns `BLOCKED` (with specific `blocking_issues`) when document
verification stops the claim, or `DECIDED` (with `decision`, `approved_amount`,
`rejection_reasons`, `confidence`, `explanation`, and `financial_breakdown`)
otherwise. A claim that fails request validation returns `422`; if the policy
isn't loaded the endpoint returns `503` rather than deciding without a policy.

---

## Tests

```bash
pytest
```

Covers the policy loader, claim models, rule engine, diagnosis matcher, document
checks, LLM nodes (with fakes), the full pipeline, and the API endpoints.

## Eval report

Regenerate the eval over all 12 test cases (runs offline, deterministic):

```bash
.venv/bin/python scripts/run_eval.py
```

This writes [`docs/EVAL_REPORT.md`](docs/EVAL_REPORT.md) — currently **12/12
matching** the expected outcomes, with each case's full decision output.

---

## Project structure

```
.
├── app/
│   ├── main.py            # FastAPI factory + lifespan (loads policy + graph once)
│   ├── config.py          # typed settings from env / .env
│   ├── api/               # /claims, /health, UI routes
│   ├── graph/             # LangGraph state, builder, and one file per node
│   ├── rules/             # deterministic rule engine (decision logic)
│   ├── llm/               # LLM client + prompts (perception + communication)
│   ├── models/            # Pydantic models: policy, claim, decision/trace
│   ├── policy/            # policy_terms.json loader
│   ├── verification/      # early document checks
│   └── static/            # single-page UI
├── tests/                 # pytest suite
├── scripts/run_eval.py    # generates docs/EVAL_REPORT.md
├── docs/
│   ├── architecture.md            # design: components, decisions, trade-offs, scaling
│   ├── TECHNICAL_DOCUMENTATION.md # file-by-file reference + component contracts
│   └── EVAL_REPORT.md             # all 12 test cases with full traces
├── policy_terms.json      # policy config, coverage rules, member roster (read at runtime)
├── test_cases.json        # 12 test scenarios with expected outcomes
├── assignment.md          # the assignment brief
├── sample_documents_guide.md  # Indian medical document formats reference
├── requirements.txt  pyproject.toml  .env.example  .gitignore
```

---

## Documentation

- **[`docs/architecture.md`](docs/architecture.md)** — the *why* and the *shape*:
  problem, approach, high-level architecture, the rule engine, financial
  computation order, confidence scoring, observability, failure handling,
  decision log, risk register, scaling to 10×, and per-test-case routing.
- **[`docs/TECHNICAL_DOCUMENTATION.md`](docs/TECHNICAL_DOCUMENTATION.md)** — the
  *what's in each file*: file-by-file reference and component contracts (inputs,
  outputs, and errors for every significant component).
- **[`docs/EVAL_REPORT.md`](docs/EVAL_REPORT.md)** — the eval results.

---

## Key trade-offs

- **Deterministic decisions, LLM perception only** — chosen for auditability and
  a reproducible eval; the cost is that diagnosis/field normalization must map
  onto policy keys, and unmapped cases route to `MANUAL_REVIEW`.
- **Single `policy_terms.json` loaded at startup** — no hardcoded policy logic
  and one source of truth; at scale this becomes a versioned policy store keyed
  by `policy_id`.
- **Degrade, don't crash** — a failed node or an unloadable policy is reported
  (`/health` degraded, confidence penalty, trace entry) rather than crashing.
- **Two input paths, one pipeline** — real uploads (`/claims/upload`) are read by
  Claude vision; the JSON path (`/claims`) accepts pre-extracted `content` and a
  declared type. The injected-`content` bypass is what keeps the 12-case eval
  deterministic and offline, while the upload path exercises the real
  classify/extract vision calls.

Full reasoning, rejected alternatives, and the 10× scaling plan are in
[`docs/architecture.md`](docs/architecture.md).
