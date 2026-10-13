"""Algebra 1 question generators.

Every generator takes a seeded random.Random and returns a dict. Because the
seed is derived from (user, day, index), the server can regenerate any question
to grade it without storing it or ever sending the answer to the browser early.
The server keys that seed with its secret, so it can't be reproduced from the source.
"""
import random
import re
from fractions import Fraction
from math import gcd

_SUP = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")


def sup(n):
    return str(n).translate(_SUP)


def fnum(v):
    v = Fraction(v)
    return str(v.numerator) if v.denominator == 1 else f"{v.numerator}/{v.denominator}"


def poly(*terms):
    """Format (coef, var) pairs as an expression, e.g. poly((3,'x'),(-5,'')) -> '3x - 5'."""
    out = ""
    for c, var in terms:
        if c == 0:
            continue
        mag = abs(c)
        body = var if (mag == 1 and var) else f"{fnum(mag)}{var}"
        if not out:
            out = ("-" if c < 0 else "") + body
        else:
            out += (" - " if c < 0 else " + ") + body
    return out or "0"


def tail(*terms):
    """Same as poly but formatted to follow another term: ' + 3x - 2'."""
    s = poly(*terms)
    if s == "0":
        return ""
    return " - " + s[1:] if s.startswith("-") else " + " + s


def mono(c, e):
    if e == 0:
        return fnum(c)
    var = "x" if e == 1 else f"x{sup(e)}"
    return poly((c, var))


def p(n):
    return f"({fnum(n)})" if n < 0 else fnum(n)


def nz(rng, lo, hi, exclude=(0,)):
    while True:
        v = rng.randint(lo, hi)
        if v not in exclude:
            return v


def inp(topic, prompt, answer, steps, unit="", hint="Type a number. Fractions like 3/4 are fine."):
    answer = Fraction(answer)
    return {
        "topic": topic, "kind": "input", "prompt": prompt, "answer": answer,
        "answer_text": fnum(answer) + (f" {unit}" if unit else ""), "hint": hint, "steps": steps,
    }


def mc(rng, topic, prompt, correct, distractors, steps):
    """Distractors are choice strings, or (choice, mistake) pairs where mistake explains
    what goes wrong if a player picks that choice."""
    opts, mistakes = [correct], {}
    for d in distractors:
        text, why = d if isinstance(d, tuple) else (d, None)
        if text not in opts:
            opts.append(text)
            if why:
                mistakes[text] = why
        if len(opts) == 4:
            break
    rng.shuffle(opts)
    return {
        "topic": topic, "kind": "mc", "prompt": prompt, "choices": opts,
        "answer_index": opts.index(correct), "answer_text": correct, "steps": steps,
        "mistakes": mistakes,
    }


# ---------------------------------------------------------------- equations

def two_step(rng):
    x = rng.randint(-10, 10)
    a = nz(rng, -9, 9, (0, 1))
    b = nz(rng, -15, 15)
    c = a * x + b
    lhs = poly((a, "x"), (b, ""))
    undo = f"Subtract {b} from both sides" if b > 0 else f"Add {-b} to both sides"
    steps = [
        "Undo the operations around x in reverse order: addition or subtraction first, then multiplication or division.",
        f"Start with {lhs} = {c}.",
        f"{undo}: {poly((a, 'x'))} = {c - b}.",
        f"Divide both sides by {a}: x = {c - b} ÷ {p(a)} = {x}.",
        f"Check it: {a}·{p(x)}{tail((b, ''))} = {a * x}{tail((b, ''))} = {c}. ✓",
    ]
    return inp("Two-step equations", f"Solve for x:\n{lhs} = {c}", x, steps)


def both_sides(rng):
    x = rng.randint(-8, 8)
    a = nz(rng, -9, 9)
    c = nz(rng, -9, 9, (0, a))
    b = rng.randint(-12, 12)
    d = (a - c) * x + b
    k = a - c
    move = (f"Subtract {poly((c, 'x'))} from both sides" if c > 0
            else f"Add {poly((-c, 'x'))} to both sides")
    steps = [
        "Get all the x-terms on one side and all the plain numbers on the other.",
        f"Start with {poly((a, 'x'), (b, ''))} = {poly((c, 'x'), (d, ''))}.",
        f"{move}: {poly((k, 'x'), (b, ''))} = {d}.",
    ]
    if b:
        undo = f"Subtract {b} from both sides" if b > 0 else f"Add {-b} to both sides"
        steps.append(f"{undo}: {poly((k, 'x'))} = {d - b}.")
    if k != 1:
        steps.append(f"Divide both sides by {k}: x = {d - b} ÷ {p(k)} = {x}.")
    steps.append(f"Check it: left side = {a * x + b}, right side = {c * x + d}. They match. ✓")
    return inp("Variables on both sides",
               f"Solve for x:\n{poly((a, 'x'), (b, ''))} = {poly((c, 'x'), (d, ''))}", x, steps)


