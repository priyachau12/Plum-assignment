# Claims Processing System — Deep-Dive Q&A

> **How to read this file**
> Every answer is written in simple English. Each answer gives you: (1) a short direct answer, (2) the exact file + line where it happens (`file.py:line` — clickable), and (3) plain-English notes for any technical term used. Read the questions **in order** — they follow the real execution order of the system, so by the end you can draw the whole codebase from memory.
>
> Questions are grouped into 8 rounds + a final "master understanding" set, exactly like the study list.

---

## Part 0 — Foundation (read this first)

### 0.1 The 30-second mental model

This is an **OPD health-insurance claims processor**. A claim comes in (member id, policy, category, amount, documents). The system runs it down a **fixed assembly line** of 7 steps and returns one of: `BLOCKED` (a document problem — fix and resend) or `DECIDED` (`APPROVED` / `PARTIAL` / `REJECTED` / `MANUAL_REVIEW`) with the money math, reasons, confidence, a human explanation, and a full audit trace.

The assembly line (the "graph"):

```
START → intake → classify → verify_documents ──(blocking issue?)──► STOP → END
                                   │
                                   └──(clean)──► extract → normalize_diagnosis → adjudicate → explain → END
```

- **intake** — open the audit trail, look up the member in the policy.
- **classify** — figure out each document's type / readability / patient name.
- **verify_documents** — the early-stop gate (right docs? readable? same patient?).
- **extract** — pull structured fields out of each document.
- **normalize_diagnosis** — map free text ("Type 2 Diabetes") to policy vocabulary ("diabetes").
- **adjudicate** — the brain: run ordered deterministic rules → a decision + amount.
- **explain** — turn the decision into friendly member-facing text.

### 0.2 Glossary of terms (everything used below, in plain English)

| Term | Plain meaning |
|---|---|
| **API** | A way for other programs to talk to this system over HTTP. |
| **Endpoint / route** | One URL the system answers, e.g. `POST /claims`. |
| **FastAPI** | The Python web framework that receives HTTP requests and calls our functions. |
| **Uvicorn** | The server program that runs FastAPI (`uvicorn app.main:app`). |
| **Handler** | The Python function that runs when a route is hit (e.g. `submit_claim`). |
| **Pydantic** | A library that validates data shapes. If JSON is the wrong shape, it errors automatically. |
| **BaseModel** | A Pydantic class you inherit to define a validated data shape. |
| **Validation** | Checking incoming data is correct (right types, required fields present) before using it. |
| **422 / 503 / 500** | HTTP error codes: 422 = your input was invalid; 503 = service not ready (no policy); 500 = server crashed (we avoid this). |
| **lifespan** | Code that runs once at startup and once at shutdown (loads policy + builds graph once). |
| **app.state** | A shared "shelf" on the app where startup stores the loaded policy, graph, and LLM client. |
| **LangGraph** | A library to build a **workflow as a graph** of steps (nodes) connected by arrows (edges). |
| **StateGraph** | LangGraph's graph type where every node reads and updates one shared **state** object. |
| **Node** | One step in the graph (a Python function that takes state and returns updates). |
| **Edge** | An arrow saying "after this node, go to that node". |
| **Conditional edge** | An arrow that picks the next node based on a small routing function. |
| **START / END** | LangGraph's built-in entry and exit markers of the graph. |
| **State** | The single shared object that travels through every node (here: `ClaimState`). |
| **TypedDict** | A dictionary with a fixed, typed set of keys (used to define `ClaimState`). |
| **Reducer (`operator.add`)** | A merge rule. For list fields it means "append my new items" instead of "overwrite". |
| **`functools.partial`** | Pre-fills some arguments of a function. We use it to "bake" the policy/LLM into each node. |
| **invoke** | The call that actually runs the compiled graph from START to END. |
| **Deterministic** | Same input → exactly same output, every time. No randomness, no AI guessing. |
| **LLM** | Large Language Model (here Claude). Used only for 3 narrow text/vision tasks. |
| **Vision** | Giving the model an image/PDF so it can read a real document photo. |
| **Trace** | The step-by-step audit log of everything the system checked (our observability). |
| **Blocking issue** | A document problem that stops the claim before any decision. |
| **Degraded** | A flag meaning "a component failed, we continued anyway with lower confidence". |
| **Adjudicate** | Insurance word for "decide the claim" (approve / reject / etc.). |
| **Co-pay** | The % the member pays themselves; the insurer pays the rest. |
| **Network discount** | A discount applied when treatment is at a partner ("network") hospital. |
| **Waiting period** | A time after joining during which certain conditions aren't covered yet. |
| **Pre-authorization (pre-auth)** | Prior approval the member must get for expensive tests (e.g. MRI). |
| **Exclusion** | A condition/treatment the policy never covers (e.g. obesity/bariatric). |
| **Per-claim limit** | The maximum payable on a single claim. |
| **Annual limit** | The maximum payable across the whole policy year. |
| **Confidence score** | A 0–1 number for how sure the system is about this decision. |
| **Agentic** | An AI that decides *what to do next* on its own (chooses tools, loops). This system is **not** that — see below. |

