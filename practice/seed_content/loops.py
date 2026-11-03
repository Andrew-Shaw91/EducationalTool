"""Loops: ten more activities (one at level 1, then pairs at levels 2-6 where needed)."""

from . import ATOMS, BLOCKS, MACRO, RELATIONS, ai, claim, code, mc, op

T = "loops"
ACTIVITIES = []

# --- Level 1 ---------------------------------------------------------------------
ACTIVITIES.append(op(
    T, "define-concept", "Define a loop", ATOMS,
    stem="In your own words, what is a loop and why would a program use one?",
    concepts=[
        ("Repeats code", "A loop runs the same block of code more than once.",
         ["repeat", "repeats", "again", "multiple times", "many times", "over and over", "iterate", "iterates"]),
        ("Controlled by a rule", "It stops when a condition or a sequence of items runs out.",
         ["until", "while", "stops", "ends", "condition", "each", "every", "finished"]),
        ("Avoids copying code", "It saves writing the same lines out again and again.",
         ["avoid", "avoids", "saves", "shorter", "copy", "duplicate", "duplicates", "less code"]),
    ],
    explain=(
        "A loop repeats a block of code. A for loop runs it once for each item "
        "in a sequence, or a set number of times; a while loop keeps going "
        "while a condition stays True. Programs use loops so that one short "
        "block can handle ten items or ten thousand."
    ),
    criteria="Says a loop repeats code under some rule and that this avoids writing the same lines many times.",
    misconceptions=[
        "Thinking a loop runs only once and waits.",
        "Believing a loop must always run a fixed, known number of times.",
    ],
    hint="Think about printing the numbers 1 to 100. How would you avoid writing 100 lines?",
    follow_up="Give one example of a task you would use a for loop for and one for a while loop.",
    minutes=2,
))

# --- Level 2 ---------------------------------------------------------------------
SRC = code("""
    words = ["tree", "moon", "stars"]
    best = ""
    for word in words:
        if len(word) > len(best):
            best = word
    print(best)
""")
claim(SRC, "stars")
ACTIVITIES.append(mc(
    T, "purpose", "What does this loop find?", MACRO,
    stem="What overall problem is this program solving? Avoid describing only the syntax.",
    code=SRC,
    correct="It finds the longest word in the list.",
    wrong=[
        "It finds the shortest word in the list.",
        "It counts how many words are in the list.",
        "It finds the word that comes last alphabetically.",
    ],
    explain=(
        "best starts empty, and every word that is longer than the current best "
        "replaces it. After the loop best holds the longest word seen. Here that "
        "is \"stars\" (5 letters). When two words are tied, as \"tree\" and \"moon\" "
        "are, the first one is kept because the test uses > and not >=."
    ),
    criteria="Names the purpose as finding the longest word, not only describing the loop.",
    misconceptions=[
        "Describing the loop and if instead of the problem solved.",
        "Reading best as a counter rather than the current best candidate.",
    ],
    hint="What does best hold after each word, and when does it change?",
    follow_up="Change one character so the program keeps the LAST of two tied words.",
))

# --- Level 3 ---------------------------------------------------------------------
SRC = code("""
    for i in range(5):
        print(i)
""")
ACTIVITIES.append(op(
    T, "modify-code", "Count down instead", BLOCKS,
    stem=(
        "This program counts 0, 1, 2, 3, 4. Change it so it counts down: 5, 4, 3, 2, 1. "
        "Describe or write the change."
    ),
    code=SRC,
    concepts=[
        ("Start at 5", "The sequence starts at 5.", ["5", "start", "starts", "begin"]),
        ("Step of -1", "It moves downwards by 1 each time (a negative step).",
         ["-1", "negative", "step", "backwards", "reverse", "down"]),
        ("Stops before 0", "The end value is 0, which range does not include, so 1 is the last number.",
         ["0", "stop", "stops", "exclusive", "not included", "excluded", "before"]),
    ],
    explain=(
        "range(5, 0, -1) starts at 5, steps by -1 and stops before 0, giving 5, 4, "
        "3, 2, 1. The stop value is never included, which is why it is 0 and "
        "not 1."
    ),
    criteria="Uses a start of 5, a step of -1 and an end that excludes 0 (range(5, 0, -1)).",
    misconceptions=[
        "Using range(5, 1, -1), which stops at 2 because the end is excluded.",
        "Forgetting that range needs a negative step to go downwards.",
    ],
    hint="range can take three values: where to start, where to stop (not included), and the step.",
    follow_up="Print only the even numbers from 10 down to 2 and say what changes.",
))
claim("for i in range(5, 0, -1):\n    print(i)", "5", "4", "3", "2", "1")

