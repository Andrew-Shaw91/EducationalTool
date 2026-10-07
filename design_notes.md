# Design Notes

CodeSense is a research prototype. These notes record the design decisions that matter for evaluation, and the reasoning behind them, in a form suitable for adaptation into a dissertation chapter. Where a claim has not yet been tested, it is marked as such.

## 0. Curriculum design: one cognitive task per Bloom level

Every topic contains at least one activity at every level, and the levels are deliberately **different tasks, not harder versions of one question**. Each level is defined by what the learner must *do*, and each task type is chosen to require that skill and not a neighbouring one.

| Level | The learner must... | Task types |
|-------|---------------------|-----------|
| L1 Knowledge | recall or recognise vocabulary | Identify Terminology, Match Terms to Definitions, Define a Concept |
| L2 Comprehension | build a mental model of code that is given | Trace, Explain, Purpose |
| L3 Application | use a concept to complete or change existing code | Complete the Code, Modify the Code, Prompt Construction |
| L4 Analysis | take code or reasoning apart to find where it goes wrong | Debug, Compare Solutions, Analyse a Misconception |
| L5 Synthesis | build something new from a working base, combining ideas | Improve / Refactor, Extend the Code |
| L6 Evaluation | judge code against a requirement, including AI output | Judge an AI Suggestion, Review Code Quality |

Current coverage (46 activities): 15 / 7 / 6 / 6 / 6 / 6 across L1-L6. Several design choices follow from the project's focus on comprehension:

- **Reading and judging dominate.** About four fifths of the activities ask students to read, trace, compare or evaluate code; writing-style tasks (modify, extend, improve, prompt) are the minority, and even those accept a description in words as well as code. Tests enforce both properties.
- **Matching is scored per pair.** Each Match Terms item pairs five terms with six definitions (one fits nothing, so the last pair cannot be won by elimination), anchored to a short code fragment. Credit is per pair and the item counts as correct only if every pair is; feedback names the missed terms rather than just a score. The order of definitions is a seeded shuffle, so it is stable across sessions and reseeding. The student's choices are stored as term -> definition text, a closed-choice answer kept even when free-text storage is off.
- **Trust has to be earned, not assumed.** Level 6 AI-judgement items include both correct and incorrect suggestions (two *accept*, three *reject*). If every AI suggestion were wrong, students would learn to reject by reflex, which is not evaluation. The accept items (a leap-year check, a stock total) look unusual or dense so that suspicion alone cannot score.
- **Distractors are misconceptions, not noise.** Wrong options are drawn from documented novice errors (stop value of `range` included, `=` as equality, parameter vs argument, a list assignment treated as a copy). Two Level 4 items deliberately pair up: in Variables, `b = a` followed by `a = 10` leaves `b` unchanged; in Lists, `b = a` followed by `b.append(4)` *does* change `a`. Students must explain why, which distinguishes rebinding a name from changing an object.

**Quality controls.** (1) Every claim a model answer makes about output or errors is verified by executing the code (`practice/test_content_claims.py`); for example the leap-year function is compared with Python's own `calendar.isleap` for years 1-3000. (2) The correct option is placed round-robin across positions (a, b, c, d) so it cannot be guessed from position; placement is deterministic, so a stored choice key keeps its meaning when the database is re-seeded. New multiple-choice items must be appended to the end of the activity list to keep earlier positions stable. (3) Tests check that every activity has all required fields (topic, level, type, question, model answer, success criteria, misconceptions, follow-up) and that each topic's activities progress from L1 to L6.

**Limitation.** These activities have been checked for correctness and internal consistency, not yet for difficulty, clarity or validity with real students. Whether the levels are genuinely distinct cognitive demands (rather than just labelled so) is an empirical question; per-level scores and hint usage in the research data are the intended evidence (see Future work).

## 1. Why keyword matching is currently used for free-text assessment

