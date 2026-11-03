"""Lists: eleven more activities (one at level 1, two each at levels 2-6)."""

from . import ATOMS, BLOCKS, MACRO, RELATIONS, ai, claim, code, mc, op

T = "lists"
ACTIVITIES = []

# --- Level 1 ---------------------------------------------------------------------
ACTIVITIES.append(op(
    T, "define-concept", "Define a list", ATOMS,
    stem="In your own words, what is a list and what is an index?",
    concepts=[
        ("Ordered collection", "A list holds several values in a fixed order under one name.",
         ["collection", "several", "multiple", "many", "values", "items", "ordered", "order", "sequence"]),
        ("Index is a position", "An index is the position of an item in the list.",
         ["position", "place", "location", "number", "address"]),
        ("Counting starts at zero", "The first item is at index 0.",
         ["0", "zero", "starts at 0", "first item"]),
    ],
    explain=(
        "A list stores several values, in order, under a single name, for "
        "example [4, 8, 15]. An index is the position of one item, and counting "
        "starts at 0: in that list index 0 holds 4 and index 2 holds 15."
    ),
    criteria="Says a list is an ordered collection and an index is a position that starts at 0.",
    misconceptions=[
        "Believing the first item of a list is at index 1.",
        "Thinking a list can hold only one value at a time.",
    ],
    hint="Think of a row of numbered boxes. Where does the numbering begin?",
    follow_up="For the list [4, 8, 15], say what is at index 1 and what is at index 3.",
    minutes=2,
))

# --- Level 2 ---------------------------------------------------------------------
SRC = code("""
    colours = ["red", "green", "blue", "pink"]
    print(colours[2])
    print(len(colours))
""")
claim(SRC, "blue", "4")
ACTIVITIES.append(mc(
    T, "tracing", "Index versus length", RELATIONS,
    stem="What does this program print, line by line?",
    code=SRC,
    correct="blue, then 4",
    wrong=["green, then 3", "blue, then 3", "green, then 4"],
    explain=(
        "Indexes start at 0, so index 2 is the THIRD item, \"blue\". len counts "
        "how many items there are: 4. The index of the last item is len - 1 = 3, "
        "so length and last index are different numbers."
    ),
    criteria="Selects blue and 4 and can explain why index 2 is the third item.",
    misconceptions=[
        "Counting indexes from 1 and choosing green.",
        "Mixing up the number of items with the last index.",
    ],
    hint="Write 0, 1, 2, 3 under the four colours, then read off index 2.",
    follow_up="Which index gives \"pink\", and how could you write it without typing the number?",
))

SRC = code("""
    scores = [10, 20, 30]
    scores.append(40)
    scores[0] = 15
    print(scores)
""")
claim(SRC, "[15, 20, 30, 40]")
ACTIVITIES.append(op(
    T, "explain-code", "Add to a list and change an item", BLOCKS,
    stem="Explain in plain English what this code does and what it prints. Name the values, not only the syntax.",
    code=SRC,
    concepts=[
        ("Append adds to the end", "append puts 40 on the end of the list.",
         ["append", "end", "adds", "add", "40", "last"]),
        ("Assignment replaces an item", "scores[0] = 15 replaces the first item (10) with 15.",
         ["replace", "replaces", "changes", "change", "first", "10", "index 0", "15", "overwrite"]),
        ("Output", "The final list [15, 20, 30, 40] is printed.",
         ["[15, 20, 30, 40]", "15, 20, 30, 40", "prints", "print"]),
    ],
    explain=(
        "The list starts as [10, 20, 30]. append(40) adds a new item at the end, "
        "making [10, 20, 30, 40]. scores[0] = 15 then replaces the item at index "
        "0, so the list becomes [15, 20, 30, 40], which print shows. append "
        "grows the list; index assignment changes an item without changing the "
        "length."
    ),
    criteria="Explains append adds to the end, index assignment replaces an item, and gives the final list.",
    misconceptions=[
        "Thinking append puts the new item at the start.",
        "Believing scores[0] = 15 inserts 15 and moves the others along.",
    ],
    hint="Write out the list after each line, not only at the end.",
    follow_up="What would the list be if the last two lines were swapped? Predict, then check.",
))