SRC = code("""
    numbers = [3, 5, 8]
    doubled = []
    for n in numbers:
        doubled.append(______)
    print(doubled)
""")
ACTIVITIES.append(mc(
    T, "code-completion", "Complete the doubling loop", ATOMS,
    stem="Which expression completes the blank so the program prints [6, 10, 16]?",
    code=SRC,
    correct="n * 2",
    wrong=["numbers * 2", "n + 2", "n ** 2"],
    explain=(
        "n is the current item, so n * 2 doubles each one: 6, 10, 16. numbers * "
        "2 would repeat the whole list instead of doubling its items; n + 2 adds "
        "two, giving 5, 7, 10; n ** 2 squares each item, giving 9, 25, 64."
    ),
    criteria="Selects n * 2 and knows n is the single current item.",
    misconceptions=[
        "Using the whole list name inside the loop instead of the loop variable.",
        "Confusing doubling, adding two and squaring.",
    ],
    hint="Work out what each option gives for n = 3, and compare with the first expected value.",
    follow_up="Change the program so it keeps only the doubled values greater than 7.",
))
claim("numbers = [3, 5, 8]\ndoubled = []\nfor n in numbers:\n    doubled.append(n * 2)\nprint(doubled)", "[6, 10, 16]")

# --- Level 4 ---------------------------------------------------------------------
SRC = code("""
    total = 0
    for n in [2, 3, 4]:
        total = total + n
        print(total)
""")
claim(SRC, "2", "5", "9")
ACTIVITIES.append(mc(
    T, "debugging", "Print inside or outside the loop?", RELATIONS,
    stem="The program should print only the final total, 9. It prints three lines instead. What is the bug?",
    code=SRC,
    correct="print is indented inside the loop, so it runs on every pass. It should be outside the loop.",
    wrong=[
        "total must start at 1 rather than 0.",
        "The loop needs range() to run three times.",
        "total = total + n should be total = n.",
    ],
    explain=(
        "Indentation decides what repeats. print is inside the loop, so it shows "
        "2, then 5, then 9. Moving print back to the left margin (after the loop) "
        "shows only 9. Starting total at 1 would give a wrong total, and "
        "iterating over a list needs no range()."
    ),
    criteria="Identifies that the print is inside the loop and should be moved out.",
    misconceptions=[
        "Not realising that indentation decides which lines repeat.",
        "Changing the calculation when the calculation is already correct.",
    ],
    hint="Which lines are indented under the for? Which of them should run only once?",
    follow_up="Move the print and say what output you expect, then run it to check.",
))

SRC = code("""
    for i in range(3):
        print(i)
""")
claim(SRC, "0", "1", "2")
ACTIVITIES.append(mc(
    T, "misconception-analysis", "Why did the student predict 1, 2, 3?", RELATIONS,
    stem=(
        "A student predicted this program prints 1, 2 and 3. It prints 0, 1 and 2. "
        "Which misconception best explains the student's prediction?"
    ),
    code=SRC,
    correct=(
        "The student thinks range(3) starts counting at 1 and includes 3, but it starts "
        "at 0 and stops before 3."
    ),
    wrong=[
        "The student thinks the loop runs four times.",
        "The student thinks print can only show one number.",
        "The student thinks i is a string rather than a number.",
    ],
    explain=(
        "range(3) produces the three numbers 0, 1, 2: it starts at 0 and stops "
        "before 3. People often expect counting to start at 1, as in everyday "
        "life. The loop runs three times either way, which is why the student's "
        "three numbers looked plausible."
    ),
    criteria="Identifies the wrong belief that range(3) counts 1 to 3 rather than 0 to 2.",
    misconceptions=[
        "Believing range(n) starts at 1.",
        "Believing the end value of range is included.",
    ],
    hint="Count how many numbers range(3) gives, then ask where the counting starts.",
    follow_up="Write the range call that really does give 1, 2 and 3.",
))

# --- Level 5 ---------------------------------------------------------------------
SRC = code("""
    print(7)
    print(14)
    print(21)
    print(28)
    print(35)
""")
ACTIVITIES.append(op(
    T, "code-improvement", "Replace the repeated prints", MACRO,
    stem=(
        "An AI wrote this program to print the first five multiples of 7. It is correct "
        "but would be painful to change for fifty multiples. Improve it."
    ),
    code=SRC,
    concepts=[
        ("Use a loop", "A for loop replaces the five separate print lines.",
         ["loop", "for", "range", "repeat", "iterate"]),
        ("Calculate the value", "Each multiple is calculated from the loop variable instead of typed in.",
         ["* 7", "7 *", "multiply", "calculate", "calculated", "multiple", "formula"]),
        ("Easy to change", "The number of multiples is set in one place, such as the range.",
         ["range", "one place", "change", "scale", "fifty", "50"]),
    ],
    explain=(
        "for i in range(1, 6): print(i * 7) prints the same five values (7, 14, "
        "21, 28, 35). The numbers are now calculated rather than typed in, and "
        "asking for fifty multiples means changing a single number. The output "
        "has not changed; the code is just easier to maintain."
    ),
    criteria="Uses a for loop over a range and calculates each multiple instead of typing it.",
    misconceptions=[
        "Keeping the typed-in values and only wrapping them in a loop.",
        "Starting the range at 0, which would print 0 first.",
    ],
    hint="What is the pattern between the lines? Which part changes and which stays the same?",
    follow_up="Change your loop to print the first ten multiples of 9.",
))
claim("for i in range(1, 6):\n    print(i * 7)", "7", "14", "21", "28", "35")