Free-text items (explaining code, improving code, writing requirements) need some form of assessment, because the prototype's pedagogy depends on students articulating understanding rather than selecting from options. Keyword matching is the current baseline for four reasons:

- **Transparency.** A concept is marked present if one of its listed keywords appears as a whole word. The rule can be stated in one sentence, inspected in the content, and explained to a supervisor or participant. This matters in a study where the assessor itself may be a variable.
- **Reproducibility.** The same answer always receives the same result. LLM output varies between runs and between model versions, which complicates comparison across participants and over time.
- **Independence.** It needs no network, API key, cost, or third-party data sharing, so the prototype runs anywhere and no participant text leaves the machine.
- **A baseline to beat.** If an LLM assessor is introduced later, its value can only be claimed relative to a simple, well-understood alternative.

**Known limitations.** Keyword matching rewards vocabulary, not understanding. It misses correct ideas expressed in unexpected words ("goes through each" instead of "loop"), and it can credit answers that only echo terms from the question (during testing, the phrase "nothing relevant" matched the keyword `nothing` for the empty-string concept). To limit harm, the interface never presents the result as a grade: open responses are labelled *formative*, are never marked right or wrong, and the page states that correct ideas in unusual wording can be missed. Multiple-choice and accept/reject items, which are objectively checkable, are still scored deterministically.

**Code answers.** Several activities (modify, extend, refactor) invite students to write code. The matcher therefore treats operators and brackets as tokens, so `>=` and `>` are distinguishable and `[]` or `+=` can be recognised; without this, a correct `age >= 65` and an incorrect `age > 66` could not be told apart. Accepting a description in words as well as code keeps these tasks about reasoning rather than syntax. Code has many correct forms, though, so this remains a coarse signal and a clear case for LLM assessment.

**How it is structured.** Each free-text activity declares `expected_concepts`: a name, a one-sentence `description` of the idea, and `keywords`. The description is used by an LLM assessor; the keywords by the keyword assessor. Content therefore does not change when the assessor does.

## 2. How LLM-based assessment can replace it

Assessment is behind one interface, `FeedbackService`, which takes an activity and a response and returns:

```json
{"concepts_found": [...], "concepts_missing": [...], "score": 0.0, "feedback": "..."}
```

Two implementations exist, selected by the `FEEDBACK_SERVICE` setting (`keyword` or `ai`). `AIEnhancedFeedbackService` is built as a three-step pipeline, each step a replaceable seam:

1. `build_prompt` assembles the question, the code, the concept names with their descriptions, the student's answer, and rules (use only the listed concepts; never write the answer for the student; reply in JSON).
2. `_call_llm` is the only method that contacts a model. It is deliberately unimplemented; with no API key, `_mock_llm_response` returns JSON in the identical shape so the rest of the pipeline is already exercised.
3. `_parse_response` validates what came back.

**Going live** means implementing `_call_llm` and setting `CODESENSE_LLM_API_KEY`. Views, templates, the database schema and the tests do not change.

**Safeguards designed in, because an LLM assessor is itself a measurement instrument:**

- Concept names returned by the model are filtered against the activity's list, and `concepts_missing` is recomputed, so an invented concept cannot enter the data.
- Scores are clamped to 0-1.
- Unparseable output falls back to keyword matching and is labelled `keyword-fallback`.
- Every stored attempt records which assessor produced it (`keyword`, `ai-mock`, `ai-enhanced`, `keyword-fallback`). Mock output is never recorded as real LLM output.
- If a key is set but no client is implemented, the service fails loudly rather than silently degrading.

**What remains to be established (not yet done).** Before an LLM assessor's output is treated as valid, it should be compared with human ratings on a sample of real answers, for agreement and for systematic bias (for example, favouring fluent or longer answers). The side-by-side design makes this straightforward: both services can score the same stored responses.

## 3. Why local Bootstrap improves portability

Bootstrap and the three fonts are vendored in `static/` and served through Django's static files with the `{% static %}` tag. The application makes no external network request.

