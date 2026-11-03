"""Variables: ten more activities (two each at Bloom levels 2-6)."""

from . import ATOMS, BLOCKS, MACRO, RELATIONS, ai, claim, code, mc, op

T = "variables"
ACTIVITIES = []

# --- Level 2 ---------------------------------------------------------------------
SRC = code("""
    x = 4
    y = x + 1
    x = y * 2
    print(x, y)
""")
claim(SRC, "10 5")
ACTIVITIES.append(mc(
    T, "tracing", "Follow the values through three lines", RELATIONS,
    stem="What is printed when this program finishes?",
    code=SRC,
    correct="10 5",
    wrong=["8 5", "10 10", "4 5"],
    explain=(
        "x starts at 4, so y becomes 5. The third line then uses the CURRENT "
        "value of y (5), so x becomes 10. y is not touched again, so it is "
        "still 5 and print shows 10 5. The option 8 5 doubles the old x; 10 10 "
        "assumes y follows x; 4 5 ignores the reassignment of x."
    ),
    criteria="Selects 10 5 and can say which value of each name was used on each line.",
    misconceptions=[
        "Believing y changes automatically whenever x changes.",
        "Using the first value of x after it has been reassigned.",
    ],
    hint="Write the value of x and y after each line, not just at the end.",
    follow_up="Swap lines 2 and 3 and predict the new output before running it.",
))

SRC = code("""
    celsius = 25
    fahrenheit = celsius * 9 / 5 + 32
    print(fahrenheit)
""")
claim(SRC, "77.0")
ACTIVITIES.append(mc(
    T, "purpose", "What is this temperature fragment for?", MACRO,
    stem="What overall problem is this program solving? Avoid describing only the syntax.",
    code=SRC,
    correct="It converts a temperature from Celsius to Fahrenheit.",
    wrong=[
        "It converts a temperature from Fahrenheit to Celsius.",
        "It adds 9, 5 and 32 together.",
        "It checks whether 25 is a valid temperature.",
    ],
    explain=(
        "The value 25 is a temperature in Celsius. Multiplying by 9 / 5 and "
        "adding 32 is the Celsius-to-Fahrenheit formula, so the program prints "
        "77.0. The names celsius and fahrenheit carry the purpose, which is why "
        "good naming matters when you read generated code."
    ),
    criteria="Names the conversion Celsius to Fahrenheit rather than listing the operations.",
    misconceptions=[
        "Describing the arithmetic instead of the problem it solves.",
        "Ignoring what the variable names say about direction.",
    ],
    hint="Read the names first: what is going in, and what is coming out?",
    follow_up="Write the reverse conversion and say what each name should be.",
))

# --- Level 3 ---------------------------------------------------------------------
SRC = code("""
    price = 20
    quantity = 3
    total = price * quantity
    print(total)
""")
ACTIVITIES.append(op(
    T, "modify-code", "Add a delivery fee", BLOCKS,
    stem=(
        "The shop now charges a delivery fee of 5. Change the program so the fee "
        "is stored in its own variable and included in the total that is printed."
    ),
    code=SRC,
    concepts=[
        ("Fee in its own variable", "The fee of 5 is stored under a name rather than typed into the sum.",
         ["delivery", "fee", "variable", "named"]),
        ("Fee added to the total", "The fee is added to the total (price * quantity) before printing.",
         ["+", "add", "added", "plus", "include"]),
        ("Result printed", "The new total is displayed with print.", ["print", "display", "output"]),
    ],
    explain=(
        "One correct change is: delivery = 5, then total = price * quantity + "
        "delivery, then print(total), which prints 65. Giving the fee a name "
        "means a future change to the fee is made in one place, and the reader "
        "can see what the 5 means."
    ),
    criteria="Stores the fee in a variable, adds it to the total, and prints the result.",
    misconceptions=[
        "Typing 5 into the formula so its meaning is hidden.",
        "Adding the fee after print has already run.",
    ],
    hint="Decide where the fee should be stored, then where it must be added so print sees it.",
    follow_up="Make the fee depend on the quantity (free above 5 items) and say which line changes.",
))
claim(SRC + "\ndelivery = 5\ntotal = price * quantity + delivery\nprint(total)", "60", "65")

SRC = code("""
    a = 6
    b = 10
    average = ______
    print(average)
""")
ACTIVITIES.append(mc(
    T, "code-completion", "Complete the average line", ATOMS,
    stem="Which expression completes the blank so the program prints 8.0, the average of a and b?",
    code=SRC,
    correct="(a + b) / 2",
    wrong=["a + b / 2", "(a + b) * 2", "a + b * 2"],
    explain=(
        "Brackets make the addition happen first: (6 + 10) / 2 is 8.0. Without "
        "them, a + b / 2 divides only b, giving 6 + 5.0 = 11.0, because division "
        "binds more tightly than addition. The options with * 2 double instead "
        "of halving."
    ),
    criteria="Selects (a + b) / 2 and can explain why the brackets are needed.",
    misconceptions=[
        "Reading the expression left to right and ignoring operator precedence.",
        "Confusing halving with doubling.",
    ],
    hint="Work out what each option gives for a = 6 and b = 10 before choosing.",
    follow_up="Find the average of three values and say where the brackets go.",
))
claim("a = 6\nb = 10\nprint((a + b) / 2)\nprint(a + b / 2)\nprint((a + b) * 2)", "8.0", "11.0", "32")

