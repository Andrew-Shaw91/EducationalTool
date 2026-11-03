"""Conditionals: eleven more activities (one at level 1, two each at levels 2-6)."""

from . import ATOMS, BLOCKS, MACRO, RELATIONS, ai, claim, code, mc, op

T = "conditionals"
ACTIVITIES = []

# --- Level 1 ---------------------------------------------------------------------
ACTIVITIES.append(op(
    T, "define-concept", "Define a condition", ATOMS,
    stem="In your own words, what is a condition in a program?",
    concepts=[
        ("True or False", "A condition is something that works out to True or False.",
         ["true", "false", "boolean", "bool", "yes or no"]),
        ("Decides what runs", "Its result decides which code runs (or whether some code runs at all).",
         ["decide", "decides", "choose", "chooses", "branch", "controls", "whether"]),
        ("A comparison or test", "It is usually a question asked about values, such as a comparison.",
         ["compare", "comparison", "test", "tests", "check", "question", "expression"]),
    ],
    explain=(
        "A condition is an expression that works out to True or False, such as "
        "age >= 18. The program uses the result to decide whether to run some "
        "code, or which of two blocks of code to run."
    ),
    criteria="Says a condition is a True/False test and that its result decides what the program does.",
    misconceptions=[
        "Thinking a condition is the code that runs rather than the test that decides.",
        "Believing a condition can have more than two possible results.",
    ],
    hint="Think about what an if statement needs before it can choose, and what kind of answer that is.",
    follow_up="Write one condition about a number and say what it works out to for the value 7.",
    minutes=2,
))

# --- Level 2 ---------------------------------------------------------------------
SRC = code("""
    age = 15
    if age < 12:
        price = 5
    elif age < 18:
        price = 8
    else:
        price = 12
    print(price)
""")
claim(SRC, "8")
ACTIVITIES.append(op(
    T, "explain-code", "Describe this ticket-price rule", BLOCKS,
    stem="Explain in plain English what this code does and what it prints. Name the values, not only the syntax.",
    code=SRC,
    concepts=[
        ("Checks in order", "The tests are tried from the top; the first one that is true decides the price.",
         ["order", "first", "elif", "else", "branch", "chain", "check", "checks"]),
        ("Which branch applies", "15 is not under 12 but is under 18, so the middle branch sets the price to 8.",
         ["< 18", "under 18", "less than 18", "teenager", "middle", "second"]),
        ("Output", "The price, 8, is printed.", ["print", "prints", "display", "output", "8"]),
    ],
    explain=(
        "The program sets age to 15 and then tries three cases in order. 15 is "
        "not less than 12, so the first branch is skipped; 15 is less than 18, "
        "so the elif branch sets price to 8 and the else branch is never "
        "reached. print then shows 8. Only one of the three branches runs."
    ),
    criteria="Says the tests run top to bottom, that 15 falls in the under-18 branch, and that 8 is printed.",
    misconceptions=[
        "Believing every true branch in an if/elif chain runs.",
        "Describing the syntax instead of which branch 15 reaches.",
    ],
    hint="Take the age of 15 and ask each question in turn. Stop at the first one that is true.",
    follow_up="Change age to 12 and say which branch runs, and why 12 is not in the first group.",
))

SRC = code("""
    value = 120
    if value > 100:
        value = 100
    print(value)
""")
claim(SRC, "100")
ACTIVITIES.append(mc(
    T, "purpose", "What is this check for?", MACRO,
    stem="What overall problem is this program solving? Avoid describing only the syntax.",
    code=SRC,
    correct="It caps a value so it can never be more than 100.",
    wrong=[
        "It checks whether the value is exactly 100.",
        "It always changes the value to 100.",
        "It counts how many values are over 100.",
    ],
    explain=(
        "When value is above 100 the if-block replaces it with 100; otherwise "
        "the value is left alone. The result can therefore never be more than "
        "100: this is a cap, or upper limit. With 120 the program prints 100. "
        "With 80 the if-block would not run and 80 would be printed."
    ),
    criteria="Names the purpose as capping or limiting to a maximum of 100.",
    misconceptions=[
        "Describing the if and assignment instead of what the program achieves.",
        "Thinking the assignment happens whatever the value is.",
    ],
    hint="Try a value below 100 and a value above 100. What is true about the result in both cases?",
    follow_up="Change the program so a value can never be below 0, and say what the condition becomes.",
))