def distribute_solve(rng):
    x = rng.randint(-9, 9)
    a = nz(rng, -6, 6, (0, 1))
    b = nz(rng, -9, 9)
    c = a * (x + b)
    ab = a * b
    undo = f"Subtract {ab} from both sides" if ab > 0 else f"Add {-ab} to both sides"
    steps = [
        f"The {a} outside the parentheses multiplies everything inside. That's the distributive property.",
        f"Distribute: {a}·x{tail((ab, ''))} = {c}, so {poly((a, 'x'), (ab, ''))} = {c}.",
        f"{undo}: {poly((a, 'x'))} = {c - ab}.",
        f"Divide both sides by {a}: x = {x}.",
        f"Shortcut: you could also divide both sides by {a} first: {poly((1, 'x'), (b, ''))} = {c // a}, then x = {x}.",
    ]
    return inp("Distributive property", f"Solve for x:\n{a}({poly((1, 'x'), (b, ''))}) = {c}", x, steps)


def inequality(rng):
    a = nz(rng, -6, 6, (0, 1, -1)) if rng.random() < 0.7 else rng.choice([-1, 2, 3])
    b = nz(rng, -12, 12)
    k = rng.randint(-8, 8)
    c = a * k + b
    op = rng.choice(["<", ">", "≤", "≥"])
    flip = {"<": ">", ">": "<", "≤": "≥", "≥": "≤"}
    sol_op = flip[op] if a < 0 else op
    correct = f"x {sol_op} {k}"
    distractors = [
        f"x {flip[sol_op]} {k}",
        f"x {sol_op} {-k}" if k else f"x {sol_op} {k + 1}",
        f"x {flip[sol_op]} {-k}" if k else f"x {flip[sol_op]} {k - 1}",
        f"x {sol_op} {fnum(Fraction(c + b, a))}",
    ]
    undo = f"Subtract {b} from both sides" if b > 0 else f"Add {-b} to both sides"
    steps = [
        "Solve it like an equation, with one extra rule: multiplying or dividing by a negative number flips the inequality sign.",
        f"{undo}: {poly((a, 'x'))} {op} {c - b}.",
    ]
    if a < 0:
        steps.append(f"Divide both sides by {a}. It's negative, so {op} flips to {sol_op}: x {sol_op} {k}.")
    else:
        steps.append(f"Divide both sides by {a}. It's positive, so the sign stays {op}: x {sol_op} {k}.")
    test = k + (1 if sol_op in (">", "≥") else -1)
    steps.append(f"Sanity check with x = {test}: {a}·{p(test)}{tail((b, ''))} = {a * test + b}, "
                 f"and {a * test + b} {op} {c} is true. ✓")
    return mc(rng, "Inequalities", f"Solve the inequality:\n{poly((a, 'x'), (b, ''))} {op} {c}",
              correct, distractors, steps)


# ---------------------------------------------------------------- lines

def slope(rng):
    while True:
        x1, x2 = rng.randint(-8, 8), rng.randint(-8, 8)
        if x1 != x2:
            break
    y1, y2 = rng.randint(-9, 9), rng.randint(-9, 9)
    dy, dx = y2 - y1, x2 - x1
    m = Fraction(dy, dx)
    steps = [
        "Slope is rise over run: how much y changes divided by how much x changes.",
        "m = (y₂ − y₁) / (x₂ − x₁)",
        f"m = ({y2} − {p(y1)}) / ({x2} − {p(x1)}) = {dy} / {p(dx)}",
    ]
    steps.append(f"Simplify: m = {fnum(m)}.")
    if m == 0:
        steps.append("A slope of 0 means the line is flat (horizontal).")
    else:
        steps.append(f"Meaning: for every {m.denominator} step{'s' if m.denominator > 1 else ''} right, the line goes "
                     f"{abs(m.numerator)} {'up' if m > 0 else 'down'}.")
    return inp("Slope", f"Find the slope of the line through ({x1}, {y1}) and ({x2}, {y2}).", m, steps)


def line_equation(rng):
    m = nz(rng, -5, 5)
    x1 = nz(rng, -5, 5)
    y1 = rng.randint(-9, 9)
    b = y1 - m * x1
    correct = f"y = {poly((m, 'x'), (b, ''))}"
    distractors = [
        f"y = {poly((m, 'x'), (y1 + m * x1, ''))}",
        f"y = {poly((m, 'x'), (y1, ''))}",
        f"y = {poly((b, 'x'), (m, ''))}",
        f"y = {poly((-m, 'x'), (y1 + m * x1, ''))}",
        f"y = {poly((m, 'x'), (-b, ''))}",
    ]
    steps = [
        "Slope-intercept form is y = mx + b, where m is the slope and b is the y-intercept.",
        f"You know m = {m}, so y = {poly((m, 'x'))} + b. You need b.",
        f"The point ({x1}, {y1}) is on the line, so plug it in: {y1} = {m}·{p(x1)} + b.",
        f"Simplify: {y1} = {m * x1} + b.",
        f"Solve for b: b = {y1} − {p(m * x1)} = {b}.",
        f"Answer: {correct}.",
    ]
    return mc(rng, "Writing linear equations",
              f"Which equation is the line with slope {m} passing through ({x1}, {y1})?",
              correct, distractors, steps)


# ---------------------------------------------------------------- expressions

def evaluate(rng):
    a = nz(rng, -4, 4)
    b = rng.randint(-9, 9)
    c = rng.randint(-9, 9)
    v = nz(rng, -5, 5)
    expr = poly((a, "x²"), (b, "x"), (c, ""))
    result = a * v * v + b * v + c
    steps = [
        f"Replace every x with {p(v)}. Use parentheses so negative signs don't get lost.",
        f"{a}·{p(v)}²" + ((" + " if b > 0 else " - ") + f"{abs(b)}·{p(v)}" if b else "") + tail((c, "")),
        f"Exponents first: {p(v)}² = {v * v}.",
        f"Multiply: {a}·{v * v} = {a * v * v}" + (f", and {b}·{p(v)} = {b * v}." if b else "."),
        f"Add it up: {a * v * v}{tail((b * v, ''))}{tail((c, ''))} = {result}.",
    ]
    return inp("Evaluating expressions", f"Evaluate {expr} when x = {v}.", result, steps)