### 0.3 Why this is NOT "agentic" or "multi-agentic" (important)

People hear "LangGraph + Claude" and assume "AI agent". This system is deliberately the opposite. Here is the precise reason.

**What "agentic" means:** an LLM sits *in the control loop*. It looks at the situation and decides, on its own, which tool to call next, whether to loop again, and when it's done. The LLM has **authority over the flow and the outcome**. "Multi-agentic" = several such LLM agents talking to and delegating to each other.

**What this system actually does:**

1. **The flow is fixed in code, not chosen by an LLM.** All the arrows are hardcoded in `app/graph/builder.py:65-76`. There is exactly **one** branch in the whole graph — after `verify_documents` — and it is decided by a plain Python `if`, not a model:

   ```python
   # app/graph/builder.py:47-49
   def _after_document_verification(state: ClaimState) -> str:
       return "stop" if state.get("blocking_issues") else "continue"
   ```
   No LLM is consulted to route anything. There are no loops. It is a straight pipeline (a state machine).

2. **The actual decision is 100% deterministic — no AI.** Approve / reject / partial / manual-review and every rupee of the amount are computed by ordered Python rules in `app/rules/engine.py` and `app/rules/financials.py`. The LLM is never asked "should we approve this?". This is why the same claim always gives the same answer (reproducible, auditable, regulator-safe).

3. **The LLM is used only as a narrow "tool" at 3 fixed points**, and each has a deterministic fallback:
   - `classify_document` — what type is this scan? (only for real uploads)
   - `extract_document` — read fields off a real photo/PDF
   - `generate_explanation` — reword the final decision in friendly language (it is forbidden from changing numbers — see the prompt at `app/llm/prompts.py:36-48`).

   The model perceives and phrases. It never **decides** and never **routes**. If it fails, the system degrades and continues (`degraded=True`), it does not hand control to the model.

**So the correct label is:** a **deterministic, rule-based workflow (orchestrated by LangGraph) with three optional, sandboxed AI assists** — not an agent, and not a multi-agent system. LangGraph here is used as a *workflow engine / state machine*, even though the same library *can* be used to build agents. The design choice is intentional: in insurance, an explainable, reproducible rulebook beats a model that "decides" money. (See Q136–Q139 for the trade-offs.)

---

# Round 1 — Entry Point & Request Flow

### Q1. When I hit `POST /claims`, what is the exact first Python function that executes?

**Answer (English):** The first function *in our code* is `submit_claim(...)` in `app/api/routes_claims.py:90`. But just before it, FastAPI itself runs first: it reads the JSON body and validates it into a `ClaimRequest` object (because the handler declares `claim: ClaimRequest` as a parameter). If validation fails, FastAPI returns `422` and `submit_claim` is never called.