# --- Level 3 ---------------------------------------------------------------------
SRC = code("""
    total = 80
    if ______:
        print("free delivery")
""")
claim("total = 50\nif total >= 50:\n    print('free delivery')\nif total > 50:\n    print('x')", "free delivery")
ACTIVITIES.append(mc(
    T, "code-completion", "Complete the free-delivery test", ATOMS,
    stem="Delivery is free for totals of 50 or more. Which condition completes the blank?",
    code=SRC,
    correct="total >= 50",
    wrong=["total > 50", "total = 50", "total <= 50"],
    explain=(
        "\"50 or more\" includes 50 itself, so the comparison must be >=. "
        "total > 50 would charge for a total of exactly 50. A single = assigns "
        "a value instead of testing one, and is not allowed in an if condition. "
        "total <= 50 selects the wrong side entirely."
    ),
    criteria="Selects total >= 50 and can say why 50 itself is included.",
    misconceptions=[
        "Treating 'or more' as 'more than' and leaving out the boundary value.",
        "Confusing = (assign) with the comparison operators.",
    ],
    hint="Test each option with 49, 50 and 51. Which one is right for all three?",
    follow_up="Change the rule to 'more than 50' and say which single character in your answer changes.",
))

ACTIVITIES.append(op(
    T, "prompt-construction", "Specify a ticket-price function", MACRO,
    stem=(
        "Do not write the Python. Write a short specification (the kind of prompt you "
        "would give a colleague or a model) that would produce a function meeting the "
        "requirements below. Include behaviour at the boundaries."
    ),
    requirements=(
        "Need a function that gives the price of a cinema ticket from a customer's age. "
        "Children under 12 pay 5, people aged 12 to 17 pay 8, and everyone else pays 12. "
        "The age is a whole number and is never negative. The function should return the "
        "price, not print it."
    ),
    concepts=[
        ("Return value", "States that the function returns the price rather than printing it.",
         ["return", "returns", "returned"]),
        ("The three bands", "Gives the three prices (5, 8 and 12) for the three age groups.",
         ["5", "8", "three", "bands", "groups"]),
        ("Boundary ages", "Says what happens at 12 and 17/18 (which group each belongs to).",
         ["boundary", "boundaries", "inclusive", "exclusive", "17", "18", "exactly"]),
        ("Input assumptions", "States that the age is a whole number and not negative.",
         ["negative", "whole number", "integer", "invalid", "valid"]),
    ],
    explain=(
        "A strong specification names the input (age as a whole number), the "
        "output (the price, returned), the three bands with their prices, and "
        "which band the boundary ages belong to: 12 pays 8, and 18 pays 12. "
        "It also says what is assumed (no negative ages). A weak prompt says "
        "'ticket prices by age' and leaves the boundaries to be guessed."
    ),
    criteria="States input, returned price, all three bands, and the boundary ages.",
    misconceptions=[
        "Writing code instead of a specification.",
        "Leaving the boundary ages unstated, so 12 and 18 could go either way.",
    ],
    hint="List the decisions a generator would otherwise have to guess: return or print, and what happens at exactly 12 and 18.",
    follow_up="Add a rule that over-65s pay 6 and say which existing band it changes.",
    minutes=5,
))

# --- Level 4 ---------------------------------------------------------------------
GRADE_A = code("""
    if mark >= 70:
        grade = "A"
    elif mark >= 60:
        grade = "B"
    else:
        grade = "C"
""")
GRADE_B = code("""
    if mark >= 70:
        grade = "A"
    if mark >= 60:
        grade = "B"
    if mark < 60:
        grade = "C"
""")
for _mark, _a, _b in ((75, "A", "B"), (65, "B", "B"), (50, "C", "C")):
    claim(f"mark = {_mark}\n{GRADE_A}\nprint(grade)", _a)
    claim(f"mark = {_mark}\n{GRADE_B}\nprint(grade)", _b)