# --- Level 3 ---------------------------------------------------------------------
SRC = code("""
    days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    print(days[______])
""")
claim('days = ["Mon", "Tue", "Wed", "Thu", "Fri"]\nprint(days[3])\nprint(days[4])\nprint(days[2])', "Thu", "Fri", "Wed")
ACTIVITIES.append(mc(
    T, "code-completion", "Pick the right index", ATOMS,
    stem="Which index completes the blank so the program prints Thu?",
    code=SRC,
    correct="3",
    wrong=["4", "2", "5"],
    explain=(
        "Indexes start at 0: Mon is 0, Tue is 1, Wed is 2 and Thu is 3. Index 4 "
        "gives Fri, 2 gives Wed, and 5 does not exist in a five-item list, so "
        "it would raise an IndexError."
    ),
    criteria="Selects 3 and counts from 0.",
    misconceptions=[
        "Counting positions from 1, which gives 4 for the fourth item.",
        "Not realising that an index past the end causes an error.",
    ],
    hint="Number the items from 0 first, then find Thu.",
    follow_up="Which index gives the last item of this list, and what would it be for a list of any length?",
))

ACTIVITIES.append(op(
    T, "prompt-construction", "Specify a list-averaging function", MACRO,
    stem=(
        "Do not write the Python. Write a short specification (the kind of prompt you "
        "would give a colleague or a model) that would produce a function meeting the "
        "requirements below. Include the edge case."
    ),
    requirements=(
        "Need a function that takes a list of numbers and returns their average. The "
        "average of an empty list is not defined, so the function should say so in a "
        "way the caller can detect, rather than crash with a confusing error."
    ),
    concepts=[
        ("Input and output", "States that a list of numbers goes in and the average is returned.",
         ["list", "numbers", "return", "returns", "average", "mean"]),
        ("Empty list handled", "Says what happens for an empty list.",
         ["empty", "no items", "nothing", "zero items", "len", "length"]),
        ("How the caller can tell", "Names how the problem is signalled, such as returning None or raising a clear error.",
         ["none", "raise", "raises", "error", "exception", "valueerror", "signal"]),
        ("An example", "Gives a worked example of the expected result.",
         ["example", "for instance", "e.g.", "such as", "[2, 4, 6]", "=> 4"]),
    ],
    explain=(
        "A strong specification names the input (a list of numbers), the "
        "output (the average, returned, not printed), the empty-list rule (for "
        "example return None or raise ValueError) and an example such as [2, 4, 6] "
        "giving 4.0. Without the empty-list rule a model may divide by zero "
        "and crash."
    ),
    criteria="States input, returned average, a clear empty-list behaviour, and an example.",
    misconceptions=[
        "Leaving the empty list unspecified so the function crashes.",
        "Describing the code instead of the behaviour the caller needs.",
    ],
    hint="What should happen when there are no numbers? Say it explicitly, as a caller needs to know.",
    follow_up="Add a rule that non-numbers in the list are skipped and say how this changes your example.",
    minutes=5,
))

# --- Level 4 ---------------------------------------------------------------------
SRC = code("""
    nums = [3, 5, 4]
    total = 0
    for i in range(len(nums) - 1):
        total = total + nums[i]
    print(total)
""")
claim(SRC, "8")
ACTIVITIES.append(mc(
    T, "debugging", "The total that misses an item", RELATIONS,
    stem="The program should print 12, the sum of the list, but it prints 8. Identify the bug.",
    code=SRC,
    correct="range(len(nums) - 1) stops one position early, so the last item (4) is never added.",
    wrong=[
        "total must start at 1.",
        "nums[i] should be nums[i + 1].",
        "The loop needs to run twice.",
    ],
    explain=(
        "len(nums) is 3, so range(2) gives the indexes 0 and 1: only 3 and 5 are "
        "added, giving 8. The last index, 2, is never reached. The fix is "
        "range(len(nums)), or better, for n in nums. Starting total at 1 would "
        "give a wrong total, and nums[i + 1] would just skip a different item."
    ),
    criteria="Identifies the range stopping one short and the last item never being added.",
    misconceptions=[
        "Subtracting 1 from the length because the last index is len - 1, without noticing that range already stops early.",
        "Changing the calculation when the loop is what misses the item.",
    ],
    hint="Which index values does range(len(nums) - 1) produce, and which index holds 4?",
    follow_up="Rewrite the loop so it cannot go wrong on the last item.",
))

