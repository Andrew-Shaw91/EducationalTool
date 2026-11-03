"""Dictionaries: nine more activities (levels 2-6)."""

from . import ATOMS, BLOCKS, MACRO, RELATIONS, ai, claim, code, mc, op

T = "dictionaries"
ACTIVITIES = []

# --- Level 2 ---------------------------------------------------------------------
SRC = code("""
    stock = {"apple": 3, "pear": 5}
    stock["apple"] = stock["apple"] + 2
    stock["pear"] = stock["pear"] - 3
    print(stock["apple"], stock["pear"])
""")
claim(SRC, "5 2")
ACTIVITIES.append(mc(
    T, "tracing", "Update the stock counts", RELATIONS,
    stem="What does this program print?",
    code=SRC,
    correct="5 2",
    wrong=["3 5", "5 5", "2 2"],
    explain=(
        "Each line reads the current value for a key, works out a new one and "
        "stores it back under the same key. apple goes 3 + 2 = 5 and pear goes 5 - 3 "
        "= 2. Reassigning a value never adds a second entry for the same key."
    ),
    criteria="Selects 5 2 and tracks each key's value separately.",
    misconceptions=[
        "Believing a dictionary assignment adds a new entry instead of replacing the value.",
        "Mixing up the values of the two keys.",
    ],
    hint="Keep a small table with one row per key, and update it after each line.",
    follow_up="Add a line that sets \"plum\" to 4 and say what len(stock) is afterwards.",
))

# --- Level 3 ---------------------------------------------------------------------
SRC = code("""
    basket = {"apple": 3, "pear": 2}
    print(basket)
""")
ACTIVITIES.append(op(
    T, "modify-code", "Add a new fruit and count the entries", BLOCKS,
    stem=(
        "Change the program so the basket also contains 4 bananas, and then print how "
        "many different kinds of fruit the basket holds. Describe or write the change."
    ),
    code=SRC,
    concepts=[
        ("Add a key", "A new key \"banana\" is assigned the value 4.",
         ["banana", "4", "new key", "add", "assign", "basket[\"banana\"]", "basket['banana']"]),
        ("Number of entries", "len is used to count the entries.",
         ["len", "length", "count", "number of"]),
        ("Printed after adding", "The count is printed after the banana is added, giving 3.",
         ["print", "after", "3"]),
    ],
    explain=(
        "basket[\"banana\"] = 4 adds a new key with its value. print(len(basket)) "
        "then gives 3: apple, pear and banana. len on a dictionary counts the "
        "keys, not the total of the values (which would be 9). The count must be "
        "taken after the banana is added."
    ),
    criteria="Adds a banana key with value 4 and prints len(basket) afterwards.",
    misconceptions=[
        "Expecting len to give the total quantity, not the number of keys.",
        "Printing the length before adding the new entry.",
    ],
    hint="You need two things: a way to add an entry by key, and a way to count the entries.",
    follow_up="Print the total number of pieces of fruit instead, and say what you would use.",
))
claim(SRC.replace("print(basket)", 'basket["banana"] = 4\nprint(len(basket))\nprint(sum(basket.values()))'), "3", "9")

ACTIVITIES.append(op(
    T, "prompt-construction", "Specify a word counter", MACRO,
    stem=(
        "Do not write the Python. Write a short specification (the kind of prompt you "
        "would give a colleague or a model) that would produce a function meeting the "
        "requirements below. Include the details a generator might guess wrongly."
    ),
    requirements=(
        "Need a function that takes a list of words and returns a dictionary showing how "
        "many times each word appears. Words that differ only in capital letters should "
        "count as the same word. The input list is not changed."
    ),
    concepts=[
        ("Input and output", "States that a list goes in and a dictionary of word counts comes out.",
         ["list", "dictionary", "dict", "returns", "return", "counts"]),
        ("Words are the keys", "Says that each word is a key and its count is the value.",
         ["key", "keys", "value", "values", "word maps", "maps to", "each word"]),
        ("Capitalisation rule", "Says that upper and lower case are treated as the same word.",
         ["case", "lowercase", "lower case", "capital", "capitals", "uppercase", "same word"]),
        ("An example", "Gives a worked example of the expected result.",
         ["example", "for instance", "e.g.", "such as", "{", "=>"]),
    ],
    explain=(
        "A strong specification names the input (a list of words), the output "
        "(a dictionary from word to count), the capitalisation rule (so \"Red\" "
        "and \"red\" add to the same entry) and an example such as [\"Red\", "
        "\"red\", \"blue\"] giving {\"red\": 2, \"blue\": 1}. Saying the input is "
        "not changed removes another common surprise."
    ),
    criteria="States input list, output dictionary of counts, the capitalisation rule, and an example.",
    misconceptions=[
        "Leaving capitalisation unspecified so Red and red are counted apart.",
        "Describing the loop instead of the result the caller needs.",
    ],
    hint="Which details would two different generators answer differently? Say each one explicitly.",
    follow_up="Add a rule to ignore punctuation and say how this changes your example.",
    minutes=5,
))