ACTIVITIES.append(mc(
    T, "compare-solutions", "Two ways to write the bands", RELATIONS,
    stem=(
        "Both fragments assign a grade from mark: 70 or more is A, 60 to 69 is B, "
        "below 60 is C.\n\nSolution A:\n" + GRADE_A + "\n\nSolution B:\n" + GRADE_B +
        "\n\nWhat happens when mark is 75?"
    ),
    correct="A gives \"A\" but B gives \"B\": in B the second if is also true and replaces the grade.",
    wrong=[
        "They give the same grade for every mark.",
        "B gives \"A\" and A gives \"B\".",
        "A is invalid, because elif cannot follow an if.",
    ],
    explain=(
        "With mark = 75, A stops at the first true test and sets \"A\". In B each "
        "if is checked independently: 75 >= 70 sets \"A\", then 75 >= 60 is also "
        "true and overwrites it with \"B\". The two versions agree for 65 and 50 "
        "but disagree for every mark of 70 or more. A chain of separate ifs does "
        "not mean 'stop at the first match'."
    ),
    criteria="Traces mark = 75 through both and sees that B's later if overwrites the grade.",
    misconceptions=[
        "Believing separate if statements stop after the first true one.",
        "Assuming two versions that look similar must behave the same.",
    ],
    hint="Do not compare the layout. Run mark = 75 through each version and write down grade after every line.",
    follow_up="Change B so it behaves like A without using elif, and say what you had to add to each condition.",
))

SRC = code("""
    score = 85
    if score >= 50:
        print("pass")
    elif score >= 80:
        print("distinction")
""")
claim(SRC, "pass")
ACTIVITIES.append(mc(
    T, "misconception-analysis", "Why did the student predict two lines?", RELATIONS,
    stem=(
        "A student predicted this program prints pass and then distinction. It prints only "
        "pass. Which misconception best explains the student's prediction?"
    ),
    code=SRC,
    correct=(
        "The student thinks every true condition runs, but in an if/elif chain only "
        "the first true branch runs."
    ),
    wrong=[
        "The student thinks 85 is smaller than 50.",
        "The student thinks elif is checked before if.",
        "The student thinks print can only show one word.",
    ],
    explain=(
        "85 >= 50 is true, so pass is printed and the rest of the chain is "
        "skipped, including the elif, even though 85 >= 80 is also true. The "
        "student expected both true tests to run. This also shows a real bug: "
        "no score can ever reach \"distinction\", because the pass test catches "
        "it first."
    ),
    criteria="Identifies that the student expects every true condition to run, not just the first.",
    misconceptions=[
        "Believing all true conditions in an if/elif chain run.",
        "Not noticing that the order of tests can make a branch unreachable.",
    ],
    hint="Ask which tests are true for 85, then ask which of them Python actually acts on.",
    follow_up="Reorder the tests so distinction is reachable, and check with the scores 85, 60 and 30.",
))