```python
# app/api/routes_claims.py:89-92
@router.post("/claims", response_model=ClaimProcessingResult)
def submit_claim(claim: ClaimRequest, request: Request) -> ClaimProcessingResult:
    """Submit a claim as JSON (documents may carry pre-extracted `content`)."""
    return _run_pipeline(claim, request)
```

**Term:** *Handler* = the function tied to a route. *422* = "your input was invalid".

---

### Q2. Show the complete call chain from FastAPI endpoint to `graph.invoke()`.

**Answer (English):**

```
HTTP POST /claims
  → FastAPI validates body → ClaimRequest        (Pydantic, automatic)
  → submit_claim(claim, request)                  app/api/routes_claims.py:90
      → _run_pipeline(claim, request)             app/api/routes_claims.py:39
          → graph = request.app.state.graph        (the compiled graph, built at startup)
          → graph.invoke({"claim_id": ..., "request": claim})   app/api/routes_claims.py:55
```

So: `submit_claim` → `_run_pipeline` → `graph.invoke(...)`. Both the JSON endpoint and the upload endpoint funnel into the **same** `_run_pipeline`, so they behave identically from here on.

---

### Q3. Which file contains the route handler?

**Answer (English):** `app/api/routes_claims.py`. It defines an `APIRouter` (line 36) with two handlers — `submit_claim` (`POST /claims`, line 90) and `submit_claim_upload` (`POST /claims/upload`, line 96) — plus the shared `_run_pipeline` helper (line 39). The router is attached to the app in `app/main.py:87` via `app.include_router(routes_claims.router)`.

---

### Q4. Which function creates the initial `ClaimState`?

**Answer (English):** There is **no dedicated builder function**. The initial state is just the plain dict passed into `graph.invoke(...)`:

```python
# app/api/routes_claims.py:52-55
claim_id = "CLM_" + uuid.uuid4().hex[:8].upper()
...
final_state = graph.invoke({"claim_id": claim_id, "request": claim})
```

LangGraph takes that dict `{"claim_id": ..., "request": ...}` as the starting `ClaimState`. Only two keys are set at the start; every other field in `ClaimState` is filled in later by the nodes. The `claim_id` is generated one line earlier (line 52) using a random UUID.

**Term:** *UUID* = a random unique identifier, here shortened to 8 hex chars, e.g. `CLM_3F9A1C20`.

---

### Q5. How is request validation happening before the graph starts?

**Answer (English):** There are **two validation layers** before any node runs:

1. **Body validation (automatic).** Because `submit_claim` declares `claim: ClaimRequest`, FastAPI + Pydantic validate the JSON into a `ClaimRequest`. Wrong types / missing required fields → automatic `422`. For the upload endpoint, the `ClaimRequest(...)` is built by hand and wrapped in a `try/except ValidationError` that raises `422` itself:
   ```python
   # app/api/routes_claims.py:131-144
   try:
       claim = ClaimRequest(member_id=member_id, ...)
   except ValidationError as exc:
       raise HTTPException(status_code=422, detail=exc.errors()) from exc
   ```
2. **Readiness check.** `_run_pipeline` checks the policy and graph actually loaded at startup; if not, it returns `503` (never decide without a policy):
   ```python
   # app/api/routes_claims.py:44-50
   if policy is None or graph is None:
       raise HTTPException(status_code=503, detail="Policy not loaded; ...")
   ```

Only after both pass does `graph.invoke(...)` run.

---

### Q6. Which Pydantic model validates incoming claims?

**Answer (English):** `ClaimRequest`, defined in `app/models/claim.py:130-149`. It is the system's **trust boundary** — everything downstream gets typed, validated data. It also pulls in nested models: `Document` (`claim.py:77`), `ClaimHistoryEntry` (`claim.py:115`), and three enums (`ClaimCategory`, `DocumentType`, `DocumentQuality`).