# --- Level 4 ---------------------------------------------------------------------
SRC = code("""
    counts = {}
    for word in ["red", "blue", "red"]:
        counts[word] = 1
    print(counts)
""")
claim(SRC, "{'red': 1, 'blue': 1}")
ACTIVITIES.append(mc(
    T, "debugging", "The counts that never grow", RELATIONS,
    stem="The program should print {'red': 2, 'blue': 1}, but prints {'red': 1, 'blue': 1}. Identify the bug.",
    code=SRC,
    correct="counts[word] = 1 overwrites the count on every pass, so a repeated word is reset to 1 instead of increased.",
    wrong=[
        "A dictionary cannot hold the same key twice, so the loop skips the second red.",
        "The list must be sorted before it is counted.",
        "counts must start as a list rather than a dictionary.",
    ],
    explain=(
        "The second time \"red\" comes round, counts[\"red\"] is set to 1 again "
        "and the earlier 1 is thrown away. A correct version has to add to what "
        "is already there when the key exists: counts[word] = counts[word] + 1, "
        "with a first-time check or .get(word, 0). The loop does visit the "
        "second red; it just does not accumulate."
    ),
    criteria="Identifies that the assignment overwrites rather than increases the count.",
    misconceptions=[
        "Believing duplicate keys make the loop skip items.",
        "Not realising assignment replaces the previous value.",
    ],
    hint="What is counts[\"red\"] after the first red? What does the third pass do to it?",
    follow_up="Fix it with counts.get(word, 0) and say why the zero is needed.",
))

SRC = code("""
    menu = {"tea": 2, "cake": 4, "soup": 3}
    print(menu["cake"])
""")
claim(SRC, "4")
ACTIVITIES.append(mc(
    T, "misconception-analysis", "Why did the student predict cake?", RELATIONS,
    stem=(
        "A student predicted this program prints cake. It prints 4. Which misconception "
        "best explains the student's prediction?"
    ),
    code=SRC,
    correct="The student thinks the text in square brackets is looked up as a value, when it is the key and the lookup returns the value stored under it.",
    wrong=[
        "The student thinks a dictionary cannot hold numbers.",
        "The student thinks cake is at position 1, so it must be a list.",
        "The student thinks print always shows the key it was given.",
    ],
    explain=(
        "A dictionary maps keys to values. menu[\"cake\"] looks up the key "
        "\"cake\" and returns what is stored there, 4. The student gave back the "
        "key itself, treating the brackets as a way to display the name. "
        "Looking up by key never returns the key."
    ),
    criteria="Identifies that a lookup returns the value stored under the key, not the key.",
    misconceptions=[
        "Believing a lookup returns the key you asked with.",
        "Confusing dictionary keys with list positions.",
    ],
    hint="Which part of menu[\"cake\"] is the key, and what is stored under it?",
    follow_up="Write the line that prints the price of tea and say what the key is.",
))

# --- Level 5 ---------------------------------------------------------------------
SRC = code("""
    prices = {"tea": 2, "cake": 5}
    order = ["tea", "cake", "tea"]
    print(prices["tea"])
""")
ACTIVITIES.append(op(
    T, "extend-code", "Total up an order", MACRO,
    stem=(
        "Extend the program so that it prints the total price of every item in order, "
        "using prices (here 2 + 5 + 2 = 9). Do not type the numbers in."
    ),
    code=SRC,
    concepts=[
        ("Loop over the order", "A for loop visits each item in order, including repeats.",
         ["loop", "for", "each", "every", "iterate"]),
        ("Look up each price", "The price for each item is looked up in prices by its key.",
         ["prices[", "look up", "lookup", "key", "dictionary"]),
        ("Running total", "The prices are added into a total that is printed after the loop.",
         ["total", "sum", "add", "adds", "running", "accumulate"]),
    ],
    explain=(
        "total = 0, then for item in order: total = total + prices[item], then "
        "print(total). tea is looked up twice, so the result is 2 + 5 + 2 = 9. "
        "Because the prices come from the dictionary, changing a price in one "
        "place changes the total everywhere."
    ),
    criteria="Loops over order, looks up each price by key, accumulates a total, and prints it after the loop.",
    misconceptions=[
        "Summing the dictionary's values, which counts each item once and ignores the order.",
        "Typing the prices into the sum.",
    ],
    hint="For each item in the order, where do you find its price, and where does it go?",
    follow_up="Handle an item that is not in prices without crashing, and say what price it should have.",
))
claim(SRC.replace('print(prices["tea"])', 'total = 0\nfor item in order:\n    total = total + prices[item]\nprint(total)'), "9")

