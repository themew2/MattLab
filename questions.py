"""Algebra 1 question generators.

Every generator takes a seeded random.Random and returns a dict. Because the
seed is derived from (user, day, index), the server can regenerate any question
to grade it without storing it or ever sending the answer to the browser early.
The server keys that seed with its secret, so it can't be reproduced from the source.
"""
import math
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


def temperature(rng):
    # C is a multiple of 5, so both temperatures are whole numbers: F = 9k + 32 when C = 5k
    frac = rng.random() < 0.5  # state the formula with 9/5, or with its decimal form 1.8
    if rng.random() < 0.5:
        text, k = rng.choice([
            ("A weather app in Paris shows {C}°C. Use F = {f} to find the temperature in degrees Fahrenheit.",
             rng.randint(-3, 7)),
            ("A European recipe says to bake bread at {C}°C, but Ana's oven is in Fahrenheit. "
             "Using F = {f}, what should she set the oven to?", rng.randint(30, 46)),
            ("A swimming pool is heated to {C}°C. The formula F = {f} converts Celsius to Fahrenheit. "
             "How warm is the pool in degrees Fahrenheit?", rng.randint(5, 6)),
            ("A science class measures a freezer at {C}°C. Use F = {f} to convert it to degrees Fahrenheit.",
             rng.randint(-6, -2)),
        ])
        C, F = 5 * k, 9 * k + 32
        f = "9/5·C + 32" if frac else "1.8C + 32"
        mult = (f"9/5 · {p(C)} = {9 * k} ({C} ÷ 5 = {k}, then × 9 = {9 * k})." if frac
                else f"1.8 × {p(C)} = {9 * k}.")
        steps = [
            f"The formula is F = {f}. You know C, so substitute C = {C}.",
            f"F = {f'9/5 · {p(C)}' if frac else f'1.8 × {p(C)}'} + 32.",
            f"Multiply first: {mult}",
            f"Then add 32: {9 * k} + 32 = {F}.",
            f"Check: ({F} - 32) ÷ 1.8 = {9 * k} ÷ 1.8 = {C}. ✓",
        ]
        return inp("Word problems: temperature", text.format(C=C, f=f), F, steps, unit="degrees Fahrenheit",
                   hint="Type a number. Negative numbers are fine.")
    text, k = rng.choice([
        ("The forecast in Chicago says {F}°F. Use C = {f} to find the temperature in degrees Celsius.",
         rng.randint(-4, 7)),
        ("Leo's thermostat is set to {F}°F. His cousin in Canada asks for it in Celsius. "
         "Using C = {f}, what is it in degrees Celsius?", rng.randint(3, 5)),
        ("An American recipe says to roast vegetables at {F}°F. Using C = {f}, "
         "what temperature is that in degrees Celsius?", rng.randint(36, 46)),
        ("A patient has a fever of {F}°F. The formula C = {f} converts Fahrenheit to Celsius. "
         "What is it in degrees Celsius?", 8),
    ])
    C, F = 5 * k, 9 * k + 32
    f = "5/9·(F - 32)" if frac else "(F - 32) ÷ 1.8"
    div = (f"5/9 · {p(9 * k)} = {C} ({p(9 * k)} ÷ 9 = {k}, then × 5 = {C})." if frac
           else f"{p(9 * k)} ÷ 1.8 = {C}.")
    steps = [
        f"The formula is C = {f}. You know F, so substitute F = {F}.",
        f"C = {f.replace('F', str(F))}.",
        f"Parentheses first: {F} - 32 = {9 * k}.",
        f"Then {div}",
        f"Check: 1.8 × {p(C)} + 32 = {9 * k} + 32 = {F}. ✓",
    ]
    return inp("Word problems: temperature", text.format(F=F, f=f), C, steps, unit="degrees Celsius",
               hint="Type a number. Negative numbers are fine.")


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


# ---------------------------------------------------------------- bonus: geometry
# Identify-the-concept questions with a picture: no calculating. Only used for the bonus question.

FIG_W, FIG_H, FIG_PAD = 260, 190, 30


def _unit(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy) or 1
    return dx / n, dy / n