**Term:** *Trust boundary* = the single point where untrusted outside input is checked once, so the rest of the code can trust it.

---

### Q7. What fields are mandatory in `ClaimRequest` and why?

**Answer (English):** Mandatory fields (no default value) are:

| Field | Why it's required |
|---|---|
| `member_id` | Needed to look the person up in the policy roster (eligibility). |
| `policy_id` | Must match the loaded policy; guards against cross-policy claims. |
| `claim_category` | Drives required-documents, sub-limits, co-pay, discount rules. Enum-validated. |
| `treatment_date` | Needed for waiting-period and submission-deadline math. |
| `claimed_amount` | The money being claimed; `Field(gt=0)` forces it to be positive. |
| `documents` | `Field(min_length=1)` forces at least one document — you can't claim with nothing. |

```python
# app/models/claim.py:133-138
member_id: str
policy_id: str
claim_category: ClaimCategory
treatment_date: date
claimed_amount: float = Field(gt=0, description="Amount claimed, in INR; must be positive")
documents: list[Document] = Field(min_length=1, description="At least one document")
```

Everything else (`hospital_name`, `ytd_claims_amount`, `submission_date`, `claims_history`, `pre_authorization_obtained`, `simulate_component_failure`) is **optional** with a sensible default, because those only appear in some claims/test cases (`claim.py:140-149`).

**Term:** *Enum* = a fixed list of allowed values; an unknown category is rejected at the edge.

---

### Q8. How does `POST /claims` differ from `POST /claims/upload`?

**Answer (English):** They are two **front doors to the same pipeline**:

| | `POST /claims` | `POST /claims/upload` |
|---|---|---|
| Body | JSON (`ClaimRequest`) | multipart form + real files |
| Documents | may carry `actual_type` + pre-extracted `content` | raw image/PDF bytes; `actual_type = None` |
| Document type | declared by caller (trusted) | resolved by the **vision classifier** |
| Field extraction | uses the provided `content` (no AI) | AI reads the file (`extract` node) |
| Used by | the 12 deterministic test cases | real-world uploads / the vision demo |
| Then | both call `_run_pipeline` → same graph | same |

So the **only** real difference is *how the documents arrive*. The JSON path is the deterministic eval path; the upload path is the live vision path. Code: JSON handler `routes_claims.py:90`; upload handler `routes_claims.py:96-146`.

---

### Q9. For an upload request, where are files converted into `Document` objects?

**Answer (English):** In the `for` loop inside `submit_claim_upload`, `app/api/routes_claims.py:113-126`. Each uploaded file's raw bytes are read, base64-encoded, and wrapped in a `Document` with `actual_type=None` (so the vision classifier resolves the type later):

```python
# app/api/routes_claims.py:113-126
documents: list[Document] = []
for index, upload in enumerate(files, start=1):
    raw = await upload.read()
    if not raw:
        continue
    documents.append(
        Document(
            file_id=f"F{index:03d}",
            file_name=upload.filename,
            media_type=upload.content_type,
            data_base64=base64.b64encode(raw).decode("ascii"),
            actual_type=None,  # resolved by the vision classifier
        )
    )
```

If no non-empty file is uploaded, it raises `422` (`routes_claims.py:128-129`).

**Term:** *base64* = a way to turn binary file bytes into plain text so they can sit inside a JSON/model field.

---

### Q10. At what exact line does execution leave FastAPI and enter LangGraph?

**Answer (English):** `app/api/routes_claims.py:55`:

```python
final_state = graph.invoke({"claim_id": claim_id, "request": claim})
```

Before this line we are in FastAPI/our handler code. The moment `graph.invoke(...)` is called, control passes into the **compiled LangGraph**, which runs `intake → classify → verify_documents → ...` and only returns once it reaches `END`. The returned `final_state` is then read back (lines 57-86) to build the HTTP response.

---

# Round 2 — LangGraph Architecture

### Q11. Show me `builder.py` and explain every line.