# --- Level 4 ---------------------------------------------------------------------
SRC = code("""
    subtotal = 40
    delivery = 5
    total = subtotal
    total + delivery
    print(total)
""")
claim(SRC, "40")
ACTIVITIES.append(mc(
    T, "debugging", "A total that ignores the fee", RELATIONS,
    stem="The program should print 45, but it prints 40. Identify the bug.",
    code=SRC,
    correct="The line total + delivery works out a value but never stores it, so total stays 40.",
    wrong=[
        "delivery should be a string so it can be added.",
        "print must come before total is assigned.",
        "A variable cannot be given the value of another variable.",
    ],
    explain=(
        "total + delivery is a valid expression that evaluates to 45, but "
        "nothing keeps the result, so it is thrown away. total still holds 40 "
        "when print runs. The fix is total = total + delivery. Python raised no "
        "error, which is why the bug is easy to miss."
    ),
    criteria="Identifies that the sum is computed but not assigned to anything.",
    misconceptions=[
        "Assuming an expression on its own line updates the variable.",
        "Blaming types or ordering instead of the missing assignment.",
    ],
    hint="After the fourth line, what does total hold? Does any line change it?",
    follow_up="Write the corrected line, then change delivery to 7 and predict the output.",
))

DISCOUNT_A = code("""
    price = 80
    price = price - price * 0.25
    print(price)
""")
DISCOUNT_B = code("""
    price = 80
    discounted = price - price * 0.25
    print(price)
""")
claim(DISCOUNT_A, "60.0")
claim(DISCOUNT_B, "80")
ACTIVITIES.append(mc(
    T, "compare-solutions", "Two ways to take off the discount", RELATIONS,
    stem=(
        "Both programs try to print the price after a 25% discount.\n\n"
        "Solution A:\n" + DISCOUNT_A + "\n\nSolution B:\n" + DISCOUNT_B +
        "\n\nHow do they differ?"
    ),
    correct=(
        "A overwrites price with the discounted value and prints 60.0; B keeps "
        "the result in discounted but prints price, so it still prints 80."
    ),
    wrong=[
        "They print the same, because both calculate the discount.",
        "A is invalid, because a variable cannot be used in its own assignment.",
        "B prints 60.0, because discounted stays linked to price.",
    ],
    explain=(
        "In A the right-hand side is worked out from the old price (80), then "
        "stored back into price, so print shows 60.0. In B the result goes into "
        "a new name, discounted, but print asks for price, which is unchanged "
        "at 80. A variable can appear on both sides of an assignment because the "
        "right side is evaluated first."
    ),
    criteria="Traces both programs and states that A prints 60.0 while B prints 80.",
    misconceptions=[
        "Believing a new variable stays linked to the one it was calculated from.",
        "Thinking price = price - ... is impossible because price is on both sides.",
    ],
    hint="For each program, say what price holds when print runs.",
    follow_up="Change B's last line so it prints the discounted value, and name one reason to keep both prices.",
))

# --- Level 5 ---------------------------------------------------------------------
SRC = code("""
    t = 50 * 3
    t2 = t + t * 0.2
    print(t2)
""")
claim(SRC, "180.0")
ACTIVITIES.append(op(
    T, "code-improvement", "Give the numbers and names meaning", MACRO,
    stem=(
        "An AI wrote this to find the cost of 3 items at 50 each plus 20% tax. It "
        "gives the right answer, but a reader cannot tell what t, t2 or the numbers "
        "mean. Improve it. You may rename, add variables and split steps."
    ),
    code=SRC,
    concepts=[
        ("Meaningful names", "t and t2 are renamed to names that say what they hold (for example subtotal and total).",
         ["rename", "descriptive", "meaningful", "subtotal", "clear names"]),
        ("Named values for the numbers", "50, 3 and 0.2 are stored in variables such as price, quantity and tax_rate.",
         ["tax_rate", "price", "quantity", "magic", "constant", "named"]),
        ("Steps kept separate", "The subtotal is calculated on its own line before tax is applied.",
         ["subtotal", "separate", "step", "intermediate"]),
    ],
    explain=(
        "A clearer version: price = 50, quantity = 3, tax_rate = 0.2, "
        "subtotal = price * quantity, total = subtotal + subtotal * tax_rate, "
        "print(total). It prints the same 180.0. Nothing about the answer "
        "changed; what improved is that each number and result now says what "
        "it means, so the next person can change the tax rate in one place."
    ),
    criteria="Renames t and t2 and gives the three numbers names, keeping the result 180.0.",
    misconceptions=[
        "Thinking code that gives the right answer needs no improvement.",
        "Renaming only some of the names and leaving the magic numbers.",
    ],
    hint="For each name and number, ask: would someone new know what this means?",
    follow_up="Change the tax rate to 0.25 in your version and say how many lines you had to touch.",
))

