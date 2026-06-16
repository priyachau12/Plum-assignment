# Live Review & Demo Script — Plum AI Engineer Assignment

A presentation/defense script for the demo and the 60-minute technical review.
It answers **every question the assignment asks** (the 6 required behaviours, the
5 deliverables, the 5 weighted criteria, the bonus) and — most importantly —
**every hard question a sharp reviewer will ask**, with the honest answer for each.

> The video storyboard (3 beats, shot-by-shot) lives in [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md).
> This doc is the **talk track + Q&A defense** for the live walkthrough.

**Golden rule for this review: volunteer the weaknesses before they're found.**
This is a strong submission. The only way it goes badly is getting *caught* on a
gap instead of *naming* it first. Every "honest caveat" below is something to say
out loud, not hide.

---

## 0. Setup before you present

Have open in tabs:
- The UI — `https://plum-assignment-a651.onrender.com/` (or `uvicorn app.main:app --reload` → `http://127.0.0.1:8000/`)
- `/docs` (FastAPI Swagger) — to show the contracts live
- `docs/EVAL_REPORT.md` — the 12/12 table
- `docs/VISION_DEMO.md` — the real Claude-vision path on actual images
- In an editor: `app/rules/engine.py`, `app/rules/financials.py`, `app/policy/policy_loader.py`, `app/verification/document_verifier.py`, `app/graph/builder.py`

Re-verify before the call (takes ~10s):
```bash
python scripts/run_eval.py   # -> "12/12 cases passed all checks"
python -m pytest -q          # -> all green
```

---

## 1. The 90-second opener (the one big idea)

> "This automates health-insurance claim adjudication. The core design decision
> is a strict three-way split: **LLMs do perception and communication —
> reading messy documents and writing the member-facing explanation — and
> deterministic code does cognition: the actual decision.** The LLM never decides
> a claim. Every LLM output is validated by a Pydantic schema before the rule
> engine touches it.
>
> That one choice is what earns the grade: decisions are **reproducible** (same
> validated input → same decision → same trace), which makes them **auditable**,
> and it **contains hallucination** — a wrong extracted field still flows through
> the same rules and lowers confidence rather than silently changing a payout."

**Show:** the README "Core idea" table, then `app/graph/builder.py` — the 7-node
pipeline with the conditional early-stop edge.

---

## 2. The 6 required behaviours — show + say + honest caveat

### Behaviour 1 — Accept a claim submission
- **Show:** UI submit form + `POST /claims` and `POST /claims/upload` in `/docs`.
- **Say:** "Two entry points: a JSON path for structured submissions and a
  multipart upload path that sends real image/PDF bytes to Claude vision."
- **Where:** `app/api/routes_claims.py`, `app/models/claim.py`.

### Behaviour 2 — Catch document problems early
- **Show:** TC001 in the UI → status **BLOCKED**, no decision. Read the message:
  > "You uploaded: PRESCRIPTION, PRESCRIPTION. A CONSULTATION claim requires
  > PRESCRIPTION, HOSPITAL_BILL. The following required document(s) are missing:
  > HOSPITAL_BILL. Please upload the missing document(s) and resubmit."
- **Say:** "The gate is a conditional edge after verification — `extract` and
  `adjudicate` never run. Three checks run together: required docs present,
  readable, same patient. Messages name the specific types and names involved."
- **Where:** `app/verification/document_verifier.py`, edge in `app/graph/builder.py:68`.
- **Honest caveat (say it):** "On the JSON path this is fully deterministic. On a
  *real upload*, wrong-document detection depends on Claude classifying the type
  correctly — there's no deterministic backstop yet. A misclassified scan could
  pass the gate. That's the first thing I'd harden."

### Behaviour 3 — Extract structured information
- **Show:** `docs/VISION_DEMO.md` — actual prescription + bill images read by Claude.
- **Say:** "Vision reads handwriting, stamps, phone photos. Critically, the model's
  JSON is validated into a typed `ExtractedDocument` before rules see it — a
  hallucinated non-numeric total fails validation and *degrades* the claim instead
  of corrupting the decision."
- **Where:** `app/llm/client.py:208` (`extract_document` → `model_validate`).
- **Honest caveat (say it):** "My headline 12/12 eval runs on *injected* content,
  not the AI — that's a deliberate choice to keep the eval deterministic and
  offline. The AI path is tested separately: fake-client unit tests in
  `tests/test_llm_nodes.py` plus the live vision demo. So 12/12 proves the
  *rulebook*, the vision demo proves the *perception*."