SRC = code("""
    voters = {"ana": True, "ben": False}
    name = "cy"
    if name in voters.keys():
        if voters[name] == True:
            print("can vote")
        else:
            print("cannot vote")
    else:
        print("cannot vote")
""")
claim(SRC, "cannot vote")
ACTIVITIES.append(op(
    T, "code-improvement", "Shorten the voter check", MACRO,
    stem=(
        "An AI wrote this to say whether a name is registered and allowed to vote. It "
        "works, but it is longer than it needs to be and has repeated branches. Improve it."
    ),
    code=SRC,
    concepts=[
        ("Test the dictionary directly", "name in voters works without .keys().",
         ["in voters", "without .keys", "no .keys", "directly", "keys()"]),
        ("Combine the checks", "The membership test and the value test are joined into one condition with and.",
         ["and", "combine", "combined", "one condition", "single condition", "together"]),
        ("One repeated branch removed", "The two identical 'cannot vote' branches become a single else.",
         ["else", "repeated", "duplicate", "twice", "one branch", "single branch"]),
    ],
    explain=(
        "if name in voters and voters[name]: print(\"can vote\") else: "
        "print(\"cannot vote\"). The in operator checks keys directly, == True is "
        "unnecessary, and the second check only runs when the first passed, so "
        "a missing key cannot cause an error. Behaviour is unchanged; "
        "the shorter version also states the rule in one place."
    ),
    criteria="Joins the checks with and, drops .keys() and == True, and merges the duplicate branches.",
    misconceptions=[
        "Reversing the order of the and, which can cause a KeyError for a missing name.",
        "Keeping == True on a value that is already True or False.",
    ],
    hint="How many different results are there? Which tests lead to the same one?",
    follow_up="Explain why swapping the two parts of your and could crash for the name \"cy\".",
))
claim(
    'voters = {"ana": True, "ben": False}\nfor name in ["ana", "ben", "cy"]:\n'
    '    if name in voters and voters[name]:\n        print("can vote")\n'
    '    else:\n        print("cannot vote")',
    "can vote", "cannot vote", "cannot vote",
)

# --- Level 6 ---------------------------------------------------------------------
ACTIVITIES.append(ai(
    T, "Will this word counter run?", RELATIONS,
    stem=(
        "A student asked an AI to count the words in a list, using the dictionary counts. The "
        "AI suggested the highlighted loop. Accept or reject the suggestion, then explain "
        "your reasoning."
    ),
    code='counts = {}\nwords = ["red", "blue", "red"]\n# AI suggestion appears below',
    suggestion="for word in words:\n    counts[word] = counts[word] + 1",
    decision="reject",
    concepts=[
        ("Missing key", "counts is empty, so counts[word] looks up a key that does not exist yet.",
         ["missing", "not exist", "does not exist", "empty", "not there", "no key", "first time", "not yet"]),
        ("KeyError", "The program stops with a KeyError on the first word.",
         ["keyerror", "key error", "error", "crash", "crashes", "fail", "fails"]),
        ("The fix", "Start from a default, such as counts.get(word, 0) + 1.",
         ["get", "default", "0", "check", "if word in", "in counts"]),
    ],
    explain=(
        "On the first pass counts is empty, so counts[\"red\"] on the right-hand "
        "side raises KeyError before anything can be assigned. The corrected line "
        "is counts[word] = counts.get(word, 0) + 1 (or an if/else on whether the "
        "word is already a key). The suggestion looks reasonable because it "
        "mirrors how you would update a number you already have."
    ),
    criteria="Rejects the code, saying the key is missing at first and a KeyError will be raised.",
    misconceptions=[
        "Assuming a missing key evaluates to zero.",
        "Accepting the line because the update pattern looks right.",
    ],
    hint="What does counts contain when the loop starts, and what does counts[\"red\"] do then?",
    follow_up="Write the corrected line and say what counts holds at the end.",
))
claim('counts = {}\nfor word in ["red", "blue", "red"]:\n    counts[word] = counts[word] + 1', raises="KeyError")

SRC = code("""
    def price_of(item, prices):
        if item in prices:
            return prices[item]
        return 0

    menu = {"tea": 2, "cake": 5}
    print(price_of("tea", menu), price_of("soup", menu))
""")
claim(SRC, "2 0")
ACTIVITIES.append(mc(
    T, "code-quality-review", "Review the price lookup", MACRO,
    stem=(
        "An AI generated this function to look up the price of an item. Its output for the "
        "example is correct. Which review comment is the most justified?"
    ),
    code=SRC,
    correct=(
        "It avoids a KeyError for unknown items, but returning 0 makes an unknown item look "
        "free, which may hide a mistake; consider whether the caller should be told."
    ),
    wrong=[
        "It is incorrect: in cannot be used on a dictionary.",
        "It is incorrect: a function cannot take a dictionary as a parameter.",
        "It must use a loop to find the key.",
    ],
    explain=(
        "item in prices checks the keys, and a known item returns its price, so "
        "the function is correct for the example. The design question is the "
        "default: 0 means an unknown item is silently free. Depending on the "
        "program, returning None, raising an error or using a clearly named "
        "constant may be safer. The other comments are false claims."
    ),
    criteria="Confirms the function works, then names the risk of 0 as a silent default.",
    misconceptions=[
        "Believing in does not work on dictionaries.",
        "Treating a silent default as always harmless.",
    ],
    hint="Check both calls first. Then ask what the caller sees when an item is unknown.",
    follow_up="Change the function to return None for unknown items and say what the caller must now do.",
))