# --- Level 5 ---------------------------------------------------------------------
SRC = code("""
    score = 85
    if score >= 50:
        print("pass")
    else:
        print("fail")
""")
ACTIVITIES.append(op(
    T, "extend-code", "Add a distinction band", MACRO,
    stem=(
        "Extend the program so a score of 80 or more prints distinction, a score from 50 "
        "to 79 prints pass, and anything lower prints fail."
    ),
    code=SRC,
    concepts=[
        ("Distinction threshold", "A new test for scores of 80 or more is added.",
         ["80", ">= 80", "distinction"]),
        ("Tested before pass", "The distinction test comes first (or pass is limited to below 80), so it can be reached.",
         ["first", "before", "order", "above", "top", "elif"]),
        ("Pass and fail kept", "The existing pass (50 or more) and fail cases still work.",
         ["50", "pass", "fail", "else"]),
    ],
    explain=(
        "One correct version tests the highest band first: if score >= 80: "
        "print(\"distinction\"), elif score >= 50: print(\"pass\"), else: "
        "print(\"fail\"). If the pass test came first, every score of 80 or more "
        "would be caught by it and distinction would never be printed. For "
        "score = 85 the program prints distinction."
    ),
    criteria="Adds an 80-or-more test placed before the pass test, keeping pass and fail.",
    misconceptions=[
        "Adding the new test after the one that already matches, so it is never reached.",
        "Writing separate ifs that print more than one result for the same score.",
    ],
    hint="Think about which test must be asked first so the highest band is not swallowed by a lower one.",
    follow_up="Add a fourth band for scores of 90 or more and say where it goes.",
))
claim(SRC.replace('if score >= 50:\n    print("pass")', 'if score >= 80:\n    print("distinction")\nelif score >= 50:\n    print("pass")'), "distinction")

SRC = code("""
    def can_vote(age, registered):
        if age >= 18:
            if registered == True:
                return True
            else:
                return False
        else:
            return False
""")
ACTIVITIES.append(op(
    T, "code-improvement", "Flatten the nested ifs", MACRO,
    stem=(
        "An AI produced this function for: a person can vote if they are 18 or over and "
        "registered. It works, but it is longer and harder to read than it needs to be. "
        "Improve it."
    ),
    code=SRC,
    concepts=[
        ("Combine with and", "The two conditions are joined with and instead of being nested.",
         ["and", "combine", "combined", "both conditions", "single condition"]),
        ("No comparison to True", "registered == True is unnecessary; registered is already True or False.",
         ["== true", "redundant", "unnecessary", "already", "directly"]),
        ("Return the condition", "The function returns the condition itself instead of returning True or False from branches.",
         ["return the condition", "just return", "return age", "single return", "boolean", "directly"]),
    ],
    explain=(
        "The whole function is one yes/no question, so it can be: return age >= "
        "18 and registered. The nested ifs, the comparison to True and the "
        "separate return True/return False branches all say the same thing in "
        "more words. The improvement keeps the behaviour exactly the same and "
        "makes the rule visible at a glance."
    ),
    criteria="Joins the tests with and and returns the condition directly, without == True.",
    misconceptions=[
        "Thinking more lines mean more careful code.",
        "Writing == True on something that is already True or False.",
    ],
    hint="The function answers a single yes/no question. What is the shortest way to say it?",
    follow_up="Test your version with all four combinations of age 17/18 and registered True/False.",
))
for _age, _reg in ((17, True), (18, True), (18, False), (17, False)):
    claim(
        SRC + f"\nprint(can_vote({_age}, {_reg}) == ({_age} >= 18 and {_reg}))",
        "True",
    )

# --- Level 6 ---------------------------------------------------------------------
ACTIVITIES.append(ai(
    T, "Is this discount test boundary-safe?", RELATIONS,
    stem=(
        "A student asked an AI to complete qualifies(total) so it returns True when the "
        "total is at least 100. The AI suggested the highlighted line. Accept or reject "
        "the suggestion, then explain your reasoning."
    ),
    code="def qualifies(total):\n    # AI suggestion appears below",
    suggestion="return total > 100",
    decision="reject",
    concepts=[
        ("Boundary value", "A total of exactly 100 should qualify, but > leaves it out.",
         ["100", "exactly", "boundary", "equal", "edge", "not included"]),
        ("Right operator", "'At least 100' needs >= rather than >.",
         [">=", "at least", "greater than or equal", "or equal"]),
        ("Checked with a value", "The suggestion is tested with 100 and the wrong result noticed.",
         ["false", "returns false", "example", "test", "try"]),
    ],
    explain=(
        "total > 100 is False for exactly 100, but the requirement says 'at "
        "least 100', so 100 should qualify. The correct line is return total >= "
        "100. The suggestion works for most values, which is exactly why it "
        "passes a casual check: boundary values need testing on purpose."
    ),
    criteria="Rejects the line and says that 100 itself is wrongly excluded, or that >= is needed.",
    misconceptions=[
        "Accepting a comparison without testing the boundary value.",
        "Treating 'at least' and 'more than' as the same.",
    ],
    hint="Try the suggestion with 99, 100 and 101. Does each result match 'at least 100'?",
    follow_up="Write the corrected line and list three totals you would test it with.",
))
claim("def qualifies(total):\n    return total > 100\nprint(qualifies(99), qualifies(100), qualifies(101))", "False False True")