### Behaviour 4 — Make a claim decision
- **Show:** TC004 (APPROVED 1350), TC006 (PARTIAL 8000), TC005 (REJECTED), TC009 (MANUAL_REVIEW).
- **Say:** "All four verdicts, each with approved amount, reason, and a composed
  confidence score."

### Behaviour 5 — Explainable
- **Show:** Expand the full trace on any decided claim.
- **Say:** "One ordered `trace` list. **Every rule writes an entry whether it
  passes or fails** — so you see everything that was checked, not just what
  failed. The trace is embedded in the response; you can reconstruct any decision
  without reading code."
- **Where:** trace assembled across all nodes; rule trace in `app/rules/engine.py`.
- **This is your strongest area — lean into it.**

### Behaviour 6 — Handle failures gracefully
- **Show:** TC011 → APPROVED, **confidence 0.65** (vs 0.95 normal), trace shows a
  `FAILED` extract entry, note recommends manual review. No 500.
- **Say:** "A failed component records a `FAILED` trace entry, sets `degraded`,
  applies a −0.30 confidence penalty, and the pipeline continues. Real `LLMError`
  paths degrade through the exact same mechanism — the `simulate_component_failure`
  flag just triggers it deterministically for the test."
- **Where:** `app/graph/nodes/extract.py:35`, penalty in `app/rules/engine.py:88`.

---

## 3. The 5 deliverables — confirm each

| Deliverable | Where | Status |
|---|---|---|
| Working system + UI + deploy | `app/static/index.html`, Render URL | ✅ live |
| Architecture document | `docs/architecture.md` (21 sections incl. 10× scaling, risk register, decision log) | ✅ |
| Component contracts | `docs/TECHNICAL_DOCUMENTATION.md` §5 — every component's input/output/errors | ✅ |
| Eval report (all 12) | `docs/EVAL_REPORT.md` — decision + full trace + match per case | ✅ 12/12 |
| Demo video (8–12 min, 3 beats) | storyboard in `docs/DEMO_SCRIPT.md` | scripted |

---

## 4. The 5 weighted criteria — the honest line on each

- **System Design (30%):** "Clean separation, single-responsibility nodes, the
  perception/cognition/communication split, conditional early-stop. **Weakness I'll
  name: it's synchronous and in-memory** — no queue, no DB. That was a conscious
  2–3-day cut; §18 of the architecture doc sketches the async + persistence path."
- **Engineering Quality (25%):** "Typed end-to-end with Pydantic, every component
  has tests (~68 passing), ruff clean, DI via the LLM interface so the AI paths are
  tested without network."
- **Observability (20%):** "Strongest area — full reconstructable trace, every
  rule logged pass or fail."
- **AI Integration (15%):** "Thoughtful — LLM for perception only, output schema-
  validated, failure degrades not crashes. The eval doesn't exercise it (by design);
  the vision demo does."
- **Document Verification (10%):** "Specific, actionable messages. Deterministic on
  declared types; AI-dependent on raw uploads."
- **Bonus — multi-agent:** see the honest answer in §5.

---

## 5. The HARD QUESTIONS — and the honest answer to each

> This is the section that wins or loses the review. Read it twice.

### Q1. "Are you hardcoding any policy logic?" *(the one they care about most)*
**Honest answer:** "Policy **values** — no, not one. Every waiting period, sub-limit,
co-pay, network discount, threshold, exclusion list, network hospital, and the
member roster is read from `policy_terms.json` via the typed `Policy` model. You can
grep the rule engine for any policy number and find nothing — the only constants in
there are confidence-tuning weights.
>
> Where I *do* have hardcoded **interpretation**, and I want to be upfront: four places.
> 1. `effective_per_claim_cap = max(per_claim_limit, sub_limit)` — the file doesn't
>    state how those two limits interact; I inferred `max` from the expected outputs.
> 2. `_LINE_ITEM_CATEGORIES = {DENTAL, VISION}` — which categories do line-item
>    exclusion; derivable from the policy, currently a literal.
> 3. The financial order (discount → co-pay → caps) lives in code.
> 4. The diagnosis synonym lexicon — the canonical keys come from the policy, but the
>    synonyms mapping free text to them are a Python dict."
- **Where to point:** `app/policy/policy_loader.py`, `app/rules/engine.py`, `app/rules/financials.py:104`.