**Answer (English):** Full file is `app/graph/builder.py`. The two functions that matter:

```python
# app/graph/builder.py:47-49  — the router for the one branch
def _after_document_verification(state: ClaimState) -> str:
    """The fork: a blocked claim stops; a clean one continues to extraction."""
    return "stop" if state.get("blocking_issues") else "continue"

# app/graph/builder.py:52-84  — build + wire + compile the pipeline
def build_graph(policy: Policy, llm: LLMClient | None = None):
    graph = StateGraph(ClaimState)                 # 54: empty graph over our state type

    # 57-63: register the 7 nodes. partial() bakes policy/llm into each node so its
    #        signature stays (state) -> dict.
    graph.add_node("intake", partial(intake, policy=policy))
    graph.add_node("classify", partial(classify, llm=llm))
    graph.add_node("verify_documents", partial(verify_documents, policy=policy))
    graph.add_node("extract", partial(extract, llm=llm))
    graph.add_node("normalize_diagnosis", partial(normalize_diagnosis, policy=policy))
    graph.add_node("adjudicate", partial(adjudicate, policy=policy))
    graph.add_node("explain", partial(explain, llm=llm))

    # 65-76: the wiring (edges)
    graph.add_edge(START, "intake")                # 65: entry
    graph.add_edge("intake", "classify")           # 66
    graph.add_edge("classify", "verify_documents") # 67
    graph.add_conditional_edges(                    # 68-72: the only branch
        "verify_documents",
        _after_document_verification,
        {"stop": END, "continue": "extract"},
    )
    graph.add_edge("extract", "normalize_diagnosis")   # 73
    graph.add_edge("normalize_diagnosis", "adjudicate")# 74
    graph.add_edge("adjudicate", "explain")            # 75
    graph.add_edge("explain", END)                     # 76

    compiled = graph.compile()                         # 78: freeze into a runnable graph
    return compiled
```

Line-by-line meaning:
- **54** `StateGraph(ClaimState)` — create an empty graph whose shared state is `ClaimState`.
- **57-63** `add_node(name, fn)` — register each step. `partial(intake, policy=policy)` makes a new function that already knows the policy, so LangGraph can call it with just `(state)`.
- **65-76** `add_edge(a, b)` — "after a, run b". `add_conditional_edges(node, router, mapping)` — after `verify_documents`, call `_after_document_verification`; if it returns `"stop"` jump to `END`, if `"continue"` go to `extract`.
- **78** `compile()` — turn the definition into an executable object (the thing `graph.invoke` runs).

---

### Q12. How is the graph created?

**Answer (English):** With `StateGraph(ClaimState)` at `app/graph/builder.py:54`. This makes an empty graph that knows its shared-state type is `ClaimState`. You then add nodes and edges to it, and finally `.compile()` it (line 78) into a runnable object. This whole `build_graph(...)` runs **once** at startup (`app/main.py:72`) and the compiled graph is stored on `app.state.graph`.

**Term:** *Compile* = lock the node/edge definition into an optimized, runnable form. After compiling you don't change the structure, you just `invoke` it.

---

### Q13. Where is `START` defined?

**Answer (English):** `START` (and `END`) are **built-in constants from LangGraph**, imported at `app/graph/builder.py:31`:

```python
from langgraph.graph import END, START, StateGraph
```

They are not our values — they are LangGraph's special markers for "the entry point" and "the exit point" of the graph. We connect them with `graph.add_edge(START, "intake")` (line 65) and `graph.add_edge("explain", END)` (line 76).

---

### Q14. Which node executes first?

**Answer (English):** `intake`, because of the edge `graph.add_edge(START, "intake")` at `app/graph/builder.py:65`. When you call `graph.invoke(...)`, LangGraph starts at `START`, follows that edge, and runs the `intake` node first.

---

### Q15. How are nodes registered into the graph?