def _dist(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _xy(p):
    return f"{p[0]:.1f},{p[1]:.1f}"


def _angle_at(v, p1, p2):
    u1, u2 = _unit(v, p1), _unit(v, p2)
    return math.degrees(math.acos(max(-1, min(1, u1[0] * u2[0] + u1[1] * u2[1]))))


def _a(word):
    return "an" if word[0].lower() in "aeiou" else "a"


class Fig:
    """Shapes in model coordinates (y points down), rotated and scaled to fit the picture.
    Marks (ticks, right-angle squares, arcs, arrows) are sized in pixels after fitting."""

    def __init__(self):
        self.items = []

    def add(self, kind, *pts, **kw):
        self.items.append((kind, pts, kw))
        return self

    def svg(self, rot=0.0):
        c, s = math.cos(rot), math.sin(rot)

        def turn(p):
            return p[0] * c - p[1] * s, p[0] * s + p[1] * c

        ext = []
        for kind, pts, kw in self.items:
            ext += [turn(p) for p in pts]
            if kind == "circle":
                cx, cy = turn(pts[0])
                ext += [(cx - kw["r"], cy - kw["r"]), (cx + kw["r"], cy + kw["r"])]
            if kind == "ellipse":  # only used unrotated
                cx, cy = pts[0]
                ext += [(cx - kw["rx"], cy - kw["ry"]), (cx + kw["rx"], cy + kw["ry"])]
        xs, ys = [p[0] for p in ext], [p[1] for p in ext]
        w, h = (max(xs) - min(xs)) or 1, (max(ys) - min(ys)) or 1
        k = min((FIG_W - 2 * FIG_PAD) / w, (FIG_H - 2 * FIG_PAD) / h)
        ox = (FIG_W - w * k) / 2 - min(xs) * k
        oy = (FIG_H - h * k) / 2 - min(ys) * k

        def f(p):
            x, y = turn(p)
            return x * k + ox, y * k + oy

        out = []
        for kind, pts, kw in self.items:
            P = [f(p) for p in pts]
            out.append(getattr(self, "_" + kind)(P, k, **kw))
        return (f'<svg class="geo" viewBox="0 0 {FIG_W} {FIG_H}" role="img" '
                f'aria-label="Figure for the question">{"".join(out)}</svg>')

    # each renderer takes fitted points and the scale
    @staticmethod
    def _poly(P, k, cls="s fill"):
        return f'<polygon class="{cls}" points="{" ".join(_xy(p) for p in P)}"/>'

    @staticmethod
    def _seg(P, k, cls="s"):
        (x1, y1), (x2, y2) = P
        return f'<line class="{cls}" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>'

    @staticmethod
    def _head(tip, frm):
        u = _unit(frm, tip)
        n = (-u[1], u[0])
        a = (tip[0] - u[0] * 10 + n[0] * 5, tip[1] - u[1] * 10 + n[1] * 5)
        b = (tip[0] - u[0] * 10 - n[0] * 5, tip[1] - u[1] * 10 - n[1] * 5)
        return f'<path class="s" d="M{_xy(a)} L{_xy(tip)} L{_xy(b)}"/>'

    def _ray(self, P, k):
        return self._seg(P, k) + self._head(P[1], P[0])

    def _line(self, P, k):
        return self._seg(P, k) + self._head(P[1], P[0]) + self._head(P[0], P[1])

    @staticmethod
    def _ticks(P, k, n=1):
        a, b = P
        u = _unit(a, b)
        nrm = (-u[1], u[0])
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        out = ""
        for i in range(n):
            off = (i - (n - 1) / 2) * 5
            cx, cy = mid[0] + u[0] * off, mid[1] + u[1] * off
            out += Fig._seg([(cx - nrm[0] * 7, cy - nrm[1] * 7), (cx + nrm[0] * 7, cy + nrm[1] * 7)], k, "m")
        return out

    @staticmethod
    def _par(P, k, n=1):
        """Arrow marks in the middle of a side, showing it's parallel to sides with the same marks."""
        a, b = P
        u = _unit(a, b)
        nrm = (-u[1], u[0])
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        out = ""
        for i in range(n):
            off = (i - (n - 1) / 2) * 7
            tip = (mid[0] + u[0] * (off + 4), mid[1] + u[1] * (off + 4))
            l = (tip[0] - u[0] * 8 + nrm[0] * 6, tip[1] - u[1] * 8 + nrm[1] * 6)
            r = (tip[0] - u[0] * 8 - nrm[0] * 6, tip[1] - u[1] * 8 - nrm[1] * 6)
            out += f'<path class="m" d="M{_xy(l)} L{_xy(tip)} L{_xy(r)}"/>'
        return out

    @staticmethod
    def _angle(P, k, label=None, right=False, n=1, r=22, sweep=1):
        v, p1, p2 = P
        u1, u2 = _unit(v, p1), _unit(v, p2)
        out = ""
        if right:
            s = 12
            a = (v[0] + u1[0] * s, v[1] + u1[1] * s)
            b = (a[0] + u2[0] * s, a[1] + u2[1] * s)
            c = (v[0] + u2[0] * s, v[1] + u2[1] * s)
            out += f'<path class="m" d="M{_xy(a)} L{_xy(b)} L{_xy(c)}"/>'
        else:
            cross = u1[0] * u2[1] - u1[1] * u2[0]
            sw = sweep if abs(cross) < 1e-6 else (1 if cross > 0 else 0)
            for i in range(n):
                rr = r + i * 5
                a = (v[0] + u1[0] * rr, v[1] + u1[1] * rr)
                b = (v[0] + u2[0] * rr, v[1] + u2[1] * rr)
                out += f'<path class="m" d="M{_xy(a)} A{rr} {rr} 0 0 {sw} {_xy(b)}"/>'
        if label:
            bx, by = u1[0] + u2[0], u1[1] + u2[1]
            if math.hypot(bx, by) < 1e-6:  # straight angle: label on the arc's side
                bx, by = (-u1[1], u1[0]) if sweep == 1 else (u1[1], -u1[0])
            nb = math.hypot(bx, by)
            deg = _angle_at(v, p1, p2)
            d = r + 16 + max(0, 45 - deg) * 0.5
            x, y = v[0] + bx / nb * d, v[1] + by / nb * d
            out += f'<text class="lbl" x="{x:.1f}" y="{y:.1f}" text-anchor="middle" dominant-baseline="central">{label}</text>'
        return out

    @staticmethod
    def _dot(P, k):
        return f'<circle class="dot" cx="{P[0][0]:.1f}" cy="{P[0][1]:.1f}" r="3.5"/>'

    @staticmethod
    def _circle(P, k, r=1.0):
        return f'<circle class="s fill" cx="{P[0][0]:.1f}" cy="{P[0][1]:.1f}" r="{r * k:.1f}"/>'

    @staticmethod
    def _ellipse(P, k, rx=1.0, ry=0.3, part="full", cls="s"):
        (cx, cy), RX, RY = P[0], rx * k, ry * k
        if part == "full":
            return f'<ellipse class="{cls}" cx="{cx:.1f}" cy="{cy:.1f}" rx="{RX:.1f}" ry="{RY:.1f}"/>'
        sweep = 0 if part == "front" else 1  # front = the lower half, nearer the viewer
        return f'<path class="{cls}" d="M{cx - RX:.1f},{cy:.1f} A{RX:.1f} {RY:.1f} 0 0 {sweep} {cx + RX:.1f},{cy:.1f}"/>'


def _geo(rng, topic, prompt, fig, correct, pool, steps, why, hint):
    others = [c for c in pool if c != correct]
    rng.shuffle(others)
    q = mc(rng, topic, prompt, correct, [(o, why(o)) for o in others[:3]], steps)
    q.update(figure=fig, hint=hint)
    return q


TRI_SIDES = {
    "Equilateral": "An equilateral triangle has all three sides the same length.",
    "Isosceles": "An isosceles triangle has exactly two sides the same length.",
    "Scalene": "A scalene triangle has no sides the same length.",
    "Right": "A right triangle has one 90° angle, marked with a small square.",
}


def triangle_sides(rng):
    kind = rng.choice(["Equilateral", "Isosceles", "Scalene"])
    if kind == "Equilateral":
        A, B, C = (0, 0), (1, 0), (0.5, -math.sqrt(3) / 2)
        marks = [(A, C, 1), (C, B, 1), (A, B, 1)]
        seen = "one tick mark on every side, so all three sides are the same length"
    elif kind == "Isosceles":
        while True:
            w, ht = rng.uniform(0.8, 1.6), rng.uniform(0.6, 1.5)
            if abs(ht - 0.866 * w) > 0.25 and abs(ht - w / 2) > 0.2:
                break
        A, B, C = (0, 0), (w, 0), (w / 2, -ht)
        marks = [(A, C, 1), (C, B, 1)]
        seen = "matching tick marks on two sides, so exactly two sides are the same length"
    else:
        while True:
            A, B, C = (0, 0), (rng.uniform(1.2, 1.8), 0), (rng.uniform(0.1, 0.5), -rng.uniform(0.6, 1.1))
            sides = sorted([_dist(A, B), _dist(B, C), _dist(A, C)])
            angles = [_angle_at(A, B, C), _angle_at(B, C, A), _angle_at(C, A, B)]
            if sides[1] / sides[0] > 1.15 and sides[2] / sides[1] > 1.15 and all(abs(x - 90) > 10 for x in angles):
                break
        marks = [(A, B, 1), (B, C, 2), (C, A, 3)]
        seen = "a different number of tick marks on every side, so no two sides are the same length"
    fig = Fig().add("poly", A, B, C)
    for a, b, n in marks:
        fig.add("ticks", a, b, n=n)

    def why(o):
        if o == "Isosceles" and kind == "Equilateral":
            return ("An equilateral triangle does have two equal sides, but here all three match, so "
                    "equilateral is the better name.")
        if o == "Right":
            return f"{TRI_SIDES[o]} This triangle has no square mark, so it has no 90° angle."
        return f"{TRI_SIDES[o]} That doesn't match the tick marks here."

    steps = ["Tick marks show which sides are the same length: sides with the same number of ticks match.",
             f"This triangle has {seen}.",
             f"That makes it {_a(kind)} {kind.lower()} triangle. {TRI_SIDES[kind]}"]
    return _geo(rng, "Geometry: triangles", "The triangle in the picture is an example of which type of triangle?",
                fig.svg(rng.uniform(0, 2 * math.pi)), kind, list(TRI_SIDES), steps, why,
                "Sides with the same tick marks are the same length.")


TRI_ANGLES = {
    "Acute": "An acute triangle has all three angles smaller than 90°.",
    "Right": "A right triangle has one 90° angle, marked with a small square.",
    "Obtuse": "An obtuse triangle has one angle bigger than 90°.",
    "Equilateral": "An equilateral triangle has three equal sides and three 60° angles.",
}


def triangle_angles(rng):
    kind = rng.choice(["Acute", "Right", "Obtuse"])
    while True:
        if kind == "Acute":
            a, b = rng.randint(45, 80), rng.randint(45, 80)
        elif kind == "Right":
            a, b = 90, rng.randint(25, 65)
        else:
            a = rng.randint(105, 130)
            b = rng.randint(20, 180 - a - 20)
        c = 180 - a - b
        if c >= 20 and (kind != "Acute" or c < 85) and len({a, b, c}) == 3:
            break
    angs = [a, b, c]
    rng.shuffle(angs)
    al, be, ga = (math.radians(x) for x in angs)
    A, B = (0, 0), (1, 0)
    ac = math.sin(be) / math.sin(ga)
    C = (ac * math.cos(al), -ac * math.sin(al))
    fig = Fig().add("poly", A, B, C)
    for v, p1, p2, deg in [(A, B, C, angs[0]), (B, C, A, angs[1]), (C, A, B, angs[2])]:
        # the square marks the right angle; a "90°" label would crowd the small angle beside it
        fig.add("angle", v, p1, p2, label=None if deg == 90 else f"{deg}°", right=deg == 90)
    big = max(angs)
    listed = ", ".join(f"{x}°" for x in angs)

    def why(o):
        if o == "Equilateral":
            return f"{TRI_ANGLES[o]} These angles are {listed}."
        return f"{TRI_ANGLES[o]} This triangle's biggest angle is {big}°."

    seen = {"Acute": f"The biggest angle is {big}°, which is less than 90°, so every angle is acute.",
            "Right": "One angle is exactly 90°, marked with the small square.",
            "Obtuse": f"The biggest angle is {big}°, which is more than 90°."}[kind]
    steps = ["To name a triangle by its angles, look at its biggest angle.", seen,
             f"That makes it {_a(kind)} {kind.lower()} triangle. {TRI_ANGLES[kind]}"]
    return _geo(rng, "Geometry: triangles", "The triangle in the picture is an example of which type of triangle?",
                fig.svg(rng.uniform(-0.5, 0.5)), kind, list(TRI_ANGLES), steps, why, None)


ANGLES = {
    "Acute": "An acute angle is smaller than a right angle (less than 90°).",
    "Right": "A right angle is exactly 90°, like the corner of a square. It's marked with a small square.",
    "Obtuse": "An obtuse angle is bigger than a right angle but smaller than a straight line "
              "(between 90° and 180°).",
    "Straight": "A straight angle is a straight line: exactly 180°.",
}


def angle_types(rng):
    kind = rng.choice(list(ANGLES))
    deg = {"Acute": rng.randint(20, 65), "Right": 90, "Obtuse": rng.randint(115, 160), "Straight": 180}[kind]
    t = math.radians(deg)
    V, P1, P2 = (0, 0), (1.4, 0), (1.4 * math.cos(t), -1.4 * math.sin(t))
    fig = (Fig().add("ray", V, P1).add("ray", V, P2)
           .add("angle", V, P1, P2, right=kind == "Right", r=26, sweep=0).add("dot", V))
    seen = {"Acute": "This angle is narrower than the corner of a square.",
            "Right": "The small square shows this angle is exactly 90°.",
            "Obtuse": "This angle is wider than the corner of a square, but not a straight line.",
            "Straight": "The two sides point in opposite directions, making a straight line."}[kind]
    steps = ["Compare the angle to a right angle, the corner of a square.", seen,
             f"So it's {_a(kind)} {kind.lower()} angle. {ANGLES[kind]}"]
    return _geo(rng, "Geometry: angles", "The angle in the picture is an example of which type of angle?",
                fig.svg(rng.uniform(-0.6, 0.6)), kind, list(ANGLES), steps,
                lambda o: f"{ANGLES[o]} That doesn't match this angle.", "A small square marks a right angle.")


PAIRS = {
    "Complementary": "Complementary angles add up to 90°. Side by side, they make a right angle.",
    "Supplementary": "Supplementary angles add up to 180°. Side by side, they make a straight line.",
    "Vertical": "Vertical angles are across from each other where two lines cross. They're always equal.",
    "Corresponding": "Corresponding angles sit in matching spots where one line crosses two parallel lines.",
}


def angle_pairs(rng):
    kind = rng.choice(["Complementary", "Supplementary", "Vertical"])
    V = (0, 0)

    def at(deg, r=1.4):
        return r * math.cos(math.radians(deg)), -r * math.sin(math.radians(deg))

    fig = Fig()
    if kind == "Complementary":
        a = rng.randint(25, 65)
        fig.add("ray", V, at(0)).add("ray", V, at(a)).add("ray", V, at(90))
        fig.add("angle", V, at(0), at(90), right=True)
        fig.add("angle", V, at(0), at(a), label=f"{a}°", r=30).add("angle", V, at(a), at(90), label=f"{90 - a}°", r=30)
        seen = f"Together, {a}° and {90 - a}° fill the right angle (the small square): they add up to 90°."
    elif kind == "Supplementary":
        a = rng.choice([rng.randint(35, 75), rng.randint(105, 145)])
        fig.add("line", at(180), at(0)).add("ray", V, at(a))
        fig.add("angle", V, at(0), at(a), label=f"{a}°").add("angle", V, at(a), at(180), label=f"{180 - a}°")
        seen = f"Together, {a}° and {180 - a}° make a straight line: they add up to 180°."
    else:
        t = rng.choice([rng.randint(35, 70), rng.randint(110, 145)])
        fig.add("line", at(180), at(0)).add("line", at(t + 180), at(t))
        fig.add("angle", V, at(0), at(t), label="1").add("angle", V, at(180), at(t + 180), label="2")
        seen = "Angles 1 and 2 are across from each other where the two lines cross."
    fig.add("dot", V)

    def why(o):
        if o == "Corresponding":
            return f"{PAIRS[o]} There are no parallel lines in this picture."
        return f"{PAIRS[o]} That's not what the marked angles show."

    steps = ["Look at how the two marked angles sit next to each other.", seen,
             f"That makes them {kind.lower()} angles. {PAIRS[kind]}"]
    return _geo(rng, "Geometry: angle pairs", "The two marked angles are an example of which kind of angle pair?",
                fig.svg(rng.uniform(-0.5, 0.5)), kind, list(PAIRS), steps, why, None)


QUADS = {
    "Square": "A square has four equal sides and four right angles.",
    "Rectangle": "A rectangle has four right angles, with opposite sides equal.",
    "Rhombus": "A rhombus has four equal sides, but its angles don't have to be right angles.",
    "Parallelogram": "A parallelogram has two pairs of parallel sides.",
    "Trapezoid": "A trapezoid has exactly one pair of parallel sides.",
}
QUAD_PARENTS = {"Square": {"Rectangle", "Rhombus", "Parallelogram"}, "Rectangle": {"Parallelogram"},
                "Rhombus": {"Parallelogram"}}


def quadrilaterals(rng):
    kind = rng.choice(list(QUADS))
    fig = Fig()
    if kind in ("Square", "Rectangle"):
        w = 1 if kind == "Square" else rng.uniform(1.6, 2.2)
        A, B, C, D = (0, 0), (w, 0), (w, -1), (0, -1)
        fig.add("poly", A, B, C, D)
        for v, p1, p2 in [(A, B, D), (B, C, A), (C, D, B), (D, A, C)]:
            fig.add("angle", v, p1, p2, right=True)
        long_n = 1
        short_n = 1 if kind == "Square" else 2
        fig.add("ticks", A, B, n=long_n).add("ticks", D, C, n=long_n)
        fig.add("ticks", B, C, n=short_n).add("ticks", A, D, n=short_n)
        seen = ("four right angles and four sides with the same tick mark" if kind == "Square"
                else "four right angles, with opposite sides matching")
    elif kind == "Rhombus":
        t = math.radians(rng.uniform(55, 72))
        A, B, C, D = (0, 0), (1, 0), (1 + math.cos(t), -math.sin(t)), (math.cos(t), -math.sin(t))
        fig.add("poly", A, B, C, D)
        for a, b in [(A, B), (B, C), (C, D), (D, A)]:
            fig.add("ticks", a, b, n=1)
        seen = "four sides with the same tick mark, and no right angles"
    elif kind == "Parallelogram":
        base, t = rng.uniform(1.6, 2.1), math.radians(rng.uniform(55, 72))
        A, B = (0, 0), (base, 0)
        C, D = (base + math.cos(t), -math.sin(t)), (math.cos(t), -math.sin(t))
        fig.add("poly", A, B, C, D)
        fig.add("par", A, B, n=1).add("par", D, C, n=1).add("par", A, D, n=2).add("par", B, C, n=2)
        seen = "two pairs of parallel sides (the arrow marks) and no right angles"
    else:
        w, w2 = rng.uniform(1.8, 2.2), rng.uniform(0.8, 1.2)
        x0 = rng.uniform(0.15, w - w2 - 0.15)
        A, B, C, D = (0, 0), (w, 0), (x0 + w2, -0.9), (x0, -0.9)
        fig.add("poly", A, B, C, D)
        fig.add("par", A, B, n=1).add("par", D, C, n=1)
        seen = "exactly one pair of parallel sides (the arrow marks)"

    def why(o):
        if o in QUAD_PARENTS.get(kind, ()):
            return (f"Every {kind.lower()} is also {_a(o)} {o.lower()}, but {kind.lower()} is the more "
                    f"specific name. {QUADS[kind]}")
        return f"{QUADS[o]} That doesn't match the marks on this shape."

    steps = ["Tick marks show equal sides, arrow marks show parallel sides, and a small square shows a right angle.",
             f"This shape has {seen}.",
             f"The most specific name is {kind.lower()}. {QUADS[kind]}"]
    return _geo(rng, "Geometry: quadrilaterals", "What is the most specific name for the shape in the picture?",
                fig.svg(rng.uniform(-0.45, 0.45)), kind, list(QUADS), steps, why,
                "Tick marks show equal sides, arrow marks show parallel sides, and a small square shows a right angle.")


POLY_NAMES = {3: "Triangle", 4: "Quadrilateral", 5: "Pentagon", 6: "Hexagon", 7: "Heptagon", 8: "Octagon",
              9: "Nonagon", 10: "Decagon"}
POLY_TIPS = {5: "Penta- means five, like the five-sided Pentagon building.", 6: "Hexa- means six.",
             7: "Hepta- means seven.", 8: "Octa- means eight, like an octopus's eight arms.",
             9: "Nona- means nine.", 10: "Deca- means ten, like a decade is ten years."}


def polygons(rng):
    n = rng.randint(5, 10)
    t0 = rng.uniform(0, 2 * math.pi)
    pts = [(math.cos(t0 + 2 * math.pi * i / n), math.sin(t0 + 2 * math.pi * i / n)) for i in range(n)]
    fig = Fig().add("poly", *pts)
    for p in pts:
        fig.add("dot", p)
    name = POLY_NAMES[n]
    near = sorted((k for k in POLY_NAMES if k != n), key=lambda k: (abs(k - n), k))[:3]
    sides = {v: k for k, v in POLY_NAMES.items()}
    steps = [f"Count the sides: this shape has {n}.",
             f"A polygon with {n} sides is called {_a(name)} {name.lower()}. {POLY_TIPS[n]}"]
    return _geo(rng, "Geometry: polygons", "What is the name of the shape in the picture?", fig.svg(), name,
                [name] + [POLY_NAMES[k] for k in near], steps,
                lambda o: f"{_a(o).capitalize()} {o.lower()} has {sides[o]} sides. This shape has {n}.",
                "Count the sides.")


CIRCLE = {
    "Radius": "A radius goes from the center of the circle to its edge.",
    "Diameter": "A diameter goes all the way across the circle, through the center.",
    "Chord": "A chord connects two points on the circle.",
    "Tangent": "A tangent touches the circle at exactly one point, from the outside.",
}


def circle_parts(rng):
    kind = rng.choice(list(CIRCLE))
    t = rng.uniform(0, 2 * math.pi)

    def on(a):
        return math.cos(a), -math.sin(a)

    O = (0, 0)
    fig = Fig().add("circle", O, r=1.0).add("dot", O)
    if kind == "Radius":
        ends = [O, on(t)]
        seen = "It starts at the center dot and stops at the edge of the circle."
    elif kind == "Diameter":
        ends = [on(t), on(t + math.pi)]
        seen = "It goes from one side of the circle to the other, passing through the center dot."
    elif kind == "Chord":
        ends = [on(t), on(t + math.radians(rng.uniform(70, 130)))]
        seen = "It connects two points on the circle, but it doesn't pass through the center."
    else:
        p, d = on(t), (math.sin(t), math.cos(t))
        ends = [(p[0] - d[0] * 0.9, p[1] - d[1] * 0.9), (p[0] + d[0] * 0.9, p[1] + d[1] * 0.9)]
        seen = "It touches the circle at just one point and stays outside it."
    fig.add("seg", *ends, cls="hl")
    for e in ends if kind != "Tangent" else [on(t)]:
        if e != O:
            fig.add("dot", e)

    def why(o):
        if kind == "Diameter" and o == "Chord":
            return ("A diameter is a special chord: it passes through the center, so diameter is the more "
                    "specific name.")
        if kind == "Diameter" and o == "Radius":
            return "A radius stops at the center. This line goes all the way across."
        return f"{CIRCLE[o]} That's not what the highlighted line does."

    steps = ["Find the center dot, then look at where the highlighted line starts and ends.", seen,
             f"So it's {_a(kind)} {kind.lower()}. {CIRCLE[kind]}"]
    return _geo(rng, "Geometry: circles", "What is the most specific name for the highlighted line?", fig.svg(),
                kind, list(CIRCLE), steps, why, "The dot in the middle is the center of the circle.")


LINES = {
    "Parallel": "Parallel lines run side by side and never meet, like train tracks.",
    "Perpendicular": "Perpendicular lines cross at a right angle, marked with a small square.",
    "Intersecting": "Intersecting lines cross each other at a point.",
    "Skew": "Skew lines are in 3D space: they never meet and aren't parallel. Two lines drawn flat on a page "
            "can't be skew.",
}


def lines(rng):
    kind = rng.choice(["Parallel", "Perpendicular", "Intersecting"])
    fig = Fig()
    if kind == "Parallel":
        s1, s2 = rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3)
        a, b, c, d = (-1.4 + s1, -0.5), (1.4 + s1, -0.5), (-1.4 + s2, 0.5), (1.4 + s2, 0.5)
        fig.add("line", a, b).add("line", c, d).add("par", a, b, n=1).add("par", c, d, n=1)
        seen = "The arrow marks show the lines are parallel: they run side by side and never meet."
    else:
        deg = 90 if kind == "Perpendicular" else rng.choice([rng.randint(30, 60), rng.randint(120, 150)])
        t = math.radians(deg)
        u = (1.4 * math.cos(t), -1.4 * math.sin(t))
        fig.add("line", (-1.4, 0), (1.4, 0)).add("line", (-u[0], -u[1]), u)
        if kind == "Perpendicular":
            fig.add("angle", (0, 0), (1.4, 0), u, right=True)
            seen = "The lines cross, and the small square shows they meet at a right angle."
        else:
            seen = "The lines cross at one point, and the angle between them isn't a right angle."

    def why(o):
        if kind == "Perpendicular" and o == "Intersecting":
            return ("These lines do intersect, but they meet at a right angle (the small square), so "
                    "perpendicular is the better word.")
        if o == "Skew":
            return LINES[o]
        return f"{LINES[o]} That doesn't match these lines."

    steps = ["Check whether the lines cross, and if they do, whether there's a right-angle square.", seen,
             f"So they're {kind.lower()} lines. {LINES[kind]}"]
    return _geo(rng, "Geometry: lines", "Which word best describes the two lines in the picture?",
                fig.svg(rng.uniform(0, math.pi)), kind, list(LINES), steps, why,
                "Arrow marks show parallel lines. A small square shows a right angle.")