SRC = code("""
    total = 0
    for n in [4, 7, 1]:
        total = total + n
    print(total)
""")
claim(SRC, "12")
ACTIVITIES.append(op(
    T, "extend-code", "Print each total as it grows", MACRO,
    stem=(
        "Extend the program so that it prints the running total after each number is "
        "added (4, then 11, then 12), as well as the final total."
    ),
    code=SRC,
    concepts=[
        ("Print inside the loop", "A print is placed inside the loop, after the total is updated.",
         ["inside", "in the loop", "indent", "indented", "each time", "every time", "each pass"]),
        ("After the update", "The print comes after total is updated, so it shows the new value.",
         ["after", "updated", "new total", "once added"]),
        ("Final total kept", "The existing print after the loop still shows the final total.",
         ["final", "end", "after the loop", "outside", "12"]),
    ],
    explain=(
        "Add print(total) inside the loop, indented under total = total + n. The "
        "loop then prints 4, 11 and 12, and the original print after the loop "
        "prints 12 once more. Placing the new print before the update would show "
        "0, 4 and 11 instead: one step behind."
    ),
    criteria="Adds an indented print after the update in the loop and keeps the final print.",
    misconceptions=[
        "Putting the new print before the update so the totals are one step behind.",
        "Printing only after the loop, which shows a single value.",
    ],
    hint="Which line changes total, and where must the new print go to see the change?",
    follow_up="Print the number and the total together, such as 'added 4, total is 4'.",
))
claim(SRC.replace("total + n\n", "total + n\n    print(total)\n"), "4", "11", "12", "12")

# --- Level 6 ---------------------------------------------------------------------
ACTIVITIES.append(ai(
    T, "Does this loop visit every name?", RELATIONS,
    stem=(
        "A student asked an AI to print every name in the list names. The AI suggested the "
        "highlighted lines. Accept or reject the suggestion, then explain your reasoning."
    ),
    code='names = ["Ana", "Ben", "Cy"]\n# AI suggestion appears below',
    suggestion="for i in range(1, len(names)):\n    print(names[i])",
    decision="reject",
    concepts=[
        ("Skips the first item", "range starts at 1, so the item at position 0 is never printed.",
         ["skip", "skips", "first", "ana", "position 0", "index 0", "start at 1", "starts at 1", "misses"]),
        ("Output", "Only Ben and Cy are printed.",
         ["ben", "cy", "two names", "only two", "2 names"]),
        ("The fix", "Start from 0 (range(len(names))) or loop over the list directly.",
         ["range(len", "directly", "start at 0", "starts at 0", "for name in names", "for name in"]),
    ],
    explain=(
        "Positions in a list start at 0, so names[0] is \"Ana\". range(1, len(names)) "
        "starts at 1 and never reaches it: the program prints Ben and Cy only. "
        "The correct loop is for name in names: print(name). Nothing crashes, "
        "so the mistake is invisible unless you check the output against the "
        "requirement."
    ),
    criteria="Rejects the code, noticing that the first name is skipped.",
    misconceptions=[
        "Assuming list positions start at 1.",
        "Accepting code that runs without errors as code that is right.",
    ],
    hint="Which positions does range(1, len(names)) give, and which position holds Ana?",
    follow_up="Rewrite the loop so it needs no position at all.",
))
claim('names = ["Ana", "Ben", "Cy"]\nfor i in range(1, len(names)):\n    print(names[i])', "Ben", "Cy")

SRC = code("""
    def has_seven(numbers):
        found = False
        for n in numbers:
            if n == 7:
                found = True
        return found
""")
claim(SRC + "\nprint(has_seven([1, 7, 3]), has_seven([2, 4]))", "True False")
ACTIVITIES.append(mc(
    T, "code-quality-review", "Review the search for a seven", MACRO,
    stem=(
        "An AI generated this function to say whether a list contains the number 7. It "
        "returns the right answer for every list you try. Which review comment is the most "
        "justified?"
    ),
    code=SRC,
    correct=(
        "It is correct, but it keeps looping after finding a 7; returning True straight "
        "away would be simpler and faster on long lists."
    ),
    wrong=[
        "It is incorrect: found is reset to False on every pass.",
        "It is incorrect: a function cannot contain a loop.",
        "It should print the result instead of returning it.",
    ],
    explain=(
        "found is set to False once, before the loop, and only ever changed to "
        "True, so the result is correct. The quality point is efficiency and "
        "clarity: after the first 7 is found the remaining items are checked for "
        "nothing. Returning True inside the loop (and False after it) stops "
        "early. The other comments make false claims about the code."
    ),
    criteria="Confirms correctness first, then identifies the unneeded work after a 7 is found.",
    misconceptions=[
        "Misreading where found is set and thinking it resets each pass.",
        "Confusing returning a value with printing it.",
    ],
    hint="Check carefully where found is set to False, then ask what the loop does after finding a 7.",
    follow_up="Rewrite it with an early return and test it with [], [7] and [1, 7, 3].",
))
