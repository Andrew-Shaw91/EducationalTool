"""Functions: nine more activities (levels 2-6)."""

from . import ATOMS, BLOCKS, MACRO, RELATIONS, ai, claim, code, mc, op

T = "functions"
ACTIVITIES = []

# --- Level 2 ---------------------------------------------------------------------
SRC = code("""
    def count_big(items):
        count = 0
        for item in items:
            if item > 10:
                count = count + 1
        return count
""")
claim(SRC + "\nprint(count_big([4, 12, 30, 9]))", "2")
ACTIVITIES.append(mc(
    T, "purpose", "What does count_big report?", MACRO,
    stem="What overall problem is this function solving? Avoid describing only the syntax.",
    code=SRC,
    correct="It returns how many of the items are greater than 10.",
    wrong=[
        "It returns the largest item in the list.",
        "It returns the items that are greater than 10.",
        "It returns True if any item is greater than 10.",
    ],
    explain=(
        "count starts at 0 and goes up by one for every item above 10, so the "
        "function returns a number: how many items qualify. For [4, 12, 30, 9] "
        "that is 2. It does not return the items themselves, the largest one, or "
        "a True/False answer."
    ),
    criteria="Names the purpose as counting items over 10, and notes that a number is returned.",
    misconceptions=[
        "Confusing counting items with returning the items.",
        "Describing the loop rather than what the function reports.",
    ],
    hint="Look at what count starts as, when it changes, and what is returned at the end.",
    follow_up="Change the function so it returns the items themselves instead of how many.",
))

# --- Level 3 ---------------------------------------------------------------------
SRC = code("""
    def square(n):
        return ______

    print(square(4))
""")
ACTIVITIES.append(mc(
    T, "code-completion", "Complete the square function", ATOMS,
    stem="Which expression completes the blank so the program prints 16?",
    code=SRC,
    correct="n * n",
    wrong=["n + n", "square * n", "n"],
    explain=(
        "Squaring means multiplying a number by itself: 4 * 4 is 16. n + n gives "
        "8, a doubling. square * n tries to use the function's own name as a "
        "number, which is an error. Returning n alone gives back 4 unchanged."
    ),
    criteria="Selects n * n and distinguishes squaring from doubling.",
    misconceptions=[
        "Confusing squaring with doubling.",
        "Using the function name as if it were a value inside its own body.",
    ],
    hint="Try each option with n = 4 and compare it with the expected 16.",
    follow_up="Write a cube function and say what one change turns square into cube.",
))
claim("def square(n):\n    return n * n\nprint(square(4))\nprint(4 + 4)", "16", "8")

SRC = code("""
    name = "Ana"
    print("Hello, " + name)
""")
ACTIVITIES.append(op(
    T, "modify-code", "Turn the greeting into a function", BLOCKS,
    stem=(
        "Turn this into a function called greet that takes a name and prints the "
        "greeting for that name, so greet(\"Ana\") and greet(\"Ben\") both work. "
        "Describe or write the change."
    ),
    code=SRC,
    concepts=[
        ("Defined with def and a parameter", "The function is defined with def and takes name as a parameter.",
         ["def", "parameter", "parameters", "argument", "greet(name)", "(name)"]),
        ("Body uses the parameter", "The greeting uses the parameter rather than the fixed value \"Ana\".",
         ["name", "instead of", "not fixed", "not hard", "variable", "uses the parameter"]),
        ("Called with different names", "It is called with different values, such as greet(\"Ben\").",
         ["call", "called", "greet(", "ben", "different"]),
    ],
    explain=(
        "def greet(name): print(\"Hello, \" + name). The fixed value \"Ana\" is "
        "replaced by the parameter name, so greet(\"Ana\") prints Hello, Ana and "
        "greet(\"Ben\") prints Hello, Ben. One definition now serves every name."
    ),
    criteria="Defines greet(name) using the parameter in the greeting, then calls it with different names.",
    misconceptions=[
        "Leaving \"Ana\" inside the function so every call greets Ana.",
        "Defining the function but never calling it.",
    ],
    hint="Which part of the code should change from call to call? That part becomes the parameter.",
    follow_up="Add a second parameter for the greeting word (Hello, Hi) and say how the calls change.",
))
claim('def greet(name):\n    print("Hello, " + name)\ngreet("Ana")\ngreet("Ben")', "Hello, Ana", "Hello, Ben")