SOLIDS = {
    "Cube": "A cube has six square faces, and all its edges are the same length.",
    "Rectangular prism": "A rectangular prism has six rectangle faces, like a box.",
    "Triangular prism": "A triangular prism has two triangle ends joined by three rectangles.",
    "Cylinder": "A cylinder has two flat circle ends joined by a curved side, like a can.",
    "Cone": "A cone has one flat circle base and comes to a point.",
    "Sphere": "A sphere is perfectly round, like a ball, with no flat faces.",
    "Square pyramid": "A square pyramid has a square base and four triangle faces that meet at a point.",
}


def _box(fig, w, h, dx, dy):
    F = [(0, 0), (w, 0), (w, h), (0, h)]
    fig.add("seg", (0, h), (dx, h - dy), cls="d").add("seg", (dx, h - dy), (w + dx, h - dy), cls="d")
    fig.add("seg", (dx, h - dy), (dx, -dy), cls="d")
    fig.add("poly", *F, cls="s")
    fig.add("poly", (0, 0), (dx, -dy), (w + dx, -dy), (w, 0), cls="s")
    fig.add("poly", (w, 0), (w + dx, -dy), (w + dx, h - dy), (w, h), cls="s")


def solids(rng):
    kind = rng.choice(list(SOLIDS))
    fig = Fig()
    if kind == "Cube":
        _box(fig, 1, 1, 0.45, 0.35)
        fig.add("ticks", (0, 1), (1, 1)).add("ticks", (0, 0), (0, 1)).add("ticks", (1, 0), (1.45, -0.35))
        seen = "It's a box whose edges all have the same tick mark, so every edge is the same length."
    elif kind == "Rectangular prism":
        _box(fig, rng.uniform(1.7, 2.2), rng.uniform(0.75, 0.95), 0.5, 0.35)
        seen = "It's a box shape: six flat rectangle faces, and the edges aren't all the same length."
    elif kind == "Triangular prism":
        w, h, dx, dy = 1.1, 0.95, 1.1, 0.35
        fig.add("seg", (0, h), (dx, h - dy), cls="d").add("seg", (dx, h - dy), (w + dx, h - dy), cls="d")
        fig.add("seg", (dx, h - dy), (w / 2 + dx, -dy), cls="d")
        fig.add("poly", (0, h), (w, h), (w / 2, 0), cls="s")
        fig.add("seg", (w / 2, 0), (w / 2 + dx, -dy)).add("seg", (w, h), (w + dx, h - dy))
        fig.add("seg", (w / 2 + dx, -dy), (w + dx, h - dy))
        seen = "Both ends are triangles, joined by flat rectangle sides."
    elif kind == "Cylinder":
        rx, ry, h = 0.8, 0.25, 1.4
        fig.add("ellipse", (0, 0), rx=rx, ry=ry)
        fig.add("ellipse", (0, h), rx=rx, ry=ry, part="back", cls="d").add("ellipse", (0, h), rx=rx, ry=ry, part="front")
        fig.add("seg", (-rx, 0), (-rx, h)).add("seg", (rx, 0), (rx, h))
        seen = "It has two flat circle ends joined by a curved side."
    elif kind == "Cone":
        rx, ry = 0.9, 0.28
        fig.add("ellipse", (0, 0), rx=rx, ry=ry, part="back", cls="d").add("ellipse", (0, 0), rx=rx, ry=ry, part="front")
        fig.add("seg", (0, -1.5), (-rx, 0)).add("seg", (0, -1.5), (rx, 0))
        seen = "It has one flat circle base and rises to a single point."
    elif kind == "Sphere":
        fig.add("circle", (0, 0), r=1.0)
        fig.add("ellipse", (0, 0), rx=1.0, ry=0.3, part="back", cls="d").add("ellipse", (0, 0), rx=1.0, ry=0.3, part="front")
        seen = "It's perfectly round all the way around, with no flat faces or edges."
    else:
        FL, FR, BR, BL, T = (-0.9, 0), (0.7, 0), (1.2, -0.4), (-0.4, -0.4), (0.15, -1.5)
        fig.add("seg", FL, BL, cls="d").add("seg", BL, BR, cls="d").add("seg", T, BL, cls="d")
        fig.add("seg", FL, FR).add("seg", FR, BR).add("seg", T, FL).add("seg", T, FR).add("seg", T, BR)
        seen = "It has a square base, and its triangle sides all meet at one point at the top."

    def why(o):
        if kind == "Cube" and o == "Rectangular prism":
            return ("Every cube is a rectangular prism, but here all the edges are the same length, so cube is "
                    "the more specific name.")
        return f"{SOLIDS[o]} That doesn't match this solid."

    steps = ["Look at the shape of the ends or base, and whether the sides are flat or curved. Dashed lines are "
             "edges hidden at the back.", seen, f"So it's {_a(kind)} {kind.lower()}. {SOLIDS[kind]}"]
    return _geo(rng, "Geometry: solids", "What is the name of the solid in the picture?", fig.svg(), kind,
                list(SOLIDS), steps, why, "Dashed lines are edges hidden at the back of the shape.")