**Answer (English):** With `graph.add_node("name", function)` — seven calls at `app/graph/builder.py:57-63`. Each node function is wrapped in `functools.partial(...)` to pre-fill its dependency:

- deterministic steps get the **policy**: `partial(intake, policy=policy)`
- AI-allowed steps get the optional **llm client**: `partial(classify, llm=llm)`

This keeps every node's runtime signature uniform — LangGraph always calls it as `node(state)` and gets back a dict of updates.

**Term:** *`functools.partial(f, x=1)`* = makes a new function that calls `f` with `x` already filled in, so callers don't have to pass it.

---

### Q16. Where is the conditional edge defined?

**Answer (English):** `app/graph/builder.py:68-72`:

```python
graph.add_conditional_edges(
    "verify_documents",
    _after_document_verification,
    {"stop": END, "continue": "extract"},
)
```

This says: after the `verify_documents` node runs, call the router function `_after_document_verification(state)`; map its returned string to a destination — `"stop"` → `END`, `"continue"` → `extract`. This is the only place the pipeline can branch.

---

### Q17. How does `_after_document_verification` work?

**Answer (English):** It is a tiny **pure router** that reads the state and returns a label string (`app/graph/builder.py:47-49`):

```python
def _after_document_verification(state: ClaimState) -> str:
    return "stop" if state.get("blocking_issues") else "continue"
```

It checks one thing: did `verify_documents` put any `blocking_issues` into the state? If yes → `"stop"`; if the list is empty/absent → `"continue"`. It makes **no AI call** and changes no state — it only *chooses a path*.

---

### Q18. What values can `_after_document_verification` return?

**Answer (English):** Exactly two strings: `"stop"` or `"continue"`. These are the keys of the mapping passed to `add_conditional_edges` (`builder.py:71`): `"stop"` routes to `END`, `"continue"` routes to the `extract` node. Any other return value would be an error (no matching route), but the function can only ever return these two.

---

### Q19. How does LangGraph decide which node runs next?

**Answer (English):** By following the **edges** you defined:

- For a **normal edge** (`add_edge("a", "b")`) the answer is fixed: after `a`, always run `b`.
- For the **conditional edge**, LangGraph runs the router function (`_after_document_verification`), takes the string it returns, looks it up in the mapping `{"stop": END, "continue": "extract"}`, and goes there.

There is no AI and no hidden logic — the next node is 100% determined by the edges + that one Python router. This is why it's a deterministic state machine, not an agent (see Part 0.3).

---

### Q20. If `verify_documents` returns blocking issues, which nodes are skipped?

**Answer (English):** Everything after the gate is skipped: **`extract`, `normalize_diagnosis`, `adjudicate`, and `explain`**. When `blocking_issues` is non-empty, the router returns `"stop"` and the graph jumps straight to `END`. So a blocked claim (TC001–TC003) never gets extracted and never gets a decision — it returns `status=BLOCKED` with the specific fix-it message. The `verify_documents` node also sets `status=BLOCKED` (`app/graph/nodes/verify_documents.py:39-41`).

---

### Q21. Draw the exact runtime graph from code.

**Answer (English):** Built from the edges at `builder.py:65-76`:

```
            START
              │
            intake                      (policy looked up, trace opened)
              │
           classify                     (doc type / readable / patient name)
              │
        verify_documents                (right docs? readable? same patient?)
              │
   ┌──────────┴───────────┐
 "stop"                "continue"
   │                       │
  END                   extract          (structured fields per document)
                           │
                  normalize_diagnosis    (free text → policy vocabulary)
                           │
                       adjudicate         (ordered rules → decision + amount)
                           │
                        explain           (friendly member-facing text)
                           │
                          END
```

Two ways to reach `END`: the early-stop (`"stop"`) and the full clean path (`explain → END`).

---

### Q22. How is `END` reached?

**Answer (English):** Two routes, both defined in `builder.py`:
1. **Early stop:** the conditional edge maps `"stop"` → `END` (line 71). Reached when `verify_documents` produced blocking issues.
2. **Clean finish:** the explicit edge `graph.add_edge("explain", END)` (line 76). Reached after a full decision is explained.