ACTIVITIES.append(ai(
    T, "Is this cap function correct?", MACRO,
    stem=(
        "A student asked an AI to complete limit(value) so it returns value, but never more "
        "than 100. The AI suggested the highlighted lines. Accept or reject the suggestion, "
        "then explain your reasoning."
    ),
    code="def limit(value):\n    # AI suggestion appears below",
    suggestion="if value > 100:\n    return 100\nreturn value",
    decision="accept",
    concepts=[
        ("Caps large values", "Values above 100 are replaced by 100.",
         ["100", "cap", "caps", "limit", "maximum", "over", "above"]),
        ("Keeps other values", "Values of 100 or below are returned unchanged.",
         ["unchanged", "same", "below", "keeps", "returns value", "smaller", "less"]),
        ("Checked with examples", "The reasoning uses example values such as 120, 100 and 50.",
         ["120", "50", "example", "examples", "trace", "test"]),
    ],
    explain=(
        "For 120 the if-block runs and 100 is returned. For 100 or 50 it does "
        "not, so the value itself is returned. At exactly 100 either route gives "
        "100, so the boundary is safe. The suggestion meets the requirement, so "
        "accepting it is correct; the skill is checking, not suspecting everything."
    ),
    criteria="Accepts the suggestion and justifies it with large, boundary or small example values.",
    misconceptions=[
        "Assuming every AI suggestion must hide a mistake.",
        "Accepting without checking a value above, at and below the limit.",
    ],
    hint="Trace the function with 120, 100 and 50, and compare each result with the requirement.",
    follow_up="Rewrite it as a single line using min, and say which version you find easier to read.",
))
claim(
    "def limit(value):\n    if value > 100:\n        return 100\n    return value\n"
    "print(limit(120), limit(100), limit(50))",
    "100 100 50",
)

SRC = code("""
    def shipping(total):
        if total >= 50:
            return 0
        else:
            return 4
""")
ACTIVITIES.append(mc(
    T, "code-quality-review", "Review the shipping rule", MACRO,
    stem=(
        "An AI generated this function: shipping is free for totals of 50 or more, "
        "otherwise it costs 4. It passes every test you try. Which review comment is "
        "the most justified?"
    ),
    code=SRC,
    correct=(
        "It is correct, including at exactly 50; the else is not strictly needed "
        "because the function has already returned, but it does make both cases visible."
    ),
    wrong=[
        "It is incorrect: a total of exactly 50 pays 4.",
        "It must use elif, because there are two outcomes.",
        "Functions may not return from inside an if statement.",
    ],
    explain=(
        "First, correctness: shipping(50) returns 0, shipping(49) returns 4 and "
        "shipping(100) returns 0, matching the rule. The quality point is "
        "small: after return 0 the function has finished, so else is optional "
        "style. The other comments make false claims (50 is free; elif is "
        "required; return inside if is illegal)."
    ),
    criteria="Confirms correctness (including 50) and treats else as a style choice, rejecting false claims.",
    misconceptions=[
        "Believing code must be wrong because a comment sounds critical.",
        "Thinking a function cannot return from inside a branch.",
    ],
    hint="Check shipping(49), shipping(50) and shipping(51) first. Only then think about style.",
    follow_up="Rewrite it without the else and say whether the behaviour changes for any total.",
))
claim(SRC + "\nprint(shipping(49), shipping(50), shipping(100))", "4 0 0")
