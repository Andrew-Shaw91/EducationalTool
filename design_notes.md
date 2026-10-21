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

Current coverage (48 activities): 15 / 9 / 6 / 6 / 6 / 6 across L1-L6. Several design choices follow from the project's focus on comprehension:

- **Reading and judging dominate.** About four fifths of the activities ask students to read, trace, compare or evaluate code; writing-style tasks (modify, extend, improve, prompt) are the minority, and even those accept a description in words as well as code. Tests enforce both properties.
- **Matching is scored per pair.** Each Match Terms item pairs five terms with six definitions (one fits nothing, so the last pair cannot be won by elimination), anchored to a short code fragment. Credit is per pair and the item counts as correct only if every pair is; feedback names the missed terms rather than just a score. The order of definitions is a seeded shuffle, so it is stable across sessions and reseeding. The student's choices are stored as term -> definition text, a closed-choice answer kept even when free-text storage is off.
- **Trust has to be earned, not assumed.** Level 6 AI-judgement items include both correct and incorrect suggestions (two *accept*, three *reject*). If every AI suggestion were wrong, students would learn to reject by reflex, which is not evaluation. The accept items (a leap-year check, a stock total) look unusual or dense so that suspicion alone cannot score.
- **Distractors are misconceptions, not noise.** Wrong options are drawn from documented novice errors (stop value of `range` included, `=` as equality, parameter vs argument, a list assignment treated as a copy). Two Level 4 items deliberately pair up: in Variables, `b = a` followed by `a = 10` leaves `b` unchanged; in Lists, `b = a` followed by `b.append(4)` *does* change `a`. Students must explain why, which distinguishes rebinding a name from changing an object.

**Quality controls.** (1) Every claim a model answer makes about output or errors is verified by executing the code (`practice/test_content_claims.py`); for example the leap-year function is compared with Python's own `calendar.isleap` for years 1-3000. (2) The correct option is placed round-robin across positions (a, b, c, d) so it cannot be guessed from position; placement is deterministic, so a stored choice key keeps its meaning when the database is re-seeded. New multiple-choice items must be appended to the end of the activity list to keep earlier positions stable. (3) Tests check that every activity has all required fields (topic, level, type, question, model answer, success criteria, misconceptions, follow-up) and that each topic's activities progress from L1 to L6.

**Limitation.** These activities have been checked for correctness and internal consistency, not yet for difficulty, clarity or validity with real students. Whether the levels are genuinely distinct cognitive demands (rather than just labelled so) is an empirical question; per-level scores and hint usage in the research data are the intended evidence (see Future work).

## 0a. The Block Model of Program Comprehension (added after the initial prototype)

The Block Model is an **additional layer** on the framework above. It replaces nothing: the Many Small Problems format, the Bloom-inspired levels, every activity type and the interface are unchanged. It adds one piece of metadata to every activity and a way to see it.

**Summary of the model.** Schulte's Block Model (2008) is an educational model of program comprehension. It describes understanding at four levels of grain:

| Block level | The learner is understanding... | Typical evidence |
|-------------|--------------------------------|------------------|
| Atoms | individual syntax elements: names, operators, keywords, values | naming a term, picking an operator, completing one expression |
| Blocks | a logical group of statements read as one unit: a loop, a conditional, a function | explaining what a loop or function does |
| Relations | how parts affect each other: variable updates, calls, data flow, control flow | tracing, finding a fault, spotting aliasing |
| Macro Structure | the purpose of the whole program: the problem it solves | stating what a program is for, extending or improving it towards a goal |

Understanding is expected to build from Atoms towards Macro Structure. The full model also crosses these levels with three dimensions (text surface, program execution, goals). This prototype uses **only the level axis**; the dimensions are not modelled (see Limitations).

**Why program comprehension matters here.** When code can be generated on request, a student's most frequent task is no longer writing code but reading it: judging whether generated code does what was asked, tracing why it fails, and deciding whether it can be trusted. Studies of novices (for example Lister et al., 2004) link weak tracing and reading skills to weak writing. The Block Model gives a vocabulary for *what part* of a program a student can and cannot yet read. (Citations are to be checked against the originals before submission.)

**Relationship between Bloom and Block levels.** They answer different questions. Bloom describes the **thinking demanded** (recall, comprehend, apply, analyse, synthesise, evaluate); the Block Model describes **what that thinking is about** (an atom, a block, a relation, the whole). They are correlated but deliberately not the same ladder. The distribution across the current 48 activities:

| Bloom \ Block | Atoms | Blocks | Relations | Macro |
|---------------|:-----:|:------:|:---------:|:-----:|
| L1 Knowledge | 15 | 0 | 0 | 0 |
| L2 Comprehension | 0 | 4 | 3 | 2 |
| L3 Application | 1 | 4 | 0 | 1 |
| L4 Analysis | 0 | 0 | 6 | 0 |
| L5 Synthesis | 0 | 0 | 0 | 6 |
| L6 Evaluation | 0 | 0 | 3 | 3 |
| **Total** | **16** | **8** | **12** | **12** |

Three patterns follow from the task types and are enforced by tests: recall (L1) is always about atoms; analysis (L4) is always about relations, since finding a fault means following cause and effect; evaluation (L6) is always about relations or the whole program. L2 spans three block levels on purpose: reading a block (Explain), following relations (Trace) and stating the purpose (Purpose) are different comprehension skills at the same Bloom level.

**How levels were assigned.** One rule per activity type, with the exceptions stated explicitly:

- Identify Terminology, Define a Concept, Match Terms: **Atoms**.
- Explain Code, Modify the Code: **Blocks** (the learner works on a loop, conditional or function as a unit).
- Trace, Debug, Compare Solutions, Analyse a Misconception: **Relations** (data flow and control flow decide the answer).
- Program Purpose, Improve/Refactor, Extend the Code, Prompt Construction: **Macro Structure** (the answer depends on the goal of the whole program).
- Judge an AI Suggestion and Review Code Quality are decided **per activity**: Relations when the verdict hinges on following specific values or execution (the swap line, the countdown, the even-number test), Macro Structure when it hinges on whether the whole function meets a stated requirement (the leap-year rule, the stock total, the negative-number check).
- Complete the Code is decided per activity: **Atoms** when one operator or expression is the point (the bill total), **Blocks** when the learner must understand how a whole loop behaves (`range(...)` bounds, iterating a dictionary).

**How Many Small Problems support progression.** Each activity is small, tests one concept and sits at one grain, so a topic becomes a short path through the grain levels: vocabulary (Atoms), reading one unit (Blocks), following interactions (Relations), then stating or serving a purpose (Macro Structure). Every topic contains all four levels (tested). `Topic.block_progression()` returns a topic's activities grouped Atoms to Macro Structure. This is **metadata only**: the order students meet activities is still Bloom order, nothing is gated, and a student may start anywhere. Because Bloom order does not follow Block order exactly (tracing at L2 is a Relations task and precedes the Blocks tasks at L3), Block progression is currently something to *analyse* rather than *enforce*. Using it to sequence or adapt activities is future work.

**Interface.** A small badge beside the Bloom badge (for example `L4 Analysis` `Relations`) on the topic list, the activity page and the feedback page. The activity page has an expandable "Why this activity was chosen" listing the Bloom level, the Block Model level and the misconception targeted. Before the student answers, the misconception line says it is shown afterwards: many items are built around a specific misconception, and naming it first would give away the answer (for example, "Why did the student predict 10?"). The feedback page shows it in full.

**Research data.** The CSV export gains a `block_level` column, taken from the activity. No new participant data is collected, so analyses can compare performance by grain of understanding (for example, whether students who match terms correctly still fail to trace).

**Why it was introduced after the initial prototype.** The prototype was organised around Bloom levels alone. That says how demanding a task is but leaves implicit which part of a program the task is about. Applying the Block Model as a review lens exposed a real gap: Functions and Dictionaries had no activity at the Blocks level (no item asking the learner to read a function or a dictionary update as a unit), so two Explain Code items were added. The model was therefore introduced as a diagnostic enhancement to the existing design, not as a new foundation, and the earlier design choices stand.

**Limitations.**
- The tags were assigned by the author *after* the activities were written, which risks post-hoc fitting. The fixed rule above, and tests that check it, reduce but do not remove that risk. No second rater has checked the assignments; agreement should be measured (for example with Cohen's kappa) before the tags are used as a research variable.
- The levels overlap in practice: tracing a loop also involves reading a block. Each activity is tagged with the grain its *answer depends on*, a judgement call.
- The distribution is uneven by design (16 / 8 / 12 / 12): Atoms is large because every topic has several vocabulary items, Blocks is small because few task types sit naturally there.
- The model's dimensions (text surface, execution, goals) are not represented.
- Nothing yet shows that the progression helps students; it is a design hypothesis.

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
