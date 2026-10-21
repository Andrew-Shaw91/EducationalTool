import random

from django.core.management.base import BaseCommand, CommandError

from practice.models import Activity, BlockLevel, QuestionType, Topic


QUESTION_TYPES = [
    {
        "slug": "terminology",
        "name": "Identify Terminology",
        "bloom_level": 1,
        "stance": "read",
        "display_order": 0,
        "short_description": "Pick the correct technical term for a piece of code.",
        "pedagogical_aim": (
            "Shared vocabulary is the foundation for everything else: students "
            "cannot explain, debug, or critique generated code (or specify what "
            "they want) without words such as parameter, index, key and "
            "iteration. Distractors are near-miss terms that novices genuinely "
            "confuse, such as parameter versus argument."
        ),
        "student_prompt_stem": "What is the correct term for this part of the code?",
        "ai_role": (
            "AI may hint at what distinguishes two similar terms. It must not "
            "simply name the term, because recall is the skill being practised."
        ),
    },
    {
        "slug": "define-concept",
        "name": "Define a Concept",
        "bloom_level": 1,
        "stance": "read",
        "display_order": 1,
        "short_description": "State what a core programming idea is, in your own words.",
        "pedagogical_aim": (
            "Putting a definition into one's own words shows whether a term is "
            "understood or merely recognised. Short, low-pressure definitions "
            "give an early, honest baseline before students read or evaluate "
            "code that depends on the idea."
        ),
        "student_prompt_stem": "In your own words, what is this concept?",
        "ai_role": (
            "AI may suggest which aspect of the idea to think about. It must not "
            "supply the definition; feedback names ideas still missing, not "
            "their wording."
        ),
    },
    {
        "slug": "match-terms",
        "name": "Match Terms to Definitions",
        "bloom_level": 1,
        "stance": "read",
        "display_order": 2,
        "short_description": "Pair each technical term with the definition that fits it.",
        "pedagogical_aim": (
            "Recall of vocabulary is the base of the taxonomy, and matching "
            "tests several related terms at once, including the pairs novices "
            "mix up. The terms are anchored to a short code fragment so each "
            "definition can be checked against something concrete, and one "
            "extra definition fits no term so the last pair cannot be "
            "answered by elimination."
        ),
        "student_prompt_stem": "Which definition belongs to each term?",
        "ai_role": (
            "AI may point at the part of the code a term refers to. It must not "
            "reveal the pairing, because retrieving the link is the skill."
        ),
    },
    {
        "slug": "code-completion",
        "name": "Complete the Code",
        "bloom_level": 3,
        "stance": "shape",
        "display_order": 10,
        "short_description": "Choose the fragment that completes a partly written program.",
        "pedagogical_aim": (
            "Application without a blank page: students apply a concept by "
            "deciding what the missing piece must be, which requires reading "
            "the surrounding code and the stated requirement. Distractors "
            "encode off-by-one, quoting and operator errors that generated "
            "code often contains."
        ),
        "student_prompt_stem": "Which fragment completes this code correctly?",
        "ai_role": (
            "AI may hint at what the blank has to do. It must not name the "
            "fragment."
        ),
    },
    {
        "slug": "modify-code",
        "name": "Modify the Code",
        "bloom_level": 3,
        "stance": "shape",
        "display_order": 11,
        "short_description": "Change existing code to meet a new requirement.",
        "pedagogical_aim": (
            "Most real programming, and most work with AI output, is changing "
            "code that already exists. Students must find the part of the "
            "code a new requirement touches and change only that, which is a "
            "different skill from writing a solution from scratch."
        ),
        "student_prompt_stem": "Modify this code to meet the new requirement.",
        "ai_role": (
            "AI may suggest which line to look at. It must not supply the "
            "changed line."
        ),
    },
    {
        "slug": "compare-solutions",
        "name": "Compare Solutions",
        "bloom_level": 4,
        "stance": "judge",
        "display_order": 12,
        "short_description": "Decide how two solutions to the same problem differ.",
        "pedagogical_aim": (
            "Generated code often arrives as alternatives. Comparing them "
            "means tracing both and finding the exact point where they "
            "diverge: analysis rather than recall."
        ),
        "student_prompt_stem": "Compare the two solutions. Which statement is true?",
        "ai_role": (
            "AI may suggest an input to trace both solutions on. It must not "
            "say which one is correct."
        ),
    },
    {
        "slug": "misconception-analysis",
        "name": "Analyse a Misconception",
        "bloom_level": 4,
        "stance": "judge",
        "display_order": 13,
        "short_description": "Diagnose why a student's prediction is wrong.",
        "pedagogical_aim": (
            "Diagnosing why an answer is wrong needs a model of how a novice "
            "reasons. The same analytic skill is used to review explanations "
            "written by AI tools, which can be fluent and still wrong."
        ),
        "student_prompt_stem": "Which misconception best explains this prediction?",
        "ai_role": (
            "AI may point to the student's own wording. It must not name the "
            "misconception."
        ),
    },
    {
        "slug": "extend-code",
        "name": "Extend the Code",
        "bloom_level": 5,
        "stance": "shape",
        "display_order": 14,
        "short_description": "Add functionality to working code, combining ideas.",
        "pedagogical_aim": (
            "Synthesis: combining concepts already met (variables, loops, "
            "conditions, lists, functions) to build something new on a "
            "working base, and reasoning about where the new code belongs."
        ),
        "student_prompt_stem": "Extend this program so that it also does the following.",
        "ai_role": (
            "AI may ask what information the new feature needs. It must not "
            "write the extension."
        ),
    },
    {
        "slug": "code-quality-review",
        "name": "Review Code Quality",
        "bloom_level": 6,
        "stance": "judge",
        "display_order": 15,
        "short_description": "Judge working code and pick the most justified review comment.",
        "pedagogical_aim": (
            "Evaluating quality is different from checking correctness. "
            "Learners practise separating 'wrong' from 'could be better', and "
            "rejecting confident but unjustified criticism or praise, which is "
            "a core skill when reviewing generated code."
        ),
        "student_prompt_stem": "Which review comment is the most justified?",
        "ai_role": (
            "AI may prompt the learner to test correctness first. It must not "
            "rank the comments."
        ),
    },
    {
        "slug": "explain-code",
        "name": "Explain Code",
        "bloom_level": 2,
        "stance": "read",
        "display_order": 1,
        "short_description": "Say in plain English what a short fragment does.",
        "pedagogical_aim": (
            "Before students generate or accept code, they need a verbal "
            "model of behaviour. Explanation items make reading a first-class "
            "activity rather than a prelude to writing."
        ),
        "student_prompt_stem": "Explain in plain English what this code does.",
        "ai_role": (
            "AI may offer a hint about where to start reading, or a second "
            "explanation after the student has answered. It must not replace "
            "the student's own account of the code."
        ),
    },
    {
        "slug": "tracing",
        "name": "Program Tracing",
        "bloom_level": 2,
        "stance": "read",
        "display_order": 2,
        "short_description": "Predict output by simulating execution.",
        "pedagogical_aim": (
            "Tracing builds an operational mental model: what is true after "
            "each statement. Distractors are drawn from documented novice "
            "misconceptions rather than random wrong answers."
        ),
        "student_prompt_stem": "What is the output of this code?",
        "ai_role": (
            "AI may ask the student to fill a trace table. It must not emit "
            "the final output on demand."
        ),
    },
    {
        "slug": "purpose",
        "name": "Program Purpose",
        "bloom_level": 2,
        "stance": "read",
        "display_order": 3,
        "short_description": "Name the problem the fragment is solving.",
        "pedagogical_aim": (
            "Students often describe syntax ('it uses a for loop') instead of "
            "purpose ('it finds the largest value'). Purpose items separate "
            "mechanism from intention — a distinction needed when judging "
            "AI-generated code that may be locally plausible but globally wrong."
        ),
        "student_prompt_stem": "What overall problem is this program solving?",
        "ai_role": (
            "AI may contrast a syntactic description with a purpose "
            "description after the attempt. It must not tell the student "
            "the purpose first."
        ),
    },
    {
        "slug": "debugging",
        "name": "Debugging",
        "bloom_level": 4,
        "stance": "judge",
        "display_order": 4,
        "short_description": "Find the fault and say why it matters.",
        "pedagogical_aim": (
            "Debugging is analysis: locating the mismatch between intended "
            "and actual behaviour. In an AI-rich setting this is the same "
            "skill used to inspect generated code."
        ),
        "student_prompt_stem": "Identify the bug.",
        "ai_role": (
            "AI may hint at the region of the program to inspect. It must "
            "not point at the exact line as a completed answer."
        ),
    },
    {
        "slug": "ai-suggestion",
        "name": "AI Suggestion Evaluation",
        "bloom_level": 6,
        "stance": "judge",
        "display_order": 5,
        "short_description": "Accept or reject a generated line, with a reason.",
        "pedagogical_aim": (
            "The pedagogically interesting moment is not generating code but "
            "deciding whether to trust it. Students practise evaluation: "
            "correctness, fit to the requirement, and a stated justification."
        ),
        "student_prompt_stem": "Should this AI suggestion be accepted?",
        "ai_role": (
            "The platform presents a supposed AI suggestion. A live model "
            "must not quietly correct the suggestion or complete the function "
            "for the student."
        ),
    },
    {
        "slug": "code-improvement",
        "name": "Code Improvement",
        "bloom_level": 5,
        "stance": "shape",
        "display_order": 6,
        "short_description": "Improve a working but weak generated solution.",
        "pedagogical_aim": (
            "Synthesis here means revising an existing artefact: names, "
            "structure, edge cases. Students start from AI-like output so "
            "the task is judgement plus rewriting, not blank-page authorship."
        ),
        "student_prompt_stem": "Improve this AI-generated solution.",
        "ai_role": (
            "AI may later comment on the student's revision. It must not "
            "hand back a fully rewritten program as the student's answer."
        ),
    },
    {
        "slug": "prompt-construction",
        "name": "Prompt Construction",
        "bloom_level": 3,
        "stance": "shape",
        "display_order": 7,
        "short_description": "State requirements clearly enough to specify a solution.",
        "pedagogical_aim": (
            "The learning goal is precise communication of behaviour — inputs, "
            "outputs, and edge cases — not prompt-engineering tricks. If a "
            "requirement is underspecified, generated code will guess."
        ),
        "student_prompt_stem": (
            "Write a prompt that would generate a solution meeting these requirements."
        ),
        "ai_role": (
            "AI may later critique missing constraints in the student's "
            "specification. It must not generate the program itself."
        ),
    },
]


TOPICS = [
    {
        "slug": "variables",
        "name": "Variables",
        "display_order": 1,
        "summary": (
            "Names, assignment, and how values persist from one statement "
            "to the next."
        ),
        "why_it_matters": (
            "Generated code is full of names. If students cannot say what a "
            "name currently holds, they cannot judge whether a suggestion is "
            "safe to accept."
        ),
    },
    {
        "slug": "conditionals",
        "name": "Conditionals",
        "display_order": 2,
        "summary": "Decisions: Boolean conditions, branches, and boundary values.",
        "why_it_matters": (
            "AI suggestions often look locally tidy while encoding the wrong "
            "boundary (for example > instead of >=). Conditionals are where "
            "that error hides."
        ),
    },
    {
        "slug": "loops",
        "name": "Loops",
        "display_order": 3,
        "summary": "Repeated action, accumulating state, and stopping conditions.",
        "why_it_matters": (
            "Novices and models both lose track of what is true after each "
            "iteration. Tracing a tiny loop is cheaper than debugging a "
            "generated one."
        ),
    },
    {
        "slug": "functions",
        "name": "Functions",
        "display_order": 4,
        "summary": "Parameters, return values, and the difference between printing and returning.",
        "why_it_matters": (
            "Generated helpers often print when the caller needed a value, "
            "or ignore an edge case in the contract. Students need to read "
            "the function as a specification, not as a block of syntax."
        ),
    },
    {
        "slug": "lists",
        "name": "Lists",
        "display_order": 5,
        "summary": "Ordered collections, indexing, and aggregation over items.",
        "why_it_matters": (
            "List processing is a common AI default. Students should be able "
            "to say whether a fragment is searching, counting, filtering, or "
            "reducing — and whether the empty list is handled."
        ),
    },
    {
        "slug": "dictionaries",
        "name": "Dictionaries",
        "display_order": 6,
        "summary": "Key–value lookup and updating associated data.",
        "why_it_matters": (
            "Models frequently confuse membership of keys with membership of "
            "values. That is an evaluation opportunity, not a reason to skip "
            "the concept."
        ),
    },
]


