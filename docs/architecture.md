# Architecture — Health Insurance Claims Processing System

> **Status:** living document, updated every phase. **Phase 1 baseline.**
> **Scope:** this is the master design document — problem, approach, decisions,
> tech stack, pipeline, flow, rule engine, observability, failure handling,
> scaling, risks, and the 12 test-case flows.
> **Companion:** [`TECHNICAL_DOCUMENTATION.md`](./TECHNICAL_DOCUMENTATION.md)
> is the file-by-file / phase-by-phase reference. This file is the *why* and
> the *shape*; that file is the *what's-in-each-file*.
>
> **Base files (never modified):** `assignment.md`, `policy_terms.json`,
> `README.md`, `sample_documents_guide.md`, `test_cases.json`. The system reads
> `policy_terms.json` at runtime; it is treated as read-only input.

---

## Table of contents

1. [Problem](#1-problem)
2. [Goals & non-negotiables](#2-goals--non-negotiables)
3. [Approach & guiding principles](#3-approach--guiding-principles)
4. [High-level architecture](#4-high-level-architecture)
5. [Tech stack & rationale](#5-tech-stack--rationale)
6. [The pipeline (nodes)](#6-the-pipeline-nodes)
7. [End-to-end flow](#7-end-to-end-flow)
8. [The deterministic rule engine](#8-the-deterministic-rule-engine)
9. [Financial computation order](#9-financial-computation-order)
10. [Confidence scoring](#10-confidence-scoring)
11. [Data model](#11-data-model)
12. [Observability & the trace](#12-observability--the-trace)
13. [Failure handling & graceful degradation](#13-failure-handling--graceful-degradation)
14. [Decision log](#14-decision-log)
15. [Risk register](#15-risk-register)
16. [Test-case routing map](#16-test-case-routing-map)
17. [Folder structure](#17-folder-structure)
18. [Scaling to 10x](#18-scaling-to-10x)
19. [Security & data handling](#19-security--data-handling)
20. [Phase roadmap & status](#20-phase-roadmap--status)
21. [Assumptions & open questions](#21-assumptions--open-questions)

---

## 1. Problem

When an employee submits a health-insurance claim, they upload medical
documents (bills, prescriptions, lab reports) plus basic details. Today a human
reviews those documents against the member's policy and decides to **approve,
partially approve, or reject**. This is slow, inconsistent, and doesn't scale.

We automate it: accept a submission + documents, **catch document problems
early**, extract structured data, **decide deterministically against the
policy**, and make **every decision explainable** and **resilient to component
failure**.

Output decision is one of: `APPROVED`, `PARTIAL`, `REJECTED`, `MANUAL_REVIEW`,
each with approved amount (if any), reason(s), and a confidence score.

---

## 2. Goals & non-negotiables

Derived from the assignment and mapped to the grading weights:

| Behavior (non-negotiable) | Maps to grade | How we satisfy it |
|---|---|---|
| Accept a claim submission | Engineering | FastAPI endpoint + Pydantic request model. |
| Catch document problems **early**, with **specific** messages | Document Verification (10%) | Deterministic `verify` gate that halts before any decision with an actionable, named message. |
| Extract structured info from messy docs | AI Integration (15%) | LLM `extract` node, output Pydantic-validated. |
| Make a deterministic claim decision | System Design (30%) | Pure, ordered **rule engine** (`adjudicate`). |
| Make every decision explainable | Observability (20%) | A single `trace` accumulated through the graph; embedded in the response. |
| Handle failures gracefully (no crash) | System Design / Engineering | Per-node try/except → trace + degrade confidence, never 500. |
| UI for submission and review | Engineering | Built in a later phase. |

**Hard constraint:** *policy decisions must be deterministic*; LLMs are used
**only** for classification, extraction, diagnosis normalization, and
explanation generation.

---

## 3. Approach & guiding principles

### 3.1 The spine: separate perception, cognition, and communication

> **LLMs do perception and communication. Deterministic code does cognition
> (the decision).**

| Stage | Owner | Examples |
|---|---|---|
| **Perception** (messy → structured) | LLM | classify document type, extract fields, normalize `"Type 2 Diabetes Mellitus"` → `diabetes` |
| **Cognition** (structured → decision) | Deterministic rule engine | waiting periods, exclusions, pre-auth, limits, co-pay math, fraud |
| **Communication** (decision → human) | LLM | member-facing explanation generated *from the trace* |

The LLM **never decides**. Every LLM output is validated by a Pydantic schema
before the engine touches it. Same validated input → same decision, always.

### 3.2 Why this split is the right call

- **Reproducibility & auditability** (30% + 20% of grade): a pure function is
  unit-testable and produces an identical trace every run.
- **Containment of hallucination** (15%): if the model guesses a wrong field,
  the engine still applies the same rules to validated data, and low extraction
  confidence flows into the final confidence score.
- **Testability of the eval**: `test_cases.json` injects pre-extracted
  `content`, so we exercise the engine without depending on live OCR/vision
  output — the 12 cases are deterministic.

### 3.3 Secondary principles

- **Simplicity over abstraction.** No layer is added without a concrete reason.
  One `OpdCategory` model, not six; one error type for policy load, not three.
- **Fail soft, report loudly.** A degraded component lowers confidence and is
  visible in the trace; the pipeline still returns a decision.
- **One source of truth for rules.** Everything comes from `policy_terms.json`;
  no policy constant is hardcoded.
- **Multi-agent framing.** Each node is a single-responsibility "agent"
  (classifier, verifier, adjudicator, explainer) — the brief awards bonus points
  for multi-agentic architectures.

---

## 4. High-level architecture

```
                 ┌──────────────────────────────────────────────────────────┐
   Browser UI    │                      FastAPI app                          │
  (submit /      │                                                           │
   review)  ───▶ │  POST /claims ─┐                          GET /health     │
                 │                │                               │          │
                 │                ▼                               ▼          │
                 │        ┌───────────────┐               app.state.policy   │
                 │        │  LangGraph     │               app.state.graph    │
                 │        │  (pipeline)    │◀── reads ── app.state.settings   │
                 │        └───────┬────────┘                                  │
                 │                │ uses                                      │
                 │   ┌────────────┼─────────────┐                            │
                 │   ▼            ▼              ▼                            │
                 │ LLM client  Rule engine   Policy models                   │
                 │ (perception) (cognition)  (typed policy)                  │
                 └──────────────────────────────────────────────────────────┘
                                  │ loads once at startup
                                  ▼
                          policy_terms.json  (read-only base file)
```

**Composition root** = `app/main.py`. At startup (`lifespan`) it: configures
logging, **loads the policy once**, **builds the graph once**, and stashes
both plus settings on `app.state`. Request handlers never re-load these.

**Request lifecycle (target):** `POST /claims` → validate request → `graph.invoke(state)` → graph runs nodes → returns a `ClaimDecision` (decision + amount + reasons + confidence + full trace) → JSON response. `GET /health` reports readiness including whether the policy loaded.

---

## 5. Tech stack & rationale

| Layer | Choice | Why | Rejected alternative |
|---|---|---|---|
| Language | Python 3.11+ | LLM/ML ecosystem; team familiarity. | — |
| Web framework | **FastAPI** | Async, Pydantic-native validation, auto OpenAPI/Swagger, DI. | Flask (no native async/validation), Django (too heavy). |
| Server | **uvicorn[standard]** | Standard ASGI server; uvloop/httptools for speed. | gunicorn-only (no ASGI). |
| Modeling/validation | **Pydantic v2** | Validates policy + LLM output; types everywhere. | dataclasses (no validation), raw dicts. |
| Settings | **pydantic-settings** | Typed env/.env config validated at startup. | hand-rolled `os.environ`. |
| Orchestration | **LangGraph** | Graph of nodes + shared state + conditional edges → early-stop branch + multi-agent framing + a single trace channel. | Plain function chain (routing/observability buried), Celery (wrong granularity). |
| LLM provider | **Anthropic Claude** (`claude-sonnet-4-6`, configurable) | Vision-capable for handwritten docs; strong structured output. | Hardcoding any provider; leaving it unset. |
| Tests | **pytest** + **httpx** | Standard; httpx drives `TestClient`. | unittest (more boilerplate). |
| Lint/format | **ruff** | One fast tool for lint + import sort + format. | flake8 + isort + black (three tools). |

Dependencies are pinned to **minimum** versions in `requirements.txt` for clean
installs; a hash-pinned lockfile is the production hardening step.

---

## 6. The pipeline (nodes)

Each node is a single-responsibility step. `(det)` = deterministic, `(LLM)` =
model call with a deterministic bypass when test `content` is injected and a
graceful-failure wrapper.

| # | Node | Type | Input | Output | On failure |
|---|---|---|---|---|---|
| 1 | `intake` | det | raw request | validated claim, resolved member + policy, trace initialized | invalid request → 422 before graph |
| 2 | `classify` | LLM | each document | `{file_id, type, confidence}` | fall back to provided `actual_type` |
| 3 | `verify` | det | docs + types + quality + patient names | pass, or **blocking issues** | n/a (pure) |
| — | `halt` | det | blocking issues | specific, actionable member message | n/a |
| 4 | `extract` | LLM | each document | structured `content` per type | use injected `content`; else flag fields LOW |
| 5 | `normalize_dx` | LLM | free-text diagnosis | canonical policy key (e.g. `diabetes`) | unmapped → flag → MANUAL_REVIEW |
| 6 | `adjudicate` | det | claim + policy + normalized data | decision + amount + per-line reasons + confidence | runs on whatever data exists |
| 7 | `explain` | LLM | the trace + decision | member-facing explanation string | template fallback from trace |
| 8 | `respond` | det | full state | `ClaimDecision` payload | n/a |

The **early-stop gate** is node 3 (`verify`): a conditional edge routes blocking
issues to `halt` (which builds the specific message and ends), otherwise to
`extract`. This is what makes TC001–TC003 stop *before* any decision.

---

## 7. End-to-end flow

### 7.1 Happy path (e.g. TC004 — clean consultation)

```
POST /claims
  └─ intake      ✓ member EMP001 found, policy active, trace started
  └─ classify    ✓ PRESCRIPTION + HOSPITAL_BILL  (or use provided types)
  └─ verify      ✓ required docs present, readable, same patient
  └─ extract     ✓ fields (or use injected content)
  └─ normalize   ✓ "Viral Fever" → no waiting/exclusion key
  └─ adjudicate  ✓ covered; 10% co-pay on ₹1500 = ₹150
  └─ explain     ✓ "Approved ₹1350 after 10% consultation co-pay…"
  └─ respond     → { decision: APPROVED, approved_amount: 1350,
                     confidence: 0.9x, trace: [...8 entries...] }
```

### 7.2 Early-stop path (e.g. TC001 — wrong document)

```
POST /claims
  └─ intake      ✓
  └─ classify    ✓ two PRESCRIPTIONs
  └─ verify      ✗ BLOCKING: CONSULTATION requires [PRESCRIPTION, HOSPITAL_BILL];
                   got 2× PRESCRIPTION, missing HOSPITAL_BILL
  └─ halt        → message: "You uploaded a PRESCRIPTION where a HOSPITAL_BILL
                   is required for a consultation claim. Please upload the
                   hospital bill and resubmit."
  └─ respond     → { decision: null, blocking_issue: {...}, trace: [...] }
       (extract / adjudicate / explain are never reached)
```

### 7.3 Degraded path (e.g. TC011 — component failure)

```
POST /claims
  └─ intake      ✓
  └─ classify    ✓
  └─ verify      ✓
  └─ extract     ⚠ simulate_component_failure → node raises, caught:
                   trace entry status=failed, degraded=true, confidence penalty
  └─ normalize   ✓ (runs on whatever was extracted)
  └─ adjudicate  ✓ produces a decision from available data
  └─ explain     ✓ + "manual review recommended due to incomplete processing"
  └─ respond     → { decision: APPROVED, confidence: <normal,
                     degraded: true, notes: "...component X skipped..." }
```

No node failure becomes a 500; it becomes a trace entry plus a confidence
penalty.

---

## 8. The deterministic rule engine

`adjudicate` runs an **ordered list of pure rule functions**, each
`(claim, policy) -> RuleResult` where `RuleResult` carries a verdict, a reason
code, a human reason, and a trace entry. Ordering encodes precedence.

| Order | Rule | Reads from policy | Verdict on hit | Test |
|---|---|---|---|---|
| 1 | **Eligibility** | `members`, `policy_holder` | REJECT (not eligible) | — |
| 2 | **Submission window / min amount** | `submission_rules` | REJECT | — |
| 3 | **Waiting periods** | `waiting_periods` (+ `normalize_dx`) | REJECT | TC005 |
| 4 | **Exclusions** (whole claim) | `exclusions.conditions` | REJECT | TC012 |
| 4b | **Exclusions** (line-item) | category `excluded_procedures/items` | PARTIAL | TC006 |
| 5 | **Pre-authorization** | `pre_authorization`, category thresholds | REJECT | TC007 |
| 6 | **Limits** (per-claim, sub-limit, annual OPD) | `coverage`, category `sub_limit` | REJECT or cap | TC008 |
| 7 | **Fraud signals** | `fraud_thresholds`, `claims_history` | MANUAL_REVIEW | TC009 |
| 8 | **High-value auto review** | `fraud_thresholds.auto_manual_review_above` | MANUAL_REVIEW | — |
| 9 | **Financial computation** | category `network_discount_percent`, `copay_percent` | compute approved amount | TC004, TC010 |

**Decision precedence** (when multiple fire): hard **REJECT** >
**MANUAL_REVIEW** > **PARTIAL** > **APPROVED**. A waiting-period or exclusion
rejection always wins over a fraud flag, etc. Each rule appends its trace entry
regardless of whether it changed the outcome, so the trace shows *everything
that was checked*, not just the deciding rule.

---

## 9. Financial computation order

TC010 makes the order explicit and gradeable:

```
covered_base                         = sum of covered line items
after_network_discount               = covered_base × (1 − network_discount%)   ← FIRST
after_copay                          = after_network_discount × (1 − copay%)     ← SECOND
approved_amount                      = min(after_copay, sub_limit, per_claim_limit,
                                           remaining_annual_opd_limit)            ← caps last
```

Worked example (TC010, Apollo network, consultation):
`4500 → ×0.80 = 3600 (discount) → ×0.90 = 3240 (co-pay) → within limits → ₹3240`.

Worked example (TC004, non-network consultation): `1500 → no discount →
×0.90 = 1350 → ₹1350`.

The breakdown (each multiplier and cap) is written to the trace so the
`explain` node and the reviewer can see exactly how the number was reached.

---

## 10. Confidence scoring

A single confidence in `[0, 1]` attached to every decision, composed
deterministically from:

- **Decision determinism** — pure-rule rejections (waiting period, exclusion,
  per-claim limit) are near-certain (≈0.95+); TC012 expects > 0.90, TC004 > 0.85.
- **Extraction quality** — average field-extraction confidence from the
  `extract`/`classify` nodes drags the score down when documents were poor.
- **Degradation penalty** — any failed/skipped node applies a fixed penalty and
  forces a "manual review recommended" note (TC011).
- **Ambiguity penalty** — unmapped diagnosis or conflicting fields lower it.

Confidence is *informational + routing*: very low confidence on an otherwise
APPROVED claim can itself route to MANUAL_REVIEW. The exact formula lives in the
rule engine (a later phase) and is unit-tested against the expected bounds.

---

## 11. Data model

**Phase 1 (built):** `app/models/policy.py` — a validated Pydantic tree mirroring
`policy_terms.json`, plus normalized lookups (`get_member`, `get_category`,
`document_requirement`) that absorb the file's casing inconsistencies in one
tested place.

**Phase 2 (built):**
- `claim.py` — `ClaimRequest` (member_id, policy_id, category, treatment_date,
  claimed_amount, optional hospital_name / ytd_claims_amount / claims_history,
  documents[]) and `Document` (file_id, actual_type, optional quality / content /
  patient_name_on_doc) — modeled to accept exactly what `test_cases.json`
  provides. Enums for category / document type / quality.
- `decision.py` — `Decision` enum, `TraceEntry`/`TraceStatus`,
  `BlockingIssue`/`BlockingReason`, `ProcessingStatus`, and
  `ClaimProcessingResult` (the `POST /claims` response). `Decision` is defined
  but returned as `None` until the rule engine lands.

**Later phases:** extend `decision.py` with the adjudicated fields
(approved_amount, reasons[], line_items[], confidence, degraded).

Casing reality absorbed by the model layer: `opd_categories` keys are
**lowercase**, `document_requirements` keys and claim categories are
**UPPERCASE** — the lookups normalize both.

---

## 12. Observability & the trace

Observability is 20% of the grade and the design centers on one idea: **a single
`trace` list flows through the graph; every node appends a structured entry.**
The final `ClaimDecision` embeds the full trace, so any decision is
reconstructable step-by-step without reading code.

Planned `TraceEntry` shape:

```json
{
  "step": "adjudicate.waiting_period",
  "status": "ok | failed | blocked | skipped",
  "detail": "diabetes waiting period 90d; member joined 2024-09-01; "
            "eligible from 2024-11-30; treatment 2024-10-15 is within period",
  "data": { "rule": "waiting_period", "verdict": "REJECT" }
}
```

Concurrency note: with a single Phase-1 node, plain assignment to `trace` is
safe. When nodes run in parallel (later), `trace` becomes
`Annotated[list[dict], operator.add]` so LangGraph **concatenates** updates
instead of overwriting (risk R8).

---

## 13. Failure handling & graceful degradation

Two distinct failure surfaces:

1. **Startup (policy load).** If `policy_terms.json` can't be read/parsed/
   validated, `load_policy` raises `PolicyLoadError`. `main.py` catches it,
   sets `app.state.policy = None`, logs an error, and the app starts in
   **DEGRADED** mode — `GET /health` reports `status: degraded`. The claims
   endpoint (later) refuses to decide without a policy and returns a clear
   error. *Rationale (D5):* a process that can report why it's unhealthy beats
   one that exits silently; graceful failure + observability are graded.

2. **Per-request (node failure).** Each LLM/IO node is wrapped: on exception it
   writes a `status: failed` trace entry, sets a degraded flag, applies a
   confidence penalty, and the pipeline continues. The rule engine adjudicates
   on whatever validated data exists. **No node failure becomes a 500** (TC011).

---

## 14. Decision log

| ID | Decision | Rationale | Alternative rejected |
|---|---|---|---|
| D1 | LLMs for perception/communication only; decisions deterministic | Reproducible, testable, auditable; matches the brief | LLM-makes-decision (non-deterministic, unauditable) |
| D2 | LangGraph for orchestration | Conditional early-stop edge + shared trace + multi-agent framing (bonus) | Plain function chain (hides routing/observability) |
| D3 | Single `Policy` Pydantic tree from the file | "Don't hardcode policy"; validate once; typed access | Reading raw dicts everywhere |
| D4 | `TypedDict` for graph state, Pydantic for domain models | TypedDict is LangGraph's idiom for partial/incremental state; Pydantic validates where it matters | All-Pydantic state (awkward partial updates) |
| D5 | Policy load failure → DEGRADED, not crash | Graceful failure + observability are graded; `/health` reports it | Fail-fast exit (less observable) |
| D6 | Point config at the provided repo-root `policy_terms.json` | Single source of truth; no copy to drift; base file untouched | Copy into `data/` (duplication, drift) |
| D7 | LLM provider = Anthropic Claude (`claude-sonnet-4-6`), configurable | Vision-capable for handwritten docs; strong default | Hardcoding a provider; unset until needed |
| D8 | One `OpdCategory` model with optional category-specific fields | Six categories share most fields; one model is simpler to explain | Discriminated union of six models (more code) |
| D9 | Inject test `content`, bypass `extract` when present | Makes the 12-case eval deterministic | Always call the LLM (flaky eval) |
| D10 | Rules are ordered pure functions with explicit precedence | Auditable; every check is traced even when not deciding | One big `if/else` (opaque, untestable) |

---

## 15. Risk register

| # | Risk | Mitigation |
|---|---|---|
| R1 | Inconsistent policy key casing | Normalized lookups in `Policy` (tested). |
| R2 | Per-category shape differences | One `OpdCategory`; category-specific fields optional. |
| R3 | LLM hallucination → bad decision | LLMs never decide; output Pydantic-validated. |
| R4 | LLM/timeout crashes pipeline (TC011) | Per-node try/except → trace + degrade, never 500. |
| R5 | Diagnosis text ≠ policy keys | `normalize_dx` node; unmapped → MANUAL_REVIEW. |
| R6 | Non-deterministic eval | Inject test `content`; engine is pure. |
| R7 | Policy missing/corrupt | `PolicyLoadError` + `/health` degraded; no decision without policy. |
| R8 | Concurrent trace mutation | `Annotated[list, add]` reducer when nodes parallelize. |
| R9 | Ambiguous co-pay/discount order | Fixed, documented order (§9) + dedicated test (TC010). |
| R10 | PII in documents/logs | Don't log raw document content; redact in traces (later). |

---

## 16. Test-case routing map

| TC | Name | Stops/decides at | Mechanism | Expected |
|---|---|---|---|---|
| TC001 | Wrong document | verify→halt | required `[PRESCRIPTION, HOSPITAL_BILL]`, got 2× prescription | stop; name uploaded vs required type |
| TC002 | Unreadable document | verify→halt | quality=UNREADABLE | stop; ask re-upload that file (don't reject) |
| TC003 | Patient mismatch | verify→halt | patient-name consistency (Rajesh vs Arjun) | stop; surface both names |
| TC004 | Clean consultation | adjudicate | 10% co-pay on ₹1500 | APPROVED ₹1350, conf > 0.85 |
| TC005 | Waiting period (diabetes) | adjudicate | join 2024-09-01 + 90d > treat 2024-10-15 | REJECTED + eligible date 2024-11-30 |
| TC006 | Dental partial | adjudicate | root canal covered, whitening excluded | PARTIAL ₹8000 + per-line reasons |
| TC007 | MRI without pre-auth | adjudicate | MRI > ₹10k requires pre-auth, none | REJECTED PRE_AUTH_MISSING + how to resubmit |
| TC008 | Per-claim limit | adjudicate | ₹7500 > ₹5000 | REJECTED PER_CLAIM_EXCEEDED + both numbers |
| TC009 | Same-day fraud | adjudicate | 3 prior + this = 4 > limit 2 | MANUAL_REVIEW + listed signals |
| TC010 | Network discount | adjudicate | 20% discount then 10% co-pay | APPROVED ₹3240 + breakdown |
| TC011 | Component failure | adjudicate (degraded) | `simulate_component_failure` | APPROVED, degraded note, no 500 |
| TC012 | Excluded treatment | adjudicate | obesity/bariatric ∈ exclusions | REJECTED EXCLUDED_CONDITION, conf > 0.90 |

Three stop at the verification gate; nine reach the deterministic engine; every
one produces a full trace.

---

## 17. Folder structure

```
multi_agent_claims_pipeline/            # repo root (this directory)
├── app/
│   ├── main.py            # FastAPI factory + lifespan      ◀ P1
│   ├── config.py          # typed settings                  ◀ P1
│   ├── logging_config.py  # central logging                 ◀ P1
│   ├── exceptions.py      # typed error hierarchy            ◀ P1
│   ├── api/
│   │   ├── routes_health.py     # GET /health               ◀ P1
│   │   └── routes_claims.py     # POST /claims              (P3)
│   ├── models/
│   │   ├── policy.py            # policy models             ◀ P1
│   │   ├── claim.py             # claim request/response    (P2)
│   │   └── decision.py          # decision + trace          (P2)
│   ├── policy/loader.py         # load_policy()             ◀ P1
│   ├── graph/
│   │   ├── state.py             # ClaimState                ◀ P1
│   │   ├── builder.py           # build_graph()             ◀ P1
│   │   └── nodes/               # one file per node         (P2–P3)
│   ├── rules/                   # deterministic rule engine (P4)
│   └── llm/                     # LLM clients + prompts      (P2–P3)
├── tests/                       # pytest                    ◀ P1
├── docs/
│   ├── architecture.md          # this file                 ◀ P1
│   └── TECHNICAL_DOCUMENTATION.md  # file/phase reference    ◀ P1
├── policy_terms.json   test_cases.json   assignment.md      # base files (read-only)
├── README.md           sample_documents_guide.md            # base files (read-only)
├── requirements.txt    pyproject.toml    .env.example   .gitignore  ◀ P1
```

---

## 18. Scaling to 10x

Today: 75k claims/year; target 10M lives by 2030. Where this design bends and
how to extend it:

- **Stateless app** → horizontal scale behind a load balancer; the policy is
  read-only and loaded per-process (or from a cache).
- **LLM calls are the cost/latency bottleneck** → (a) cache classification &
  extraction keyed by document hash; (b) route cheap models (Haiku-class) for
  classification, stronger models only for hard extraction; (c) batch and run
  document nodes concurrently.
- **Throughput** → make `POST /claims` enqueue work and process the graph
  asynchronously; return a claim id and let the UI poll/stream.
- **State & audit** → move `ClaimState` + trace to a datastore (e.g. Postgres +
  object storage for documents) so traces are queryable and claims resumable.
- **Policy versioning** → load policies by `policy_id` + version from a store,
  not a single file; decisions record which policy version applied.
- **Observability at scale** → structured JSON logs + per-claim correlation id +
  metrics on decision mix, confidence distribution, node failure rates.

---

## 19. Security & data handling

- **Secrets** via env only (`ANTHROPIC_API_KEY`); never committed (`.env`
  gitignored).
- **PII** (patient names, diagnoses) must not be logged raw; trace `detail`
  strings are reviewed for leakage and redacted as the system matures (R10).
- **Input validation** at the edge (Pydantic request model) rejects malformed
  submissions before they reach the graph.
- **Determinism as a control** — because decisions are pure functions of
  validated input + policy, they are reproducible for audit and dispute.

---

## 20. Phase roadmap & status

| Phase | Scope | Status |
|---|---|---|
| **P1** | Repo structure, FastAPI, LangGraph scaffold, config, policy loader, `/health` | ✅ done, verified (8 tests pass, server boots) |
| **P2** | `claim`/`decision` models + `intake` & `verify` nodes + conditional early-stop branch + `POST /claims` (TC001–TC003) | ✅ done, verified (23 tests pass; TC001–TC003 block, TC004 passes) |
| **P3** | LLM client + `classify`/`extract`/`normalize_dx`/`explain` nodes | ✅ done, verified (LLM behind an interface; deterministic-first; fake-tested) |
| **P4** | Deterministic rule engine (`adjudicate`) — ordered rules + financials + confidence | ✅ done, verified (49 tests; engine pure & unit-tested) |
| **P5** | UI for submission and review | ✅ done (`/` SPA + `/sample-claims`) |
| **P6** | Eval report over all 12 test cases | ✅ done — **12/12 match** (`docs/EVAL_REPORT.md`) |

---

## 21. Assumptions & open questions

- **A1 (provider):** LLM provider is Anthropic Claude (`claude-sonnet-4-6`),
  configurable via env. No LLM is called in Phase 1.
- **A2 (injected content):** when a document carries pre-extracted `content`
  (as in `test_cases.json`), the `extract` node uses it and skips the LLM —
  this keeps the eval deterministic.
- **A3 (degrade on policy load failure):** the app starts and reports degraded
  rather than crashing; revisit if "fail-fast on missing core config" is
  preferred for production.
- **Open:** persistence layer for claims/traces; auth model for the UI; exact
  confidence formula coefficients (tuned in P4 against expected bounds).
```