# --- Level 4 ---------------------------------------------------------------------
SRC_A = code("""
    def ratio(a, b):
        return a / b

    print(ratio(10, 2))
""")
SRC_B = code("""
    def ratio(a, b):
        return a / b

    print(ratio(2, 10))
""")
claim(SRC_A, "5.0")
claim(SRC_B, "0.2")
ACTIVITIES.append(mc(
    T, "compare-solutions", "Same function, different arguments", RELATIONS,
    stem=(
        "Two programs define the same function and call it.\n\nProgram A:\n" + SRC_A +
        "\n\nProgram B:\n" + SRC_B + "\n\nWhat is the difference in what they print?"
    ),
    correct="A prints 5.0 and B prints 0.2, because the order of the arguments decides which is a and which is b.",
    wrong=[
        "Both print 5.0, because the function name is the same.",
        "Both print 0.2, because division always gives a small number.",
        "B is an error, because the larger number must come first.",
    ],
    explain=(
        "Arguments are matched to parameters by position. In A, a is 10 and b "
        "is 2, giving 10 / 2 = 5.0. In B they are swapped, so a is 2 and b is 10, "
        "giving 2 / 10 = 0.2. The definition is identical; only the call "
        "differs. Division is not symmetrical, so the order matters."
    ),
    criteria="States that the calls give 5.0 and 0.2 because arguments are matched by position.",
    misconceptions=[
        "Believing the order of arguments does not matter.",
        "Assuming the same function always produces the same output.",
    ],
    hint="For each call, write down which value goes to a and which goes to b.",
    follow_up="Rewrite one call using named arguments (a=2, b=10) and say whether the order still matters.",
))

SRC = code("""
    def double(x):
        x = x * 2
        return x

    x = 10
    double(x)
    print(x)
""")
claim(SRC, "10")
ACTIVITIES.append(mc(
    T, "misconception-analysis", "Why did the student predict 20?", RELATIONS,
    stem=(
        "A student predicted this program prints 20. It prints 10. Which misconception "
        "best explains the student's prediction?"
    ),
    code=SRC,
    correct=(
        "The student thinks calling double(x) changes the x outside the function, but "
        "the function works on its own copy and the returned value was not stored."
    ),
    wrong=[
        "The student thinks x * 2 means x plus 2.",
        "The student thinks print runs before double is called.",
        "The student thinks a function can only be called once.",
    ],
    explain=(
        "Inside double, x is a separate variable that starts as a copy of the "
        "argument. Doubling it does not change the x outside. The function "
        "returns 20, but the call double(x) throws that value away because it "
        "is not assigned to anything. To keep it: x = double(x), which would "
        "make the program print 20."
    ),
    criteria="Identifies that the function's x is separate from the outside x and the result was not kept.",
    misconceptions=[
        "Believing a function changes the variable that was passed to it.",
        "Ignoring a returned value that is not stored.",
    ],
    hint="Which x does the function change, and what happens to the value it returns?",
    follow_up="Change one line so the program prints 20 and say why it now works.",
))

# --- Level 5 ---------------------------------------------------------------------
SRC = code("""
    def apply_discount(price):
        return price - price * 0.1

    print(apply_discount(200))
""")
claim(SRC, "180.0")
ACTIVITIES.append(op(
    T, "extend-code", "Make the discount adjustable", MACRO,
    stem=(
        "The 10% discount is fixed. Extend the function so the caller can supply a different "
        "rate, but calls that do not supply one still use 10%."
    ),
    code=SRC,
    concepts=[
        ("Second parameter", "The rate becomes a parameter of the function.",
         ["parameter", "rate", "second", "argument", "extra"]),
        ("Default value", "The parameter has a default of 0.1 so older calls keep working.",
         ["default", "= 0.1", "=0.1", "0.1", "optional"]),
        ("Used in the calculation", "The calculation uses the parameter instead of the fixed 0.1.",
         ["use", "uses", "replace", "replaces", "instead", "calculation", "inside"]),
    ],
    explain=(
        "def apply_discount(price, rate=0.1): return price - price * rate. A call "
        "such as apply_discount(200) still uses 0.1 and gives 180.0, while "
        "apply_discount(200, 0.25) gives 150.0. A default value lets the "
        "function grow without breaking the code that already calls it."
    ),
    criteria="Adds a rate parameter with a default of 0.1 and uses it in the calculation.",
    misconceptions=[
        "Adding the parameter without a default, which breaks existing calls.",
        "Adding the parameter but leaving 0.1 inside the calculation.",
    ],
    hint="You need a new input, but old calls must keep working. What lets a parameter be optional?",
    follow_up="Add a check so a rate above 1 is rejected, and decide whether to raise an error or return the price.",
))
claim(
    "def apply_discount(price, rate=0.1):\n    return price - price * rate\n"
    "print(apply_discount(200))\nprint(apply_discount(200, 0.25))",
    "180.0", "150.0",
)