SRC_A = code("""
    def best(scores):
        top = 0
        for s in scores:
            if s > top:
                top = s
        return top
""")
SRC_B = code("""
    def best(scores):
        top = scores[0]
        for s in scores:
            if s > top:
                top = s
        return top
""")
claim(SRC_A + "\nprint(best([8, 3, 9]), best([-4, -2, -9]))", "9 0")
claim(SRC_B + "\nprint(best([8, 3, 9]), best([-4, -2, -9]))", "9 -2")
ACTIVITIES.append(mc(
    T, "compare-solutions", "Two ways to find the highest score", RELATIONS,
    stem=(
        "Both functions return the highest value in a list.\n\nSolution A:\n" + SRC_A +
        "\n\nSolution B:\n" + SRC_B + "\n\nWhat happens for the list [-4, -2, -9]?"
    ),
    correct="A returns 0, which is not in the list; B returns -2, the real highest value.",
    wrong=[
        "Both return -2.",
        "Both return 0.",
        "A returns -2 and B returns 0.",
    ],
    explain=(
        "A starts top at 0 and only replaces it with a larger value. Every "
        "number here is below 0, so top is never replaced and A returns 0, a "
        "value that is not in the list. B starts from the first item of the "
        "list, so it can only ever hold a real item and returns -2. For lists of "
        "positive numbers the two agree, which is why A can look correct."
    ),
    criteria="Traces [-4, -2, -9] through both and spots A's starting value of 0.",
    misconceptions=[
        "Assuming a starting value of 0 is safe for any list.",
        "Judging two solutions only on the examples where they agree.",
    ],
    hint="Do not compare the layout. Run [-4, -2, -9] through each and write down top after each item.",
    follow_up="Say what B does on an empty list and how you would handle that case.",
))

# --- Level 5 ---------------------------------------------------------------------
SRC = code("""
    names = ["Ana", "Ben", "Cy"]
    found = False
    for name in names:
        if name == "Ben":
            found = True
    print(found)
""")
claim(SRC, "True")
ACTIVITIES.append(op(
    T, "code-improvement", "Use the membership test", MACRO,
    stem=(
        "An AI wrote this to check whether \"Ben\" is in the list. It works, but Python "
        "has a shorter way to ask the question. Improve it."
    ),
    code=SRC,
    concepts=[
        ("Use in", "The in operator tests membership directly.",
         ["in", "membership", "operator", "in names"]),
        ("No loop or flag", "The loop and the found flag are no longer needed.",
         ["no loop", "no flag", "remove", "removes", "without", "unnecessary", "shorter", "one line"]),
        ("Same result", "The result is still True or False and prints the same.",
         ["true", "false", "same", "result", "boolean"]),
    ],
    explain=(
        "print(\"Ben\" in names) prints True, the same result in one line. The in "
        "operator already does the looping and flagging internally. The "
        "improvement does not change what the code says; it just lets the "
        "language do the routine work and makes the intent obvious."
    ),
    criteria="Replaces the loop and flag with an in test and keeps the True/False result.",
    misconceptions=[
        "Writing a loop for something the language provides directly.",
        "Believing in only works on strings.",
    ],
    hint="Is there an operator that asks 'is this item in that list'?",
    follow_up="Change it to print whether \"Dee\" is NOT in the list, using the opposite operator.",
))
claim('names = ["Ana", "Ben", "Cy"]\nprint("Ben" in names)\nprint("Dee" not in names)', "True", "True")