### Q2. "Walk me through the `max()` on the limits. Why?" *(the sharpest follow-up)*
**Honest answer:** "The policy has a ₹5,000 per-claim limit *and* per-category
sub-limits, with no stated interaction. TC006 approves ₹8,000 for dental (sub-limit
₹10,000) and TC010 approves ₹3,240 for a consultation — both **exceed** the ₹5,000
per-claim base, so the test data tells me the *higher of the two* is the binding cap.
Hence `max`. The honest consequence: **any sub-limit below ₹5,000 is never enforced
per-claim** — consultation's ₹2,000 sub-limit is effectively dead. If this were
production I'd confirm the intended semantics with the policy owner, because real
sub-limits are usually *annual per-category* caps, which would need per-category YTD
tracking I haven't built."
- This answer turns the weakness into evidence you understand insurance domain modeling.

### Q3. "Is this really multi-agentic?" *(re: the bonus)*
**Honest answer:** "It's a LangGraph DAG of single-responsibility nodes — three call
an LLM, the rest are pure functions. I describe them as small agents because each owns
one decision and they compose, but I won't oversell it: there's no autonomous
planning or tool-use loop. If you want true agentic behaviour, the natural place is a
*classification/extraction supervisor* that retries with a stronger model or asks for
a better photo when confidence is low — that's a clean extension of the current graph."

### Q4. "Your eval is 12/12 but on injected content — does it test your AI at all?"
**Honest answer:** "Correct, and that's deliberate. The 12/12 proves the deterministic
rulebook is correct and reproducible. The AI is validated two other ways: fake-client
unit tests for the node logic, and the live vision demo on real images in
`VISION_DEMO.md`. I split them on purpose — I didn't want LLM nondeterminism in my
regression suite. If you'd like, I can run a claim through `POST /claims/upload` live
right now against real images."