- **Classroom and lab reliability.** Teaching rooms and study sessions often have restricted or unreliable networks. A CDN failure would otherwise silently degrade the interface mid-session.
- **Reproducibility.** The pinned Bootstrap 5.3.3 files cannot change underneath a study; a CDN URL can.
- **Privacy.** Loading assets from third parties discloses each participant's IP address and browser details to those providers. Serving locally removes that disclosure, which supports the anonymity claims in Section 4.
- **Archiving.** The repository is self-contained, so the exact system evaluated can be preserved and rerun for examination or replication.

The cost is a larger repository (about 350 KB of vendored assets) and that library updates are manual. For a time-limited research artefact this is an acceptable trade. Outside DEBUG, run `collectstatic` and serve `STATIC_ROOT` from the web server.

## 4. Ethical considerations around participant data

**Principle: collect the minimum needed to answer the research questions, and make that minimum visible and adjustable.**

- **Anonymity by construction.** A participant is a random code (e.g. `P-3F9A12C4`) created by the server and held in the browser session. There are no names, emails, accounts, IP addresses, user agents, or stored session keys. Clearing cookies starts a new participant. No field in the schema could identify a person, and a test enforces this.
- **Separation of concerns.** Teaching content lives in the `practice` app; everything about participants lives in the `research` app. Content can be edited or shared without touching participant data, and evaluation data can be exported, anonymised or deleted as a unit.
- **Complete, documented field list.** Every stored field is described in `research/models.py`.
- **Configurable collection.** `ANALYTICS_ENABLED` turns collection off entirely (no participant, no attempts, no hint counts; the application behaves identically for the student). Finer switches control storing response text, hint usage, and timestamps. Defaults can be overridden with environment variables without code changes.
- **Transparency to participants.** The footer states whether answers are recorded and that no personal details are collected.
- **Evidence integrity.** Evaluation data is read-only in the admin, and activities referenced by attempts cannot be deleted (`PROTECT`).

**Residual risks and open decisions (to resolve with the ethics process, not by code alone):**

- Free-text answers can contain personal information a student chooses to type. Anonymous codes do not remove that. Options are to disable `STORE_RESPONSE_TEXT`, or to warn participants not to enter personal details.
- Fine-grained timestamps combined with a small cohort could allow re-identification by someone who knows who was online; `STORE_TIMESTAMPS` can be disabled.
- The anonymous code cannot be linked to a participant, so withdrawal of an individual's data is not possible after the fact unless the participant records their own code. This should be stated in the participant information sheet.
- If a real LLM is connected, student text is sent to a third party. This needs explicit consent, a data-processing review, and a provider whose terms do not retain or train on submitted data.
- The prototype has not yet been reviewed against institutional ethics requirements or data-protection regulations; settings above should be treated as capabilities, not approval.

## 5. Future work

- **Validate the assessors.** Collect real answers, have humans rate them against the concept lists, and compare keyword and LLM results for agreement and bias. This is the most important missing evidence.
- **Connect a live LLM** behind `_call_llm`, and move hints, explanations and follow-ups (currently mocked in `MockAIService`) to the same provider while keeping the rule that AI scaffolds but never solves.
- **Experimental conditions.** Add an optional condition label to participants (for example, hints on or off, AI feedback on or off) to support controlled comparisons.
- **Analytics for learning questions.** Examine score and hint usage by Bloom level and by activity type; identify items whose distractors reveal common misconceptions; track whether repeated attempts improve.
- **Researcher-issued participant codes**, so participants can later withdraw their data without being identifiable.
- **Content breadth.** More activities per topic, authored misconception-based distractors, and an authoring workflow with review.
- **Accessibility and usability testing** with the intended audience before any formal evaluation.
- **Live code execution** in a sandbox, only if a research question requires it; it is deliberately out of scope now to keep the focus on reading, judging and specifying code.