SRC = code("""
    temps = [18, 31, 25, 33, 29]
    count = 0
    print(count)
""")
ACTIVITIES.append(op(
    T, "extend-code", "Count the hot days", MACRO,
    stem=(
        "Extend the program so that count holds the number of days over 30 degrees "
        "(here 2), and prints it."
    ),
    code=SRC,
    concepts=[
        ("Loop over the list", "A for loop visits every temperature.",
         ["loop", "for", "each", "every", "iterate"]),
        ("Test each value", "An if checks whether the temperature is over 30.",
         ["if", "> 30", "over 30", "greater than 30", "above 30", "condition"]),
        ("Update the count", "count is increased by one for each hot day, before the final print.",
         ["count + 1", "count = count", "add one", "increase", "increment", "+= 1", "adds 1"]),
    ],
    explain=(
        "for t in temps: if t > 30: count = count + 1 and then print(count). "
        "31 and 33 are over 30, so the output is 2. The print must come after "
        "the loop, otherwise it would show the count before any day is "
        "checked."
    ),
    criteria="Loops over the list, tests > 30, increases count, and prints after the loop.",
    misconceptions=[
        "Using >= 30 and counting a day at exactly 30.",
        "Printing before the loop has finished.",
    ],
    hint="You need to visit every item, ask a question about it, and keep a running tally.",
    follow_up="Change the program to report the hottest day instead, and say what you start from.",
))
claim(SRC.replace("print(count)", "for t in temps:\n    if t > 30:\n        count = count + 1\nprint(count)"), "2")

# --- Level 6 ---------------------------------------------------------------------
ACTIVITIES.append(ai(
    T, "Does this give a sorted copy?", RELATIONS,
    stem=(
        "A student asked an AI to make ordered a sorted copy of scores. The AI suggested "
        "the highlighted line. Accept or reject the suggestion, then explain your reasoning."
    ),
    code="scores = [30, 10, 20]\n# AI suggestion appears below\nprint(ordered)",
    suggestion="ordered = scores.sort()",
    decision="reject",
    concepts=[
        ("sort returns None", "The sort method sorts the list in place and returns None.",
         ["none", "returns nothing", "no value", "in place", "in-place"]),
        ("What ordered holds", "ordered would be None, so the program prints None.",
         ["ordered is none", "prints none", "none"]),
        ("The fix", "Use sorted(scores) to get a new sorted list.",
         ["sorted(", "sorted", "new list", "copy"]),
    ],
    explain=(
        "list.sort() changes the original list and returns None, so ordered is "
        "None and the program prints None. The original is sorted, but no copy "
        "is made. sorted(scores) returns a new sorted list and leaves scores "
        "untouched. The suggestion looks natural because the method is called "
        "sort and the name is ordered."
    ),
    criteria="Rejects the line and says that sort returns None (it does not produce a copy).",
    misconceptions=[
        "Assuming a method that changes a list also returns the changed list.",
        "Trusting that a line does what its name suggests.",
    ],
    hint="Think about what value the call scores.sort() gives back, then what ordered is set to.",
    follow_up="Write the corrected line and say what scores contains afterwards.",
))
claim("scores = [30, 10, 20]\nordered = scores.sort()\nprint(ordered)\nprint(scores)", "None", "[10, 20, 30]")

ACTIVITIES.append(ai(
    T, "Does this get the last item?", RELATIONS,
    stem=(
        "A student asked an AI to set last to the final item of items, whatever its length. "
        "The AI suggested the highlighted line. Accept or reject the suggestion, then "
        "explain your reasoning."
    ),
    code="items = [4, 8, 15, 16]\n# AI suggestion appears below\nprint(last)",
    suggestion="last = items[len(items) - 1]",
    decision="accept",
    concepts=[
        ("Last index is len minus 1", "Indexes start at 0, so the last one is one less than the length.",
         ["len", "minus 1", "- 1", "length", "last index", "one less"]),
        ("Works for any length", "The expression adapts to the list rather than using a fixed number.",
         ["any length", "whatever", "always", "adapts", "any list", "not fixed", "general"]),
        ("Checked with the example", "With four items it gives index 3, so it prints 16.",
         ["16", "index 3", "3", "example", "trace"]),
    ],
    explain=(
        "len(items) is 4, so len(items) - 1 is 3, the index of 16. The expression "
        "adjusts itself if items gets longer or shorter. (items[-1] is a "
        "shorter equivalent, but the suggestion is correct.) Accepting after "
        "checking is the right decision; the case it fails on is an empty list, "
        "which the requirement does not ask for."
    ),
    criteria="Accepts the line and explains that len minus 1 is the last index.",
    misconceptions=[
        "Assuming the last index equals the length.",
        "Rejecting a correct suggestion without testing it.",
    ],
    hint="Work out len(items) and then the index the expression gives. Which item sits there?",
    follow_up="Write the same thing with a negative index and say what happens on an empty list.",
))
claim("items = [4, 8, 15, 16]\nlast = items[len(items) - 1]\nprint(last)", "16")