When `END` is reached, `graph.invoke(...)` returns the final accumulated state back to `_run_pipeline` (`routes_claims.py:55`), which reads it to build the response.

---

# Round 3 — State Management

> The "state" is the single object that travels through every node — think of it as a **clipboard** passed down the assembly line. Each worker reads it and clips on what they produced.

### Q23. Show me `ClaimState` in `state.py`.

**Answer (English):** Full definition, `app/graph/state.py:34-50`:

```python
class ClaimState(TypedDict, total=False):
    claim_id: str
    request: ClaimRequest
    member: Member | None
    status: ProcessingStatus
    trace: Annotated[list[TraceEntry], operator.add]
    blocking_issues: Annotated[list[BlockingIssue], operator.add]

    # Working fields filled in as the claim moves down the line.
    classified_docs: dict[str, str]
    extracted_content: dict[str, Any]
    extraction_confidence: float  # avg field-extraction confidence (1.0 on the inject path)
    normalized_diagnosis: DiagnosisMatch
    degraded: bool
    adjudication_result: DecisionResult
    explanation: str
```

It's a `TypedDict` (a dictionary with a fixed, typed set of keys). `total=False` means **every key is optional** — the state starts almost empty and fills in as it goes.

**Term:** *`TypedDict`* = a normal Python dict at runtime, but with declared key names and types so editors/type-checkers can catch mistakes.

---

### Q24. What fields exist inside `ClaimState`?

**Answer (English):** 13 fields, each owned (written) by a specific step (`state.py:34-49`, ownership map in the docstring `state.py:8-15`):

| Field | Type | Written by |
|---|---|---|
| `claim_id` | `str` | set at `invoke` (the endpoint) |
| `request` | `ClaimRequest` | set at `invoke` |
| `member` | `Member \| None` | `intake` |
| `status` | `ProcessingStatus` | `verify_documents` (BLOCKED) / `adjudicate` (DECIDED) |
| `trace` | `list[TraceEntry]` (append) | **every** node |
| `blocking_issues` | `list[BlockingIssue]` (append) | `verify_documents` |
| `classified_docs` | `dict[str,str]` | `classify` |
| `extracted_content` | `dict[str,Any]` | `extract` |
| `extraction_confidence` | `float` | `extract` |
| `normalized_diagnosis` | `DiagnosisMatch` | `normalize_diagnosis` |
| `degraded` | `bool` | `extract` |
| `adjudication_result` | `DecisionResult` | `adjudicate` |
| `explanation` | `str` | `explain` |

---

### Q25. Which fields are input fields?

**Answer (English):** Only two are set *before* the graph runs (in `graph.invoke({...})` at `routes_claims.py:55`):
- `claim_id` — the generated id.
- `request` — the validated `ClaimRequest`.