SRC = code("""
    length = 8
    width = 3
    area = length * width
    print(area)
""")
claim(SRC, "24")
claim(SRC + "\nperimeter = 2 * (length + width)\nprint(perimeter)", "24", "22")
ACTIVITIES.append(op(
    T, "extend-code", "Report the perimeter as well", MACRO,
    stem=(
        "Extend the program so it also prints the perimeter of the rectangle (the "
        "distance all the way round), stored in its own variable."
    ),
    code=SRC,
    concepts=[
        ("Perimeter in its own variable", "The perimeter is stored under a name such as perimeter.",
         ["perimeter", "variable", "named"]),
        ("Both sides counted twice", "The calculation doubles the sum of length and width (or adds all four sides).",
         ["2 *", "twice", "double", "doubled", "+ length", "all four"]),
        ("Printed", "The perimeter is displayed with print.", ["print", "display", "output"]),
    ],
    explain=(
        "perimeter = 2 * (length + width) then print(perimeter) gives 22 for an "
        "8 by 3 rectangle. Reusing the existing names length and width keeps the "
        "new line connected to the data: change either value and both results "
        "update when the program is run again."
    ),
    criteria="Stores perimeter in a variable using length and width, doubled, and prints it.",
    misconceptions=[
        "Typing the answer 22 instead of calculating it from the variables.",
        "Counting only length + width, which is half the distance round.",
    ],
    hint="Which two names already hold what you need, and how many times does each side appear?",
    follow_up="Add a third value, height, and say which new lines a box needs.",
))

# --- Level 6 ---------------------------------------------------------------------
ACTIVITIES.append(ai(
    T, "Is this average line right?", RELATIONS,
    stem=(
        "A student asked an AI to complete the program so average holds the mean of a "
        "and b. The AI suggested the highlighted line. Accept or reject the "
        "suggestion, then explain your reasoning."
    ),
    code="a = 6\nb = 10\n# AI suggestion appears below",
    suggestion="average = a + b / 2",
    decision="reject",
    concepts=[
        ("Operator precedence", "Division happens before addition, so only b is halved.",
         ["precedence", "order", "division", "first", "only b", "divides"]),
        ("Wrong value shown", "With a = 6 and b = 10 it gives 11.0, not the mean 8.0.",
         ["11", "wrong", "incorrect", "not the mean", "8.0"]),
        ("The fix", "Brackets around a + b make the addition happen first.",
         ["bracket", "brackets", "parenthes", "(a + b)"]),
    ],
    explain=(
        "In Python b / 2 is evaluated before the addition, so the line means "
        "a + (b / 2) = 6 + 5.0 = 11.0. The mean is 8.0, which needs (a + b) / 2. "
        "The suggestion reads like a maths formula, which is why it is "
        "convincing; checking one example exposes it."
    ),
    criteria="Rejects the line, saying division happens first or giving 11.0 instead of 8.0.",
    misconceptions=[
        "Reading code as if it were written maths and assuming the author's intent.",
        "Accepting a line because it uses the right variables and operators.",
    ],
    hint="Try the suggestion with a = 6 and b = 10 and compare it with the average you expect.",
    follow_up="Write the corrected line, then say which example values would have caught the error.",
))
claim("a = 6\nb = 10\naverage = a + b / 2\nprint(average)", "11.0")

SRC = code("""
    width = 4
    height = 3
    print(width * height)
    print(width * height)
""")
claim(SRC, "12", "12")
ACTIVITIES.append(mc(
    T, "code-quality-review", "Review the repeated area", MACRO,
    stem=(
        "An AI generated this program to show the area of a 4 by 3 rectangle twice. It "
        "prints the right answer both times. Which review comment is the most justified?"
    ),
    code=SRC,
    correct=(
        "It is correct, but the same expression is written twice; storing it in a "
        "variable such as area would remove the repetition."
    ),
    wrong=[
        "It is incorrect: print cannot be called twice in one program.",
        "It is incorrect: width and height must be strings to be multiplied.",
        "No change is ever worth making to code that prints the right answer.",
    ],
    explain=(
        "First, correctness: 4 * 3 is 12 and it is printed twice, so the "
        "program does what was asked. The quality point is separate: the same "
        "calculation is repeated, so a later change to the formula must be made "
        "in two places. A variable named area fixes that. The other comments "
        "make false claims (print can be repeated; numbers multiply) or an "
        "absolute one about working code."
    ),
    criteria="Separates correctness from quality: confirms it works, then names the repeated calculation.",
    misconceptions=[
        "Treating code that gives the right answer as having no quality concerns.",
        "Accepting confident but false claims about print or numbers.",
    ],
    hint="First decide whether the output is right. Only then ask what could be clearer.",
    follow_up="Rewrite it with an area variable and say which line you would change if the shape became a square.",
))