ACTIVITIES = [
    {
        "topic": "variables",
        "question_type": "explain-code",
        "title": "What does this checkout fragment do?",
        "display_order": 1,
        "bloom_level": 2,
        "block_level": BlockLevel.BLOCKS,
        "estimated_minutes": 3,
        "stem": "Explain in plain English what this code does. Name the values, not only the syntax.",
        "code_snippet": "price = 12\nquantity = 3\ntotal = price * quantity\nprint(total)",
        "choices": [],
        "correct_choice": "",
        "model_explanation": (
            "The program stores a unit price of 12 and a quantity of 3, "
            "multiplies them to get a total of 36, and displays that total. "
            "Each name holds one value after assignment; total does not update "
            "again if price later changed — it already holds 36."
        ),
        "success_criteria": (
            "Mentions storing values, multiplying price by quantity, and "
            "producing 36 / printing the total."
        ),
        "expected_concepts": [
            {
                "name": "Assignment",
                "description": "Values are stored under names (price, quantity) before being used.",
                "keywords": ["store", "assign", "variable", "holds", "set", "value"],
            },
            {
                "name": "Multiplication",
                "description": "total is computed by multiplying price by quantity, giving 36.",
                "keywords": ["multipl", "times", "product"],
            },
            {
                "name": "Output",
                "description": "The final value is displayed with print.",
                "keywords": ["print", "display", "show", "output"],
            },
        ],
        "misconceptions": [
            "Treating the names as labels on the formula rather than as stored values.",
            "Believing total stays linked to price and would change if price changed.",
        ],
        "hint_text": (
            "Read one line at a time and say what each name holds after that line. "
            "Then say what print shows."
        ),
        "follow_up_idea": (
            "Change quantity to 0 and explain what total becomes, and why that "
            "might be a legitimate checkout total."
        ),
    },
    {
        "topic": "loops",
        "question_type": "tracing",
        "title": "Running total over three numbers",
        "display_order": 1,
        "bloom_level": 2,
        "block_level": BlockLevel.RELATIONS,
        "estimated_minutes": 3,
        "stem": "What is printed when this program finishes?",
        "code_snippet": "total = 0\nfor n in [2, 4, 6]:\n    total = total + n\nprint(total)",
        "choices": [
            {"key": "a", "text": "6"},
            {"key": "b", "text": "12"},
            {"key": "c", "text": "2"},
            {"key": "d", "text": "0"},
        ],
        "correct_choice": "b",
        "model_explanation": (
            "total starts at 0. The loop adds 2 (total becomes 2), then 4 "
            "(total becomes 6), then 6 (total becomes 12). print runs after "
            "the loop, so the output is 12. The choice 6 is the last item, not "
            "the sum; the choice 2 is the first item; the choice 0 is the start value "
            "if the loop were ignored."
        ),
        "success_criteria": "Selects 12 and, in later discussion, can recap the three updates.",
        "expected_concepts": [],
        "misconceptions": [
            "Reporting the last item instead of the accumulated sum.",
            "Thinking print happens inside the loop and only the first value appears.",
        ],
        "hint_text": (
            "Make a tiny table: after each pass, what is n and what is total? "
            "Notice that print is not indented inside the loop."
        ),
        "follow_up_idea": (
            "Same loop, but print(total) is indented inside the for. Predict "
            "the three lines of output before checking."
        ),
    },
    {
        "topic": "conditionals",
        "question_type": "debugging",
        "title": "Pass mark labelled the wrong way",
        "display_order": 1,
        "bloom_level": 4,
        "block_level": BlockLevel.RELATIONS,
        "estimated_minutes": 4,
        "stem": (
            "The intended rule is: a score of 50 or more is a pass. "
            "Identify the bug."
        ),
        "code_snippet": (
            "score = 70\n"
            "if score >= 50:\n"
            '    print("fail")\n'
            "else:\n"
            '    print("pass")'
        ),
        "choices": [
            {
                "key": "a",
                "text": "score is the wrong type; it should be a string.",
            },
            {
                "key": "b",
                "text": "The branch bodies are swapped, so a high score is labelled fail.",
            },
            {
                "key": "c",
                "text": "The program needs a loop because there might be many scores.",
            },
            {
                "key": "d",
                "text": "else is illegal in Python; only if is allowed.",
            },
        ],
        "correct_choice": "b",
        "model_explanation": (
            "The condition score >= 50 correctly captures the pass rule, "
            "including the boundary value 50. The fault is that the messages "
            "are attached to the wrong branches: with score = 70 the condition "
            "is true, so the program prints fail. The two print strings are "
            "swapped — a realistic slip when generating two similar branches. "
            "Fluent syntax does not tell you the labels are on the right sides."
        ),
        "success_criteria": "Identifies swapped pass/fail messages rather than inventing a type or loop problem.",
        "expected_concepts": [],
        "misconceptions": [
            "Assuming any if/else that 'looks like Python' must be correct.",
            "Blaming the data type instead of the logical attachment of messages.",
        ],
        "hint_text": (
            "Do not start by asking whether the syntax is legal. Plug in 70 "
            "and say which print runs. Then ask whether that matches the rule."
        ),
        "follow_up_idea": (
            "Fix the messages, then change the rule to 'more than 50 passes'. "
            "Trace the values 49, 50 and 51 and say which one changes outcome."
        ),
    },
    {
        "topic": "functions",
        "question_type": "ai-suggestion",
        "title": "Is this even-number test trustworthy?",
        "display_order": 1,
        "bloom_level": 6,
        "block_level": BlockLevel.RELATIONS,
        "estimated_minutes": 4,
        "stem": (
            "A student asked an AI to complete is_even so that it returns True "
            "when n is even. The AI suggested the highlighted line. Accept or "
            "reject the suggestion, then explain your reasoning."
        ),
        "code_snippet": "def is_even(n):\n    # AI suggestion appears below",
        "ai_suggestion": "return n % 2 == 1",
        "choices": [],
        "correct_choice": "reject",
        "model_explanation": (
            "n % 2 == 1 is true for odd integers, not even ones. The "
            "suggestion is syntactically fine and uses the right operator, "
            "which is exactly why it is tempting. The correct test is "
            "n % 2 == 0. Rejecting it is an evaluation move: fluency of the "
            "line is not evidence that it meets the specification."
        ),
        "success_criteria": (
            "Rejects the suggestion and mentions odd vs even or remainder 1 vs 0."
        ),
        "expected_concepts": [
            {
                "name": "Remainder test",
                "description": "The suggestion tests the remainder after dividing by 2 (modulo).",
                "keywords": ["remainder", "modulo", "mod", "divisible", "divide"],
            },
            {
                "name": "Odd versus even",
                "description": "A remainder of 1 means odd, so the suggestion is true for odd numbers, the opposite of the requirement.",
                "keywords": ["odd", "opposite", "inverted", "wrong"],
            },
            {
                "name": "Correct comparison",
                "description": "An even number has remainder 0, so the comparison should be against 0.",
                "keywords": ["0", "zero"],
            },
        ],
        "misconceptions": [
            "Assuming a short, idiomatic line from an AI is probably correct.",
            "Confusing the remainder of even numbers with 1.",
        ],
        "hint_text": (
            "Try the suggested line in your head with n = 4 and n = 5. "
            "What Boolean comes back? What did the specification ask for?"
        ),
        "follow_up_idea": (
            "Write one sentence specifying is_even including the n = 0 case, "
            "then decide whether return n % 2 == 0 meets that sentence."
        ),
    },
    {
        "topic": "lists",
        "question_type": "purpose",
        "title": "What problem is this list fragment solving?",
        "display_order": 1,
        "bloom_level": 2,
        "block_level": BlockLevel.MACRO,
        "estimated_minutes": 3,
        "stem": "What overall problem is this program solving? Avoid describing only the syntax.",
        "code_snippet": (
            "values = [3, 9, 4, 9, 1]\n"
            "best = values[0]\n"
            "for item in values:\n"
            "    if item > best:\n"
            "        best = item\n"
            "print(best)"
        ),
        "choices": [
            {
                "key": "a",
                "text": "It counts how many times 9 appears in the list.",
            },
            {
                "key": "b",
                "text": "It finds the largest value in the list.",
            },
            {
                "key": "c",
                "text": "It sorts the list into ascending order.",
            },
            {
                "key": "d",
                "text": "It checks whether the list contains only positive numbers.",
            },
        ],
        "correct_choice": "b",
        "model_explanation": (
            "best remembers the largest value seen so far, starting from the "
            "first item. Each later item replaces best only when it is greater. "
            "The program does not count, sort, or test signs. A syntactic "
            "answer ('it uses a for loop and an if') would miss the purpose."
        ),
        "success_criteria": "Names 'largest / maximum value', not merely 'it loops'.",
        "expected_concepts": [],
        "misconceptions": [
            "Describing the control structures instead of the problem being solved.",
            "Assuming any loop over a list is sorting it.",
        ],
        "hint_text": (
            "After the loop, what question about the original list does 'best' answer?"
        ),
        "follow_up_idea": (
            "Change > to < and state the new purpose in one sentence before tracing."
        ),
    },
    {
        "topic": "dictionaries",
        "question_type": "code-improvement",
        "title": "Tighten this generated lookup",
        "display_order": 1,
        "bloom_level": 5,
        "block_level": BlockLevel.MACRO,
        "estimated_minutes": 5,
        "stem": (
            "An AI produced the function below for: return the stock count for "
            "a product name, or 0 if the product is missing. The function works "
            "for the happy path but is unclear and brittle. Improve it. You may "
            "rewrite names, structure, and the missing-key case."
        ),
        "code_snippet": (
            "def get(d, x):\n"
            "    # generated solution\n"
            "    found = False\n"
            "    answer = 0\n"
            "    for k in d:\n"
            "        if k == x:\n"
            "            found = True\n"
            "            answer = d[k]\n"
            "    if found == True:\n"
            "        return answer\n"
            "    else:\n"
            "        return 0"
        ),
        "choices": [],
        "correct_choice": "",
        "model_explanation": (
            "A clearer solution uses dictionary lookup directly, for example "
            "return stock.get(product_name, 0), with names that match the "
            "domain. The generated loop reinvents membership, compares booleans "
            "to True, and hides the idea that dictionaries are keyed access. "
            "Improvement here is conceptual, not cosmetic."
        ),
        "success_criteria": (
            "Uses key lookup or .get, better names, and a default of 0; avoids "
            "a hand-rolled search unless justified."
        ),
        "expected_concepts": [
            {
                "name": "Direct key lookup",
                "description": "Uses dictionary access by key (.get or indexing) instead of searching every key in a loop.",
                "keywords": ["get", "lookup", "key", "index", "bracket"],
            },
            {
                "name": "Missing-key default",
                "description": "Handles an absent product by returning 0, ideally via the default argument.",
                "keywords": ["default", "0", "zero", "missing", "absent", "fallback"],
            },
            {
                "name": "Meaningful names",
                "description": "Renames d and x to names that state the requirement (for example stock and product).",
                "keywords": ["rename", "descriptive", "clear", "stock", "product", "meaningful"],
            },
            {
                "name": "Removing unnecessary code",
                "description": "Removes the manual loop and boolean flag because they add nothing.",
                "keywords": ["loop", "simpl", "shorter", "unnecessary", "redundant", "flag"],
            },
        ],
        "misconceptions": [
            "Thinking a longer generated loop is more 'real programming' than lookup.",
            "Leaving names as d and x, which hide the requirement.",
        ],
        "hint_text": (
            "Ask: what operation is this loop reconstructing? Dictionaries "
            "already offer that operation. Also rename d and x so a reader "
            "can see the requirement."
        ),
        "follow_up_idea": (
            "Add one sentence to the specification about invalid stock values "
            "(for example negative counts) and say whether your improved "
            "function should accept or reject them."
        ),
    },
    {
        "topic": "functions",
        "question_type": "prompt-construction",
        "title": "Specify a vowel counter without writing it",
        "display_order": 2,
        "bloom_level": 3,
        "block_level": BlockLevel.MACRO,
        "estimated_minutes": 5,
        "stem": (
            "Do not write the Python. Write a short specification (the kind of "
            "prompt you would give a colleague or a model) that would produce "
            "a function meeting the requirements below. Include behaviour for "
            "edge cases. Tricks such as 'act as a senior engineer' are not the point."
        ),
        "requirements_text": (
            "Need a function that counts vowels in a string. Vowels are "
            "a, e, i, o, u. The function will be used on user names, so "
            "letter case should not matter. The empty string should be allowed. "
            "The caller needs the count as a number, not a printed message. "
            "The letter y should not be treated as a vowel in this first version."
        ),
        "code_snippet": "",
        "choices": [],
        "correct_choice": "",
        "model_explanation": (
            "A strong specification names the function's purpose, inputs, "
            "return type, the exact vowel set, case handling, the empty-string "
            "result (0), and the decision about y. Weak prompts say 'count "
            "vowels' and leave the model to invent policy. The educational "
            "target is requirements communication, which remains necessary "
            "even when generation is cheap."
        ),
        "success_criteria": (
            "States input and return value, vowel set, case insensitivity, "
            "empty string, and y."
        ),
        "expected_concepts": [
            {
                "name": "Input and return value",
                "description": "States that the function takes a string and returns the count as a number (not a printed message).",
                "keywords": ["return", "returns", "integer", "number"],
            },
            {
                "name": "Vowel set",
                "description": "Names exactly which letters count: a, e, i, o, u.",
                "keywords": ["aeiou", "u"],
            },
            {
                "name": "Case insensitivity",
                "description": "Says upper and lower case letters are treated the same.",
                "keywords": ["case", "uppercase", "lowercase", "capital", "insensitive"],
            },
            {
                "name": "Empty string",
                "description": "Says what happens for an empty string (the count is 0).",
                "keywords": ["empty", "blank", "zero", "nothing"],
            },
            {
                "name": "Letter y excluded",
                "description": "States that y is not treated as a vowel in this version.",
                "keywords": ["y"],
            },
        ],
        "misconceptions": [
            "Writing implementation instead of a specification.",
            "Omitting edge cases and then blaming the generated code.",
        ],
        "hint_text": (
            "List decisions a generator would otherwise have to guess: return "
            "versus print, which letters count, and what happens with ''."
        ),
        "follow_up_idea": (
            "Swap your specification with the expert criteria and mark any "
            "constraint you left implicit. Rewrite only those sentences."
        ),
    },
    {
        "topic": "loops",
        "question_type": "explain-code",
        "title": "Explain this letter-counting loop",
        "display_order": 2,
        "bloom_level": 2,
        "block_level": BlockLevel.BLOCKS,
        "estimated_minutes": 3,
        "stem": (
            "Explain in plain English what this code does. Say what repeats, "
            "what changes each time, and what the program finally shows."
        ),
        "code_snippet": (
            'words = ["a", "bb", "ccc"]\n'
            "count = 0\n"
            "for w in words:\n"
            "    count = count + len(w)\n"
            "print(count)"
        ),
        "choices": [],
        "correct_choice": "",
        "model_explanation": (
            "The loop visits each word in the list in turn (iteration). On each "
            "pass it adds that word's length to count, so count builds up "
            "1, then 3, then 6 (accumulation). After the loop finishes, the "
            "program prints the final count, 6: the total number of letters in "
            "all the words (output)."
        ),
        "success_criteria": (
            "Mentions repeating over each item, a running total that grows, "
            "and printing the final result."
        ),
        "expected_concepts": [
            {
                "name": "Iteration",
                "description": "The loop repeats once for every item in the list.",
                "keywords": ["loop", "repeat", "each", "every", "iterate", "item", "word"],
            },
            {
                "name": "Accumulation",
                "description": "count is a running total that grows by the length of each word.",
                "keywords": ["total", "running", "add", "sum", "accumulat", "builds", "grows"],
            },
            {
                "name": "Output",
                "description": "The final total is displayed with print after the loop ends.",
                "keywords": ["print", "display", "show", "output"],
            },
        ],
        "misconceptions": [
            "Thinking count is reset on each pass of the loop.",
            "Believing print runs once per word rather than once at the end.",
        ],
        "hint_text": (
            "Pick the second word and say what count was before it, what is "
            "added, and what count is afterwards. Then ask where print sits."
        ),
        "follow_up_idea": (
            "Change len(w) to 1 and say in one sentence what the program "
            "counts now."
        ),
    },
    {
        "topic": "conditionals",
        "question_type": "tracing",
        "title": "Which branch runs?",
        "display_order": 2,
        "bloom_level": 2,
        "block_level": BlockLevel.RELATIONS,
        "estimated_minutes": 2,
        "stem": "What is printed?",
        "code_snippet": (
            "temperature = 18\n"
            "if temperature < 16:\n"
            '    print("cold")\n'
            "elif temperature < 22:\n"
            '    print("mild")\n'
            "else:\n"
            '    print("warm")'
        ),
        "choices": [
            {"key": "a", "text": "cold"},
            {"key": "b", "text": "mild"},
            {"key": "c", "text": "warm"},
            {"key": "d", "text": "cold then mild"},
        ],
        "correct_choice": "b",
        "model_explanation": (
            "18 is not less than 16, so the first branch is skipped. 18 is "
            "less than 22, so mild is printed and the else is not considered. "
            "elif means only one branch runs."
        ),
        "success_criteria": "Selects mild.",
        "expected_concepts": [],
        "misconceptions": [
            "Thinking every matching condition runs, so two messages print.",
            "Treating elif as a separate independent if.",
        ],
        "hint_text": "Evaluate the conditions from the top. Stop at the first true one.",
        "follow_up_idea": "Set temperature to 22 and predict again. The boundary is the lesson.",
    },
    {
        "topic": "variables",
        "question_type": "ai-suggestion",
        "title": "Does this line swap the two values?",
        "display_order": 2,
        "bloom_level": 6,
        "block_level": BlockLevel.RELATIONS,
        "estimated_minutes": 4,
        "stem": (
            "The student wants to swap the values of left and right. "
            "An AI suggested the line below. Accept or reject it, and explain."
        ),
        "code_snippet": "left = 3\nright = 8\n# AI suggestion appears below",
        "ai_suggestion": "left = right",
        "choices": [],
        "correct_choice": "reject",
        "model_explanation": (
            "left = right copies 8 into left and discards 3. right is still 8, "
            "so both names hold 8. A swap needs a temporary name, or the "
            "Python idiom left, right = right, left. The suggestion is a "
            "partial truth: it moves one value and loses the other."
        ),
        "success_criteria": "Rejects; notes that 3 is lost / both become 8 / a temporary is needed.",
        "expected_concepts": [
            {
                "name": "Value overwritten",
                "description": "left = right overwrites the original value of left, so 3 is lost.",
                "keywords": ["overwrit", "lost", "lose", "replace", "discard", "copy", "copies"],
            },
            {
                "name": "Both names equal",
                "description": "After the line, left and right both hold 8, so no swap happened.",
                "keywords": ["both", "same", "8", "equal"],
            },
            {
                "name": "Temporary needed",
                "description": "A swap needs somewhere to keep one value (a temporary name) or simultaneous assignment.",
                "keywords": ["temporary", "temp", "third", "extra", "simultaneous"],
            },
        ],
        "misconceptions": [
            "Believing assignment moves a value rather than copying it.",
            "Thinking the original left value is remembered automatically.",
        ],
        "hint_text": "After the suggested line, say the value of left and the value of right.",
        "follow_up_idea": "Write the two-line swap using a name called extra, then trace it.",
    },
    # ------------------------------------------------------------------
    # Level 1 (Knowledge): identify terminology
    # ------------------------------------------------------------------
    {
        "topic": "variables",
        "question_type": "terminology",
        "title": "What is the = symbol called?",
        "display_order": 0,
        "bloom_level": 1,
        "block_level": BlockLevel.ATOMS,
        "estimated_minutes": 1,
        "stem": "In the line below, which term correctly describes the = symbol?",
        "code_snippet": "age = 17",
        "choices": [
            {"key": "a", "text": "The assignment operator"},
            {"key": "b", "text": "The equality operator"},
            {"key": "c", "text": "The comparison operator"},
            {"key": "d", "text": "The concatenation operator"},
        ],
        "correct_choice": "a",
        "model_explanation": (
            "= is the assignment operator: it stores the value on its right "
            "under the name on its left. It does not ask whether the two sides "
            "are equal. Python's equality test is the separate == operator."
        ),
        "success_criteria": "Selects 'assignment operator'.",
        "expected_concepts": [],
        "misconceptions": [
            "Reading = as the mathematical 'is equal to' rather than 'store this value'.",
        ],
        "hint_text": (
            "Ask what the line does to the name age, rather than whether "
            "anything is being checked."
        ),
        "follow_up_idea": (
            "Say in one sentence how age == 17 differs from age = 17, "
            "using the correct term for each."
        ),
    },
    {
        "topic": "conditionals",
        "question_type": "terminology",
        "title": "Name the part after if",
        "display_order": 0,
        "bloom_level": 1,
        "block_level": BlockLevel.ATOMS,
        "estimated_minutes": 1,
        "stem": "What is the expression score >= 50 called in this code?",
        "code_snippet": 'if score >= 50:\n    print("pass")',
        "choices": [
            {"key": "a", "text": "A condition (a Boolean expression)"},
            {"key": "b", "text": "A loop header"},
            {"key": "c", "text": "A function call"},
            {"key": "d", "text": "An assignment"},
        ],
        "correct_choice": "a",
        "model_explanation": (
            "score >= 50 is a condition: an expression that evaluates to True "
            "or False (a Boolean value). The if statement uses it to decide "
            "whether to run the indented block."
        ),
        "success_criteria": "Selects 'condition (Boolean expression)'.",
        "expected_concepts": [],
        "misconceptions": [
            "Thinking the whole if line is an instruction to 'do' the comparison rather than a test.",
        ],
        "hint_text": (
            "What kind of value does score >= 50 produce, and what does the "
            "if statement do with it?"
        ),
        "follow_up_idea": (
            "List two other conditions you could put after if, and say what "
            "value each produces when score is 30."
        ),
    },
    {
        "topic": "loops",
        "question_type": "terminology",
        "title": "What is one pass of a loop called?",
        "display_order": 0,
        "bloom_level": 1,
        "block_level": BlockLevel.ATOMS,
        "estimated_minutes": 1,
        "stem": (
            "Each complete run of the indented block, once for each item in "
            "the list, is called a(n) ...?"
        ),
        "code_snippet": "for n in [2, 4, 6]:\n    print(n)",
        "choices": [
            {"key": "a", "text": "iteration"},
            {"key": "b", "text": "recursion"},
            {"key": "c", "text": "condition"},
            {"key": "d", "text": "parameter"},
        ],
        "correct_choice": "a",
        "model_explanation": (
            "Each repetition of a loop body is an iteration; this loop has "
            "three. Recursion is a different idea: a function calling itself."
        ),
        "success_criteria": "Selects 'iteration'.",
        "expected_concepts": [],
        "misconceptions": [
            "Using 'recursion' as a general word for anything that repeats.",
        ],
        "hint_text": (
            "One of these words is used for a single repetition of a loop "
            "body. Another describes a function that calls itself."
        ),
        "follow_up_idea": (
            "How many iterations would the loop have if the list held five "
            "items? Answer using the term."
        ),
    },
    {
        "topic": "functions",
        "question_type": "terminology",
        "title": "Parameter or argument?",
        "display_order": 0,
        "bloom_level": 1,
        "block_level": BlockLevel.ATOMS,
        "estimated_minutes": 1,
        "stem": "In this function definition, what is the name `name` called?",
        "code_snippet": 'def greet(name):\n    return "Hi " + name',
        "choices": [
            {"key": "a", "text": "A parameter"},
            {"key": "b", "text": "An argument"},
            {"key": "c", "text": "A return value"},
            {"key": "d", "text": "A function"},
        ],
        "correct_choice": "a",
        "model_explanation": (
            "name is a parameter: the placeholder listed in the definition. "
            "An argument is the actual value supplied when the function is "
            'called, such as "Ana" in greet("Ana"). The two terms are '
            "often mixed up, and the difference matters when describing code."
        ),
        "success_criteria": "Selects 'a parameter'.",
        "expected_concepts": [],
        "misconceptions": [
            "Using 'parameter' and 'argument' as interchangeable words.",
        ],
        "hint_text": (
            "Is this name in the definition (the recipe) or in a call "
            "supplying a real value (the ingredient)?"
        ),
        "follow_up_idea": (
            'Write the call greet("Ana") and label which word is the '
            "argument and which is the parameter."
        ),
    },
    {
        "topic": "lists",
        "question_type": "terminology",
        "title": "What is the number in square brackets?",
        "display_order": 0,
        "bloom_level": 1,
        "block_level": BlockLevel.ATOMS,
        "estimated_minutes": 1,
        "stem": (
            "In colours[1], what is the number 1, which picks out a single "
            "item by its position, called?"
        ),
        "code_snippet": 'colours = ["red", "green", "blue"]\nprint(colours[1])',
        "choices": [
            {"key": "a", "text": "An index"},
            {"key": "b", "text": "A key"},
            {"key": "c", "text": "The length"},
            {"key": "d", "text": "A value"},
        ],
        "correct_choice": "a",
        "model_explanation": (
            "The number is an index: the position of an item in the list, "
            "counting from 0. So colours[1] is \"green\". 'Key' is the term "
            "for dictionaries, and the length would be len(colours), which is 3."
        ),
        "success_criteria": "Selects 'an index'.",
        "expected_concepts": [],
        "misconceptions": [
            "Calling the position a 'key', which is dictionary vocabulary.",
            "Assuming positions start at 1.",
        ],
        "hint_text": (
            "Which term describes where an item sits in an ordered "
            "collection? One of the other terms belongs to dictionaries."
        ),
        "follow_up_idea": (
            "Which index would select \"red\"? Say the answer using the term "
            "index."
        ),
    },
    {
        "topic": "dictionaries",
        "question_type": "terminology",
        "title": "Keys and values",
        "display_order": 0,
        "bloom_level": 1,
        "block_level": BlockLevel.ATOMS,
        "estimated_minutes": 1,
        "stem": 'In this dictionary, what is "apples" called?',
        "code_snippet": 'stock = {"apples": 5, "pears": 2}',
        "choices": [
            {"key": "a", "text": "A key"},
            {"key": "b", "text": "A value"},
            {"key": "c", "text": "An index"},
            {"key": "d", "text": "A parameter"},
        ],
        "correct_choice": "a",
        "model_explanation": (
            'Each entry pairs a key with a value. "apples" is the key, used to '
            "look the entry up, and 5 is the value stored under it. Keys, "
            "not positions, are how dictionaries are accessed."
        ),
        "success_criteria": "Selects 'a key'.",
        "expected_concepts": [],
        "misconceptions": [
            "Treating the stored number as the thing used to look an entry up.",
            "Using 'index' for dictionaries.",
        ],
        "hint_text": (
            "Which part do you supply in order to retrieve the other part?"
        ),
        "follow_up_idea": (
            "Name the key and the value in the entry \"pears\": 2, then say "
            "which one you would type inside square brackets to look it up."
        ),
    },
    # ------------------------------------------------------------------
    # Level 1 (Knowledge): define concepts in your own words
    # ------------------------------------------------------------------
    {
        "topic": "variables",
        "question_type": "define-concept",
        "title": "Define a variable",
        "display_order": 0,
        "bloom_level": 1,
        "block_level": BlockLevel.ATOMS,
        "estimated_minutes": 2,
        "stem": "In your own words, what is a variable in programming?",
        "code_snippet": "",
        "choices": [],
        "correct_choice": "",
        "model_explanation": (
            "A variable is a name that refers to a stored value. The value "
            "can be replaced later, so the same name may hold something "
            "different at different points in a program."
        ),
        "success_criteria": (
            "Says a variable has a name, holds a value or data, and that the "
            "value can change."
        ),
        "expected_concepts": [
            {
                "name": "A name",
                "description": "A variable is referred to by a name (a label or identifier).",
                "keywords": ["name", "label", "identifier", "called"],
            },
            {
                "name": "Stores a value",
                "description": "The variable holds a value or piece of data.",
                "keywords": ["store", "holds", "hold", "value", "data", "contain", "memory"],
            },
            {
                "name": "Can change",
                "description": "The stored value can be updated or replaced while the program runs.",
                "keywords": ["change", "update", "reassign", "vary", "modif", "overwrit", "replace"],
            },
        ],
        "misconceptions": [
            "Believing a variable is the value itself rather than a name for it.",
            "Believing a variable can hold only one fixed value for the whole program.",
        ],
        "hint_text": (
            "Think about what you would see in a program: something written "
            "as a name, something it is connected to, and what can happen "
            "to that connection later."
        ),
        "follow_up_idea": (
            "Give an example line that creates a variable and another that "
            "changes it, and say what the name holds after each."
        ),
    },
    {
        "topic": "functions",
        "question_type": "define-concept",
        "title": "Define a function",
        "display_order": 0,
        "bloom_level": 1,
        "block_level": BlockLevel.ATOMS,
        "estimated_minutes": 2,
        "stem": (
            "In your own words, what is a function, and why do programmers "
            "use them? Say what it is, not how to write one."
        ),
        "code_snippet": "",
        "choices": [],
        "correct_choice": "",
        "model_explanation": (
            "A function is a named, reusable block of code. It can take inputs "
            "(parameters) and can give back a result (a return value). "
            "Programmers use functions to avoid repeating code and to give a "
            "task a meaningful name."
        ),
        "success_criteria": (
            "Describes a named, reusable block of code, mentions inputs, and "
            "mentions a result being returned."
        ),
        "expected_concepts": [
            {
                "name": "Reusable named block",
                "description": "A function is a named group of code that can be used many times.",
                "keywords": ["reuse", "reusable", "repeat", "again", "named", "block", "chunk", "group"],
            },
            {
                "name": "Inputs",
                "description": "A function can receive inputs (parameters/arguments).",
                "keywords": ["input", "parameter", "argument", "given", "pass", "receive"],
            },
            {
                "name": "Returns a result",
                "description": "A function can give back a value to the code that called it.",
                "keywords": ["return", "result", "output", "produce", "back"],
            },
        ],
        "misconceptions": [
            "Thinking a function must print something rather than give back a value.",
            "Seeing functions only as a way to make code shorter, not as named units of purpose.",
        ],
        "hint_text": (
            "Imagine using the same few lines in five places in a program. "
            "What would you want to be able to do instead, and what would "
            "you need to hand over and get back?"
        ),
        "follow_up_idea": (
            "Pick a task you do repeatedly (such as calculating a total) and "
            "say what its name, inputs and result would be."
        ),
    },
    {
        "topic": "dictionaries",
        "question_type": "define-concept",
        "title": "Define a dictionary",
        "display_order": 0,
        "bloom_level": 1,
        "block_level": BlockLevel.ATOMS,
        "estimated_minutes": 2,
        "stem": (
            "In your own words, what is a dictionary in Python, and how is it "
            "different from a list?"
        ),
        "code_snippet": "",
        "choices": [],
        "correct_choice": "",
        "model_explanation": (
            "A dictionary stores pairs of keys and values. You look up a value "
            "by its key. A list, by contrast, is ordered and its items are "
            "reached by a numbered position (an index)."
        ),
        "success_criteria": (
            "Mentions key-value pairs, looking things up by key, and the "
            "contrast with lists using position."
        ),
        "expected_concepts": [
            {
                "name": "Key-value pairs",
                "description": "Entries are pairs: a key associated with a value.",
                "keywords": ["key", "pair", "pairs", "associated", "mapping"],
            },
            {
                "name": "Lookup by key",
                "description": "A value is found by supplying its key.",
                "keywords": ["lookup", "look", "find", "access", "retrieve", "get"],
            },
            {
                "name": "Contrast with list position",
                "description": "Lists are reached by numbered position; dictionaries are not.",
                "keywords": ["position", "index", "indices", "number", "numbered", "order"],
            },
        ],
        "misconceptions": [
            "Treating a dictionary as just another list with labels.",
            "Believing values, rather than keys, are used for lookup.",
        ],
        "hint_text": (
            "Compare how you would find 'the price of apples' in a list "
            "versus a dictionary. What do you hand over each time?"
        ),
        "follow_up_idea": (
            "Describe a real-world thing that behaves like a dictionary "
            "(such as a phone book) and name its keys and values."
        ),
    },
    # ==================================================================
    # VARIABLES: L3, L4, L5 (L1, L2, L6 are defined above)
    # ==================================================================
    {
        "topic": "variables",
        "question_type": "code-completion",
        "title": "Complete the bill total",
        "bloom_level": 3,
        "block_level": BlockLevel.ATOMS,
        "estimated_minutes": 2,
        "stem": (
            "The program should print the total the customer pays: the "
            "subtotal plus delivery. Which expression completes the blank?"
        ),
        "code_snippet": (
            "subtotal = 40\n"
            "delivery = 5\n"
            "total = ______\n"
            "print(total)"
        ),
        "choices": [
            {"key": "a", "text": "subtotal + delivery"},
            {"key": "b", "text": '"subtotal + delivery"'},
            {"key": "c", "text": 'subtotal + "delivery"'},
            {"key": "d", "text": "subtotal * delivery"},
        ],
        "correct_choice": "a",
        "model_explanation": (
            "subtotal + delivery uses the values held by the two names and "
            "adds them, so 45 is printed. With quotation marks around the "
            "whole expression, Python treats it as plain text and prints the "
            "words themselves. Adding the text \"delivery\" to a number "
            "raises an error because numbers and text cannot be added. "
            "Multiplying gives 200, which is the wrong operation for "
            "'plus delivery'."
        ),
        "success_criteria": (
            "Selects subtotal + delivery, and can say why quotation marks "
            "change the meaning."
        ),
        "expected_concepts": [],
        "misconceptions": [
            "Thinking quotation marks around a name still use the variable's value.",
            "Choosing an operator by habit rather than from the requirement.",
        ],
        "hint_text": (
            "Decide whether Python should use the values held by the names or "
            "treat the words as plain text. What would print show in each case?"
        ),
        "follow_up_idea": (
            "Change delivery to 0 and predict the output. Then say what would "
            "go wrong if the total line came before delivery was assigned."
        ),
    },
    {
        "topic": "variables",
        "question_type": "misconception-analysis",
        "title": "Why did the student predict 10?",
        "bloom_level": 4,
        "block_level": BlockLevel.RELATIONS,
        "estimated_minutes": 3,
        "stem": (
            "A student predicts this program prints 10 and explains: 'b is "
            "connected to a, so when a changes, b changes too.' Which "
            "misconception best explains the prediction?"
        ),
        "code_snippet": "a = 5\nb = a\na = 10\nprint(b)",
        "choices": [
            {
                "key": "a",
                "text": "Believing b stays linked to a, so it updates whenever a changes",
            },
            {"key": "b", "text": "Believing = tests whether two names are equal"},
            {
                "key": "c",
                "text": "Believing print always shows the most recently assigned value",
            },
            {"key": "d", "text": "Believing a name can only be assigned once"},
        ],
        "correct_choice": "a",
        "model_explanation": (
            "b = a copies the value a holds at that moment (5) into b. After "
            "that the two names are independent, so a = 10 changes only a, and "
            "the program prints 5. The student treats = as a lasting link, "
            "like a spreadsheet formula. The student's own word 'connected' "
            "separates this from the 'print shows the latest value' option, "
            "which would not mention b at all."
        ),
        "success_criteria": (
            "Identifies the 'linked names' misconception and can state that "
            "the program prints 5."
        ),
        "expected_concepts": [],
        "misconceptions": [
            "Thinking = creates a lasting link, like a spreadsheet formula.",
            "Reading assignment as a mathematical equation.",
        ],
        "hint_text": (
            "Look at the student's own word: 'connected'. Ask what b = a does "
            "at the moment it runs, and whether anything later reaches back "
            "to change b."
        ),
        "follow_up_idea": (
            "Add one line to the program so that b really does end up as 10, "
            "and explain why Python needed that extra line."
        ),
    },
    {
        "topic": "variables",
        "question_type": "extend-code",
        "title": "Add a discount without a magic number",
        "bloom_level": 5,
        "block_level": BlockLevel.MACRO,
        "estimated_minutes": 5,
        "stem": (
            "This program prices an order. Extend it so it also applies a 10% "
            "discount and prints the discounted total. Use a named variable "
            "for the discount rate rather than typing the number inside the "
            "calculation. You may write code or describe your changes in words."
        ),
        "code_snippet": (
            "price = 20\n"
            "quantity = 3\n"
            "total = price * quantity\n"
            "print(total)"
        ),
        "choices": [],
        "correct_choice": "",
        "model_explanation": (
            "One good extension names the rate, applies it to the existing "
            "total, and prints the result:\n"
            "discount_rate = 0.10\n"
            "discounted_total = total - total * discount_rate\n"
            "print(discounted_total)\n"
            "This prints 54.0 after the original 60. Reusing total avoids "
            "recalculating price * quantity, and the named rate means a "
            "change to 15% is a one-place edit."
        ),
        "success_criteria": (
            "Introduces a named variable for the rate, applies it to the "
            "total (subtracting, or multiplying by 0.9), and prints the new "
            "value."
        ),
        "expected_concepts": [
            {
                "name": "Named rate variable",
                "description": "The discount rate is stored under its own name (for example discount_rate) instead of being typed inside the formula.",
                "keywords": ["rate", "discount_rate", "discount", "variable", "named", "constant", "percentage"],
            },
            {
                "name": "Applies the discount to the total",
                "description": "The new total is computed from the existing total by subtracting the discount or multiplying by 0.9.",
                "keywords": ["subtract", "minus", "reduce", "multipl", "*", "-"],
            },
            {
                "name": "Prints the result",
                "description": "The discounted value is displayed with print.",
                "keywords": ["print", "display", "show", "output"],
            },
        ],
        "misconceptions": [
            "Typing 0.1 or 10 directly into the formula (a 'magic number') so nobody can tell what it means.",
            "Believing a later line changes what an earlier print already displayed.",
        ],
        "hint_text": (
            "What number is hiding in your formula? Give it a name, then ask "
            "what you would have to edit if the discount became 15%."
        ),
        "follow_up_idea": (
            "Change the rate to 15% and count how many places in your program "
            "you had to edit. Explain why one place is the goal."
        ),
    },
    # ==================================================================
    # CONDITIONALS: L3, L5, L6 (L1, L2, L4 are defined above)
    # ==================================================================
    {
        "topic": "conditionals",
        "question_type": "modify-code",
        "title": "A rule changes: does 65 qualify?",
        "bloom_level": 3,
        "block_level": BlockLevel.BLOCKS,
        "estimated_minutes": 3,
        "stem": (
            "The pricing rule has changed: people aged 65 and over now get "
            "the senior discount (previously only people over 65 did). Modify "
            "the condition so the program follows the new rule. You may write "
            "the new line of code or describe the change in words."
        ),
        "code_snippet": (
            "age = 65\n"
            "if age > 65:\n"
            '    print("senior discount")\n'
            "else:\n"
            '    print("full price")'
        ),
        "choices": [],
        "correct_choice": "",
        "model_explanation": (
            "Change the comparison to age >= 65. With the old condition, "
            "age = 65 is not greater than 65, so the program printed 'full "
            "price'. With >= it prints 'senior discount'. The value whose "
            "behaviour changes is exactly the boundary, 65; ages such as 64 "
            "and 66 behave the same before and after."
        ),
        "success_criteria": (
            "Changes > to >= (or an equivalent such as > 64 for whole "
            "numbers) and recognises that 65 itself is the boundary value."
        ),
        "expected_concepts": [
            {
                "name": "Boundary included",
                "description": "The comparison must include 65 itself: >= 65, or > 64 for whole numbers.",
                "keywords": [">=", "at least", "or equal", "64"],
            },
            {
                "name": "Names the boundary value",
                "description": "Recognises that 65 itself is the value whose behaviour changes.",
                "keywords": ["65", "boundary", "edge", "exactly"],
            },
        ],
        "misconceptions": [
            "Changing the number (for example to 66) instead of fixing the operator.",
            "Assuming > and >= behave the same at the boundary value.",
        ],
        "hint_text": (
            "Run the old code in your head with age = 64, 65 and 66. Which of "
            "those three would behave differently under the new rule?"
        ),
        "follow_up_idea": (
            "Add a second rule: ages 12 and under pay the child fare. State "
            "the boundary values you would test for both rules."
        ),
    },
    {
        "topic": "conditionals",
        "question_type": "code-improvement",
        "title": "Tidy the repeated tests",
        "bloom_level": 5,
        "block_level": BlockLevel.MACRO,
        "estimated_minutes": 5,
        "stem": (
            "An AI generated this grading function. It gives the right "
            "answer, but it keeps re-testing conditions it already knows. "
            "Refactor it so the logic is clearer without changing what it "
            "returns. You may write code or describe the changes in words."
        ),
        "code_snippet": (
            "def grade(mark):\n"
            "    if mark >= 70:\n"
            '        return "A"\n'
            "    if mark < 70:\n"
            "        if mark >= 60:\n"
            '            return "B"\n'
            "    if mark < 60:\n"
            '        return "C"'
        ),
        "choices": [],
        "correct_choice": "",
        "model_explanation": (
            "Once the first branch has returned, any code that runs afterwards "
            "already knows mark < 70, so testing mark < 70 again tells Python "
            "nothing new. The same is true of mark < 60 after the B check. A "
            "chain says this directly:\n"
            "def grade(mark):\n"
            "    if mark >= 70:\n"
            '        return "A"\n'
            "    elif mark >= 60:\n"
            '        return "B"\n'
            "    else:\n"
            '        return "C"\n'
            "The thresholds, 70 and 60, and every returned grade are "
            "unchanged."
        ),
        "success_criteria": (
            "Uses an elif/else chain, removes the redundant comparisons, and "
            "keeps the 70 and 60 boundaries and the A/B/C results unchanged."
        ),
        "expected_concepts": [
            {
                "name": "Chains the branches",
                "description": "Uses elif/else so each later branch relies on the earlier ones having failed.",
                "keywords": ["elif", "else", "chain", "chained"],
            },
            {
                "name": "Removes redundant tests",
                "description": "Drops comparisons such as mark < 70 that are already known to be true.",
                "keywords": ["redundant", "unnecessary", "repeat", "already", "remove", "duplicate"],
            },
            {
                "name": "Keeps behaviour and boundaries",
                "description": "The thresholds 70 and 60 and the returned grades stay the same.",
                "keywords": ["70", "60", "same", "unchanged", "behaviour", "behavior", "boundary"],
            },
        ],
        "misconceptions": [
            "Thinking each if is independent, so every later test must restate the earlier ones.",
            "Assuming more checks always make code safer.",
            "Changing the thresholds while tidying the structure.",
        ],
        "hint_text": (
            "After the first return runs, what do you already know about mark "
            "whenever execution reaches the next line? Which checks tell "
            "Python nothing new?"
        ),
        "follow_up_idea": (
            "Add a grade 'D' for marks below 40. Say which single line you "
            "had to add or change in your improved version."
        ),
    },
    {
        "topic": "conditionals",
        "question_type": "ai-suggestion",
        "title": "Is this leap-year check trustworthy?",
        "bloom_level": 6,
        "block_level": BlockLevel.MACRO,
        "estimated_minutes": 5,
        "stem": (
            "Requirement: a year is a leap year if it is divisible by 4, "
            "except century years (divisible by 100), which are leap years "
            "only if divisible by 400. An AI generated the function below. "
            "Accept or reject it, then justify your decision by naming the "
            "years you checked."
        ),
        "code_snippet": "",
        "ai_suggestion": (
            "def is_leap_year(year):\n"
            "    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)"
        ),
        "choices": [],
        "correct_choice": "accept",
        "model_explanation": (
            "The function is correct, so accepting it is right. Checking "
            "evidence: 2024 gives True (divisible by 4, not a century); 1900 "
            "gives False (a century but not divisible by 400); 2000 gives "
            "True (divisible by 400); 2023 gives False (not divisible by 4). "
            "It looks denser than most AI output, which makes it easy to "
            "distrust, but suspicion is not evaluation. The decision should "
            "rest on cases that exercise each part of the rule."
        ),
        "success_criteria": (
            "Accepts the function and justifies it by checking specific years "
            "(including a century year such as 1900 or 2000), or by walking "
            "through each part of the rule."
        ),
        "expected_concepts": [
            {
                "name": "Divisible-by-4 rule",
                "description": "Recognises the year % 4 == 0 test as the basic leap-year rule.",
                "keywords": ["4", "divisible", "remainder", "modulo", "%"],
            },
            {
                "name": "Century exception",
                "description": "Recognises that years divisible by 100 are excluded by default.",
                "keywords": ["100", "century", "centuries", "exception", "except"],
            },
            {
                "name": "The 400 override",
                "description": "Recognises that years divisible by 400 are leap years again.",
                "keywords": ["400"],
            },
            {
                "name": "Tested example years",
                "description": "Names specific years that were checked, such as 1900, 2000 or 2024.",
                "keywords": ["1900", "2000", "2024", "2023", "example", "tested", "tried"],
            },
        ],
        "misconceptions": [
            "Rejecting code because it looks complicated, without testing it.",
            "Assuming AI code with several conditions probably hides a bug.",
            "Forgetting that 1900 and 2000 behave differently.",
        ],
        "hint_text": (
            "Don't judge by how it looks. Choose years that exercise each "
            "part of the rule, including 1900 and 2000, and work out what the "
            "expression returns for each."
        ),
        "follow_up_idea": (
            "Suppose the AI had dropped the 'or year % 400 == 0' part. Find a "
            "year where the two versions disagree."
        ),
    },
    # ==================================================================
    # LOOPS: L3, L4, L5, L6 (L1, L2 are defined above)
    # ==================================================================
    {
        "topic": "loops",
        "question_type": "code-completion",
        "title": "Print 1 to 5",
        "bloom_level": 3,
        "block_level": BlockLevel.BLOCKS,
        "estimated_minutes": 2,
        "stem": (
            "The program should print the numbers 1, 2, 3, 4, 5, each on its "
            "own line. Which arguments complete range(...)?"
        ),
        "code_snippet": "for i in range(______):\n    print(i)",
        "choices": [
            {"key": "a", "text": "1, 6"},
            {"key": "b", "text": "1, 5"},
            {"key": "c", "text": "5"},
            {"key": "d", "text": "6"},
        ],
        "correct_choice": "a",
        "model_explanation": (
            "range(start, stop) begins at start and stops before stop, so "
            "range(1, 6) produces 1, 2, 3, 4, 5. range(1, 5) stops one short, "
            "at 4. A single argument, as in range(5) or range(6), starts at 0, "
            "so range(5) gives 0 to 4 and range(6) gives 0 to 5."
        ),
        "success_criteria": (
            "Selects 1, 6, and can say that the stop value is not included."
        ),
        "expected_concepts": [],
        "misconceptions": [
            "Believing the stop value of range is included in the output.",
            "Forgetting that range starts at 0 when given one argument.",
        ],
        "hint_text": (
            "Write out the numbers each choice would produce, paying "
            "attention to the first and last value."
        ),
        "follow_up_idea": (
            "Predict what range(2, 11, 2) prints, and explain what the third "
            "value does."
        ),
    },
    {
        "topic": "loops",
        "question_type": "compare-solutions",
        "title": "Two ways to total a list",
        "bloom_level": 4,
        "block_level": BlockLevel.RELATIONS,
        "estimated_minutes": 4,
        "stem": (
            "Two AI-generated programs both try to print the total of the "
            "numbers in a list. Each is a separate program. Compare them. "
            "Which statement is true?"
        ),
        "code_snippet": (
            "numbers = [4, 7, 1]\n"
            "\n"
            "# Solution A\n"
            "total = 0\n"
            "for n in numbers:\n"
            "    total = total + n\n"
            "print(total)\n"
            "\n"
            "# Solution B\n"
            "for n in numbers:\n"
            "    total = 0\n"
            "    total = total + n\n"
            "print(total)"
        ),
        "choices": [
            {"key": "a", "text": "Both print 12"},
            {
                "key": "b",
                "text": "A prints 12; B prints 1, because total is reset to 0 on every pass",
            },
            {"key": "c", "text": "A prints 1; B prints 12"},
            {
                "key": "d",
                "text": "Both print 12, but B is slower because it assigns total more often",
            },
        ],
        "correct_choice": "b",
        "model_explanation": (
            "In A, total starts at 0 once, before the loop, and accumulates "
            "4, then 11, then 12. In B, total = 0 sits inside the loop, so "
            "every pass throws away the running total and starts again; after "
            "the last pass total is 0 + 1, so B prints 1. The two programs "
            "look almost identical, and the only difference is where one "
            "line sits, which is why tracing matters more than similarity."
        ),
        "success_criteria": (
            "Identifies that the initialisation inside the loop in B resets "
            "total, giving 1 rather than 12."
        ),
        "expected_concepts": [],
        "misconceptions": [
            "Believing the position of an initialisation line does not matter.",
            "Judging solutions by how similar they look instead of tracing them.",
        ],
        "hint_text": (
            "Trace each program on [4, 7, 1]. Where does total get its "
            "starting value, and how many times does that line run?"
        ),
        "follow_up_idea": (
            "Describe in one sentence the rule for where an accumulator should "
            "be initialised relative to the loop."
        ),
    },
    {
        "topic": "loops",
        "question_type": "extend-code",
        "title": "From a total to an average",
        "bloom_level": 5,
        "block_level": BlockLevel.MACRO,
        "estimated_minutes": 5,
        "stem": (
            "This program totals a list of scores. Extend it so it also "
            "prints the average score. The average should be calculated once, "
            "after all the scores have been added. You may write code or "
            "describe your changes in words."
        ),
        "code_snippet": (
            "scores = [60, 75, 90]\n"
            "total = 0\n"
            "for s in scores:\n"
            "    total = total + s\n"
            "print(total)"
        ),
        "choices": [],
        "correct_choice": "",
        "model_explanation": (
            "An average needs two things: the total and how many scores there "
            "are. Both are only known once the loop has finished, so the "
            "calculation goes after it:\n"
            "average = total / len(scores)\n"
            "print(average)\n"
            "This prints 75.0. Using len(scores) rather than a typed 3 means "
            "the program still works when scores changes."
        ),
        "success_criteria": (
            "Counts the items (for example with len), divides the total by "
            "that count after the loop, and prints the result."
        ),
        "expected_concepts": [
            {
                "name": "Counts the items",
                "description": "Finds how many scores there are, ideally with len(scores).",
                "keywords": ["len", "count", "number of", "how many", "items"],
            },
            {
                "name": "Divides the total by the count",
                "description": "The average is the total divided by the number of scores.",
                "keywords": ["/", "divide", "divided", "division"],
            },
            {
                "name": "Shows the average",
                "description": "The average is displayed with print.",
                "keywords": ["print", "display", "show", "output"],
            },
        ],
        "misconceptions": [
            "Dividing inside the loop, on every pass.",
            "Dividing by a typed-in 3 instead of the length of the list.",
            "Forgetting that an average needs both the total and the count.",
        ],
        "hint_text": (
            "What two pieces of information does an average need, and at "
            "which point in the program are both finally known?"
        ),
        "follow_up_idea": (
            "Predict what your program does if the list is empty, and say "
            "what you would check before dividing."
        ),
    },
    {
        "topic": "loops",
        "question_type": "ai-suggestion",
        "title": "Will this countdown ever finish?",
        "bloom_level": 6,
        "block_level": BlockLevel.RELATIONS,
        "estimated_minutes": 4,
        "stem": (
            "Requirement: count_down(n) prints n, n-1, ... 1 and then prints "
            "Liftoff. An AI generated the function below. Accept or reject "
            "it, then explain your reasoning, including what happens when it "
            "runs."
        ),
        "code_snippet": "",
        "ai_suggestion": (
            "def count_down(n):\n"
            "    while n > 0:\n"
            "        print(n)\n"
            '    print("Liftoff")'
        ),
        "choices": [],
        "correct_choice": "reject",
        "model_explanation": (
            "Nothing inside the loop ever changes n, so the condition n > 0 "
            "stays true forever. count_down(3) prints 3 endlessly and never "
            "reaches Liftoff. The function name and the shape of the code "
            "suggest a countdown, but only tracing shows that it does not "
            "count. Adding n = n - 1 inside the loop fixes it."
        ),
        "success_criteria": (
            "Rejects the suggestion and explains that n is never changed, so "
            "the loop never ends."
        ),
        "expected_concepts": [
            {
                "name": "The loop never ends",
                "description": "Recognises that the loop runs forever and Liftoff is never printed.",
                "keywords": ["infinite", "forever", "never", "endless", "stuck", "terminate"],
            },
            {
                "name": "n is never changed",
                "description": "Recognises that nothing in the loop updates n.",
                "keywords": ["change", "changes", "update", "decrement", "reduce", "-=", "subtract", "same"],
            },
            {
                "name": "The condition stays true",
                "description": "Connects the unchanging n to a loop condition that is always true.",
                "keywords": ["condition", "true"],
            },
        ],
        "misconceptions": [
            "Assuming a while loop lowers its own counter the way a for loop advances.",
            "Reading the code as 'count down' because of the function name instead of tracing it.",
        ],
        "hint_text": (
            "Trace count_down(3). After the first print, what is n? Does "
            "anything change it before the condition is checked again?"
        ),
        "follow_up_idea": (
            "Make the smallest change that fixes it, then trace count_down(3) "
            "to confirm it prints 3, 2, 1 and Liftoff."
        ),
    },
    # ==================================================================
    # FUNCTIONS: L2, L4, L5 (L1, L3, L6 are defined above)
    # ==================================================================
    {
        "topic": "functions",
        "question_type": "tracing",
        "title": "What does double(4) give back?",
        "bloom_level": 2,
        "block_level": BlockLevel.RELATIONS,
        "estimated_minutes": 3,
        "stem": "What is printed when this program runs?",
        "code_snippet": (
            "def double(n):\n"
            "    return n * 2\n"
            "\n"
            "result = double(4)\n"
            "print(result + 1)"
        ),
        "choices": [
            {"key": "a", "text": "9"},
            {"key": "b", "text": "8"},
            {"key": "c", "text": "5"},
            {"key": "d", "text": "An error, because double never prints anything"},
        ],
        "correct_choice": "a",
        "model_explanation": (
            "double(4) returns 8, which is stored in result. The last line "
            "then prints result + 1, which is 9. A function does not need to "
            "print to be useful: return hands a value back to the code that "
            "called it. Printing 8 ignores the + 1, and printing 5 treats "
            "the call as if it had given back 4."
        ),
        "success_criteria": (
            "Selects 9 and can describe where the value 8 went."
        ),
        "expected_concepts": [],
        "misconceptions": [
            "Thinking a function must print in order to produce a result.",
            "Ignoring the + 1 that happens after the call.",
            "Treating double(4) as though it handed back the original 4.",
        ],
        "hint_text": (
            "Follow the value: what does double(4) hand back, where does it "
            "go, and what is done with it before print?"
        ),
        "follow_up_idea": (
            "Predict the output of print(double(double(2))) and explain the "
            "order in which the calls run."
        ),
    },
    {
        "topic": "functions",
        "question_type": "debugging",
        "title": "The average that came back empty",
        "bloom_level": 4,
        "block_level": BlockLevel.RELATIONS,
        "estimated_minutes": 4,
        "stem": (
            "The programmer expected this program to print only 'Average is "
            "6.0'. Instead it prints 6.0 on one line and 'Average is None' on "
            "the next. Identify the bug."
        ),
        "code_snippet": (
            "def average(a, b):\n"
            "    print((a + b) / 2)\n"
            "\n"
            "result = average(4, 8)\n"
            'print("Average is", result)'
        ),
        "choices": [
            {
                "key": "a",
                "text": "average prints its answer instead of returning it, so result holds None",
            },
            {"key": "b", "text": "The formula should divide by 3, not 2"},
            {"key": "c", "text": "print cannot be used inside a function"},
            {
                "key": "d",
                "text": "result must be created before the function is defined",
            },
        ],
        "correct_choice": "a",
        "model_explanation": (
            "Inside average, print shows 6.0 immediately, which is the first "
            "line of output. The function has no return statement, so it gives "
            "back None, and that is what result holds when the last line "
            "prints 'Average is None'. The fix is to return (a + b) / 2 and "
            "let the caller decide what to print. The formula and the order "
            "of definitions are fine, and print is allowed inside functions."
        ),
        "success_criteria": (
            "Identifies that the function prints instead of returning, so "
            "the caller receives None."
        ),
        "expected_concepts": [],
        "misconceptions": [
            "Believing that printing a value inside a function also gives it back to the caller.",
            "Not knowing that a function without return gives back None.",
        ],
        "hint_text": (
            "List every line of output in order. Where does the first line "
            "come from, and what value does result actually hold?"
        ),
        "follow_up_idea": (
            "Fix the function, then predict what print(average(4, 8) + 1) "
            "shows before the fix and after it."
        ),
    },
    {
        "topic": "functions",
        "question_type": "code-improvement",
        "title": "Stop repeating the tax calculation",
        "bloom_level": 5,
        "block_level": BlockLevel.MACRO,
        "estimated_minutes": 5,
        "stem": (
            "An AI generated this code to show prices with 20% tax. It works "
            "but repeats itself. Improve it by removing the duplication, and "
            "avoid hiding the 20% inside the formula. You may write code or "
            "describe your changes in words."
        ),
        "code_snippet": (
            "price1 = 20\n"
            "total1 = price1 + price1 * 0.2\n"
            'print("Total:", total1)\n'
            "\n"
            "price2 = 35\n"
            "total2 = price2 + price2 * 0.2\n"
            'print("Total:", total2)\n'
            "\n"
            "price3 = 50\n"
            "total3 = price3 + price3 * 0.2\n"
            'print("Total:", total3)'
        ),
        "choices": [],
        "correct_choice": "",
        "model_explanation": (
            "The three blocks differ only in the price, so the price becomes "
            "an input and the rest becomes the body of a function:\n"
            "TAX_RATE = 0.2\n"
            "def price_with_tax(price):\n"
            "    return price + price * TAX_RATE\n"
            "for price in [20, 35, 50]:\n"
            '    print("Total:", price_with_tax(price))\n'
            "The function returns the value rather than printing it, so it "
            "can be reused. The named TAX_RATE means a change to 25% is one "
            "edit instead of three."
        ),
        "success_criteria": (
            "Extracts a function that takes the price and returns the total, "
            "and names the tax rate instead of repeating 0.2."
        ),
        "expected_concepts": [
            {
                "name": "Extracts a function",
                "description": "The repeated calculation is moved into a function that is defined once.",
                "keywords": ["def", "function", "define"],
            },
            {
                "name": "Takes input and returns the total",
                "description": "The price is passed in as a parameter and the total is returned, not printed inside.",
                "keywords": ["return", "returns", "parameter", "argument", "input"],
            },
            {
                "name": "Names the tax rate",
                "description": "The 20% rate is stored under a name instead of appearing as 0.2 in every formula.",
                "keywords": ["tax_rate", "rate", "constant", "variable", "named"],
            },
        ],
        "misconceptions": [
            "Believing copy-and-paste with changed numbers is fine because it is quick.",
            "Leaving 0.2 inside the formula, where a later reader cannot tell what it means.",
            "Believing a function has to print its answer rather than return it.",
        ],
        "hint_text": (
            "Which lines differ between the three blocks and which are "
            "identical? What differs becomes an input; the rest becomes the "
            "body."
        ),
        "follow_up_idea": (
            "The tax rate rises to 25%. Count how many places you would have "
            "to edit in the original code and in your improved version."
        ),
    },
    # ==================================================================
    # LISTS: L3, L4, L5, L6 (L1, L2 are defined above)
    # ==================================================================
    {
        "topic": "lists",
        "question_type": "modify-code",
        "title": "Print only the long names",
        "bloom_level": 3,
        "block_level": BlockLevel.BLOCKS,
        "estimated_minutes": 3,
        "stem": (
            "The program should print only the names with more than 3 "
            "letters. Modify it. You may write the new code or describe your "
            "changes in words."
        ),
        "code_snippet": (
            'names = ["Al", "Beatrice", "Cy", "Dmitri"]\n'
            "for name in names:\n"
            "    print(name)"
        ),
        "choices": [],
        "correct_choice": "",
        "model_explanation": (
            "Each name needs its own decision, so the test goes inside the "
            "loop, around the print:\n"
            "for name in names:\n"
            "    if len(name) > 3:\n"
            "        print(name)\n"
            "len(name) is the number of letters in one name, so 'Beatrice' "
            "and 'Dmitri' are printed and 'Al' and 'Cy' are skipped. "
            "len(names), by contrast, would be the number of names in the "
            "list."
        ),
        "success_criteria": (
            "Adds a condition inside the loop that uses len(name) > 3 (or an "
            "equivalent such as >= 4)."
        ),
        "expected_concepts": [
            {
                "name": "Measures each name's length",
                "description": "Uses len(name), the length of one name, to decide.",
                "keywords": ["len", "length", "letters", "characters"],
            },
            {
                "name": "Adds a condition inside the loop",
                "description": "Uses an if inside the loop so each name is judged individually.",
                "keywords": ["if", "condition", "only", "filter", "check"],
            },
            {
                "name": "Uses the right threshold",
                "description": "Keeps names with more than 3 letters: > 3 or >= 4.",
                "keywords": ["> 3", ">= 4", "more than 3", "greater than 3", "at least 4", "over 3"],
            },
        ],
        "misconceptions": [
            "Putting the if outside the loop, so it is checked only once.",
            "Using >= 3, which wrongly keeps three-letter names.",
            "Confusing len(names), the number of names, with len(name), the letters in one name.",
        ],
        "hint_text": (
            "You need a separate decision for each name. Which line runs once "
            "per name, and what could you ask there?"
        ),
        "follow_up_idea": (
            "Change the rule to names with exactly 2 letters, and say which "
            "values of len(name) each rule keeps."
        ),
    },
    {
        "topic": "lists",
        "question_type": "misconception-analysis",
        "title": "Why did the student predict [1, 2, 3]?",
        "bloom_level": 4,
        "block_level": BlockLevel.RELATIONS,
        "estimated_minutes": 3,
        "stem": (
            "A student predicts this program prints [1, 2, 3] and says: 'I "
            "only added 4 to b, so a is untouched.' Which misconception best "
            "explains the prediction?"
        ),
        "code_snippet": "a = [1, 2, 3]\nb = a\nb.append(4)\nprint(a)",
        "choices": [
            {
                "key": "a",
                "text": "Believing b = a makes b an independent copy of the list",
            },
            {"key": "b", "text": "Believing append removes an item instead of adding one"},
            {"key": "c", "text": "Believing lists cannot be changed once created"},
            {"key": "d", "text": "Believing print only shows the first item of a list"},
        ],
        "correct_choice": "a",
        "model_explanation": (
            "b = a does not copy the list. Both names refer to the same list, "
            "so b.append(4) changes that one list and print(a) shows [1, 2, 3, "
            "4]. To get an independent list you would write b = a.copy(). The "
            "student's own words, 'a is untouched', reveal the belief that "
            "assigning a list duplicates it."
        ),
        "success_criteria": (
            "Identifies the 'assignment copies the list' misconception and "
            "can state that the program prints [1, 2, 3, 4]."
        ),
        "expected_concepts": [],
        "misconceptions": [
            "Treating assignment of a list as making a copy of it.",
            "Not separating re-pointing a name from changing the object it refers to.",
        ],
        "hint_text": (
            "After b = a, how many lists exist? Ask what b.append(4) changes: "
            "the name b, or the list itself?"
        ),
        "follow_up_idea": (
            "Explain in one sentence why a = 10 in the earlier variables "
            "example did not change b, but b.append(4) here does change a."
        ),
    },
    {
        "topic": "lists",
        "question_type": "extend-code",
        "title": "Collect the passing marks",
        "bloom_level": 5,
        "block_level": BlockLevel.MACRO,
        "estimated_minutes": 5,
        "stem": (
            "This program counts passing marks (50 or more). Extend it so it "
            "also builds a new list called passed that contains the passing "
            "marks, and prints that list. You may write code or describe your "
            "changes in words."
        ),
        "code_snippet": (
            "marks = [45, 82, 67, 30, 91]\n"
            "count = 0\n"
            "for m in marks:\n"
            "    if m >= 50:\n"
            "        count = count + 1\n"
            "print(count)"
        ),
        "choices": [],
        "correct_choice": "",
        "model_explanation": (
            "This combines a list, a loop and a condition. The new list is "
            "created once, before the loop; marks are appended inside the if "
            "so only passing ones go in; and the list is printed after the "
            "loop:\n"
            "passed = []\n"
            "for m in marks:\n"
            "    if m >= 50:\n"
            "        count = count + 1\n"
            "        passed.append(m)\n"
            "print(count)\n"
            "print(passed)\n"
            "The output is 3 and then [82, 67, 91]."
        ),
        "success_criteria": (
            "Creates an empty list before the loop, appends only passing "
            "marks inside the if, and prints the list."
        ),
        "expected_concepts": [
            {
                "name": "Starts with an empty list",
                "description": "The list passed is created, empty, once before the loop.",
                "keywords": ["empty", "[ ]", "new list", "start"],
            },
            {
                "name": "Adds passing marks inside the if",
                "description": "append (or equivalent) happens inside the condition so failing marks are not added.",
                "keywords": ["append", "add", "insert", "+="],
            },
            {
                "name": "Shows the list",
                "description": "The finished list is displayed with print.",
                "keywords": ["print", "display", "show", "output"],
            },
        ],
        "misconceptions": [
            "Creating the empty list inside the loop, so it resets on every pass.",
            "Appending every mark, by putting the append outside the if.",
            "Using the list before creating it.",
        ],
        "hint_text": (
            "When does the list need to exist, and where in the program "
            "should marks be added so that only passing ones go in?"
        ),
        "follow_up_idea": (
            "Also collect the failing marks in a second list, and say which "
            "parts of your solution you were able to reuse."
        ),
    },
    {
        "topic": "lists",
        "question_type": "code-quality-review",
        "title": "Review the negative-number check",
        "bloom_level": 6,
        "block_level": BlockLevel.MACRO,
        "estimated_minutes": 4,
        "stem": (
            "An AI generated this function to report whether a list contains "
            "any negative number. It passes every test you try. Which review "
            "comment is the most justified?"
        ),
        "code_snippet": (
            "def contains_negative(numbers):\n"
            "    found = False\n"
            "    for n in numbers:\n"
            "        if n < 0:\n"
            "            found = True\n"
            "    return found"
        ),
        "choices": [
            {
                "key": "a",
                "text": "It is correct, but it keeps looping after finding a negative; returning True immediately would be clearer and faster",
            },
            {"key": "b", "text": "It is incorrect: it returns True for an empty list"},
            {
                "key": "c",
                "text": "It must be rewritten with a while loop, because for loops are unsafe with lists",
            },
            {
                "key": "d",
                "text": "No change is ever worth making to code that passes its tests",
            },
        ],
        "correct_choice": "a",
        "model_explanation": (
            "First, correctness: for [] it returns False, for [3, -1, 2] it "
            "returns True, and for [1, 2] it returns False, so it does what "
            "was asked. The quality point is separate: once one negative "
            "number has been found the answer cannot change, so continuing "
            "the loop is wasted work and returning True straight away "
            "expresses the intent more clearly. The other comments make "
            "claims that are false (an empty list gives False; for loops are "
            "safe) or absolute (passing tests means nothing can improve)."
        ),
        "success_criteria": (
            "Separates correctness from quality, confirms the function is "
            "correct, and rejects the unjustified claims."
        ),
        "expected_concepts": [],
        "misconceptions": [
            "Treating code that passes its tests as having no quality concerns.",
            "Assuming working code must be wrong because it could be shorter.",
            "Accepting confident claims about loops or lists without checking them.",
        ],
        "hint_text": (
            "First decide whether the function gives the right answer for [], "
            "[3, -1, 2] and [1, 2]. Only then ask what, if anything, could be "
            "better."
        ),
        "follow_up_idea": (
            "Rewrite the function to return as soon as a negative is found, "
            "and say what it must return after the loop."
        ),
    },
    # ==================================================================
    # DICTIONARIES: L2, L3, L4, L6 (L1, L5 are defined above)
    # ==================================================================
    {
        "topic": "dictionaries",
        "question_type": "purpose",
        "title": "What is this dictionary program for?",
        "bloom_level": 2,
        "block_level": BlockLevel.MACRO,
        "estimated_minutes": 3,
        "stem": (
            "What overall problem is this program solving? Avoid describing "
            "only the syntax."
        ),
        "code_snippet": (
            "counts = {}\n"
            'for word in ["red", "blue", "red", "green", "red"]:\n'
            "    if word in counts:\n"
            "        counts[word] = counts[word] + 1\n"
            "    else:\n"
            "        counts[word] = 1\n"
            "print(counts)"
        ),
        "choices": [
            {"key": "a", "text": "It counts how many times each word appears"},
            {"key": "b", "text": "It removes duplicate words from the list"},
            {"key": "c", "text": "It sorts the words alphabetically"},
            {"key": "d", "text": "It finds the longest word"},
        ],
        "correct_choice": "a",
        "model_explanation": (
            "Each word becomes a key, and its value is a tally that goes up "
            "by one every time the word is seen again. The result is "
            "{'red': 3, 'blue': 1, 'green': 1}. 'Removes duplicates' is "
            "tempting because keys are unique, but that reading ignores the "
            "numbers, which are the whole point."
        ),
        "success_criteria": (
            "Names the purpose as counting how often each word occurs, not "
            "just 'it uses a dictionary and a loop'."
        ),
        "expected_concepts": [],
        "misconceptions": [
            "Describing the mechanics ('a dictionary and an if') instead of the purpose.",
            "Reading unique keys as 'duplicates removed' and ignoring the stored numbers.",
        ],
        "hint_text": (
            "Look at what is stored as each value, and when it changes. What "
            "question about the list does the final dictionary answer?"
        ),
        "follow_up_idea": (
            "Predict the dictionary printed if the first word were 'blue' "
            "instead of 'red', and say which values change."
        ),
    },
    {
        "topic": "dictionaries",
        "question_type": "code-completion",
        "title": "Print every key with its value",
        "bloom_level": 3,
        "block_level": BlockLevel.BLOCKS,
        "estimated_minutes": 2,
        "stem": (
            "The program should print each item with its price, as 'tea 2' "
            "and then 'cake 4'. Which expression completes the blank?"
        ),
        "code_snippet": (
            'prices = {"tea": 2, "cake": 4}\n'
            "for item in prices:\n"
            "    print(item, ______)"
        ),
        "choices": [
            {"key": "a", "text": "prices[item]"},
            {"key": "b", "text": "prices"},
            {"key": "c", "text": "item[prices]"},
            {"key": "d", "text": "prices.item"},
        ],
        "correct_choice": "a",
        "model_explanation": (
            "Looping over a dictionary gives its keys, so item holds 'tea' and "
            "then 'cake'. To get the matching value you look the key up with "
            "prices[item]. Printing prices would show the whole dictionary "
            "every time; item[prices] tries to index text with a dictionary "
            "and fails; prices.item looks for an attribute that does not exist."
        ),
        "success_criteria": (
            "Selects prices[item] and can say that the loop variable is a key."
        ),
        "expected_concepts": [],
        "misconceptions": [
            "Believing a for loop over a dictionary gives key and value together.",
            "Mixing up which name goes inside the square brackets.",
        ],
        "hint_text": (
            "On each pass, does item hold a key or a value? And what do you "
            "supply to a dictionary to get a value back?"
        ),
        "follow_up_idea": (
            "Predict what 'for x in prices.values(): print(x)' prints, and "
            "say what information you lose compared with this loop."
        ),
    },
    {
        "topic": "dictionaries",
        "question_type": "compare-solutions",
        "title": "Two vote counters",
        "bloom_level": 4,
        "block_level": BlockLevel.RELATIONS,
        "estimated_minutes": 4,
        "stem": (
            "Two AI-generated programs both try to tally votes into a "
            "dictionary. Each is a separate program. Compare them. Which "
            "statement is true?"
        ),
        "code_snippet": (
            'votes = ["yes", "no", "yes"]\n'
            "\n"
            "# Solution A\n"
            "tally = {}\n"
            "for v in votes:\n"
            "    tally[v] = tally.get(v, 0) + 1\n"
            "\n"
            "# Solution B\n"
            "tally = {}\n"
            "for v in votes:\n"
            "    tally[v] = tally[v] + 1"
        ),
        "choices": [
            {
                "key": "a",
                "text": "A produces {'yes': 2, 'no': 1}; B fails with a KeyError on the first vote, because that key does not exist yet",
            },
            {"key": "b", "text": "Both produce {'yes': 2, 'no': 1}"},
            {
                "key": "c",
                "text": "B works and A fails, because .get cannot be used when assigning",
            },
            {
                "key": "d",
                "text": "Both fail, because a dictionary cannot be built inside a loop",
            },
        ],
        "correct_choice": "a",
        "model_explanation": (
            "In A, tally.get(v, 0) returns 0 the first time a vote is seen, "
            "so + 1 gives 1 and the key is created; later votes build on it. "
            "In B, tally[v] tries to read a key that has not been created yet "
            "and raises a KeyError on the very first vote. The two versions "
            "differ in a single call, so the divergence only shows up by "
            "tracing the first iteration."
        ),
        "success_criteria": (
            "Identifies that B reads a missing key and fails on the first "
            "vote, while A supplies a default of 0."
        ),
        "expected_concepts": [],
        "misconceptions": [
            "Assuming that reading a missing key gives 0 or None automatically.",
            "Judging by how similar the versions look instead of tracing the first iteration.",
        ],
        "hint_text": (
            "Trace only the first vote through both versions. In B, what does "
            "tally[v] look up, and does that key exist yet?"
        ),
        "follow_up_idea": (
            "Say what .get(v, 0) returns the first time a vote is seen, and "
            "why that makes the + 1 safe."
        ),
    },
    {
        "topic": "dictionaries",
        "question_type": "ai-suggestion",
        "title": "Is this stock total correct?",
        "bloom_level": 6,
        "block_level": BlockLevel.MACRO,
        "estimated_minutes": 4,
        "stem": (
            "Requirement: total_stock(stock) returns the total number of "
            "items in stock, where stock maps product names to counts (for "
            "example {'apples': 5, 'pears': 2} gives 7). An AI generated the "
            "function below. Accept or reject it, then justify your decision "
            "by checking it against the example."
        ),
        "code_snippet": "",
        "ai_suggestion": (
            "def total_stock(stock):\n"
            "    return sum(stock.values())"
        ),
        "choices": [],
        "correct_choice": "accept",
        "model_explanation": (
            "The function is correct, so accepting it is right. stock.values() "
            "holds only the counts, 5 and 2, and sum adds them to give 7. An "
            "empty dictionary gives 0. Summing the dictionary itself would "
            "instead add the keys and fail, which is why .values() is the "
            "important part. A short, idiomatic one-liner is not a reason for "
            "suspicion; working through the example is the evidence."
        ),
        "success_criteria": (
            "Accepts the function and justifies it by working through the "
            "example, noting that .values() supplies the counts."
        ),
        "expected_concepts": [
            {
                "name": "Uses the values",
                "description": "Recognises that .values() gives the counts, not the product names.",
                "keywords": ["values", "counts", "numbers"],
            },
            {
                "name": "Adds the counts together",
                "description": "Recognises that sum adds the counts to produce the total.",
                "keywords": ["sum", "add", "adds", "adding", "total"],
            },
            {
                "name": "Checks the example",
                "description": "Works through the given example (5 + 2 = 7).",
                "keywords": ["7", "5", "2", "example", "apples", "pears"],
            },
        ],
        "misconceptions": [
            "Believing sum(stock) would add the counts (it would try to add the keys).",
            "Distrusting a one-line solution simply because it is short.",
            "Accepting or rejecting without working through the example.",
        ],
        "hint_text": (
            "Work through {'apples': 5, 'pears': 2}: what does stock.values() "
            "contain, and what does sum do with it? Then ask what happens for "
            "an empty dictionary."
        ),
        "follow_up_idea": (
            "Predict what sum(stock) on its own would do, and explain why it "
            "would fail."
        ),
    },
    {
        "topic": "variables",
        "question_type": "match-terms",
        "title": "Match the variable vocabulary",
        "display_order": 0,
        "bloom_level": 1,
        "block_level": BlockLevel.ATOMS,
        "estimated_minutes": 2,
        "stem": (
            "Match each term to the definition that fits it. The code is there so "
            "you can see what each term refers to; one definition fits no term."
        ),
        "code_snippet": (
            "count = 3\n"
            "name = \"Ada\"\n"
            "count = count + 1\n"
        ),
        "choices": [],
        "correct_choice": "",
        "match_pairs": [
            {
                "term": "variable",
                "definition": "A name that refers to a stored value",
            },
            {
                "term": "assignment",
                "definition": "Giving a name a value, as the = in count = 3 does",
            },
            {
                "term": "string",
                "definition": "A value made of text, written inside quotes",
            },
            {
                "term": "integer",
                "definition": "A whole number with no decimal point",
            },
            {
                "term": "expression",
                "definition": "Something Python works out to a value, such as count + 1",
            },
        ],
        "match_distractors": [
            "A named block of code that can be run again whenever it is needed",
        ],
        "model_explanation": "Each pairing can be checked against the snippet: count is a variable, count = 3 is an assignment, \"Ada\" is a string, 3 is an integer, and count + 1 is an expression Python works out to a value. The unused definition describes a function.",
        "success_criteria": "Pairs all five terms correctly and rejects the definition that describes a function.",
        "expected_concepts": [],
        "misconceptions": [
            "Believing = means 'equals' as in mathematics, rather than 'store this value under this name'.",
            "Treating text and numbers as the same kind of value.",
            "Mixing up a variable with the value it currently holds.",
        ],
        "hint_text": "For each term, find the line in the snippet where you could point at it. Then ask which definition describes only that thing.",
        "follow_up_idea": "Pick one variable from the snippet and say which of these five terms describes each part of the line count = count + 1.",
    },
    {
        "topic": "conditionals",
        "question_type": "match-terms",
        "title": "Match the conditional vocabulary",
        "display_order": 0,
        "bloom_level": 1,
        "block_level": BlockLevel.ATOMS,
        "estimated_minutes": 2,
        "stem": (
            "Match each term to the definition that fits it. The code is there so "
            "you can see what each term refers to; one definition fits no term."
        ),
        "code_snippet": (
            "if temperature > 30:\n"
            "    print(\"hot\")\n"
            "elif temperature > 15:\n"
            "    print(\"warm\")\n"
            "else:\n"
            "    print(\"cold\")\n"
        ),
        "choices": [],
        "correct_choice": "",
        "match_pairs": [
            {
                "term": "condition",
                "definition": "An expression that is either True or False, such as temperature > 30",
            },
            {
                "term": "comparison operator",
                "definition": "A symbol such as > or == that compares two values",
            },
            {
                "term": "elif",
                "definition": "Another test, checked only if every earlier one was False",
            },
            {
                "term": "else",
                "definition": "The branch that runs when none of the tests were True",
            },
            {
                "term": "block",
                "definition": "The indented lines that belong to an if, elif or else",
            },
        ],
        "match_distractors": [
            "A way to repeat lines for as long as a test stays True",
        ],
        "model_explanation": "temperature > 30 is a condition built with the comparison operator >. elif is the extra test, checked only when the first was False. else catches everything left over. The indented print lines are the blocks. The unused definition describes a loop.",
        "success_criteria": "Pairs all five terms correctly and rejects the definition that describes a loop.",
        "expected_concepts": [],
        "misconceptions": [
            "Believing every elif is checked even after an earlier test was True.",
            "Believing else needs its own condition.",
            "Not seeing that indentation decides which lines belong to a branch.",
        ],
        "hint_text": "Look at which of the five terms appears as a word in the code and which is a symbol or a layout feature.",
        "follow_up_idea": "Change temperature > 15 to temperature > 30 in the snippet and say which of the five terms is affected.",
    },
    {
        "topic": "loops",
        "question_type": "match-terms",
        "title": "Match the loop vocabulary",
        "display_order": 0,
        "bloom_level": 1,
        "block_level": BlockLevel.ATOMS,
        "estimated_minutes": 2,
        "stem": (
            "Match each term to the definition that fits it. The code is there so "
            "you can see what each term refers to; one definition fits no term."
        ),
        "code_snippet": (
            "total = 0\n"
            "for score in [4, 7, 2]:\n"
            "    total = total + score\n"
            "print(total)\n"
        ),
        "choices": [],
        "correct_choice": "",
        "match_pairs": [
            {
                "term": "iteration",
                "definition": "One pass through the body of a loop",
            },
            {
                "term": "loop variable",
                "definition": "The name that takes each item in turn, such as score here",
            },
            {
                "term": "accumulator",
                "definition": "A variable that builds up a result as the loop runs, such as total here",
            },
            {
                "term": "loop body",
                "definition": "The indented lines that are repeated on every pass",
            },
            {
                "term": "for loop",
                "definition": "A loop that visits each item of a sequence in turn",
            },
        ],
        "match_distractors": [
            "A value handed to a function when it is called",
        ],
        "model_explanation": "The loop runs three iterations, one per item. score is the loop variable, total is the accumulator, and the indented line is the loop body. The whole for statement is a for loop that visits each item of the sequence. The unused definition describes an argument.",
        "success_criteria": "Pairs all five terms correctly and rejects the definition that describes an argument.",
        "expected_concepts": [],
        "misconceptions": [
            "Believing the loop variable keeps a single value instead of taking each item in turn.",
            "Confusing the number of iterations with the number of lines in the body.",
            "Not recognising that a running total must be set up before the loop.",
        ],
        "hint_text": "Count how many times the body runs for this list. That count is the answer for one of the terms.",
        "follow_up_idea": "Say how many iterations the snippet performs and what total holds after each one.",
    },
    {
        "topic": "functions",
        "question_type": "match-terms",
        "title": "Match the function vocabulary",
        "display_order": 0,
        "bloom_level": 1,
        "block_level": BlockLevel.ATOMS,
        "estimated_minutes": 2,
        "stem": (
            "Match each term to the definition that fits it. The code is there so "
            "you can see what each term refers to; one definition fits no term."
        ),
        "code_snippet": (
            "def add_tax(price, rate):\n"
            "    return price * (1 + rate)\n"
            "\n"
            "cost = add_tax(20, 0.2)\n"
        ),
        "choices": [],
        "correct_choice": "",
        "match_pairs": [
            {
                "term": "function definition",
                "definition": "The code that creates a function and says what it does",
            },
            {
                "term": "parameter",
                "definition": "A name in the def line that receives a value, such as price",
            },
            {
                "term": "argument",
                "definition": "A value supplied when the function is called, such as 20",
            },
            {
                "term": "function call",
                "definition": "Asking a function to run, as add_tax(20, 0.2) does",
            },
            {
                "term": "return value",
                "definition": "The result a function hands back to the code that called it",
            },
        ],
        "match_distractors": [
            "A variable that can be used from anywhere in the program",
        ],
        "model_explanation": "The def block is the definition. price and rate are parameters; 20 and 0.2 are the arguments supplied by the call add_tax(20, 0.2). The value the call hands back is the return value, stored in cost. The unused definition describes a global variable.",
        "success_criteria": "Pairs all five terms correctly, keeping parameter and argument apart, and rejects the global variable definition.",
        "expected_concepts": [],
        "misconceptions": [
            "Using parameter and argument as if they meant the same thing.",
            "Believing a function runs when it is defined rather than when it is called.",
            "Believing print and return do the same job.",
        ],
        "hint_text": "Separate what you see in the def line from what you see in the line that uses the function.",
        "follow_up_idea": "Say which of the five terms describes 20, which describes price, and which describes what cost ends up holding.",
    },
    {
        "topic": "lists",
        "question_type": "match-terms",
        "title": "Match the list vocabulary",
        "display_order": 0,
        "bloom_level": 1,
        "block_level": BlockLevel.ATOMS,
        "estimated_minutes": 2,
        "stem": (
            "Match each term to the definition that fits it. The code is there so "
            "you can see what each term refers to; one definition fits no term."
        ),
        "code_snippet": (
            "names = [\"Ada\", \"Grace\", \"Alan\"]\n"
            "print(names[0])\n"
            "names.append(\"Linus\")\n"
            "print(len(names))\n"
        ),
        "choices": [],
        "correct_choice": "",
        "match_pairs": [
            {
                "term": "list",
                "definition": "An ordered collection of values that can be changed",
            },
            {
                "term": "element",
                "definition": "One item stored in a list",
            },
            {
                "term": "index",
                "definition": "The position number used to reach an element, starting at 0",
            },
            {
                "term": "append",
                "definition": "Adds an item to the end of a list",
            },
            {
                "term": "len",
                "definition": "Gives the number of elements a list holds",
            },
        ],
        "match_distractors": [
            "A pair made of a label and the value stored under it",
        ],
        "model_explanation": "names is a list; each name inside it is an element. names[0] uses the index 0 to reach \"Ada\". append adds \"Linus\" at the end, and len then reports 4. The unused definition describes a dictionary entry.",
        "success_criteria": "Pairs all five terms correctly and rejects the dictionary definition.",
        "expected_concepts": [],
        "misconceptions": [
            "Believing the first element has index 1.",
            "Mixing up an element with its index.",
            "Believing append puts the new item at the start.",
        ],
        "hint_text": "Note which terms name things (a collection, an item, a position) and which name actions or tools.",
        "follow_up_idea": "Say what names[0] gives and what len(names) prints, and which of the five terms each result involves.",
    },
    {
        "topic": "dictionaries",
        "question_type": "match-terms",
        "title": "Match the dictionary vocabulary",
        "display_order": 0,
        "bloom_level": 1,
        "block_level": BlockLevel.ATOMS,
        "estimated_minutes": 2,
        "stem": (
            "Match each term to the definition that fits it. The code is there so "
            "you can see what each term refers to; one definition fits no term."
        ),
        "code_snippet": (
            "stock = {\"apples\": 5, \"pears\": 2}\n"
            "print(stock[\"apples\"])\n"
            "stock[\"plums\"] = 7\n"
        ),
        "choices": [],
        "correct_choice": "",
        "match_pairs": [
            {
                "term": "key",
                "definition": "The label used to look an entry up",
            },
            {
                "term": "value",
                "definition": "The data stored under a key",
            },
            {
                "term": "key-value pair",
                "definition": "One key together with the value it labels",
            },
            {
                "term": "lookup",
                "definition": "Getting a value by supplying its key, as stock[\"apples\"] does",
            },
            {
                "term": "KeyError",
                "definition": "The error raised when a key that is not in the dictionary is looked up",
            },
        ],
        "match_distractors": [
            "The position number of an item in a list",
        ],
        "model_explanation": "\"apples\" is a key and 5 is its value; together they are a key-value pair. stock[\"apples\"] is a lookup. Looking up a key that is not there, such as \"kiwis\", raises a KeyError. The unused definition describes an index.",
        "success_criteria": "Pairs all five terms correctly and rejects the index definition.",
        "expected_concepts": [],
        "misconceptions": [
            "Mixing up a key with a value.",
            "Believing a dictionary is found by position, as a list is.",
            "Believing looking up a missing key quietly gives an empty result.",
        ],
        "hint_text": "In \"apples\": 5, decide which half is used to find things and which half is the thing found.",
        "follow_up_idea": "Say what stock[\"kiwis\"] would do in the snippet, and which of the five terms names that outcome.",
    },
    {
        "topic": "functions",
        "question_type": "explain-code",
        "title": "What does this function take in and give back?",
        "display_order": 0,
        "bloom_level": 2,
        "block_level": BlockLevel.BLOCKS,
        "estimated_minutes": 3,
        "stem": (
            "Explain in plain English what the function does and how the "
            "program uses it. Say what goes in, what comes out, and what is "
            "printed."
        ),
        "code_snippet": (
            "def area(width, height):\n"
            "    return width * height\n"
            "\n"
            "print(area(3, 4))\n"
            "print(area(5, 2))"
        ),
        "choices": [],
        "correct_choice": "",
        "model_explanation": (
            "area is a function: a named block that takes two inputs, width "
            "and height (its parameters), and hands back their product with "
            "return. The program then calls it twice with different "
            "arguments, so the same block of code is reused: area(3, 4) gives "
            "12 and area(5, 2) gives 10, and each result is printed."
        ),
        "success_criteria": (
            "Says the function takes two values in, returns their product, "
            "and is called twice with different values, printing 12 and 10."
        ),
        "expected_concepts": [
            {
                "name": "Takes inputs",
                "description": "The function receives two values (width and height) as parameters.",
                "keywords": ["input", "parameter", "argument", "takes", "receives", "width", "height", "two"],
            },
            {
                "name": "Returns a result",
                "description": "The function multiplies the two values and returns the product to the caller.",
                "keywords": ["return", "returns", "gives back", "product", "multipl", "result"],
            },
            {
                "name": "Reused with different values",
                "description": "The same function is called twice with different arguments, giving 12 and 10.",
                "keywords": ["twice", "again", "reuse", "different", "12", "10", "called", "call"],
            },
        ],
        "misconceptions": [
            "Believing the function runs where it is defined, rather than where it is called.",
            "Believing width and height are fixed numbers rather than placeholders for whatever is passed in.",
        ],
        "hint_text": (
            "Look at the two lines that start with print. Which values go "
            "into area on each one, and what does the line with return do "
            "with them?"
        ),
        "follow_up_idea": (
            "Say what area(10, 10) would print, without running it, and "
            "which line of the function produced that number."
        ),
    },
    {
        "topic": "dictionaries",
        "question_type": "explain-code",
        "title": "What does this dictionary update do?",
        "display_order": 0,
        "bloom_level": 2,
        "block_level": BlockLevel.BLOCKS,
        "estimated_minutes": 3,
        "stem": (
            "Explain in plain English what this code does. Say what the "
            "dictionary holds, what the second line changes, and what is "
            "printed."
        ),
        "code_snippet": (
            'ages = {"Ada": 36, "Alan": 41}\n'
            'ages["Ada"] = 37\n'
            'print(ages["Ada"])\n'
            "print(len(ages))"
        ),
        "choices": [],
        "correct_choice": "",
        "model_explanation": (
            "ages is a dictionary holding two entries: each name (key) is "
            "paired with an age (value). The second line assigns to a key "
            "that already exists, so it replaces Ada's value (36 becomes 37) "
            "rather than adding a new entry. The program prints 37, then the "
            "number of entries, which is still 2."
        ),
        "success_criteria": (
            "Says the dictionary pairs names with ages, that the second line "
            "replaces an existing value instead of adding an entry, and that "
            "37 and 2 are printed."
        ),
        "expected_concepts": [
            {
                "name": "Keys paired with values",
                "description": "The dictionary stores names (keys) paired with ages (values).",
                "keywords": ["key", "value", "pair", "name", "age", "entries", "entry", "stores", "holds"],
            },
            {
                "name": "Existing value replaced",
                "description": "Assigning to an existing key replaces its value; it does not create a second entry.",
                "keywords": ["replace", "update", "change", "overwrit", "37", "same key", "already"],
            },
            {
                "name": "Output",
                "description": "37 is printed, then the number of entries, which is still 2.",
                "keywords": ["37", "2", "prints", "print", "len", "count", "size", "two"],
            },
        ],
        "misconceptions": [
            "Believing assigning to an existing key adds a second entry (so len would print 3).",
            "Believing a dictionary entry cannot be changed once it has been created.",
        ],
        "hint_text": (
            "Compare the dictionary before and after line 2. Is there a "
            "new key, or did something about an existing key change? Then "
            "ask what len counts."
        ),
        "follow_up_idea": (
            'Predict what changes if line 2 uses the new key "Grace" '
            "instead of \"Ada\", and what len(ages) would print then."
        ),
    },
]