def simplify(rng):
    a = nz(rng, -5, 5, (0, 1))
    b = nz(rng, -5, 5)
    c = nz(rng, -9, 9)
    d = nz(rng, -9, 9, (0, -a * b))
    e = rng.randint(-9, 9)
    prompt = f"Simplify:\n{a}({poly((b, 'x'), (c, ''))}){tail((d, 'x'), (e, ''))}"
    correct = poly((a * b + d, "x"), (a * c + e, ""))
    distractors = [
        poly((a * b + d, "x"), (c + e, "")),
        poly((b + d, "x"), (a * c + e, "")),
        poly((a * b - d, "x"), (a * c + e, "")),
        poly((a * b + d, "x"), (a * c - e, "")),
        poly((a * b + d, "x"), (-a * c + e, "")),
        poly((a * b + d + 1, "x"), (a * c + e, "")),
        poly((a * b + d, "x"), (a * c + e - 2, "")),
    ]
    steps = [
        f"Distribute the {a} to both terms inside the parentheses.",
        f"{a}·{poly((b, 'x'))} = {poly((a * b, 'x'))} and {a}·{p(c)} = {a * c}.",
        f"Rewrite: {poly((a * b, 'x'), (a * c, ''))}{tail((d, 'x'), (e, ''))}.",
        f"Combine the x-terms: {a * b} + {p(d)} = {a * b + d}, giving {poly((a * b + d, 'x'))}.",
        f"Combine the constants: {a * c} + {p(e)} = {a * c + e}.",
        f"Result: {correct}.",
    ]
    return mc(rng, "Combining like terms", prompt, correct, distractors, steps)


