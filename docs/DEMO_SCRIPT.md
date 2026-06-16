# Demo Video Script (8–12 min)

A shot-by-shot storyboard for the assignment's demo video. It covers the three
required beats: **(1)** a claim stopped early on a document problem (show the
message), **(2)** a successful end-to-end approval with the full trace visible,
and **(3)** one decision I'm proud of + one I'd change with more time.

- **Live app:** https://plum-assignment-a651.onrender.com/ (or `uvicorn app.main:app --reload` → http://127.0.0.1:8000/)
- **Have open in tabs:** the UI (`/`), the API docs (`/docs`), `docs/EVAL_REPORT.md`, `docs/VISION_DEMO.md`, `app/rules/engine.py`.
- **Target length:** ~10 min. Timings are guides.

---

## 0. Intro & the one big idea (0:00–1:15)

**Say:**
> "This is an automated health-insurance claims processor for Plum. The core
> design idea is a strict split: **LLMs do perception and communication —
> reading messy documents and writing explanations — and deterministic code does
> cognition, the actual decision.** The LLM never decides a claim. That's what
> makes every decision reproducible and auditable."

**Show:** the README "Core idea" table (perception / cognition / communication).

**Say:** "It's a LangGraph pipeline of seven single-responsibility nodes:
`intake → classify → verify_documents → extract → normalize_diagnosis →
adjudicate → explain`, with an early-stop gate after verification."

---

## 1. Beat 1 — a claim stopped early on a document problem (1:15–3:15)

**Do:** In the UI, **JSON (advanced)** tab → load **TC001 — Wrong Document
Uploaded** from the dropdown → **Process claim**.

**Show / point at the result:**
- Status badge **Action needed / BLOCKED**, no decision.
- The blocking message, read it aloud:
  > "You uploaded: PRESCRIPTION, PRESCRIPTION. A CONSULTATION claim requires
  > PRESCRIPTION, HOSPITAL_BILL. The following required document(s) are missing:
  > HOSPITAL_BILL. Please upload the missing document(s) and resubmit."

**Say:**
> "Notice it's **specific and actionable** — it names what was uploaded, what's
> required, and what's missing. It is **not** a generic error. And critically the
> trace stops at `verify.required_documents` — extraction and adjudication never
> run. A bad set of documents never reaches a decision."

**Show:** scroll the trace — `intake → classify → verify.required_documents
(BLOCKED)`, nothing after.

**Optional (30s):** load **TC002** (unreadable) to show the *re-upload* ask
("your claim has NOT been rejected"), contrasting BLOCKED-and-fixable with
REJECTED.

---

## 2. Beat 2 — a clean end-to-end approval with the full trace (3:15–6:00)

**Do:** Load **TC010 — Network Hospital — Discount Applied** → **Process claim**.

**Show:**
- Banner **Claim approved**, payout **₹3,240**, confidence **95%**.
- The **"How we calculated your payout"** waterfall:
  `claimed 4500 → eligible 4500 → network discount 20% (−900) → co-pay 10% (−360)
  → ₹3,240`.

**Say:**
> "This is the financial-order detail the brief calls out: the **network discount
> is applied first, then the co-pay** on the discounted amount. 4500 → 3600 →
> 3240. Doing it the other way gives a different number, so there's a dedicated
> test that locks the order."

**Show:** expand the **Processing trace** and walk the `adjudicate.*` entries:
> "Every rule writes a trace line whether it fires or not — eligibility, minimum
> amount, submission window, exclusions, waiting period, pre-auth, per-claim
> limit, fraud, annual OPD limit, then the money math. An ops person can
> reconstruct *exactly* why ₹3,240 was approved without reading any code."

**Then show the eval report (`docs/EVAL_REPORT.md`):**
> "All 12 provided cases run through the system and are checked against their full
> `system_must` requirements — not just the decision, but message specificity,
> the eligibility date, confidence bounds, the fraud signal, the discount
> breakdown. **12 out of 12 pass.**"

