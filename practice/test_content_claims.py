"""
Executes the code used in activities and checks the claims their model answers
make (outputs, errors, equivalences). A wrong model answer would teach students
something false, so these claims are verified by running the code, not by eye.

If you change a snippet or explanation in seed_activities.py, update the
matching case here.
"""

import calendar
import contextlib
import io
import sys

from django.test import SimpleTestCase


def run(code):
    out = io.StringIO()
    namespace = {}
    with contextlib.redirect_stdout(out):
        exec(code, namespace)
    return out.getvalue().strip().splitlines(), namespace


class ModelAnswerClaimTests(SimpleTestCase):
    def raises(self, code, exc):
        with self.assertRaises(exc):
            run(code)

    # --- Variables ---------------------------------------------------------
    def test_variables(self):
        pre = "subtotal = 40\ndelivery = 5\n"
        self.assertEqual(run(pre + "total = subtotal + delivery\nprint(total)")[0], ["45"])
        self.assertEqual(
            run(pre + 'total = "subtotal + delivery"\nprint(total)')[0], ["subtotal + delivery"]
        )
        self.raises(pre + 'total = subtotal + "delivery"\nprint(total)', TypeError)
        self.assertEqual(run(pre + "total = subtotal * delivery\nprint(total)")[0], ["200"])
        self.assertEqual(run("a = 5\nb = a\na = 10\nprint(b)")[0], ["5"])
        self.assertEqual(
            run(
                "price = 20\nquantity = 3\ntotal = price * quantity\nprint(total)\n"
                "discount_rate = 0.10\ndiscounted_total = total - total * discount_rate\n"
                "print(discounted_total)"
            )[0],
            ["60", "54.0"],
        )

    # --- Conditionals ------------------------------------------------------
    def test_conditionals(self):
        old = 'age = {a}\nif age {op} 65:\n    print("senior discount")\nelse:\n    print("full price")'
        self.assertEqual(run(old.format(a=65, op=">"))[0], ["full price"])
        self.assertEqual(run(old.format(a=65, op=">="))[0], ["senior discount"])
        for age in (64, 66):  # only the boundary value changes behaviour
            self.assertEqual(run(old.format(a=age, op=">"))[0], run(old.format(a=age, op=">="))[0])

        bad = (
            'def grade(mark):\n    if mark >= 70:\n        return "A"\n    if mark < 70:\n'
            '        if mark >= 60:\n            return "B"\n    if mark < 60:\n        return "C"\n'
        )
        good = (
            'def grade(mark):\n    if mark >= 70:\n        return "A"\n    elif mark >= 60:\n'
            '        return "B"\n    else:\n        return "C"\n'
        )
        old_grade, new_grade = run(bad)[1]["grade"], run(good)[1]["grade"]
        self.assertEqual([old_grade(m) for m in range(101)], [new_grade(m) for m in range(101)])

        leap = run(
            "def is_leap_year(year):\n"
            "    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)\n"
        )[1]["is_leap_year"]
        self.assertTrue(all(leap(y) == calendar.isleap(y) for y in range(1, 3001)))
        self.assertEqual([leap(2024), leap(1900), leap(2000), leap(2023)], [True, False, True, False])
        self.assertNotEqual(leap(2000), 2000 % 4 == 0 and 2000 % 100 != 0)  # follow-up

    # --- Loops -------------------------------------------------------------
    def test_loops(self):
        for args, want in (
            ("1, 6", list("12345")),
            ("1, 5", list("1234")),
            ("5", list("01234")),
            ("6", list("012345")),
        ):
            self.assertEqual(run(f"for i in range({args}):\n    print(i)")[0], want, args)
        self.assertEqual(
            run("for i in range(2, 11, 2):\n    print(i)")[0], ["2", "4", "6", "8", "10"]
        )

        a = "numbers = [4, 7, 1]\ntotal = 0\nfor n in numbers:\n    total = total + n\nprint(total)"
        b = "numbers = [4, 7, 1]\nfor n in numbers:\n    total = 0\n    total = total + n\nprint(total)"
        self.assertEqual(run(a)[0], ["12"])
        self.assertEqual(run(b)[0], ["1"])

        self.assertEqual(
            run(
                "scores = [60, 75, 90]\ntotal = 0\nfor s in scores:\n    total = total + s\n"
                "print(total)\naverage = total / len(scores)\nprint(average)"
            )[0],
            ["225", "75.0"],
        )
        self.raises("scores = []\ntotal = 0\nprint(total / len(scores))", ZeroDivisionError)

    def test_countdown_never_finishes_and_fix_works(self):
        steps = {"n": 0}

        def tracer(frame, event, arg):
            if event == "line" and frame.f_code.co_name == "count_down":
                steps["n"] += 1
                if steps["n"] > 1000:
                    raise TimeoutError
            return tracer

        namespace = {}
        exec('def count_down(n):\n    while n > 0:\n        print(n)\n    print("Liftoff")\n', namespace)
        sys.settrace(tracer)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(TimeoutError):
                    namespace["count_down"](3)
        finally:
            sys.settrace(None)

        fixed = (
            'def count_down(n):\n    while n > 0:\n        print(n)\n        n = n - 1\n'
            '    print("Liftoff")\ncount_down(3)'
        )
        self.assertEqual(run(fixed)[0], ["3", "2", "1", "Liftoff"])

    # --- Functions ---------------------------------------------------------
    def test_functions(self):
        dbl = "def double(n):\n    return n * 2\n\nresult = double(4)\n"
        self.assertEqual(run(dbl + "print(result + 1)")[0], ["9"])
        self.assertEqual(run(dbl + "print(double(double(2)))")[0], ["8"])

        broken = "def average(a, b):\n    print((a + b) / 2)\n\nresult = average(4, 8)\nprint('Average is', result)"
        self.assertEqual(run(broken)[0], ["6.0", "Average is None"])
        self.raises("def average(a, b):\n    print((a + b) / 2)\nprint(average(4, 8) + 1)", TypeError)
        self.assertEqual(
            run("def average(a, b):\n    return (a + b) / 2\nprint(average(4, 8) + 1)")[0], ["7.0"]
        )

        before = (
            "price1 = 20\ntotal1 = price1 + price1 * 0.2\nprint('Total:', total1)\n"
            "price2 = 35\ntotal2 = price2 + price2 * 0.2\nprint('Total:', total2)\n"
            "price3 = 50\ntotal3 = price3 + price3 * 0.2\nprint('Total:', total3)"
        )
        after = (
            "TAX_RATE = 0.2\ndef price_with_tax(price):\n    return price + price * TAX_RATE\n"
            "for price in [20, 35, 50]:\n    print('Total:', price_with_tax(price))"
        )
        self.assertEqual(run(after)[0], run(before)[0])

    # --- Lists -------------------------------------------------------------
    def test_lists(self):
        self.assertEqual(
            run(
                'names = ["Al", "Beatrice", "Cy", "Dmitri"]\nfor name in names:\n'
                "    if len(name) > 3:\n        print(name)"
            )[0],
            ["Beatrice", "Dmitri"],
        )
        self.assertEqual(run("a = [1, 2, 3]\nb = a\nb.append(4)\nprint(a)")[0], ["[1, 2, 3, 4]"])
        self.assertEqual(run("a = [1, 2, 3]\nb = a.copy()\nb.append(4)\nprint(a)")[0], ["[1, 2, 3]"])
        self.assertEqual(
            run(
                "marks = [45, 82, 67, 30, 91]\ncount = 0\npassed = []\nfor m in marks:\n"
                "    if m >= 50:\n        count = count + 1\n        passed.append(m)\n"
                "print(count)\nprint(passed)"
            )[0],
            ["3", "[82, 67, 91]"],
        )
        contains_negative = run(
            "def contains_negative(numbers):\n    found = False\n    for n in numbers:\n"
            "        if n < 0:\n            found = True\n    return found\n"
        )[1]["contains_negative"]
        self.assertEqual(
            [contains_negative([]), contains_negative([3, -1, 2]), contains_negative([1, 2])],
            [False, True, False],
        )

    # --- Dictionaries ------------------------------------------------------
    def test_dictionaries(self):
        self.assertEqual(
            run(
                'counts = {}\nfor word in ["red", "blue", "red", "green", "red"]:\n'
                "    if word in counts:\n        counts[word] = counts[word] + 1\n"
                "    else:\n        counts[word] = 1\nprint(counts)"
            )[0],
            ["{'red': 3, 'blue': 1, 'green': 1}"],
        )
        loop = 'prices = {{"tea": 2, "cake": 4}}\nfor item in prices:\n    print(item, {expr})'
        self.assertEqual(run(loop.format(expr="prices[item]"))[0], ["tea 2", "cake 4"])
        self.raises(loop.format(expr="item[prices]"), TypeError)
        self.raises(loop.format(expr="prices.item"), AttributeError)
        self.assertEqual(
            run('prices = {"tea": 2, "cake": 4}\nfor x in prices.values():\n    print(x)')[0],
            ["2", "4"],
        )

        votes = 'votes = ["yes", "no", "yes"]\ntally = {{}}\nfor v in votes:\n    tally[v] = {expr}\nprint(tally)'
        self.assertEqual(
            run(votes.format(expr="tally.get(v, 0) + 1"))[0], ["{'yes': 2, 'no': 1}"]
        )
        self.raises(votes.format(expr="tally[v] + 1"), KeyError)

        self.assertEqual(
            run(
                "def total_stock(stock):\n    return sum(stock.values())\n"
                "print(total_stock({'apples': 5, 'pears': 2}))\nprint(total_stock({}))"
            )[0],
            ["7", "0"],
        )
        self.raises("print(sum({'apples': 5, 'pears': 2}))", TypeError)


class BlockLevelActivityClaimTests(SimpleTestCase):
    """Claims made by the explain-code items added with the Block Model."""

    def test_function_area_example(self):
        code = "def area(width, height):\n    return width * height\n\nprint(area(3, 4))\nprint(area(5, 2))"
        self.assertEqual(run(code)[0], ["12", "10"])

    def test_dictionary_update_example(self):
        code = 'ages = {"Ada": 36, "Alan": 41}\nages["Ada"] = 37\nprint(ages["Ada"])\nprint(len(ages))'
        self.assertEqual(run(code)[0], ["37", "2"])
        # Follow-up: a new key adds an entry.
        followup = 'ages = {"Ada": 36, "Alan": 41}\nages["Grace"] = 37\nprint(len(ages))'
        self.assertEqual(run(followup)[0], ["3"])