OPTION_KEYS = "abcdefgh"


def balance_choices(data: dict, slot: int) -> dict:
    """
    Place the correct option so its position is evenly spread (a, b, c, d, a, ...).

    Authors write the correct option wherever is convenient; left alone, it
    clusters at 'a' or 'b' and could be guessed. Placement is round-robin by
    `slot` (the item's rank among multiple-choice items in ACTIVITIES), and the
    remaining options are shuffled with a seed taken from the title.

    The result is deterministic, so re-seeding never changes an item and a
    participant's stored choice key keeps meaning the same option.
    Important: append new multiple-choice items to the END of ACTIVITIES;
    inserting one earlier shifts the slot of every item after it.
    """
    choices = data.get("choices")
    if not choices or not data.get("correct_choice"):
        return data
    correct_text = next(c["text"] for c in choices if c["key"] == data["correct_choice"])
    others = [c["text"] for c in choices if c["key"] != data["correct_choice"]]
    random.Random(f"{data['title']}|options").shuffle(others)
    position = slot % len(choices)
    texts = others[:position] + [correct_text] + others[position:]
    data["choices"] = [{"key": OPTION_KEYS[i], "text": t} for i, t in enumerate(texts)]
    data["correct_choice"] = OPTION_KEYS[position]
    return data