### Q5. "What policy rules are loaded but NOT enforced?"
**Honest answer (have the list ready):** "Quite a few — I'll be straight: about 18
fields load but aren't acted on. `family_floater`, `sum_insured_per_employee`, the
pharmacy `branded_drug_copay_percent`/`generic_mandatory`, `max_sessions_per_year`
for alt-medicine, `pre_existing_conditions_days`, the category `covered` flag, the
`fraud_score` threshold, and the per-category `requires_*` flags. The system enforces
exactly the subset the 12 cases exercise. That was the 2–3-day scoping call — the
*framework* to enforce them is there (they're already typed on the `Policy` model);
each is a new ordered rule in `engine.py`. A branded-drug co-pay, for instance, is
~10 lines."

### Q6. "It's synchronous with `time.sleep` retries. How does this hold at 10M lives?"
**Honest answer:** "It doesn't, as-is, and I documented that (§18). Three moves:
(a) `POST /claims` enqueues and returns a claim id; the graph runs async off a worker
pool; (b) cache classification/extraction by document hash and route Haiku-class for
classification, a stronger model only for hard extraction; (c) move `ClaimState` +
trace to Postgres + object storage so traces are queryable and claims resumable. The
app is already stateless, so horizontal scale is just adding workers."

### Q7. "What happens if `policy_terms.json` is malformed or missing?"
**Honest answer:** "`load_policy` collapses three failure modes — unreadable JSON,
invalid JSON, wrong shape — into one typed `PolicyLoadError` with the root cause
preserved. Pydantic validates the whole document at startup, so a bad policy fails
loudly and early rather than deep inside a request."
- **Where:** `app/policy/policy_loader.py`.

### Q8. "How is the confidence score actually computed — is it just a constant?"
**Honest answer:** "It's composed, not flat: a base (0.95 clear-cut / 0.90 review),
minus 0.30 if degraded, minus an extraction-quality penalty `(1 − avg field
confidence) × 0.40` on the real vision path, minus 0.10 if there's genuinely nothing
to reason about. On the injected-content eval path the penalties are zero, so it lands
on the base — which is why TC004 is exactly 0.95 and TC011 is 0.65. There's also a
confidence *gate*: an otherwise-approvable claim below 0.50 is routed to manual review
instead of auto-approved."
- **Where:** `app/rules/engine.py:67` and `:479`.

### Q9. "Why deterministic normalization instead of an LLM for diagnosis?"
**Honest answer:** "Reproducibility. The vocabulary is fixed by the policy and matching
is whole-word keyword (so 'hernia' doesn't match 'herniation'). An LLM is a fine
*fallback* for text the table misses — but its answer would still be checked against
the same policy vocabulary before the rules trust it. Today the keyword table resolves
all 12 cases, so the eval stays deterministic."
- **Where:** `app/rules/normalization.py`.

### Q10. "Security / PII?"
**Honest answer:** "Secrets are env-only and gitignored. No auth on the API — that's a
named cut for the assignment scope. The real PII concern is trace `detail` strings
containing patient names and diagnoses; in production those need redaction before they
hit logs. It's in the risk register, not yet implemented."

---

## 6. "Extend it live" — the most likely asks and how to attack each

They said they'll ask you to extend it live. Most probable, in order, with the approach:

1. **"Add a branded-drug co-pay rule."** → New ordered rule in `engine.py` after the
   per-claim limit: read `cat.branded_drug_copay_percent`, detect branded line items,
   apply the higher co-pay to those. Already-typed field; ~10 lines + a test.
2. **"Enforce a category `covered: false`."** → Early rule: `if cat and not cat.covered:
   reject(CATEGORY_NOT_COVERED)`. One check, writes a trace note.
3. **"Make sub-limits annual per-category."** → This exposes Q2. Add per-category YTD to
   the request, change `effective_per_claim_cap` semantics, track remaining per category.
   Talk through it even if you don't finish — the *reasoning* is what's scored.
4. **"Add a new document type / claim category."** → Add to the `DocumentType` enum +
   `document_requirements` in the policy file; the verifier picks it up with no code change.
5. **"Block on submission date past deadline."** → Already built (Rule 1c). Show it:
   pass a `submission_date` > 30 days after treatment → `SUBMISSION_WINDOW_EXCEEDED`.

**Approach to narrate while coding:** "New rule → pick its precedence slot in the
ordered list → read the value off `policy` (never inline it) → write a trace entry
pass *and* fail → add a unit test." Saying that out loud demonstrates the architecture.

---

## 7. Cheat sheet — exact numbers per test case

| Case | Input | Result | Why |
|---|---|---|---|
| TC001 | 2× prescription, CONSULTATION | **BLOCKED** | missing HOSPITAL_BILL |
| TC002 | unreadable pharmacy bill | **BLOCKED** | re-upload asked, not rejected |
| TC003 | Rajesh vs Arjun | **BLOCKED** | patient mismatch, both names cited |
| TC004 | consultation ₹1500 | **APPROVED ₹1350** | 10% co-pay (₹150) |
| TC005 | diabetes, joined 2024-09-01 | **REJECTED** | 90-day wait; eligible 2024-11-30, treated 2024-10-15 |
| TC006 | dental: RCT ₹8000 + whitening ₹4000 | **PARTIAL ₹8000** | whitening excluded, itemized |
| TC007 | MRI ₹15000, no pre-auth | **REJECTED** | PRE_AUTH_MISSING (>₹10k threshold) |
| TC008 | consultation ₹7500 | **REJECTED** | PER_CLAIM_EXCEEDED (limit ₹5000) |
| TC009 | 4th same-day claim | **MANUAL_REVIEW** | same-day limit is 2; signals listed |
| TC010 | Apollo (network) ₹4500 | **APPROVED ₹3240** | 20% discount → ₹3600, then 10% co-pay → ₹3240 |
| TC011 | component failure | **APPROVED ₹4000, conf 0.65** | degraded −0.30, manual-review note |
| TC012 | bariatric / obesity | **REJECTED** | EXCLUDED_CONDITION, conf 0.95 |

**Rule precedence (recite if asked):** eligibility → minimum amount → submission
window → exclusion → waiting period → pre-auth → per-claim limit → all-lines-excluded
→ fraud → high-value → annual limit → money math → confidence gate.

**Money order (TC010 is the trap):** network discount **first**, then co-pay on the
discounted amount, then cap last. `4500 × 0.80 = 3600; 3600 × 0.90 = 3240`.

---

## 8. The closer — "proud of / would change" (assignment beat 3)

- **Proud of:** "The perception/cognition/communication split. It's the decision that
  makes everything else — reproducibility, auditability, hallucination containment,
  a deterministic eval — fall out for free. The LLM is powerful but never trusted to
  decide."
- **Would change with more time:** "I'd close the `max()` sub-limit ambiguity with the
  policy owner and implement annual per-category tracking; and I'd add a deterministic
  backstop to document classification so the early-stop gate doesn't depend solely on
  the vision model for raw uploads. And I'd move from synchronous to a queue + DB so
  traces are queryable at scale."

Both answers are *true* and *specific* — which is exactly what they're testing for.
