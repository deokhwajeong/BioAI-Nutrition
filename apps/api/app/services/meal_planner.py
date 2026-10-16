"""Weekly meal planner.

Builds a day-by-day plan (breakfast, lunch, dinner, snack) from the built-in food table in
``meal_analyzer.NUTRITION_DB`` so that each day's energy and macronutrients land close to
a nutrient budget, typically the one the pipeline computed.

How it works, in order:

1. Effective targets. Medical constraints on tracked nutrients are applied to the targets
   first and always win: a ``max`` lowers the target and also becomes a hard ceiling on the
   plan; a ``min`` raises the target. This mirrors the calculator's rule that medical limits
   override genetic and other adjustments.
2. Food choice. Each meal slot draws from a fixed food group (for example a main protein, a
   grain, and vegetables for lunch). Foods rotate through the week by a deterministic stride,
   so plans are reproducible and lunch and dinner never share a protein on the same day.
   Excluded foods (allergies, dislikes) are removed before choosing.
3. Portions. Servings move in half steps. Coordinate descent minimises the weighted squared
   relative error of the day's energy, protein, carbohydrate and fat against the targets,
   plus a small term that keeps each meal near its share of the day's energy.
4. Safety repair. If any hard ceiling is still exceeded, the item contributing most to it is
   cut by half a serving (down to zero) until every ceiling holds. This step always runs last.

The food table tracks energy, protein, carbohydrate and fat only. Constraints on other
nutrients (sodium, potassium, ...) cannot be checked against it and are reported in
``notes`` instead of being silently ignored.

The plan is general wellness guidance built from population-level food data. It is not a
clinical diet and must not replace advice from a clinician or dietitian.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .meal_analyzer import NUTRITION_DB

TRACKED = ("kcal", "protein_g", "carbs_g", "fat_g")
_DB_FIELD = {"kcal": "calories", "protein_g": "protein_g", "carbs_g": "carbs_g", "fat_g": "fat_g"}

# Relative weight of each nutrient's error in the portion objective.
# Energy and protein lead; carbohydrate and fat targets often do not add up to the energy
# target exactly (protein is clamped per kg), so they get less weight.
_WEIGHTS = {"kcal": 1.0, "protein_g": 1.0, "carbs_g": 0.25, "fat_g": 0.25}
_MEAL_SHARE_WEIGHT = 0.15

# Portion steps allowed per food group, in servings. Zero lets the optimiser drop an item
# (for example the main protein under a strict protein limit); vegetables and grains keep a
# floor so every meal stays a meal.
_HALVES = (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0)
GROUP_SERVINGS: dict[str, tuple[float, float]] = {
    "breakfast_protein": (0.0, 2.0),
    "breakfast_grain": (0.5, 2.5),
    "protein": (0.0, 2.0),
    "grain": (0.5, 3.0),
    "vegetable": (0.5, 2.0),
    "fruit": (0.0, 2.0),
    "snack": (0.0, 1.5),
    "fat": (0.0, 1.5),
    "oil": (0.0, 1.5),  # tablespoons of cooking oil
}

# Food groups drawn from NUTRITION_DB. Composite dishes and the image analyzer's fallback
# categories are left out so portions stay interpretable.
FOOD_GROUPS: dict[str, tuple[str, ...]] = {
    "breakfast_protein": ("eggs", "greek yogurt", "cottage cheese", "tofu", "milk"),
    "breakfast_grain": ("oatmeal", "bread", "tortilla", "sweet potato"),
    "protein": (
        "chicken breast",
        "salmon",
        "tofu",
        "turkey",
        "lentils",
        "tuna",
        "black beans",
        "shrimp",
        "chickpeas",
        "beef",
    ),
    "grain": ("brown rice", "quinoa", "pasta", "potato", "rice", "sweet potato", "corn"),
    "vegetable": (
        "broccoli",
        "spinach",
        "green beans",
        "carrot",
        "bell pepper",
        "zucchini",
        "asparagus",
        "kale",
        "mushrooms",
        "tomato",
        "cabbage",
    ),
    "fruit": ("apple", "banana", "orange", "blueberries", "strawberries", "mango", "pineapple"),
    "snack": ("almonds", "greek yogurt", "apple", "walnuts", "banana", "peanut butter", "yogurt"),
    "fat": ("avocado", "almonds", "walnuts", "peanut butter"),
    "oil": ("olive oil",),
}

# (slot, share of daily energy, food groups in that meal)
MEAL_SLOTS: tuple[tuple[str, float, tuple[str, ...]], ...] = (
    ("breakfast", 0.25, ("breakfast_protein", "breakfast_grain", "fruit", "fat")),
    ("lunch", 0.35, ("protein", "grain", "vegetable", "vegetable", "oil")),
    ("dinner", 0.30, ("protein", "grain", "vegetable", "fat", "oil")),
    ("snack", 0.10, ("fruit", "snack")),
)

# Co-prime strides so groups rotate at different rates and the week does not repeat.
_STRIDE = {"breakfast": 1, "lunch": 3, "dinner": 5, "snack": 2}

DISCLAIMER = (
    "General wellness meal ideas built from a small food table. Not a clinical diet and not "
    "medical advice; follow your clinician's or dietitian's guidance where it differs."
)


@dataclass
class PlanConstraint:
    nutrient: str
    constraint_type: str  # "max" or "min"; other types are reported, not enforced
    value: float
    reason: str
    severity: str = "warning"


@dataclass
class PlannedItem:
    food: str
    servings: float
    group: str = ""

    def steps(self) -> tuple[float, ...]:
        low, high = GROUP_SERVINGS.get(self.group, (0.5, 2.0))
        return tuple(s for s in _HALVES if low <= s <= high)

    def amount(self, nutrient: str) -> float:
        return NUTRITION_DB[self.food][_DB_FIELD[nutrient]] * self.servings


@dataclass
class PlannedMeal:
    slot: str
    energy_share: float
    items: list[PlannedItem]

    def total(self, nutrient: str) -> float:
        return sum(i.amount(nutrient) for i in self.items)


@dataclass
class PlannedDay:
    day: int
    meals: list[PlannedMeal]

    def total(self, nutrient: str) -> float:
        return sum(m.total(nutrient) for m in self.meals)

    def totals(self) -> dict[str, float]:
        return {n: round(self.total(n), 1) for n in TRACKED}


@dataclass
class MealPlan:
    days: list[PlannedDay]
    requested_targets: dict[str, float]
    effective_targets: dict[str, float]
    ceilings: dict[str, float]
    adjustments: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def default_macro_split(kcal: float) -> dict[str, float]:
    """Carbohydrate and fat from the same 40/30/30 split as ``create_default_targets``."""
    return {"carbs_g": kcal * 0.40 / 4, "fat_g": kcal * 0.30 / 9}


def _apply_constraints(
    targets: dict[str, float], constraints: list[PlanConstraint]
) -> tuple[dict[str, float], dict[str, float], list[str], list[str]]:
    """Medical limits first: lower or raise targets and collect hard ceilings."""
    effective = dict(targets)
    ceilings: dict[str, float] = {}
    adjustments: list[str] = []
    notes: list[str] = []
    # Critical before warning, then the tightest max, so the strictest limit decides.
    order = sorted(constraints, key=lambda c: (c.severity != "critical", c.value))
    for c in order:
        if c.nutrient not in TRACKED:
            notes.append(
                f"{c.nutrient} limit ({c.constraint_type} {c.value:g}, {c.reason}) is not tracked "
                "by the food table, so this plan cannot check it."
            )
            continue
        if c.constraint_type == "max":
            ceilings[c.nutrient] = min(ceilings.get(c.nutrient, c.value), c.value)
            if effective[c.nutrient] > c.value:
                adjustments.append(
                    f"{c.nutrient} target lowered from {effective[c.nutrient]:.0f} to "
                    f"{c.value:g} by a medical limit ({c.reason})"
                )
                effective[c.nutrient] = c.value
        elif c.constraint_type == "min":
            if c.nutrient in ceilings and c.value > ceilings[c.nutrient]:
                notes.append(
                    f"{c.nutrient} minimum {c.value:g} conflicts with a maximum of "
                    f"{ceilings[c.nutrient]:g}; the maximum wins."
                )
                continue
            if effective[c.nutrient] < c.value:
                adjustments.append(
                    f"{c.nutrient} target raised from {effective[c.nutrient]:.0f} to "
                    f"{c.value:g} by a medical minimum ({c.reason})"
                )
                effective[c.nutrient] = c.value
        else:
            notes.append(
                f"{c.nutrient} {c.constraint_type} constraint ({c.reason}) is reported but not "
                "enforced by the planner."
            )
    return effective, ceilings, adjustments, notes


def _balance_energy(
    targets: dict[str, float], ceilings: dict[str, float]
) -> tuple[dict[str, float], str | None]:
    """Rescale carbohydrate and fat so 4 kcal/g protein + 4 carbs + 9 fat equals the energy target.

    Protein targets are clamped per kg and medical limits can lower them, so the three macro
    targets rarely add up to the energy target on their own. Keeping protein fixed and
    sharing the remaining energy between carbohydrate and fat in their requested ratio gives
    the planner one consistent goal. Ceilings on carbohydrate or fat still apply.
    """
    kcal, protein = targets["kcal"], targets["protein_g"]
    carb_kcal, fat_kcal = targets["carbs_g"] * 4, targets["fat_g"] * 9
    remaining = kcal - protein * 4
    if remaining <= 0 or carb_kcal + fat_kcal <= 0:
        return targets, None
    scale = remaining / (carb_kcal + fat_kcal)
    if abs(scale - 1) < 0.02:
        return targets, None
    balanced = dict(targets)
    balanced["carbs_g"] = min(carb_kcal * scale / 4, ceilings.get("carbs_g", float("inf")))
    balanced["fat_g"] = min(fat_kcal * scale / 9, ceilings.get("fat_g", float("inf")))
    note = (
        f"Carbohydrate and fat targets rescaled to {balanced['carbs_g']:.0f} g and "
        f"{balanced['fat_g']:.0f} g so macronutrient energy matches {kcal:.0f} kcal."
    )
    return balanced, note


def _choose_foods(day: int, available: dict[str, list[str]]) -> list[PlannedMeal]:
    meals: list[PlannedMeal] = []
    used_today: set[str] = set()
    for slot, share, groups in MEAL_SLOTS:
        items: list[PlannedItem] = []
        for position, group in enumerate(groups):
            options = available.get(group, [])
            if not options:
                continue
            start = (day * _STRIDE[slot] + position * 2) % len(options)
            # Walk forward to the first food not already on today's menu.
            for k in range(len(options)):
                food = options[(start + k) % len(options)]
                if food not in used_today:
                    break
            else:
                food = options[start]
            used_today.add(food)
            items.append(PlannedItem(food=food, servings=1.0, group=group))
        if items:
            meals.append(PlannedMeal(slot=slot, energy_share=share, items=items))
    return meals


def _objective(
    day: PlannedDay, targets: dict[str, float], ceilings: dict[str, float], mins: dict[str, float]
) -> float:
    cost = 0.0
    totals = {n: day.total(n) for n in TRACKED}
    for n, w in _WEIGHTS.items():
        t = targets.get(n)
        if t and t > 0:
            cost += w * ((totals[n] - t) / t) ** 2
    kcal_target = targets.get("kcal") or 0
    if kcal_target > 0:
        for meal in day.meals:
            share = meal.total("kcal") / kcal_target
            cost += _MEAL_SHARE_WEIGHT * (share - meal.energy_share) ** 2
    for n, ceiling in ceilings.items():
        if totals[n] > ceiling:
            cost += 100.0 * ((totals[n] - ceiling) / max(ceiling, 1.0)) ** 2 + 10.0
    for n, floor in mins.items():
        if totals[n] < floor:
            cost += 5.0 * ((floor - totals[n]) / max(floor, 1.0)) ** 2
    return cost


def _fit_portions(
    day: PlannedDay, targets: dict[str, float], ceilings: dict[str, float], mins: dict[str, float]
) -> None:
    """Local search over half-serving portions: single-item moves, then paired swaps.

    The paired move (one item down half a serving, another up) is what lets the plan trade a
    protein-dense food for an energy-dense, low-protein one under a strict protein limit,
    which single-item moves cannot do without first breaking the limit.
    """
    items = [i for m in day.meals for i in m.items]
    best = _objective(day, targets, ceilings, mins)

    def try_set(changes: list[tuple[PlannedItem, float]]) -> bool:
        nonlocal best
        old = [(item, item.servings) for item, _ in changes]
        for item, value in changes:
            item.servings = value
        cost = _objective(day, targets, ceilings, mins)
        if cost < best - 1e-12:
            best = cost
            return True
        for item, value in old:
            item.servings = value
        return False

    for _ in range(60):
        improved = False
        for item in items:
            for step in item.steps():
                if step != item.servings and try_set([(item, step)]):
                    improved = True
        for down in items:
            for up in items:
                if down is up:
                    continue
                d, u = down.servings - 0.5, up.servings + 0.5
                if d in down.steps() and u in up.steps() and try_set([(down, d), (up, u)]):
                    improved = True
        if not improved:
            break


def _repair_ceilings(day: PlannedDay, ceilings: dict[str, float]) -> None:
    """Hard safety pass: cut portions until every medical ceiling holds."""
    items = [i for m in day.meals for i in m.items]
    for nutrient, ceiling in ceilings.items():
        while day.total(nutrient) > ceiling + 1e-9:
            candidates = [i for i in items if i.servings > 0 and i.amount(nutrient) > 0]
            if not candidates:
                break
            worst = max(candidates, key=lambda i: i.amount(nutrient) / i.servings)
            worst.servings = max(0.0, worst.servings - 0.5)
    for meal in day.meals:
        meal.items = [i for i in meal.items if i.servings > 0]


def build_meal_plan(
    targets: dict[str, float],
    constraints: list[PlanConstraint] | None = None,
    exclude_foods: list[str] | None = None,
    days: int = 7,
) -> MealPlan:
    """Plan ``days`` days of meals against ``targets`` (keys from ``TRACKED``)."""
    if "kcal" not in targets or targets["kcal"] <= 0:
        raise ValueError("targets must include a positive kcal value")
    requested = {**default_macro_split(targets["kcal"]), **targets}
    requested.setdefault("protein_g", targets["kcal"] * 0.30 / 4)
    requested = {n: float(requested[n]) for n in TRACKED}

    effective, ceilings, adjustments, notes = _apply_constraints(requested, constraints or [])
    effective, balance_note = _balance_energy(effective, ceilings)
    if balance_note:
        adjustments.append(balance_note)
    mins = {
        c.nutrient: c.value
        for c in (constraints or [])
        if c.constraint_type == "min"
        and c.nutrient in TRACKED
        and c.value <= ceilings.get(c.nutrient, float("inf"))
    }

    excluded = {f.lower().strip() for f in (exclude_foods or [])}
    available = {
        group: [f for f in foods if f not in excluded and not any(x and x in f for x in excluded)]
        for group, foods in FOOD_GROUPS.items()
    }
    if excluded:
        notes.append(f"Excluded foods: {', '.join(sorted(excluded))}.")

    plan_days: list[PlannedDay] = []
    for d in range(days):
        day = PlannedDay(day=d + 1, meals=_choose_foods(d, available))
        _fit_portions(day, effective, ceilings, mins)
        _repair_ceilings(day, ceilings)  # always last
        plan_days.append(day)

    kcal_goal = effective["kcal"]
    short = [d.day for d in plan_days if d.total("kcal") < 0.9 * kcal_goal]
    if short:
        why = " because of the medical limits above" if ceilings else ""
        notes.append(
            f"Energy is more than 10% below the {kcal_goal:.0f} kcal target on "
            f"{len(short)} of {len(plan_days)} days{why}; the food table has too few foods "
            "that fit. Treat those days as incomplete."
        )

    return MealPlan(
        days=plan_days,
        requested_targets={n: round(v, 1) for n, v in requested.items()},
        effective_targets={n: round(v, 1) for n, v in effective.items()},
        ceilings=ceilings,
        adjustments=adjustments,
        notes=notes,
    )