def exponents(rng):
    variant = rng.choice(["product", "power", "quotient"])
    if variant == "product":
        m, n = rng.randint(2, 7), rng.randint(2, 7)
        a, b = rng.randint(2, 6), rng.randint(2, 6)
        prompt = f"Simplify:\n({mono(m, a)})({mono(n, b)})"
        correct = mono(m * n, a + b)
        distractors = [mono(m + n, a + b), mono(m * n, a * b), mono(m + n, a * b), mono(m * n, a + b + 1),
                       mono(m * n + m, a + b), mono(m * n, a + b - 1)]
        steps = [
            "Multiply the numbers in front (coefficients). For matching bases, add the exponents.",
            f"Coefficients: {m}·{n} = {m * n}.",
            f"Exponents: x{sup(a)}·x{sup(b)} = x{sup(a)}⁺{sup(b)} = x{sup(a + b)}. "
            f"(x{sup(a)} is {a} x's multiplied, x{sup(b)} is {b} more — {a + b} total.)",
            f"Result: {correct}.",
        ]
    elif variant == "power":
        a, b = rng.randint(2, 5), rng.randint(2, 4)
        prompt = f"Simplify:\n(x{sup(a)}){sup(b)}"
        correct = mono(1, a * b)
        distractors = [mono(1, a + b), mono(b, a), mono(1, a ** b), mono(b, a * b), mono(1, a * b + 1)]
        steps = [
            "A power raised to a power: multiply the exponents.",
            f"(x{sup(a)}){sup(b)} means x{sup(a)} written {b} times and multiplied together.",
            f"That's {' + '.join([str(a)] * b)} = {a * b} x's in total.",
            f"Result: {correct}.",
        ]
    else:
        n = rng.randint(2, 6)
        m = n * rng.randint(2, 6)
        b = rng.randint(1, 5)
        a = b + rng.randint(2, 6)
        prompt = f"Simplify:\n{mono(m, a)} ÷ {mono(n, b)}"
        correct = mono(m // n, a - b)
        distractors = [mono(m // n, a + b), mono(m - n, a - b), mono(m // n, a * b), mono(m - n, a + b),
                       mono(m * n, a - b), mono(m // n, a - b + 1)]
        steps = [
            "Divide the coefficients. For matching bases, subtract the exponents.",
            f"Coefficients: {m} ÷ {n} = {m // n}.",
            f"Exponents: x{sup(a)} ÷ x{sup(b)} = x{sup(a)}⁻{sup(b)} = x{sup(a - b)}. "
            f"({b} of the x's on top cancel with the {b} on the bottom.)",
            f"Result: {correct}.",
        ]
    return mc(rng, "Exponent rules", prompt, correct, distractors, steps)


def factoring(rng):
    pp, qq = nz(rng, -9, 9), nz(rng, -9, 9)
    pp, qq = max(pp, qq), min(pp, qq)
    b, c = pp + qq, pp * qq

    def binom(r):
        return f"(x {'+' if r > 0 else '-'} {abs(r)})"

    correct = binom(pp) + binom(qq)
    distractors = [binom(-pp) + binom(-qq), binom(pp) + binom(-qq), binom(-pp) + binom(qq)]
    if c not in (0, 1, -1):
        distractors.append(binom(c) + binom(1 if c > 0 else -1))
    distractors.append(binom(pp + 1) + binom(qq - 1) if qq - 1 else binom(pp + 2) + binom(qq - 2))
    pairs = sorted({tuple(sorted((i, c // i), reverse=True))
                    for i in range(-abs(c), abs(c) + 1) if i and c % i == 0}, reverse=True)
    pair_txt = ", ".join(f"{i}·{p(j)} (sum {i + j}){' ← this one' if i + j == b else ''}"
                         for i, j in pairs)
    steps = [
        f"For x² + bx + c, find two numbers that multiply to c = {c} and add to b = {b}.",
        f"Pairs that multiply to {c}: {pair_txt}.",
        f"The numbers are {pp} and {qq}, so the factors are {correct}.",
        f"Check with FOIL: x·x = x², outer + inner = {poly((pp, 'x'))}{tail((qq, 'x'))} = {poly((b, 'x'))}, "
        f"last = {pp}·{p(qq)} = {c}. ✓",
    ]
    return mc(rng, "Factoring quadratics", f"Factor:\n{poly((1, 'x²'), (b, 'x'), (c, ''))}",
              correct, distractors, steps)


def system(rng):
    while True:
        x, y = rng.randint(-6, 6), rng.randint(-6, 6)
        k = rng.choice([1, -1])
        a, b = nz(rng, -5, 5), nz(rng, -5, 5)
        if b - a * k != 0 and x != y:
            break
    s = x + k * y
    c = a * x + b * y
    eq1 = f"{poly((1, 'x'), (k, 'y'))} = {s}"
    eq2 = f"{poly((a, 'x'), (b, 'y'))} = {c}"
    xexpr = poly((s, ""), (-k, "y"))
    coef = b - a * k
    correct = f"({x}, {y})"
    distractors = [f"({y}, {x})", f"({x}, {-y})", f"({-x}, {y})", f"({x + 1}, {y - 1})",
                   f"({-y}, {-x})", f"({x - 2}, {y + 1})"]
    steps = [
        "Use substitution: solve one equation for a variable, then plug it into the other.",
        f"From the first equation: x = {xexpr}.",
        f"Substitute into the second: {a}({xexpr}){tail((b, 'y'))} = {c}.",
        f"Distribute and combine y-terms: {poly((coef, 'y'), (a * s, ''))} = {c}.",
    ]
    if a * s:
        steps.append(f"Move {a * s} to the other side: {poly((coef, 'y'))} = {c - a * s}.")
    if coef != 1:
        steps.append(f"Divide both sides by {coef}: y = {y}.")
    steps += [
        f"Plug y = {y} into x = {xexpr}: x = {x}.",
        f"Solution: {correct}. Check both: {x}{tail((k * y, ''))} = {s} ✓ and "
        f"{a * x}{tail((b * y, ''))} = {c} ✓",
    ]
    return mc(rng, "Systems of equations", f"Solve the system:\n{eq1}\n{eq2}", correct, distractors, steps)


# ---------------------------------------------------------------- word problems

def word_rate(rng):
    templates = [
        ("A gym charges a ${F} sign-up fee plus ${R} per month. So far Jordan has paid ${T} total. "
         "How many months has Jordan been a member?", "months", "m"),
        ("A plumber charges ${F} for the visit plus ${R} per hour of work. The bill was ${T}. "
         "How many hours did the plumber work?", "hours", "h"),
        ("Maya has ${F} saved and adds ${R} every week. After how many weeks will she have exactly ${T}?",
         "weeks", "w"),
        ("A taxi charges ${F} to start the ride plus ${R} per mile. A ride cost ${T}. How many miles was it?",
         "miles", "m"),
        ("A bike rental costs ${F} plus ${R} per hour. Sam's rental cost ${T}. How many hours did Sam ride?",
         "hours", "h"),
    ]
    text, unit, var = rng.choice(templates)
    F, R, n = rng.randint(2, 12) * 5, rng.randint(2, 15), rng.randint(2, 14)
    T = F + R * n
    steps = [
        f"Find the one-time amount and the repeating amount. The ${F} happens once; the ${R} repeats for each of the {unit}.",
        f"Let {var} = number of {unit}. Total = one-time + rate × {var}.",
        f"Equation: {F} + {R}{var} = {T}.",
        f"Subtract {F} from both sides: {R}{var} = {T - F}.",
        f"Divide by {R}: {var} = {n}.",
        f"Check: {F} + {R}·{n} = {F} + {R * n} = {T}. ✓",
    ]
    return inp("Word problems: linear equations", text.format(F=F, R=R, T=T), n, steps, unit=unit,
               hint="Type a number.")


def consecutive(rng):
    even = rng.random() < 0.4
    n = rng.randint(3, 30) * 2 if even else rng.randint(5, 60)
    gap = 2 if even else 1
    S = 3 * n + 3 * gap
    kind = "consecutive even integers" if even else "consecutive integers"
    steps = [
        f"Call the smallest number n. {'Consecutive even numbers are 2 apart' if even else 'Consecutive integers are 1 apart'}, "
        f"so the three numbers are n, n + {gap}, and n + {2 * gap}.",
        f"Their sum: n + (n + {gap}) + (n + {2 * gap}) = {S}.",
        f"Combine like terms: 3n + {3 * gap} = {S}.",
        f"Subtract {3 * gap}: 3n = {S - 3 * gap}.",
        f"Divide by 3: n = {n}.",
        f"The numbers are {n}, {n + gap}, {n + 2 * gap}. Check: they add to {S}. ✓",
    ]
    return inp("Word problems: consecutive integers",
               f"The sum of three {kind} is {S}. What is the smallest of the three?", n, steps,
               hint="Type a whole number.")


def distance(rng):
    r1, r2 = rng.randint(6, 16) * 5, rng.randint(6, 16) * 5
    t = rng.randint(2, 6)
    D = (r1 + r2) * t
    if rng.random() < 0.5:
        text = (f"Two trains leave the same station at the same time, going opposite directions. "
                f"One travels {r1} mph and the other {r2} mph. After how many hours are they {D} miles apart?")
        setup = "They move apart from each other, so their speeds add up."
    else:
        text = (f"Two cars start {D} miles apart and drive toward each other. One goes {r1} mph, "
                f"the other {r2} mph. How many hours until they meet?")
        setup = "They close the gap from both ends, so their speeds add up."
    steps = [
        "Distance = rate × time (d = rt).",
        f"{setup} Combined rate: {r1} + {r2} = {r1 + r2} mph.",
        f"Let t = hours. Equation: {r1 + r2}t = {D}.",
        f"Divide by {r1 + r2}: t = {t}.",
        f"Check: {r1}·{t} + {r2}·{t} = {r1 * t} + {r2 * t} = {D}. ✓",
    ]
    return inp("Word problems: distance and rate", text, t, steps, unit="hours", hint="Type a number.")


# ---------------------------------------------------------------- fundamentals
# Always multiple choice. Each wrong choice carries the mistake behind it, and the app shows the
# explanation as soon as a fundamentals question is answered wrong.

PEMDAS = ("Order of operations: parentheses, exponents, multiplication and division (left to right), "
          "then addition and subtraction (left to right).")


def _near(v):
    """Fallback choices (no specific mistake) for when the real mistakes happen to coincide."""
    v = Fraction(v)
    step = Fraction(1, v.denominator)
    return [(fnum(v + k * step), None) for k in (1, -1, 2, -2)]


def order_of_operations(rng):
    variant = rng.choice(["mult", "paren", "power"])
    if variant == "mult":
        a, b, c = rng.randint(2, 9), rng.randint(2, 9), rng.randint(3, 9)
        d = rng.randint(1, c - 1)
        expr = f"{a} + {b} × {c} - {d}"
        correct = a + b * c - d
        distractors = [
            ((a + b) * c - d, f"This adds {a} + {b} first. Multiplication comes before addition, "
                              f"so {b} × {c} goes first."),
            (a + b * (c - d), f"This subtracts {c} - {d} first. Multiplication comes before subtraction."),
            ((a + b) * (c - d), "This adds and subtracts first and multiplies last. That's backwards: "
                                "multiply first."),
            (a + b * c + d, f"This adds the {d} instead of subtracting it."),
        ]
        steps = [PEMDAS, "There are no parentheses or exponents here.",
                 f"Multiply first: {b} × {c} = {b * c}.",
                 f"That leaves {a} + {b * c} - {d}. Add and subtract left to right: "
                 f"{a + b * c} - {d} = {correct}."]
    elif variant == "paren":
        a, b, c, d = rng.randint(2, 9), rng.randint(1, 9), rng.randint(1, 9), rng.randint(1, 9)
        expr = f"{a} × ({b} + {c}) - {d}"
        correct = a * (b + c) - d
        distractors = [
            (a * b + c - d, f"This skips the parentheses. Work inside them first: {b} + {c} = {b + c}, "
                            f"then multiply."),
            (a * (b + c - d), f"This subtracts {d} inside the parentheses. Only {b} + {c} is in the "
                              f"parentheses, so {d} is subtracted at the end."),
            (a + b + c - d, f"This adds {a} instead of multiplying by it."),
            (a * (b + c) + d, f"This adds the {d} instead of subtracting it."),
        ]
        steps = [PEMDAS, f"Parentheses first: {b} + {c} = {b + c}.",
                 f"Multiply: {a} × {b + c} = {a * (b + c)}.",
                 f"Subtract: {a * (b + c)} - {d} = {correct}."]
    else:
        a, b, c = rng.randint(1, 9), rng.randint(2, 6), rng.randint(2, 5)
        expr = f"{a} + {b} × {c}²"
        correct = a + b * c * c
        distractors = [
            ((a + b) * c * c, f"This adds {a} + {b} first. Exponents and multiplication both come "
                              f"before addition."),
            (a + (b * c) ** 2, f"This multiplies {b} × {c} before squaring. Exponents come before "
                               f"multiplication, so only the {c} is squared."),
            (a + b * c * 2, f"This doubles {c} instead of squaring it. {c}² means {c} × {c} = {c * c}."),
            (a + b * c, f"This leaves out the exponent. {c}² is {c * c}, not {c}."),
            ((a + b * c) ** 2, f"This squares everything. The exponent only applies to the {c}."),
        ]
        steps = [PEMDAS, f"Exponents first: {c}² = {c} × {c} = {c * c}.",
                 f"Multiply: {b} × {c * c} = {b * c * c}.",
                 f"Add: {a} + {b * c * c} = {correct}."]
    return mc(rng, "Order of operations", f"Evaluate:\n{expr}", str(correct),
              [(str(v), why) for v, why in distractors] + _near(correct), steps)


def integers(rng):
    op = rng.choice(["+", "-", "×"])
    while True:
        a, b = nz(rng, -12, 12), nz(rng, -12, 12)
        if (a < 0 or b < 0) and abs(a) != abs(b):
            break
    big, small = max(abs(a), abs(b)), min(abs(a), abs(b))
    if op == "+":
        correct = a + b
        if a < 0 and b < 0:
            sign_rule = "When the signs are the same, add the sizes and keep the sign."
            third = (-(big - small), sign_rule)
            steps = ["Both numbers are negative.", sign_rule,
                     f"{abs(a)} + {abs(b)} = {abs(a) + abs(b)}, and the sign stays negative: {correct}."]
        else:
            sign_rule = ("When the signs are different, subtract the smaller size from the larger "
                         "and keep the sign of the larger.")
            larger = a if abs(a) > abs(b) else b
            third = ((1 if larger > 0 else -1) * (big + small), sign_rule)
            steps = ["One number is negative and one is positive.", sign_rule,
                     f"{big} - {small} = {big - small}. The larger size is {larger}, so the answer is {correct}."]
        distractors = [(-correct, f"Right size, wrong sign. {sign_rule}"),
                       (a - b, f"This subtracts {p(b)} instead of adding it."), third,
                       (correct + (2 if correct > 0 else -2), None)]
    elif op == "-":
        correct = a - b
        distractors = [
            (-correct, "Right size, wrong sign. Rewrite the subtraction as adding the opposite, "
                       "then use the rules for adding."),
            (a + b, f"This adds {p(b)}. Subtracting {p(b)} means adding its opposite, {-b}."),
            ((1 if correct > 0 else -1) * (abs(a) + abs(b)),
             "This adds the sizes. After rewriting as adding the opposite, use the sign rules for adding."),
            (correct + (2 if correct > 0 else -2), None),
        ]
        steps = ["Subtracting a number is the same as adding its opposite.",
                 f"{a} - {p(b)} becomes {a} + {p(-b)}.",
                 f"{a} + {p(-b)} = {correct}."]
    else:
        correct = a * b
        sign_rule = ("Two negatives multiply to a positive." if a < 0 and b < 0
                     else "A negative times a positive is negative.")
        distractors = [(-correct, f"Right size, wrong sign. {sign_rule}"),
                       (a + b, "This adds instead of multiplying."),
                       (a - b, "This subtracts instead of multiplying.")]
        steps = [f"Multiply the sizes: {abs(a)} × {abs(b)} = {abs(correct)}.", sign_rule,
                 f"So {a} × {p(b)} = {correct}."]
    return mc(rng, "Integer operations", f"Evaluate:\n{a} {op} {p(b)}", str(correct),
              [(str(v), why) for v, why in distractors] + _near(correct), steps)


RULES = {
    "Commutative property": "Swapping the order doesn't change the result: a + b = b + a and a · b = b · a.",
    "Associative property": "Regrouping with parentheses doesn't change the result: "
                            "(a + b) + c = a + (b + c).",
    "Distributive property": "A number outside parentheses multiplies every term inside: a(b + c) = ab + ac.",
    "Identity property": "Adding 0 or multiplying by 1 leaves a number unchanged: a + 0 = a and 1 · a = a.",
    "Inverse property": "A number plus its opposite is 0, and a number times its reciprocal is 1: "
                        "a + (-a) = 0 and a · 1/a = 1.",
    "Zero property of multiplication": "Anything multiplied by 0 is 0: 0 · a = 0.",
}
RULE_GROUPS = [["Commutative property", "Associative property", "Distributive property"],
               ["Identity property", "Inverse property", "Zero property of multiplication"]]


def name_the_rule(rng):
    n, m = rng.sample(range(2, 10), 2)
    examples = {
        "Commutative property": [(f"{n} + x = x + {n}", "the two terms swap places"),
                                 (f"{n} · x = x · {n}", "the two factors swap places")],
        "Associative property": [(f"({n} + {m}) + x = {n} + ({m} + x)",
                                  "the terms stay in the same order and only the parentheses move"),
                                 (f"({n} · {m}) · x = {n} · ({m} · x)",
                                  "the factors stay in the same order and only the parentheses move")],
        "Distributive property": [(f"{n}(x + {m}) = {n}x + {n * m}", f"the {n} multiplies both x and {m}"),
                                  (f"{n}x + {n * m} = {n}(x + {m})", f"a {n} is pulled out of both terms")],
        "Identity property": [(f"{n}x + 0 = {n}x", "adding 0 leaves the term unchanged"),
                              (f"1 · {n}x = {n}x", "multiplying by 1 leaves the term unchanged")],
        "Inverse property": [(f"{n} + (-{n}) = 0", f"{n} plus its opposite gives 0"),
                             (f"{n} · 1/{n} = 1", f"{n} times its reciprocal gives 1")],
        "Zero property of multiplication": [(f"0 · {n}x = 0", "multiplying by 0 gives 0")],
    }
    name = rng.choice(list(RULES))
    eq, how = rng.choice(examples[name])
    same = [r for g in RULE_GROUPS if name in g for r in g if r != name]
    other = [r for g in RULE_GROUPS if name not in g for r in g]
    picks = rng.sample(same, len(same)) + [rng.choice(other)]
    distractors = [(r, f"The {r.lower()} doesn't fit here. {RULES[r]}") for r in picks]
    steps = [f"Compare the two sides: {how}.",
             f"That's the {name.lower()}. {RULES[name]}"]
    return mc(rng, "Properties of numbers",
              f"____ is the name of the fundamental that explains the equation below:\n{eq}",
              name, distractors, steps)


def like_terms(rng):
    v, w = rng.sample(["x", "y", "n"], 2)
    e = rng.choice([1, 2, 3])
    var = v if e == 1 else f"{v}{sup(e)}"
    higher = f"{v}{sup(e + 1)}"
    wvar = w if e == 1 else f"{w}{sup(e)}"
    c1 = nz(rng, -9, 9)
    c2 = nz(rng, -9, 9, (0, c1))
    vw = "".join(sorted(v + w))
    t1, t2 = poly((c1, var)), poly((c2, var))
    correct = f"{t1} and {t2}"
    distractors = [
        (f"{t1} and {poly((c1, higher))}", f"Same number in front, but {var} and {higher} have different "
                                            f"exponents. The variable part decides it, not the number in front."),
        (f"{t1} and {poly((c1, wvar))}", f"{var} and {wvar} use different letters, so they aren't like terms."),
        (f"{poly((c1, vw))} and {poly((c1, v))}", f"{vw} includes {w} but {v} doesn't, so they aren't "
                                                 f"like terms."),
    ]
    steps = ["Like terms have exactly the same variable part: the same letters raised to the same powers. "
             "The numbers in front can be anything.",
             f"{t1} and {t2} both have {var}, so they're like terms.",
             f"That's why they can be combined: {t1}{tail((c2, var))} = {poly((c1 + c2, var))}."]
    return mc(rng, "Like terms", "Which pair are like terms?", correct, distractors, steps)


def translate(rng):
    k, m = rng.sample(range(2, 10), 2)
    templates = [
        (f"{k} less than twice a number n", f"2n - {k}",
         [(f"{k} - 2n", f"\"Less than\" flips the order: {k} less than 2n starts with 2n and takes {k} away."),
          (f"2(n - {k})", f"Only n is doubled. The {k} is subtracted after doubling."),
          (f"2n + {k}", "\"Less than\" means subtract.")],
         [f"\"twice a number n\" is 2n.", f"\"{k} less than\" that means take {k} away from it: 2n - {k}."]),
        (f"the product of {k} and a number n, increased by {m}", f"{k}n + {m}",
         [(f"{k}(n + {m})", f"\"Increased by {m}\" is added after the product, not inside it."),
          (f"{k} + n + {m}", "\"Product\" means multiply."),
          (f"{k}n - {m}", "\"Increased by\" means add.")],
         [f"\"the product of {k} and n\" is {k}n.", f"\"increased by {m}\" adds {m}: {k}n + {m}."]),
        (f"{k} times the sum of a number n and {m}", f"{k}(n + {m})",
         [(f"{k}n + {m}", "The sum has to be found first, so it goes in parentheses."),
          (f"{k} + n + {m}", "\"Times\" means multiply."),
          (f"{k}(n - {m})", "\"Sum\" means add.")],
         [f"\"the sum of n and {m}\" is n + {m}.", f"\"{k} times\" that whole sum needs parentheses: {k}(n + {m})."]),
        (f"a number n divided by {k}, minus {m}", f"n/{k} - {m}",
         [(f"{k}/n - {m}", f"Order matters in division: n is divided by {k}, so n goes on top."),
          (f"n/({k} - {m})", f"The {m} is subtracted after dividing, not from the {k}."),
          (f"n/{k} + {m}", "\"Minus\" means subtract.")],
         [f"\"n divided by {k}\" is n/{k}.", f"\"minus {m}\" subtracts {m} from that: n/{k} - {m}."]),
        (f"the difference of a number n and {k}, squared", f"(n - {k})²",
         [(f"n - {k}²", "\"Squared\" applies to the whole difference, so it needs parentheses."),
          (f"n² - {k}²", "Squaring a difference isn't the same as squaring each part."),
          (f"({k} - n)²", f"\"The difference of n and {k}\" is n - {k}, in that order.")],
         [f"\"the difference of n and {k}\" is n - {k}.",
          f"\"squared\" applies to the whole difference: (n - {k})²."]),
    ]
    text, correct, distractors, pieces = rng.choice(templates)
    steps = ["Translate one phrase at a time.", *pieces, f"So \"{text}\" is {correct}."]
    return mc(rng, "Translating words to expressions", f"Which expression means \"{text}\"?",
              correct, distractors, steps)


def fractions(rng):
    op = rng.choice(["+", "×", "÷"])
    while True:
        b, d = rng.sample(range(2, 10), 2)
        a, c = rng.randint(1, b - 1), rng.randint(1, d - 1)
        if gcd(a, b) == 1 and gcd(c, d) == 1:
            break
    A, C = Fraction(a, b), Fraction(c, d)
    if op == "+":
        correct = A + C
        L = b * d // gcd(b, d)
        distractors = [
            (Fraction(a + c, b + d), "Fractions can't be added straight across. Find a common "
                                     "denominator first."),
            (Fraction(a + c, L), f"{L} is the right common denominator, but the tops have to be "
                                 f"rescaled too before adding."),
            (A * C, "That multiplies the fractions. To add them, use a common denominator."),
            (Fraction(a * d + c * b, b + d), f"The tops were rescaled, but the bottoms were added. "
                                             f"The bottom stays the common denominator."),
        ]
        steps = [f"To add fractions, they need the same denominator. The smallest one that works is {L}.",
                 f"{a}/{b} = {a * L // b}/{L} and {c}/{d} = {c * L // d}/{L}.",
                 f"Add the tops: {a * L // b} + {c * L // d} = {a * L // b + c * L // d}, giving "
                 f"{a * L // b + c * L // d}/{L}."]
        if fnum(correct) != f"{a * L // b + c * L // d}/{L}":
            steps.append(f"Simplify: {fnum(correct)}.")
    elif op == "×":
        correct = A * C
        distractors = [
            (Fraction(a + c, b + d), "That adds tops and bottoms. To multiply, multiply the tops and "
                                     "multiply the bottoms."),
            (Fraction(a * d, b * c), "That flips the second fraction. Flipping is only for dividing."),
            (A + C, "That adds the fractions instead of multiplying them."),
            (Fraction(a * c, b + d), "Multiply the bottoms too, don't add them."),
        ]
        steps = ["To multiply fractions, multiply the tops and multiply the bottoms.",
                 f"{a} × {c} = {a * c} and {b} × {d} = {b * d}, giving {a * c}/{b * d}."]
        if fnum(correct) != f"{a * c}/{b * d}":
            steps.append(f"Simplify: {fnum(correct)}.")
    else:
        correct = A / C
        distractors = [
            (A * C, "That multiplies without flipping. To divide, flip the second fraction, then multiply."),
            (C / A, "That flips the first fraction. Keep the first, flip the second."),
            (A + C, "That adds the fractions. To divide, flip the second fraction, then multiply."),
        ]
        steps = ["To divide by a fraction, multiply by its reciprocal: keep the first, flip the second.",
                 f"{a}/{b} ÷ {c}/{d} becomes {a}/{b} × {d}/{c}.",
                 f"Multiply: {a * d}/{b * c}."]
        if fnum(correct) != f"{a * d}/{b * c}":
            steps.append(f"Simplify: {fnum(correct)}.")
    return mc(rng, "Fraction operations", f"Evaluate:\n{a}/{b} {op} {c}/{d}", fnum(correct),
              [(fnum(v), why) for v, why in distractors] + _near(correct), steps)


# ---------------------------------------------------------------- daily rounds

FUNDAMENTALS = [order_of_operations, integers, name_the_rule, like_terms, translate, fractions]
WORD_PROBLEMS = [word_rate, consecutive, distance]
GENERATORS = [two_step, both_sides, distribute_solve, inequality, slope, line_equation, evaluate,
              simplify, exponents, factoring, system, *WORD_PROBLEMS, *FUNDAMENTALS]
ROUND_SIZE, ROUNDS = 5, 2


def _draw(rng, pool, used):
    fresh = [g for g in pool if g not in used] or pool
    g = rng.choice(fresh)
    used.add(g)
    return g


def daily_questions(seed):
    """ROUNDS rounds of ROUND_SIZE questions. Each round has at least one fundamentals question and
    one word problem; no topic repeats within the day while unused topics remain."""
    rng = random.Random(seed)
    used, plan = set(), []
    # reserve every round's required topics first so earlier fill picks can't use them up
    rounds = [[_draw(rng, FUNDAMENTALS, used), _draw(rng, WORD_PROBLEMS, used)] for _ in range(ROUNDS)]
    for picks in rounds:
        while len(picks) < ROUND_SIZE:
            picks.append(_draw(rng, GENERATORS, used))
        rng.shuffle(picks)
        plan += picks
    out = []
    for i, g in enumerate(plan):
        q = g(random.Random(f"{seed}:{i}"))
        q["category"] = "fundamentals" if g in FUNDAMENTALS else "word" if g in WORD_PROBLEMS else "core"
        out.append(q)
    return out


# ---------------------------------------------------------------- grading

_NUM = re.compile(r"(-\s*)?(\d+\s+\d+\s*/\s*\d+|\d+(?:\.\d+)?(?:\s*/\s*-?\d+(?:\.\d+)?)?|\.\d+)")
_MIXED = re.compile(r"\d+\s+\d+\s*/\s*\d+")


def _fraction(txt):
    txt = txt.replace(" ", "")
    if "/" in txt:
        num, den = txt.split("/")
        return Fraction(num) / Fraction(den)
    return Fraction(txt)


def parse_number(s):
    """First number in the text: 7, -2.5, .5, 3/4, mixed numbers like 1 1/2, '- 4', 'x = 4', '$12'."""
    s = (s or "").replace(",", "").replace("−", "-").replace("$", "")
    m = _NUM.search(s)
    if not m:
        return None
    sign, body = (-1 if m.group(1) else 1), m.group(2)
    try:
        if _MIXED.fullmatch(body):
            whole, frac = body.split(None, 1)
            return sign * (Fraction(whole) + _fraction(frac))
        return sign * _fraction(body)
    except (ValueError, ZeroDivisionError):
        return None


def _terminates(f):
    d = f.denominator
    for prime in (2, 5):
        while d % prime == 0:
            d //= prime
    return d == 1


def check_input(q, given):
    val = parse_number(given)
    if val is None:
        return None
    if val == q["answer"]:
        return True
    # allow rounded decimals only where an exact decimal doesn't exist, e.g. 0.67 for 2/3
    return "." in given and not _terminates(q["answer"]) and abs(val - q["answer"]) <= Fraction(1, 100)