SRC = code("""
    def f(a, b):
        print(a * b)

    f(6, 7)
""")
claim(SRC, "42")
ACTIVITIES.append(op(
    T, "code-improvement", "Make f say what it does", MACRO,
    stem=(
        "An AI generated this function to multiply two numbers and show the result. It "
        "works, but the name says nothing and it prints instead of returning, so the "
        "result cannot be reused. Improve it."
    ),
    code=SRC,
    concepts=[
        ("Descriptive names", "The function and parameters are given meaningful names.",
         ["rename", "name", "names", "descriptive", "meaningful", "multiply", "product", "clear"]),
        ("Return instead of print", "The function returns the value so the caller can reuse it.",
         ["return", "returns", "returned", "reuse", "reused"]),
        ("Printing at the call", "The caller decides what to do with the result, such as printing it.",
         ["caller", "call", "print(", "outside", "where it is called"]),
    ],
    explain=(
        "def multiply(a, b): return a * b, and then print(multiply(6, 7)). The "
        "output is still 42, but now the result can be stored, added to something "
        "else or tested. A function that only prints can show a value but cannot "
        "pass it on."
    ),
    criteria="Renames f meaningfully and changes print to return, printing at the call instead.",
    misconceptions=[
        "Treating print and return as the same thing.",
        "Renaming only, leaving a function that cannot be reused.",
    ],
    hint="Could the caller add 1 to the result of f(6, 7)? What would need to change for that to work?",
    follow_up="Use your function to print the area of a 6 by 7 rectangle plus a border of 4.",
))
claim("def multiply(a, b):\n    return a * b\nprint(multiply(6, 7))\nprint(multiply(6, 7) + 4)", "42", "46")

# --- Level 6 ---------------------------------------------------------------------
ACTIVITIES.append(ai(
    T, "Is this larger-of-two function right?", RELATIONS,
    stem=(
        "A student asked an AI to complete larger(a, b) so it returns the bigger of two "
        "numbers. The AI suggested the highlighted lines. Accept or reject the suggestion, "
        "then explain your reasoning."
    ),
    code="def larger(a, b):\n    # AI suggestion appears below",
    suggestion="if a > b:\n    return a\nreturn b",
    decision="accept",
    concepts=[
        ("Bigger returned", "When a is bigger it is returned; otherwise b is returned.",
         ["bigger", "larger", "greater", "returns a", "returns b", "return b"]),
        ("Equal values", "If the values are equal, returning b is still correct.",
         ["equal", "same", "tie", "tied", "either"]),
        ("Checked with examples", "The reasoning uses example values such as (3, 5), (5, 3) and (4, 4).",
         ["example", "examples", "trace", "test", "(3, 5)", "(5, 3)", "3 and 5"]),
    ],
    explain=(
        "larger(3, 5): 3 > 5 is False, so b (5) is returned. larger(5, 3): 5 > 3 "
        "is True, so a (5) is returned. larger(4, 4): 4 > 4 is False and b (4) is "
        "returned, which is also correct. All three agree with the requirement, "
        "so accepting is right."
    ),
    criteria="Accepts the suggestion and checks it with the values in either order and equal values.",
    misconceptions=[
        "Suspecting an error because there is no else.",
        "Checking only one order of the arguments.",
    ],
    hint="Try the function with (3, 5), (5, 3) and (4, 4), and compare each result with the requirement.",
    follow_up="Rewrite larger using max, and say when you would still write the version above.",
))
claim(
    "def larger(a, b):\n    if a > b:\n        return a\n    return b\n"
    "print(larger(3, 5), larger(5, 3), larger(4, 4))",
    "5 5 4",
)

SRC = code("""
    def apply_discount(price, percent):
        return price - price * percent / 100

    print(apply_discount(200, 25))
""")
claim(SRC, "150.0")
ACTIVITIES.append(mc(
    T, "code-quality-review", "Review the discount helper", MACRO,
    stem=(
        "An AI generated this function to take a percentage off a price. Its output for "
        "apply_discount(200, 25) is correct. Which review comment is the most justified?"
    ),
    code=SRC,
    correct=(
        "It is correct and clearly named; one improvement is to say in a comment or "
        "docstring that percent means 25 for 25%, not 0.25."
    ),
    wrong=[
        "It is incorrect: percent must be a decimal such as 0.25 for the answer 150.0.",
        "It is incorrect: a function cannot take two parameters.",
        "It should print the discounted price instead of returning it.",
    ],
    explain=(
        "200 - 200 * 25 / 100 is 150.0, so the function is correct for percent "
        "given as 25. The remaining risk is a caller who passes 0.25, because "
        "nothing in the signature says which convention is used; a short docstring "
        "or comment removes the doubt. The other comments are false claims."
    ),
    criteria="Confirms correctness, then names the unclear units of percent as the improvement.",
    misconceptions=[
        "Believing a plausible-sounding objection without testing it.",
        "Thinking a function should print its result rather than return it.",
    ],
    hint="Check the answer by hand first. Then ask what a caller could misunderstand.",
    follow_up="Add a docstring and an example call to the function.",
))