GEOMETRY = [triangle_sides, triangle_angles, angle_types, angle_pairs, quadrilaterals, polygons,
            circle_parts, lines, solids]


# ---------------------------------------------------------------- daily rounds

FUNDAMENTALS = [order_of_operations, integers, name_the_rule, like_terms, translate, fractions]
WORD_PROBLEMS = [word_rate, consecutive, distance, temperature]
GENERATORS = [two_step, both_sides, distribute_solve, inequality, slope, line_equation, evaluate,
              simplify, exponents, factoring, system, *WORD_PROBLEMS, *FUNDAMENTALS]
ROUND_SIZE, ROUNDS = 5, 2
BONUS_IDX = ROUND_SIZE * ROUNDS  # the geometry bonus comes after the last round


def _draw(rng, pool, used):
    fresh = [g for g in pool if g not in used] or pool
    g = rng.choice(fresh)
    used.add(g)
    return g


def daily_questions(seed):
    """ROUNDS rounds of ROUND_SIZE questions, then a geometry bonus at BONUS_IDX. Each round has at
    least one fundamentals question and one word problem; no topic repeats within the day while
    unused topics remain."""
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
    bonus = rng.choice(GEOMETRY)(random.Random(f"{seed}:bonus"))
    bonus["category"] = "bonus"
    out.append(bonus)
    _balance_answers(out, random.Random(f"{seed}:slots"))
    return out


def _balance_answers(qs, rng):
    """Deal the right answer's position like a shuffled deck, so each choice slot gets about the same
    share across the day. Shuffling each question on its own can put it first five times in a row."""
    mcs = [q for q in qs if q["kind"] == "mc"]
    deck = [slot for _ in range(-(-len(mcs) // 4)) for slot in range(4)]
    rng.shuffle(deck)
    for q, slot in zip(mcs, deck):
        others = [c for c in q["choices"] if c != q["answer_text"]]
        slot = min(slot, len(others))
        q["choices"] = others[:slot] + [q["answer_text"]] + others[slot:]
        q["answer_index"] = slot


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