Everything else is empty at START. (You could also call `member` a "near-input" since it's just a lookup of `request.member_id`, but it is produced inside `intake`, not passed in.)

---

### Q26. Which fields are generated during processing?

**Answer (English):** All the rest — they appear as the claim moves down the line:
- `member` (intake), `classified_docs` (classify), `blocking_issues` + `status=BLOCKED` (verify_documents), `extracted_content` + `extraction_confidence` + `degraded` (extract), `normalized_diagnosis` (normalize_diagnosis), `adjudication_result` + `status=DECIDED` (adjudicate), `explanation` (explain). `trace` grows at every node.

---

### Q27. How does state move from one node to another?

**Answer (English):** LangGraph holds **one running state object**. The sequence per node is:
1. LangGraph calls the node with the current state: `node(state)`.
2. The node reads what it needs (e.g. `state["request"]`) and returns a **small dict of just its updates**, e.g. `return {"member": member, "trace": entries}`.
3. LangGraph **merges** that dict into the running state.
4. The next node is called with the merged (now bigger) state.

So state isn't "passed by the node" — the node only returns a delta, and LangGraph carries the accumulated state to the next node. Example: `intake` returns `{"member": ..., "trace": [...]}` (`app/graph/nodes/intake.py:70`).

---

### Q28. Does a node mutate state or return updates?

**Answer (English):** Nodes **return updates** — a dict of only the keys they changed. They do not rebuild or replace the whole state. You can see this in every node's `return {...}` (e.g. `verify_documents.py:35-41`, `adjudicate.py:44-48`, `normalize_diagnosis.py:33-50`).

**One honest nuance:** the `classify` node *does* mutate the `Document` objects living inside `request` — it writes `doc.actual_type`, `doc.quality`, `doc.patient_name_on_doc` back onto each document (`classify.py:83-88`). That's deliberate: it lets the later gate, extractor, and rules read the resolved type straight off the document regardless of whether it was declared or AI-classified. But for the **state keys themselves**, the pattern is always "return a delta", never "mutate the state dict in place".

---

### Q29. How does LangGraph merge state updates?

**Answer (English):** Per key, with two different rules:
- **Plain fields** (no annotation) → **overwrite** (last writer wins). The returned value replaces whatever was there. e.g. `member`, `status`, `degraded`, `adjudication_result`.
- **Reducer fields** (annotated with `operator.add`) → **combine/append**. The returned list is concatenated onto the existing list. Only `trace` and `blocking_issues` use this (`state.py:39-40`).

The reducer is the `operator.add` in `Annotated[list[TraceEntry], operator.add]`. LangGraph sees it and, instead of overwriting, calls `old + new`.

**Term:** *Reducer* = the merge function for a field. Default reducer = overwrite; `operator.add` = append.

---

### Q30. Why is `trace` declared as `Annotated[list, operator.add]`?

**Answer (English):** So that **every node can return only its own new trace entries and LangGraph stitches them together** into one growing audit log — instead of each node's return overwriting the previous trace.

```python
# app/graph/state.py:39
trace: Annotated[list[TraceEntry], operator.add]
```

Without the reducer, `intake` returning `{"trace": [e1]}` then `classify` returning `{"trace": [e2]}` would leave the state with only `[e2]` (overwrite) — we'd lose `intake`'s note. With `operator.add`, the state ends up `[e1, e2, ...]` — the full step-by-step trace, which is the system's observability. Each node just appends; it never has to read or carry the whole trace.

---

### Q31. How are blocking issues accumulated?

**Answer (English):** The same way as `trace` — `blocking_issues` is also a reducer field (`state.py:40`):

```python
blocking_issues: Annotated[list[BlockingIssue], operator.add]
```

In practice the document verifier runs all three checks (required docs, readability, same-patient) and **already combines** their issues into one list before returning it (`document_verifier.py:181-185`), and the `verify_documents` node returns that list (`verify_documents.py:36-38`). The `operator.add` reducer means even if issues were produced in more than one place, they'd all survive (append, not replace) rather than the last one wiping the others.

---

### Q32. What happens if two nodes update the same field?

**Answer (English):** Depends on the field's reducer:
- **Reducer field** (`trace`, `blocking_issues`): both contributions are **kept and appended** (`old + new`). This is exactly why `trace` collects entries from all 7 nodes.
- **Plain field** (e.g. `status`): the **second writer overwrites** the first. For `status` this never actually collides, because the branch guarantees only one path runs — `verify_documents` sets `BLOCKED` on the stop path, `adjudicate` sets `DECIDED` on the continue path, never both. Same for `degraded` (only `extract` writes it) and `adjudication_result` (only `adjudicate`).

So: lists grow, scalars get replaced — and the design avoids real scalar collisions by giving each scalar a single owner.

---

> **End of Round 3 (State Management).** Next up on approval: **Round 4 — Node-by-Node Execution (Q33–Q72)** in the same format.