**Optional (30s):** show TC005 (waiting period → eligibility date 2024-11-30) or
TC011 (component failure → degraded, confidence 0.65, "manual review
recommended", no crash).

---

## 3. The real vision path (6:00–7:30)

**Say:**
> "The 12-case eval runs offline with injected content so it's deterministic. But
> the AI path is real — let me show it on actual document images."

**Do:** Either switch to the **Upload documents** tab and drag in
`samples/prescription_rajesh.png` + `samples/hospital_bill_rajesh.png` (live key
needed), **or** walk through `docs/VISION_DEMO.md` if recording offline.

**Show (from VISION_DEMO.md):**
- Clean approval: Claude classified both images, read "Rajesh Kumar", extracted
  fields (completeness 1.00) → APPROVED ₹1350.
- Wrong-document upload: Claude classified a pharmacy bill, and the gate caught
  **two** issues at once — missing HOSPITAL_BILL **and** a patient mismatch
  (Rajesh vs Sneha).
- Blurry upload: Claude judged it unreadable → re-upload ask.

**Say:**
> "Same pipeline, same gate, same deterministic engine — the only difference is
> the documents are read by Claude vision instead of being injected. LLM output
> is Pydantic-validated before the rules ever see it."

---

## 4. Beat 3 — proud of / would change (7:30–9:30)

**Proud of — the perception/cognition/communication boundary.**
**Show:** `app/rules/engine.py` — the ordered rules, no LLM calls.
> "I'm proud of the deterministic core. The decision is a pure function of
> validated input plus the policy file, so it's reproducible, unit-tested, and
> every step is traced. Exclusions are checked **before** waiting periods so
> obesity rejects as 'excluded' (permanent), not 'waiting period' (come back
> later) — the reason code is correct, which matters to the member. And no policy
> constant is hardcoded; everything is read from `policy_terms.json`."

**Would change — persistence + async.**
> "With more time, two things. First, **persistence**: today the system is
> in-memory, so a claim and its trace live only in the response. I'd add a
> datastore and a `GET /claims/{id}` so ops can look up any past claim. Second,
> **async**: the vision calls are synchronous and sequential; for a 5-document
> claim I'd parallelize them with `asyncio.gather` and move `POST /claims` to an
> enqueue-and-poll model. Both are deliberate cuts for a 2–3-day build — they're
> documented as trade-offs in `architecture.md`, not overlooked."

---

## 5. Close (9:30–10:00)

**Say:**
> "To recap: a multi-agent LangGraph pipeline; LLMs for perception and
> communication only; a deterministic, fully-traced rule engine for every
> decision; specific early-stop document checks; graceful degradation instead of
> crashes; 12/12 on the eval against full requirements; and a real, demonstrated
> vision path. Thanks for watching."

**Show:** the deployed URL and the repo one last time.

---

### Recording checklist
- [ ] Browser zoom ~125% so trace text is legible.
- [ ] If using the live upload, confirm `ANTHROPIC_API_KEY` is set and `USE_LLM=true`.
- [ ] Pre-load TC001, TC010 (and TC005/TC011 if using) so dropdown switches are quick.
- [ ] Have `docs/EVAL_REPORT.md` and `docs/VISION_DEMO.md` rendered (not raw).
- [ ] Keep it to 8–12 minutes; the three required beats are sections 1, 2, and 4.

---
---

# 📚 Project Walkthrough — Learn the Whole System (Beginner-Friendly)

> **What this section is.** A from-scratch teaching guide to *every* file in this
> project, in plain language, written so that during the 60-minute technical
> review you can (a) explain any file, (b) know exactly where the code starts and
> how a claim flows, and (c) confidently answer "now change X for me" questions.
>
> **How to read it.** Go top to bottom once. Each chapter builds on the last. The
> 🎤 **"If the interviewer asks…"** boxes are the gold — they tell you exactly
> which file to open and what to say when asked to extend something live.
>
> *Author note (Priya): this is my own revision doc. I keep appending to it.*

## Table of contents (this walkthrough)

1. [The 30-second mental model](#w1-the-30-second-mental-model)
2. [The ONE big idea (say this in the interview)](#w2-the-one-big-idea)
3. [LangGraph in 5 minutes (you're new to it — start here)](#w3-langgraph-in-5-minutes)
4. [Where does the code START? (the entry point)](#w4-where-does-the-code-start)
5. [The folder map (what lives where, and why)](#w5-the-folder-map)
6. [The full journey of one claim (room by room)](#w6-the-full-journey-of-one-claim)
7. [File-by-file — Part 1: the plumbing](#w7-file-by-file-part-1-the-plumbing)
8. [File-by-file — Part 2: the data shapes (models)](#w8-file-by-file-part-2-the-models)
9. [File-by-file — Part 3: the graph (state + builder)](#w9-file-by-file-part-3-the-graph)
10. [File-by-file — Part 4: the 7 nodes](#w10-file-by-file-part-4-the-seven-nodes)
11. [File-by-file — Part 5: the brain (rules engine)](#w11-file-by-file-part-5-the-rules-engine)
12. [File-by-file — Part 6: the LLM layer](#w12-file-by-file-part-6-the-llm-layer)
13. [File-by-file — Part 7: the API + UI](#w13-file-by-file-part-7-the-api-and-ui)
14. [File-by-file — Part 8: the data files](#w14-file-by-file-part-8-the-data-files)
15. [File-by-file — Part 9: tests](#w15-file-by-file-part-9-tests)
16. [File-by-file — Part 10: scripts & docs](#w16-file-by-file-part-10-scripts-and-docs)
17. [The 12 test cases — one-line cheat sheet](#w17-the-12-test-cases-cheat-sheet)
18. [🎤 Live "change it" drills — the interview gym](#w18-live-change-it-drills)
19. [Words you must be able to define](#w19-glossary)

---

## W1. The 30-second mental model

Imagine an employee submits a medical claim: "I spent ₹4,500 at Apollo Hospital,
here are my prescription and bill, please pay me back." Today a **human** reads
those documents, checks them against the company's insurance policy, and decides:
pay full, pay part, reject, or "I'm not sure — send to a senior."

**Our system is that human, automated.** You hand it the claim + documents, and it
returns the same four possible answers — `APPROVED`, `PARTIAL`, `REJECTED`,
`MANUAL_REVIEW` — *plus* a step-by-step record of how it decided (so an ops person
can trust it), *plus* a payout amount and a confidence score.

The whole thing is a small web server (FastAPI) with one assembly line inside it
(LangGraph). A claim walks down the line; each station does one job.

---

## W2. The ONE big idea

If you remember nothing else, remember this — it's the sentence that wins the
interview:

> **"LLMs do perception and communication. Deterministic code does cognition —
> the actual decision. The LLM never decides a claim."**

Break it down:

| Word | Meaning in this project | Who does it |
|---|---|---|
| **Perception** | Turn messy reality into clean data — "read this blurry bill", "what document type is this?", "map *Type 2 Diabetes Mellitus* → the policy word `diabetes`" | LLM (or deterministic keyword match for diagnosis) |
| **Cognition** | The decision itself — waiting periods, exclusions, limits, co-pay math, fraud | **Plain Python rules. No AI.** |
| **Communication** | Explain the decision to the member in friendly language | LLM (optional; falls back to a template) |

**Why this split is the killer design choice (and why it maps to the grade):**

- **Reproducible & auditable** — the decision is a *pure function* of (validated
  input + policy file). Same input → same output → same trace, every single time.
  You can unit-test it. (System Design 30% + Observability 20% = half the grade.)
- **Hallucination is contained** — even if the LLM misreads a field, it can't
  "decide" to approve a fraud. The wrong field flows through the *same rules*, and
  a low extraction quality *lowers the confidence score*. AI mistakes degrade
  gracefully; they don't corrupt decisions. (AI Integration 15%.)
- **The eval stays deterministic** — the 12 test cases ship with pre-extracted
  `content`, so we can run them offline with no API key and get 12/12 every time.

🎤 **If the interviewer asks "why not just let GPT/Claude decide the claim?"** →
"Because then the decision isn't reproducible or auditable, and a hallucination
becomes a wrong payout. Insurance decisions must be defensible in a dispute. I use
the LLM only where messiness lives — reading documents and writing explanations —
and keep the money decision as testable, ordered Python rules."

---

## W3. LangGraph in 5 minutes

You said you're new to LangGraph — here's everything you need.

**The problem LangGraph solves.** We have 7 steps. We *could* just write
`step1(); step2(); step3()...` in one function. That works, but: (1) the routing
("if documents are bad, STOP early") gets buried in `if` statements, (2) there's
no clean shared "notebook" that every step writes to, and (3) it doesn't *look*
like the multi-agent architecture the brief rewards. LangGraph fixes all three.

**The 3 concepts you need:**

1. **State** = a shared notebook (a Python dict) that travels with the claim.
   Every step reads from it and writes new pages into it. Ours is `ClaimState`.
2. **Node** = one station on the assembly line. It's just a function:
   `def node(state) -> dict`. It returns *only the new pages it wrote*; LangGraph
   merges them into the notebook. We have 7 nodes.
3. **Edge** = an arrow from one node to the next. Most edges are straight
   (`A → B`). One edge is **conditional**: after document verification, a little
   function looks at the notebook and says "stop" or "continue".

```
START → intake → classify → verify_documents ──(bad docs?)──→ STOP (END)
                                              └──(docs ok)───→ extract
                                                            → normalize_diagnosis
                                                            → adjudicate
                                                            → explain → END
```

**That conditional edge IS the "catch document problems early" requirement.** A
wrong/blurry/mismatched document never reaches the expensive extraction or the
decision — it bounces out immediately with a specific message.

**One subtle thing that sounds smart in interview:** the notebook's `trace` field
is special. It's declared as `Annotated[list, operator.add]`. That means when two
steps both write to `trace`, LangGraph *concatenates* the lists instead of
overwriting. So each node only returns *its own* new trace lines, and the full
audit trail builds up automatically. (Bonus: it stays correct even if we
parallelize nodes later.)

🎤 **If asked "why LangGraph and not a plain function chain?"** → "Three reasons:
the early-stop branch is a first-class conditional edge instead of buried `if`s;
the trace is a single shared channel every node appends to with a built-in
reducer; and each node is a single-responsibility agent, which is the multi-agent
framing the brief gives bonus points for. The cost is one dependency — acceptable."

---

## W4. Where does the code START?

This is the question interviewers love. The honest answer has two layers.

**Layer 1 — the process starts at `app/main.py`.** You run the app with:

```bash
uvicorn app.main:app --reload
```

That literally means: "uvicorn, import the file `app/main.py`, find the variable
named `app`, and serve it." The very last line of `main.py` is `app = create_app()`
— that's the object uvicorn grabs.

**Layer 2 — what happens the moment it boots (the `lifespan` function).** Before
the server accepts a single request, `main.py`'s `lifespan` runs *once* and does
the expensive setup, in this order:

1. `get_settings()` — read config from `.env` / environment (config.py).
2. `configure_logging()` — set up logging.
3. `load_policy()` — read `policy_terms.json` from disk and validate it into a
   typed `Policy` object. **If it fails, we do NOT crash** — we set
   `policy = None` and start in "degraded" mode (`/health` will report it).
4. `build_llm_client()` — build the Claude client *if* a key is configured;
   otherwise return `None` (deterministic offline mode).
5. `build_graph(policy, llm)` — wire the 7-node assembly line *once*, binding the
   policy and LLM into it. Stash it on `app.state.graph`.

Everything is stashed on `app.state` so that **each request reuses the same loaded
policy and the same compiled graph** — we never re-read the file or re-build the
graph per request. That's why it's fast and why startup is the only place that
does heavy lifting.

**Then a request arrives.** `POST /claims` → `routes_claims.py` grabs the graph
off `app.state`, calls `graph.invoke({...})`, and the claim walks the line. The
final notebook is turned into a JSON response.

🎤 **If asked "walk me through startup vs per-request"** → say exactly the two
layers above. "Heavy, shared, once-only work happens in `lifespan`; per-request we
just validate the body and invoke the already-compiled graph. The composition
root is `create_app()` — I keep it a factory so tests can build fresh apps."

---

## W5. The folder map

```
app/
├── main.py            ← START HERE. Builds the app, loads policy+graph once.
├── config.py          ← all settings (env vars), one typed place.
├── logging_config.py  ← logging setup.
├── exceptions.py      ← our own error types (e.g. PolicyLoadError).
├── api/               ← the web endpoints (the "doors" into the system)
│   ├── routes_claims.py   ← POST /claims  and  POST /claims/upload
│   ├── routes_health.py   ← GET /health
│   └── routes_ui.py       ← GET /  (the web page) and GET /sample-claims
├── graph/             ← the assembly line (LangGraph)
│   ├── state.py           ← the shared notebook (ClaimState)
│   ├── builder.py         ← wires nodes + edges together
│   └── nodes/             ← one file per station (7 nodes)
├── rules/             ← THE BRAIN. Deterministic decision logic. No AI here.
│   ├── engine.py          ← the ordered rulebook (adjudicate)
│   ├── financials.py      ← the money math (discount → co-pay → caps)
│   └── normalization.py   ← free-text diagnosis → policy vocabulary
├── llm/               ← the AI layer (perception + communication)
│   ├── client.py          ← Claude client + the deterministic-off switch
│   └── prompts.py         ← the prompt text
├── models/            ← the data shapes (Pydantic). The system's vocabulary.
│   ├── policy.py          ← shape of policy_terms.json
│   ├── claim.py           ← shape of a claim submission (the INPUT)
│   ├── decision.py        ← shape of the answer + trace (the OUTPUT)
│   └── extraction.py      ← shape of what the LLM reads off a document
├── policy/policy_loader.py ← reads + validates policy_terms.json
├── verification/document_verifier.py ← the early-stop gate (3 checks)
└── static/index.html  ← the single-page UI

tests/        ← pytest suite (the safety net)
scripts/      ← run_eval.py (the 12-case report), vision demo scripts
docs/         ← architecture.md, this file, eval report, vision demo
policy_terms.json  ← the policy + member roster (read at runtime, never edited)
test_cases.json    ← the 12 scenarios (read-only)
```

**The mental grouping** (this is how to *talk* about it): there are four layers —
**the doors** (`api/`), **the assembly line** (`graph/`), **the brain**
(`rules/`), and **the eyes/mouth** (`llm/`). Everything else is supporting cast:
`models/` is the shared vocabulary, `policy/` loads the rulebook data, `config/
logging/exceptions` are plumbing.

---

## W6. The full journey of one claim

Let's follow a claim through the building, room by room. Keep this picture in your
head; every file below is just one of these rooms.

1. **Door (`routes_claims.py`)** — the claim arrives as JSON. FastAPI validates it
   against `ClaimRequest` (claim.py). Bad shape → `422` instantly, never enters
   the building. We mint a `claim_id` and call `graph.invoke(...)`.
2. **Room `intake`** — "Who is this? Is the member on the roster? Does the policy
   id match?" Starts the trace.
3. **Room `classify`** — "What *type* is each document?" On the JSON path we trust
   the declared type. On a real photo upload, Claude *looks at the image* and says
   "this is a PRESCRIPTION, it's readable, the patient is Rajesh".
4. **Gate `verify_documents`** ← **the early-stop gate.** Three checks: are the
   required documents present? is everything readable? same patient on all docs?
   **If any check fails → claim STOPS here** with a specific message and never
   reaches the decision.
5. **Room `extract`** — "Pull the fields out of each document" (amounts, diagnosis,
   dates). On the JSON path the fields are already provided. On the photo path,
   Claude reads them. If something fails here, we mark the claim *degraded* and
   keep going (we never crash).
6. **Room `normalize_diagnosis`** — "Translate the doctor's free text into the
   policy's controlled words." E.g. *"Type 2 Diabetes Mellitus"* → `diabetes`.
7. **Room `adjudicate`** ← **the brain.** Runs the ordered rulebook and produces
   the decision + amount + confidence. (Details in W11.)
8. **Room `explain`** — "Write a friendly 2–4 sentence explanation for the member"
   from the decision. LLM optional; template fallback always works.
9. **Out the door** — `routes_claims.py` assembles the final JSON: decision,
   amount, reasons, confidence, the explanation, the money breakdown, and the
   **full trace**.

> Notice: rooms 5–8 only run if the gate in room 4 passed. That's the conditional
> edge from W3.

---

## W7. File-by-file — Part 1: the plumbing

These four files are the boring-but-important scaffolding. Interviewers rarely
dig here, but you should be able to say what each does in one sentence.

### `app/config.py` — the single source of settings
- **What:** one typed class (`Settings`) that reads every tunable from environment
  variables / `.env`. Things like `use_llm`, `llm_model` (`claude-sonnet-4-6`),
  `anthropic_api_key`, `policy_file_path`, timeouts.
- **Why it's nice:** nothing else in the app touches `os.environ` directly. Bad
  config fails loudly at startup, not deep inside a request. `get_settings()` is
  cached (`@lru_cache`) so the env is read once.
- **One detail to know:** `PROJECT_ROOT` is computed from the file's own location,
  so the default policy path is correct whether you launch from the repo root or
  run pytest from anywhere.
- 🎤 **"Change the model to Haiku"** → it's one line here (`llm_model`), or just
  set `LLM_MODEL=claude-haiku-4-5-...` in `.env`. No code change. Say: "config is
  12-factor; the model is an env var, not hardcoded."

### `app/logging_config.py` — one consistent log format
- **What:** configures the root logger once (timestamp | level | module | message)
  to stdout. Idempotent (clears old handlers so tests don't stack duplicates).
- **Why:** observability is 20% of the grade; one switch for log level, one format.

### `app/exceptions.py` — our own error types
- **What:** a tiny hierarchy. `ClaimsSystemError` is the base; `PolicyLoadError`
  (and later `LLMError`) inherit from it.
- **Why:** callers can `except ClaimsSystemError` to catch everything *we* raise,
  while still telling specific failures apart. Cleaner than bare `Exception`.

### `app/main.py` — the composition root (covered in W4)
- **What:** `create_app()` factory + the `lifespan` startup/shutdown.
- **The one design decision to memorize:** *policy load failure → degrade, don't
  crash.* If the policy can't load, `app.state.policy = None`, `/health` says
  `degraded`, and the claims endpoint returns `503` rather than ever deciding
  without a policy. "A process that can report why it's unhealthy beats one that
  exits silently."

---

## W8. File-by-file — Part 2: the models

**Mental model:** `models/` is the *vocabulary* of the whole system. These are
Pydantic classes — think "a dict, but with the shape enforced and validated." If
data doesn't match the shape, Pydantic rejects it. This is how we keep garbage out.

There are two sides: **input** (`claim.py`), **output** (`decision.py`), plus the
**policy** shape (`policy.py`) and the **LLM-read** shape (`extraction.py`).

### `app/models/claim.py` — the INPUT (what a caller submits)
- **`ClaimRequest`** — the whole submission: `member_id`, `policy_id`,
  `claim_category`, `treatment_date`, `claimed_amount` (must be > 0), and
  `documents` (at least one). Plus optional fields some test cases use:
  `hospital_name`, `ytd_claims_amount`, `submission_date`, `claims_history`,
  `pre_authorization_obtained`, and `simulate_component_failure` (TC011's "break a
  component on purpose" switch).
- **`Document`** — one uploaded file. It can arrive two ways:
  - **(a) JSON path:** `actual_type` is declared + `content` carries the
    pre-extracted fields. This is the deterministic eval path.
  - **(b) Real upload path:** `data_base64` + `media_type` carry the raw image/PDF
    bytes, and `actual_type` is left empty for the classifier to fill in.
- **Enums** (`ClaimCategory`, `DocumentType`, `DocumentQuality`) give a fixed
  vocabulary so a typo like `"CONSULTATON"` is rejected at the edge.
- **Handy methods:** `type_label()` (UI label even before classification),
  `patient_name()` (best-known patient name — explicit field, else from content).
- 🎤 **"Add a new field to the claim"** → add it here as an optional field with a
  default, so old callers don't break. Then read it wherever you need it (usually
  the rule engine). Say: "I'd make it optional to keep the request shape
  backward-compatible."

### `app/models/decision.py` — the OUTPUT (what we return)
- **`Decision`** enum — the four verdicts: `APPROVED`, `PARTIAL`, `REJECTED`,
  `MANUAL_REVIEW`.
- **`TraceEntry`** — ONE line of the audit trail: `step`, `status`
  (`OK/BLOCKED/FAILED/SKIPPED`), `detail` (human text), `data` (machine dict).
  **The list of these IS our observability.**
- **`BlockingIssue` / `BlockingReason`** — the early-stop problems (missing doc,
  unreadable, patient mismatch) with member-facing messages.
- **`RejectionReason`** enum — every way a claim can be rejected
  (`NOT_ELIGIBLE`, `WAITING_PERIOD`, `PRE_AUTH_MISSING`, `PER_CLAIM_EXCEEDED`, …).
- **`DecisionResult`** — what the rule engine returns: decision + approved_amount +
  reasons + line_items + confidence + financial_breakdown + notes + trace_entries.
- **`ClaimProcessingResult`** — the final HTTP response body the user sees.
- 🎤 **"Add a new rejection reason"** → add it to the `RejectionReason` enum here,
  then raise it from a rule in `engine.py`. Two-file change.

### `app/models/policy.py` — the shape of `policy_terms.json`
- **What:** a Pydantic tree mirroring the policy file (`Coverage`, `OpdCategory`,
  `WaitingPeriods`, `Exclusions`, `FraudThresholds`, `Member`, …).
- **The clever bit — normalized lookups:** `get_member(id)`, `get_category(name)`,
  `document_requirement(name)`. These absorb an annoying real-world quirk: in the
  file, `opd_categories` keys are **lowercase** (`"consultation"`) but
  `document_requirements` keys are **UPPERCASE** (`"CONSULTATION"`). The lookups
  hide that inconsistency in one tested place so the rest of the code never
  worries about casing.
- **Design note:** there's ONE `OpdCategory` model with the *union* of all
  category fields (dental's `excluded_procedures`, diagnostic's
  `pre_auth_threshold`, etc.), most of them optional. Simpler than six near-
  identical models. (Decision D8.)
- 🎤 **"Why one OpdCategory model and not six?"** → "Six categories share most
  fields. One model with optional category-specific fields is less code and easier
  to explain; the cost is a few always-None fields per category. If the categories
  diverged a lot I'd switch to a discriminated union."

### `app/models/extraction.py` — the validated shape of LLM-read fields
- **What:** `ExtractedDocument` — the typed shape Claude's extraction must fit
  (`patient_name`, `diagnosis`, `line_items`, `total`, …). `extra="allow"` keeps
  any bonus keys (GSTIN, NABL id…) without failing.
- **Why it matters:** the LLM returns JSON; we validate it into *this* before the
  rules ever see it. A hallucinated `total: "lots"` fails validation here → becomes
  an `LLMError` → the claim degrades, instead of corrupting the math.
- **`extraction_completeness()`** — a rough 0–1 score: did we get an identity + a
  date + some substantive content? Feeds the confidence score on the vision path.

---

## W9. File-by-file — Part 3: the graph

### `app/graph/state.py` — the shared notebook
- **What:** `ClaimState`, a `TypedDict(total=False)`. `total=False` means every key
  is optional — the notebook fills in as the claim moves down the line.
- **Field ownership** (who writes what) is documented right in the file: `intake`
  writes `member`; `classify` writes `classified_docs`; `verify_documents` writes
  `blocking_issues`/`status`; `extract` writes `extracted_content`/`degraded`; and
  so on.
- **The reducer trick:** `trace` and `blocking_issues` are
  `Annotated[list[...], operator.add]`. As explained in W3 — each node returns only
  its own new entries, LangGraph concatenates. This is *the* observability
  mechanism.
- 🎤 **"Why TypedDict here but Pydantic everywhere else?"** → "TypedDict is
  LangGraph's idiom for partial, incremental state with reducers. Pydantic is for
  the domain objects where I want validation. Right tool per job." (Decision D4.)

### `app/graph/builder.py` — the wiring diagram
- **What:** `build_graph(policy, llm)` creates the `StateGraph`, registers the 7
  nodes, and connects them with edges.
- **Dependency binding:** each node needs either the policy or the LLM client.
  Instead of making nodes reach for globals, the builder uses
  `functools.partial(node, policy=policy)` to "pre-fill" that argument. So every
  node keeps the clean signature `(state) -> dict` but still has what it needs.
- **The early-stop fork** lives here: `_after_document_verification(state)` returns
  `"stop"` if there are blocking issues, else `"continue"`, and
  `add_conditional_edges` maps `{"stop": END, "continue": "extract"}`.
- 🎤 **"Add a new node to the pipeline"** → 3 steps: (1) write
  `app/graph/nodes/your_node.py` as `def your_node(state, *, policy) -> dict`,
  (2) `graph.add_node("your_node", partial(your_node, policy=policy))`, (3) splice
  it into the edges (`add_edge("prev", "your_node")`,
  `add_edge("your_node", "next")`). Say: "single-responsibility node, bind deps via
  partial, wire two edges."

---

## W10. File-by-file — Part 4: the seven nodes

**Big principle for all nodes:** *nodes are thin*. They read from state, call a
pure helper, and write trace entries back. The real logic lives in `rules/`,
`verification/`, and `llm/` — so it can be unit-tested without the graph.

### Node 1 — `intake.py`
- **Job:** open the trace; look up the member in the policy roster; sanity-check
  the `policy_id`. It *decides nothing*.
- **Writes:** `member`, and trace lines (including a `FAILED` line if the member
  isn't found or the policy id mismatches — the engine later turns "no member"
  into `NOT_ELIGIBLE`).

### Node 2 — `classify.py` (AI-allowed)
- **Job:** figure out each document's *type*, *readability*, and *patient name*.
- **Three branches:** (a) caller declared `actual_type` → trust it (JSON/eval
  path); (b) real upload + LLM available → call `llm.classify_document(doc)` and
  **write the findings back onto the `Document`** (`actual_type`, `quality`,
  `patient_name_on_doc`); (c) no type and no AI → mark unidentified.
- **Why write findings back onto the doc?** Because the gate, extract, and the
  engine all read `actual_type`/`quality`/patient straight off the `Document`. By
  resolving onto it, *every later step is identical* whether the type was declared
  or seen by vision. Clean.
- **Note the ordering:** classify runs *before* the gate, so vision can catch a
  wrong/blurry/mismatched real document *before* the expensive extraction.

### Node 3 — `verify_documents.py` (the gate)
- **Job:** a thin adapter. It calls the pure
  `verification.document_verifier.verify_documents(request, policy)`, appends its
  trace, and — if it failed — sets `status = BLOCKED` so the builder's fork routes
  to `END`.
- (The actual 3 checks are in W11's verification subsection.)

### Node 4 — `extract.py` (AI-allowed) + graceful degradation
- **Job:** get structured fields per document.
- **Branches:** (a) doc has inline `content` → use it, no AI; (b) real upload + LLM
  → `llm.extract_document(doc)`, record a `completeness` score; (c) neither →
  degrade.
- **TC011 lives here:** if `simulate_component_failure` is set, it writes a
  `FAILED` trace line, sets `degraded=True`, and **continues** — proving the
  pipeline survives a component failure. Any LLM error does the same.
- 🎤 **"Show me where you handle failure gracefully"** → open this file. "On any
  failure I trace it, set `degraded`, and keep going. The decision still gets made
  on whatever data exists, and the degraded flag knocks 0.30 off the confidence."

### Node 5 — `normalize_diagnosis.py`
- **Job:** thin wrapper over `rules.normalization`. Turns the free-text diagnosis
  into the policy's controlled words. Writes `normalized_diagnosis` + a trace line
  saying what it thought ("what did the system think the diagnosis was?").

### Node 6 — `adjudicate.py` (the brain's doorway)
- **Job:** assemble the rules' inputs from state
  (`request`, `member`, `normalized_diagnosis`, `extracted_content`, `degraded`,
  `extraction_confidence`), call `gather_bill_details(...)` then
  `rules.engine.adjudicate(...)`, and store the `DecisionResult` + `status=DECIDED`
  + the rules' trace.
- **Still thin** — all real logic is in `rules/engine.py`.

### Node 7 — `explain.py` (AI-allowed)
- **Job:** turn the decision into 2–4 friendly sentences.
- **Safety design:** it *always* builds a deterministic template explanation first
  (`_build_explanation_text`). If the LLM is configured, it may rephrase it more
  naturally — **but it never changes the numbers or the decision**, and on any LLM
  failure it falls back to the template. So this node can't break the response.
- 🎤 **"What if the explanation LLM lies about the amount?"** → "It can't change the
  decision — that's already computed and stored. The prompt explicitly forbids
  changing numbers, and if the LLM fails I serve the deterministic template. The
  explanation is communication, not cognition."

---

## W11. File-by-file — Part 5: the rules engine

This is **the brain** and the most likely place the interviewer will ask you to
make a change. Know it cold. Three files: `engine.py` (the rulebook),
`financials.py` (the money math), `normalization.py` (diagnosis → policy words).
Plus the gate in `verification/document_verifier.py`.

### `app/verification/document_verifier.py` — the early-stop gate (pure)
Three independent checks; **all three always run** (so a claim with multiple
problems reports all of them); each writes a trace line pass *or* fail:

1. **`_check_required_documents_present`** (TC001) — does the claim category have
   all its required document types? Consultation needs
   `[PRESCRIPTION, HOSPITAL_BILL]`; uploading two prescriptions → missing
   `HOSPITAL_BILL`. The message *names what you uploaded, what's required, and
   what's missing* — specific and actionable, never generic.
2. **`_check_readable`** (TC002) — any `quality == UNREADABLE` document blocks with
   a **re-upload** ask. Crucially the message says *"Your claim has NOT been
   rejected"* — blocked-and-fixable, not rejected.
3. **`_check_same_patient`** (TC003) — all docs that name a patient must name the
   *same* one. Names are normalized (lowercase + collapse spaces) so "Rajesh
   Kumar" == "rajesh  kumar" but ≠ "Arjun Mehta". The message lists both names.
- 🎤 **"Make the patient match fuzzy (handle typos)"** → "Today it's exact after
  normalization. I'd add a similarity threshold (e.g. Levenshtein / token-set
  ratio) in `_check_same_patient`, and below the threshold route to MANUAL_REVIEW
  rather than auto-block — a human resolves near-matches. I'd keep it deterministic
  and unit-test the threshold."

### `app/rules/engine.py` — the ordered rulebook (`adjudicate`)
This is a **pure function**: same inputs → same `DecisionResult`. It runs rules in
a fixed order; **the order encodes precedence**; the first blocking rule wins and
returns; every rule writes a trace line whether it fires or not.

The order (memorize the shape, not every line):

| # | Rule | Hit → | Test |
|---|---|---|---|
| 1 | Eligibility (member exists) | REJECT `NOT_ELIGIBLE` | — |
| 1b | Minimum claim amount (₹500) | REJECT `BELOW_MINIMUM` | — |
| 1c | Submission deadline (only if `submission_date` given) | REJECT `SUBMISSION_WINDOW_EXCEEDED` | — |
| 2 | **Exclusions** (whole claim) | REJECT `EXCLUDED_CONDITION` | TC012 |
| 3 | **Waiting period** | REJECT `WAITING_PERIOD` | TC005 |
| 4 | Pre-authorization (high-value tests) | REJECT `PRE_AUTH_MISSING` | TC007 |
| 5 | Per-claim limit | REJECT `PER_CLAIM_EXCEEDED` | TC008 |
| 6 | Line-item exclusions (dental/vision) | PARTIAL / REJECT | TC006 |
| 7 | Fraud signals | MANUAL_REVIEW | TC009 |
| 8 | High-value auto-review | MANUAL_REVIEW | — |
| 8b | Annual OPD limit exhausted | REJECT `ANNUAL_LIMIT_EXCEEDED` (or cap) | — |
| 9 | **Money math** (discount → co-pay → caps) | APPROVED amount | TC004, TC010 |

**The single most important ordering decision — and a great thing to volunteer:**

> **Exclusions (Rule 2) are checked BEFORE waiting periods (Rule 3).** Obesity is
> *both* a permanent exclusion *and* has a 365-day waiting period. If we checked
> waiting first, an obesity claim would say "come back after the waiting period" —
> which is *wrong and misleading*, because it's never covered. Checking exclusions
> first gives the member the correct reason: `EXCLUDED_CONDITION` (permanent).
> The reason code being *correct* matters to a real person. (See `test_rules.py:
> test_exclusion_takes_precedence_over_waiting_and_limit`.)

**Confidence (`_confidence_score`)** is *composed*, not a flat number:
```
base (0.95 clear-cut decision / 0.90 manual review)
  − 0.30                         if degraded (a node failed)
  − (1 − extraction_conf)×0.40   poor document reading (vision path only)
  − 0.10                         if ambiguous (no diagnosis text AND no bill lines)
```
On the deterministic eval path, extraction_conf is 1.0 and there's always a
diagnosis or bill lines, so both penalties are 0 → confidence = base (keeps the
12 cases stable). TC011 = `0.95 − 0.30 = 0.65`.

**The confidence GATE:** if an otherwise-approvable claim's confidence drops below
`0.50`, it's routed to `MANUAL_REVIEW` instead of auto-approved. *"The system
surfaces its own uncertainty instead of hiding it."*

- 🎤 **"Add a new rule — e.g. reject claims older than the policy period"** →
  "Rules are ordered pure functions in `adjudicate`. I'd add a `RejectionReason`
  enum value in `decision.py`, then insert a block at the right precedence in
  `engine.py` that reads the dates from `policy.policy_holder` and the request,
  `record(...)` a trace line, and `return rejected(reason, [...])` on a hit. Then a
  unit test in `test_rules.py`. I'd think carefully about *where* in the order it
  goes — precedence is the design."
- 🎤 **"Change fraud to also flag a high monthly total"** → it's in
  `_find_fraud_signals`; add a check against `claims_history` summed for the month
  vs a threshold read from `policy.fraud_thresholds`. Don't hardcode the number.

### `app/rules/financials.py` — the money math
- **`gather_bill_details`** — pulls the bill line items out of each document's
  content and decides if the hospital is a network hospital (case-insensitive
  match against `policy.network_hospitals`).
- **`compute_financials`** — THE order the brief grades (TC010):
  ```
  after_network_discount = covered_base × (1 − discount%)     ← FIRST
  after_copay            = after_network_discount × (1 − copay%) ← SECOND (on discounted amount)
  approved = min(after_copay, effective_cap, remaining_annual_opd) ← caps LAST
  ```
  Worked: 4500 → ×0.80 = 3600 → ×0.90 = 3240. Doing co-pay first gives a different
  number — that's why there's a dedicated test locking the order.
- **`effective_per_claim_cap`** — a subtle one worth understanding: it's
  `max(per_claim_limit, sub_limit)`, **not** min. The base per-claim limit is
  ₹5,000, but some categories *allow more* (dental sub-limit ₹10,000). So the
  sub-limit *raises* the cap for generous categories rather than capping below the
  base. TC010 approves ₹3,240 for a consultation (sub-limit ₹2,000) precisely
  because the cap is the ₹5,000 base, not ₹2,000.
- 🎤 **"What if they ask you to apply co-pay before discount?"** → "One line:
  swap the two multiplications in `compute_financials`. But I'd push back — TC010
  explicitly requires discount first, and the order changes the payout. I'd make
  sure the test and the docs change with it."

### `app/rules/normalization.py` — diagnosis → policy vocabulary
- **What:** keyword tables map free text to the policy's controlled words. E.g.
  `"diabetes"/"diabetic"/"t2dm"` → `diabetes` (a waiting-period key);
  `"obesity"/"bariatric"` → an exclusion phrase.
- **Whole-word matching** (`_contains_word` with regex `\b`) so "hernia" doesn't
  match "herniation".
- **Why deterministic when the brief allows an LLM here?** Because the *vocabulary*
  is fixed (it comes from the policy), and the decision must be reproducible. "An
  LLM could be a fallback for text the table misses, but its answer would still be
  checked against this same vocabulary before the rules trust it."
- 🎤 **"A new diagnosis isn't being caught"** → add its synonyms to
  `_WAITING_KEYWORDS` or `_EXCLUSION_KEYWORDS`. "It's a keyword table by design —
  auditable and testable. For open-ended coverage I'd add an LLM fallback that maps
  onto the *same* policy keys."

---

## W12. File-by-file — Part 6: the LLM layer

### `app/llm/client.py` — the AI client (and the off switch)
- **`LLMClient` (ABC)** — an *interface* with three methods:
  `classify_document`, `extract_document`, `generate_explanation`. **Nodes depend
  on this interface, not on Anthropic.** That's why tests pass a *fake* client and
  exercise all the LLM-handling paths with zero network calls.
- **`AnthropicLLMClient`** — the real one. Calls Claude's Messages API with
  **vision**: it attaches the actual image/PDF bytes as a content block, so Claude
  *reads the document* (handwritten scripts, stamped bills, phone photos). Has a
  small **retry** (`_create`) for transient failures, tolerant JSON parsing
  (`_parse_json_object` handles ```` ```json ```` fences), and validates extraction
  into `ExtractedDocument` before returning.
- **`build_llm_client(settings)`** — the factory. Returns a client **only if**
  `use_llm` is true *and* an API key exists; otherwise returns **`None`**. When it's
  `None`, the nodes use deterministic fallbacks. **This is the whole "works offline"
  story** — no key → no client → deterministic path → 12/12 eval.
- **Failure model:** every method raises `LLMError` on any provider/parse problem;
  nodes catch it and degrade. The LLM can never crash the request.
- 🎤 **"Swap Anthropic for OpenAI"** → "Write an `OpenAILLMClient(LLMClient)` with
  the same three methods, return it from `build_llm_client`. Nothing else changes —
  the nodes only know the interface. That's the point of the abstraction."

### `app/llm/prompts.py` — the prompt text
- **What:** three string templates (classification, extraction, explanation), kept
  separate from logic so they can be tuned without touching code.
- **They ask for STRICT output** (JSON only, no prose) which the client then
  validates. The explanation prompt explicitly says "don't change numbers, keep any
  caveat, use ₹ not $".

---

## W13. File-by-file — Part 7: the API and UI

### `app/api/routes_claims.py` — the two front doors
- **`POST /claims`** — JSON body validated as `ClaimRequest`. The deterministic
  path (documents may carry pre-extracted `content`).
- **`POST /claims/upload`** — `multipart/form-data` with real files. It reads each
  file's bytes, base64-encodes them into `Document`s with `actual_type=None`, and
  runs the *same* pipeline — so vision classifies + extracts them.
- **`_run_pipeline`** (shared by both): grabs policy+graph off `app.state`
  (→ `503` if missing — *never decide without a policy*), mints `claim_id`, calls
  `graph.invoke(...)`, then assembles either a `BLOCKED` response (with
  `blocking_issues`) or a `DECIDED` response (decision + amount + reasons +
  confidence + explanation + breakdown + trace).
- **Error codes:** `422` bad body, `503` policy unavailable.
- 🎤 **"Add `GET /claims/{id}` to look up a past claim"** → "Today the system is
  in-memory, so there's nothing to look up — the claim + trace live only in the
  response. I'd add a datastore: persist the final state keyed by `claim_id` in
  `_run_pipeline`, then add a `GET /claims/{id}` route that reads it back. This is
  exactly the 'would change with more time' item in my architecture doc." *(This is
  your headline 'would change' answer — see Demo Beat 3 above.)*

### `app/api/routes_health.py` — readiness probe
- **`GET /health`** — reports `ok` or `degraded`. It's a *readiness* check, not just
  "is the process alive": if the policy failed to load it reports `degraded` and
  the member/category counts. One honest signal for operators and graders.

### `app/api/routes_ui.py` — the web page + samples
- **`GET /`** serves `app/static/index.html`. **`GET /sample-claims`** returns the
  12 test cases so the UI can offer them as one-click dropdown examples.

### `app/static/index.html` — the single-page UI
- **What:** one self-contained HTML file (no build step). Two modes: **Upload
  documents** (drag in images/PDFs → `/claims/upload`) and **JSON (advanced)**
  (paste JSON or load a test case → `/claims`). Renders the decision banner, the
  payout, the "how we calculated" waterfall, and the full processing trace.
- **Why a static file?** The brief needs *a* UI to submit and review; a tiny static
  page + two endpoints demonstrates the whole system (early-stop messages,
  decisions, trace) with zero frontend tooling. Light, purple-accent, "real claim
  page" feel.
- 🎤 **"Change the look / add a field to the form"** → it's plain HTML/CSS/JS in
  this one file. No framework, no rebuild — edit and refresh.

---

## W14. File-by-file — Part 8: the data files

### `policy_terms.json` — the rulebook data (read-only at runtime)
- The complete policy: coverage limits, the six OPD categories with their co-pay /
  network-discount / sub-limits, waiting periods, exclusions, pre-auth, network
  hospitals, submission rules, fraud thresholds, and the **member roster**.
- **The golden rule (the brief insists on this):** *don't hardcode policy logic —
  read it from this file.* Every number the engine uses (₹500 minimum, 30-day
  deadline, 90-day diabetes wait, 20% discount, ₹5,000 per-claim limit) comes from
  here. Change the file → behavior changes, no code edit.
- 🎤 **"Bump the per-claim limit to ₹10,000"** → edit `coverage.per_claim_limit`
  in this file, restart. "No code change — that's the point of loading rules from
  the policy."

### `test_cases.json` — the 12 graded scenarios (read-only)
- Each case has an `input` (what's submitted) and an `expected` block with either a
  `decision` + `approved_amount` or a `system_must` list of behaviors. The eval
  script and the tests both read this so we're tied to the exact graded inputs.

---

## W15. File-by-file — Part 9: tests

**Why tests matter here:** the brief says "a system with no tests is incomplete,"
and Engineering Quality is 25%. There are ~67 tests; `pytest` runs them all.

- **`conftest.py`** — shared fixtures. `client` wraps the app in a `TestClient`
  *used as a context manager* (the `with` is what triggers FastAPI's lifespan, so
  policy+graph actually load). `policy` loads the real policy for pure-logic tests.
  `_disable_llm` (autouse) forces `USE_LLM=false` so the suite is offline/
  deterministic — the LLM paths are tested separately with a fake.
- **`helpers.py`** — loads scenarios straight from `test_cases.json` so tests use
  the exact graded inputs.
- **`test_rules.py`** — the meat: co-pay-only (TC004 → 1350), discount-before-co-pay
  (TC010 → 3240), per-claim reject (TC008), exclusion-beats-waiting (TC012),
  degraded lowers confidence (TC011), min amount, submission window, annual limit
  caps, and the composed-confidence bounds.
- **`test_llm_nodes.py`** — passes a *fake* `LLMClient` to test classify/extract/
  explain behavior and failure handling without any network.
- **`test_document_verifier.py`, `test_normalization.py`, `test_policy_loader.py`,
  `test_claim_models.py`, `test_config.py`** — unit tests for each pure piece.
- **`test_pipeline.py`, `test_claims_endpoint.py`, `test_health.py`** — wire-level:
  the full graph and the HTTP endpoints.
- 🎤 **"How would you test a new rule?"** → "Add a case to `test_rules.py` that
  builds a `ClaimRequest`, calls `adjudicate(...)` directly (no HTTP needed since
  the engine is pure), and asserts the decision + reason + a trace line. Pure
  functions make this a one-liner."

---

## W16. File-by-file — Part 10: scripts and docs

### `scripts/run_eval.py` — generates the eval report
- Runs all 12 cases offline through the real app (`TestClient`) and checks each
  against its `system_must` requirements — not just the decision, but message
  specificity, eligibility dates, confidence bounds, fraud signals, the discount
  breakdown. Writes `docs/EVAL_REPORT.md`. Currently **12/12**.
- The `CHECKS` dict is the interesting part: per-case lambdas that assert each
  required behavior. This is your proof you met the brief, not just "it runs".

### `scripts/make_sample_docs.py` & `scripts/run_vision_demo.py`
- `make_sample_docs.py` generates sample document images into `samples/`.
- `run_vision_demo.py` uploads them through the *real* Claude vision path (needs an
  API key) and writes `docs/VISION_DEMO.md` — proof the AI path actually works on
  images, not just on injected JSON.

### `docs/`
- **`architecture.md`** — the master design doc (the *why*): problem, the
  perception/cognition/communication split, the rule engine, financial order,
  confidence, observability, failure handling, **decision log**, **risk register**,
  **scaling to 10×**, and a per-test-case routing map. *Read this the night before
  the interview.*
- **`TECHNICAL_DOCUMENTATION.md`** — file-by-file reference + component contracts
  (input/output/errors for each component) — the brief's "Component Contracts"
  deliverable.
- **`EVAL_REPORT.md`** — the 12/12 results with full traces.
- **`VISION_DEMO.md`** — the live vision runs.
- **`DEMO_SCRIPT.md`** — this file (the video storyboard + this walkthrough).

---

## W17. The 12 test cases cheat sheet

Memorize this table — interviewers often point at a case and ask "what happens and
why?"

| TC | Name | Result | The mechanism (one line) |
|---|---|---|---|
| **TC001** | Wrong document | BLOCKED | Consultation needs PRESCRIPTION+HOSPITAL_BILL; got 2× prescription → missing doc, specific message |
| **TC002** | Unreadable doc | BLOCKED | `quality=UNREADABLE` → "re-upload this file; NOT rejected" |
| **TC003** | Patient mismatch | BLOCKED | Rajesh vs Arjun on different docs → names listed, stop |
| **TC004** | Clean consultation | APPROVED ₹1350 | 10% co-pay on ₹1500, no network discount |
| **TC005** | Waiting period | REJECTED | Joined 2024-09-01 + 90-day diabetes wait → eligible 2024-11-30 |
| **TC006** | Dental partial | PARTIAL ₹8000 | Root canal covered, teeth whitening excluded (per-line reasons) |
| **TC007** | MRI no pre-auth | REJECTED | MRI > ₹10k needs pre-auth, none given |
| **TC008** | Per-claim limit | REJECTED | ₹7500 > ₹5000 limit (both numbers in message) |
| **TC009** | Same-day fraud | MANUAL_REVIEW | 3 prior + this = 4 > limit of 2; signals listed |
| **TC010** | Network discount | APPROVED ₹3240 | 20% discount FIRST (→3600), then 10% co-pay (→3240) |
| **TC011** | Component failure | APPROVED, degraded | `simulate_component_failure` → trace FAILED, confidence 0.65, no crash |
| **TC012** | Excluded treatment | REJECTED | Obesity/bariatric ∈ exclusions; exclusion beats waiting |

Three stop at the gate (TC001–003). Nine reach the engine. All 12 produce a full
trace.

---

## W18. Live "change it" drills

This is the section to rehearse. The brief literally says *"we will ask you to
extend it live."* For each, know the **file** and the **one-sentence answer**.

| They ask… | Open this | Say this |
|---|---|---|
| "Add a new rule (e.g. reject expired policy)" | `models/decision.py` + `rules/engine.py` + `test_rules.py` | "New `RejectionReason` enum value; insert a pure rule block at the right precedence that reads dates from the policy and `record()`s a trace line; add a unit test. Precedence placement is the real decision." |
| "Add a new document type" | `models/claim.py` (`DocumentType` enum) + `policy_terms.json` (`document_requirements`) | "Add the enum value and wire it into the category's required/optional list in the policy file." |
| "Add a new claim category" | `models/claim.py` (`ClaimCategory`) + `policy_terms.json` (`opd_categories` + `document_requirements`) | "Enum value + a policy entry with its limits/co-pay; the engine and `OpdCategory` model already handle it generically." |
| "Change discount/co-pay order" | `rules/financials.py` | "Swap two lines in `compute_financials` — but I'd flag that TC010 requires discount-first and the payout changes." |
| "Make the LLM calls parallel/async" | `llm/client.py` + `graph/nodes/extract.py` + `routes_claims.py` | "Today vision calls are synchronous and sequential. I'd make them `async` and `asyncio.gather` the per-document extraction; and move `POST /claims` to enqueue-and-poll for throughput. Documented as a trade-off in architecture.md §18." |
| "Persist claims / add `GET /claims/{id}`" | `routes_claims.py` (+ a new store) | "It's in-memory by design for a 2–3-day build. I'd persist the final state by `claim_id` (Postgres + object storage for docs) and add a read route. architecture.md §18." |
| "Swap Claude for another provider" | `llm/client.py` | "Implement the `LLMClient` interface for the new provider; return it from `build_llm_client`. Nodes only know the interface, so nothing else changes." |
| "What if the LLM hallucinates a field?" | `models/extraction.py` + `rules/engine.py` | "Output is Pydantic-validated before rules see it; a bad field fails validation → `LLMError` → degrade + lower confidence. And the LLM never decides — the rules do." |
| "How do I see why a claim was decided?" | the `trace` in the response | "Every node and every rule appends a `TraceEntry`. The full trace ships in the response, so any decision is reconstructable step-by-step without reading code." |
| "Make patient-matching tolerant of typos" | `verification/document_verifier.py` | "Add a similarity threshold in `_check_same_patient`; near-matches → MANUAL_REVIEW instead of auto-block. Keep it deterministic + tested." |
| "Scale to 10× load" | `docs/architecture.md` §18 | "Stateless app → horizontal scale; cache classify/extract by document hash; cheaper model for classification; async queue; move state+trace to a datastore; version policies by id." |

**The meta-answer that always works:** *"This is deterministic by design, so the
change is localized and testable. The decision logic is pure functions in
`rules/engine.py`, configuration lives in `policy_terms.json`, and the AI is behind
an interface — so most changes touch one file plus a test."*

---

## W19. Glossary

Words you should be able to define instantly if asked:

- **Adjudicate** — to make the claim decision. Our rule engine's main function.
- **Deterministic** — same input always gives the same output. (Our decisions are.)
- **Pure function** — depends only on its inputs, no hidden state, no side effects.
  Trivially testable. (Our rule engine is one.)
- **Pydantic** — Python library that validates data against a declared shape.
- **FastAPI** — the async Python web framework serving our endpoints.
- **LangGraph** — the library that wires our nodes + state + conditional edge.
- **Node / edge / state** — station / arrow / shared notebook (see W3).
- **Trace** — the ordered list of `TraceEntry` lines = our audit trail.
- **Early-stop gate** — `verify_documents`; the conditional edge that ends a claim
  before any decision when documents are bad.
- **Co-pay** — the % the member pays themselves. **Network discount** — the %
  knocked off because the hospital is in-network. Order: discount first, then
  co-pay (TC010).
- **Degraded** — a component failed; we continued, lowered confidence, and said so.
- **Idempotent** — running it twice has the same effect as once (e.g. our logging
  setup).
- **Composition root** — the one place everything is wired together: `create_app()`.

---

> **Revision tip:** the four files an interviewer is *most* likely to open are
> `rules/engine.py` (the decision order), `rules/financials.py` (the money order),
> `graph/builder.py` (the early-stop edge), and `verification/document_verifier.py`
> (the specific messages). Be able to talk through each from memory.

---

## W20. Eval vs Vision Demo — why are there TWO reports?

This confuses everyone at first. The secret: **both run the exact same system.
They test two *different halves* of it.** Tie it back to the one big idea —
**LLM = eyes (perception)**, **deterministic code = brain (cognition)**:

- **`EVAL_REPORT.md` tests the BRAIN** 🧠 — are the *decisions* correct?
- **`VISION_DEMO.md` tests the EYES** 👁️ — can Claude actually *read real images*?

### Side by side

| | **EVAL_REPORT.md** (the eval) | **VISION_DEMO.md** (the vision path) |
|---|---|---|
| Endpoint | `POST /claims` (JSON) | `POST /claims/upload` (real files) |
| Where the document data comes from | pre-typed JSON `content` (already filled in) | real `.png` images in `samples/` |
| Is the AI used? | ❌ no — offline, `USE_LLM=false` | ✅ yes — Claude vision reads the pixels |
| API key needed? | no | yes |
| Same result every time? | ✅ 100% deterministic | ⚠️ mostly, but AI can vary |
| Result | **12/12** cases pass | 3 real-image scenarios work end-to-end |
| Generated by | `scripts/run_eval.py` | `scripts/run_vision_demo.py` |

### Why split them (the key insight)

Data enters the system **two ways**, but **both go through the same decision
engine**:

```
EVAL:    JSON with content already filled   ─┐
                                             ├─→  SAME rule engine  →  decision
VISION:  real image → Claude reads it → fields ─┘
```

If the AI were mixed into the eval, the eval would be **flaky** — Claude might read
a number slightly differently one day, and then you couldn't tell whether the
*decision logic* broke or the *AI just misread the bill*. Feeding the eval clean
injected data **isolates the brain**, so 12/12 proves the decisions are correct
**repeatably**. The vision demo then **separately** proves the eyes work on real
files (correctly classified a prescription, caught a wrong document, flagged a
blurry one).

### The analogy (self-driving car) 🚗
- **Eval = the simulator** with perfect sensor data: *"when the car sees a stop
  sign, does it brake correctly?"* (brain)
- **Vision demo = a real road test** with real cameras: *"can the cameras actually
  SEE the stop sign?"* (eyes)

Kept separate so a dirty lens never fools you into thinking the braking logic broke.

### How each maps to the assignment
- **EVAL_REPORT.md** → Deliverable #4 ("run all 12 test cases"). ✅ 12/12.
- **VISION_DEMO.md** → proof of Requirement #3 ("extract from messy docs —
  handwritten, stamped, phone photos"). Shows the AI path genuinely works, not just
  on hand-typed JSON.

🎤 **Interview one-liner:** *"The eval is deterministic and offline — it proves my
decision engine is correct and reproducible. The vision demo is the live Claude
path on real images — it proves the perception layer actually reads messy
documents. Same pipeline, same rule engine; I just separated 'are the decisions
right?' from 'can the AI read the page?' so neither test contaminates the other."*