class Command(BaseCommand):
    help = "Load pedagogical question types, topics, and Many Small Problems items."

    def handle(self, *args, **options):
        type_by_slug = {}
        # Types are listed by Bloom level so the home page reads L1 -> L6.
        ordered_types = sorted(
            QUESTION_TYPES, key=lambda p: (p["bloom_level"], p["display_order"])
        )
        for position, payload in enumerate(ordered_types):
            payload = {**payload, "display_order": position}
            obj, _ = QuestionType.objects.update_or_create(
                slug=payload["slug"], defaults=payload
            )
            type_by_slug[obj.slug] = obj

        topic_by_slug = {}
        for payload in TOPICS:
            obj, _ = Topic.objects.update_or_create(
                slug=payload["slug"], defaults=payload
            )
            topic_by_slug[obj.slug] = obj

        created = 0
        updated = 0
        mc_slot = 0
        for payload in ACTIVITIES:
            data = dict(payload)
            if data.get("choices") and data.get("correct_choice"):
                data = balance_choices(data, mc_slot)
                mc_slot += 1
            if "block_level" not in data:
                raise CommandError(
                    f"Activity {data['title']!r} has no block_level; every activity "
                    "must be tagged with a Block Model level."
                )
            topic = topic_by_slug[data.pop("topic")]
            qtype = type_by_slug[data.pop("question_type")]
            # Progression within a topic follows Bloom level (L1 first);
            # the id breaks ties. Any hand-written display_order is ignored.
            data["display_order"] = data["bloom_level"]
            lookup = {
                "topic": topic,
                "question_type": qtype,
                "title": data.pop("title"),
            }
            obj, was_created = Activity.objects.update_or_create(
                **lookup, defaults=data
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(QUESTION_TYPES)} question types, "
                f"{len(TOPICS)} topics, "
                f"{created} new activities, {updated} updated activities."
            )
        )
