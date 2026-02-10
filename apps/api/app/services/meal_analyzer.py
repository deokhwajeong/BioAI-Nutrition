from ..schemas.user_input import AnalyzeMealRequest, AnalyzeMealResponse, FoodItem, FoodNutrition

# Nutritional database (per typical serving)
# Keys are lowercased for matching.  Values are per-serving estimates.
NUTRITION_DB: dict[str, dict[str, float]] = {
    # ── Fruits ──────────────────────────────────────
    "apple":           {"calories": 95,  "protein_g": 0.5,  "carbs_g": 25,   "fat_g": 0.3},
    "banana":          {"calories": 105, "protein_g": 1.3,  "carbs_g": 27,   "fat_g": 0.4},
    "orange":          {"calories": 62,  "protein_g": 1.2,  "carbs_g": 15.4, "fat_g": 0.2},
    "grapes":          {"calories": 69,  "protein_g": 0.7,  "carbs_g": 18,   "fat_g": 0.2},
    "strawberries":    {"calories": 49,  "protein_g": 1.0,  "carbs_g": 12,   "fat_g": 0.5},
    "blueberries":     {"calories": 57,  "protein_g": 0.7,  "carbs_g": 14.5, "fat_g": 0.3},
    "mango":           {"calories": 99,  "protein_g": 1.4,  "carbs_g": 25,   "fat_g": 0.6},
    "pineapple":       {"calories": 83,  "protein_g": 0.9,  "carbs_g": 22,   "fat_g": 0.2},
    "watermelon":      {"calories": 46,  "protein_g": 0.9,  "carbs_g": 11.5, "fat_g": 0.2},
    "avocado":         {"calories": 240, "protein_g": 3.0,  "carbs_g": 13,   "fat_g": 22},

    # ── Proteins ────────────────────────────────────
    "chicken breast":  {"calories": 165, "protein_g": 31,   "carbs_g": 0,    "fat_g": 3.6},
    "chicken":         {"calories": 239, "protein_g": 27,   "carbs_g": 0,    "fat_g": 14},
    "salmon":          {"calories": 206, "protein_g": 22,   "carbs_g": 0,    "fat_g": 12},
    "tuna":            {"calories": 132, "protein_g": 28,   "carbs_g": 0,    "fat_g": 1.0},
    "shrimp":          {"calories": 85,  "protein_g": 20,   "carbs_g": 0,    "fat_g": 0.5},
    "beef":            {"calories": 250, "protein_g": 26,   "carbs_g": 0,    "fat_g": 15},
    "steak":           {"calories": 271, "protein_g": 26,   "carbs_g": 0,    "fat_g": 18},
    "pork":            {"calories": 242, "protein_g": 27,   "carbs_g": 0,    "fat_g": 14},
    "turkey":          {"calories": 135, "protein_g": 30,   "carbs_g": 0,    "fat_g": 1.0},
    "tofu":            {"calories": 76,  "protein_g": 8,    "carbs_g": 1.9,  "fat_g": 4.8},
    "egg":             {"calories": 70,  "protein_g": 6,    "carbs_g": 0.6,  "fat_g": 5},
    "eggs":            {"calories": 140, "protein_g": 12,   "carbs_g": 1.2,  "fat_g": 10},

    # ── Grains & Starches ──────────────────────────
    "rice":            {"calories": 130, "protein_g": 2.7,  "carbs_g": 28,   "fat_g": 0.3},
    "steamed rice":    {"calories": 130, "protein_g": 2.7,  "carbs_g": 28,   "fat_g": 0.3},
    "brown rice":      {"calories": 216, "protein_g": 5,    "carbs_g": 45,   "fat_g": 1.8},
    "bread":           {"calories": 79,  "protein_g": 2.7,  "carbs_g": 14.7, "fat_g": 1},
    "pasta":           {"calories": 220, "protein_g": 8,    "carbs_g": 43,   "fat_g": 1.3},
    "oatmeal":         {"calories": 158, "protein_g": 6,    "carbs_g": 27,   "fat_g": 3.2},
    "potato":          {"calories": 77,  "protein_g": 2,    "carbs_g": 17,   "fat_g": 0.1},
    "sweet potato":    {"calories": 86,  "protein_g": 1.6,  "carbs_g": 20,   "fat_g": 0.1},
    "quinoa":          {"calories": 222, "protein_g": 8,    "carbs_g": 39,   "fat_g": 3.6},
    "corn":            {"calories": 96,  "protein_g": 3.4,  "carbs_g": 21,   "fat_g": 1.5},
    "tortilla":        {"calories": 150, "protein_g": 4,    "carbs_g": 26,   "fat_g": 3.5},

    # ── Vegetables ─────────────────────────────────
    "broccoli":        {"calories": 55,  "protein_g": 3.7,  "carbs_g": 11.2, "fat_g": 0.6},
    "spinach":         {"calories": 23,  "protein_g": 2.9,  "carbs_g": 3.6,  "fat_g": 0.4},
    "kale":            {"calories": 49,  "protein_g": 4.3,  "carbs_g": 9,    "fat_g": 0.9},
    "carrot":          {"calories": 41,  "protein_g": 0.9,  "carbs_g": 10,   "fat_g": 0.2},
    "tomato":          {"calories": 22,  "protein_g": 1.1,  "carbs_g": 4.8,  "fat_g": 0.2},
    "bell pepper":     {"calories": 31,  "protein_g": 1,    "carbs_g": 6,    "fat_g": 0.3},
    "onion":           {"calories": 44,  "protein_g": 1.2,  "carbs_g": 10,   "fat_g": 0.1},
    "mushrooms":       {"calories": 22,  "protein_g": 3.1,  "carbs_g": 3.3,  "fat_g": 0.3},
    "cucumber":        {"calories": 16,  "protein_g": 0.7,  "carbs_g": 3.6,  "fat_g": 0.1},
    "lettuce":         {"calories": 15,  "protein_g": 1.4,  "carbs_g": 2.9,  "fat_g": 0.2},
    "cabbage":         {"calories": 25,  "protein_g": 1.3,  "carbs_g": 6,    "fat_g": 0.1},
    "celery":          {"calories": 14,  "protein_g": 0.7,  "carbs_g": 3,    "fat_g": 0.2},
    "zucchini":        {"calories": 17,  "protein_g": 1.2,  "carbs_g": 3.1,  "fat_g": 0.3},
    "green beans":     {"calories": 31,  "protein_g": 1.8,  "carbs_g": 7,    "fat_g": 0.2},
    "asparagus":       {"calories": 20,  "protein_g": 2.2,  "carbs_g": 3.9,  "fat_g": 0.1},

    # ── Dairy ──────────────────────────────────────
    "yogurt":          {"calories": 150, "protein_g": 10,   "carbs_g": 12,   "fat_g": 5},
    "milk":            {"calories": 103, "protein_g": 8,    "carbs_g": 12,   "fat_g": 2.4},
    "cheese":          {"calories": 113, "protein_g": 7,    "carbs_g": 0.4,  "fat_g": 9},
    "cottage cheese":  {"calories": 98,  "protein_g": 11,   "carbs_g": 3.4,  "fat_g": 4.3},
    "greek yogurt":    {"calories": 100, "protein_g": 17,   "carbs_g": 6,    "fat_g": 0.7},
    "butter":          {"calories": 102, "protein_g": 0.1,  "carbs_g": 0,    "fat_g": 12},

    # ── Legumes & Nuts ─────────────────────────────
    "lentils":         {"calories": 230, "protein_g": 18,   "carbs_g": 40,   "fat_g": 0.8},
    "chickpeas":       {"calories": 269, "protein_g": 15,   "carbs_g": 45,   "fat_g": 4.2},
    "black beans":     {"calories": 227, "protein_g": 15,   "carbs_g": 41,   "fat_g": 0.9},
    "peanut butter":   {"calories": 188, "protein_g": 8,    "carbs_g": 6,    "fat_g": 16},
    "almonds":         {"calories": 164, "protein_g": 6,    "carbs_g": 6,    "fat_g": 14},
    "walnuts":         {"calories": 185, "protein_g": 4.3,  "carbs_g": 3.9,  "fat_g": 18.5},

    # ── Image-analyzer fallback categories ─────────
    # These keys match the outputs of _estimate_food_from_image()
    "grilled protein": {"calories": 220, "protein_g": 28,   "carbs_g": 1,    "fat_g": 11},
    "mixed vegetables":{"calories": 65,  "protein_g": 3.5,  "carbs_g": 13,   "fat_g": 0.5},
    "leafy greens":    {"calories": 25,  "protein_g": 2.5,  "carbs_g": 4,    "fat_g": 0.3},
    "hearty stew":     {"calories": 235, "protein_g": 16,   "carbs_g": 22,   "fat_g": 10},
    "mixed meal":      {"calories": 450, "protein_g": 20,   "carbs_g": 50,   "fat_g": 15},

    # ── Prepared / Common Meals ────────────────────
    "salad":           {"calories": 150, "protein_g": 5,    "carbs_g": 12,   "fat_g": 10},
    "sandwich":        {"calories": 350, "protein_g": 15,   "carbs_g": 35,   "fat_g": 16},
    "pizza":           {"calories": 285, "protein_g": 12,   "carbs_g": 36,   "fat_g": 10},
    "hamburger":       {"calories": 354, "protein_g": 20,   "carbs_g": 29,   "fat_g": 17},
    "sushi":           {"calories": 200, "protein_g": 9,    "carbs_g": 38,   "fat_g": 1},
    "soup":            {"calories": 150, "protein_g": 8,    "carbs_g": 18,   "fat_g": 5},
    "fried rice":      {"calories": 238, "protein_g": 5.5,  "carbs_g": 35,   "fat_g": 8.5},
    "burrito":         {"calories": 380, "protein_g": 18,   "carbs_g": 45,   "fat_g": 14},
    "tacos":           {"calories": 210, "protein_g": 9,    "carbs_g": 21,   "fat_g": 10},
    "ramen":           {"calories": 380, "protein_g": 10,   "carbs_g": 52,   "fat_g": 14},
    "curry":           {"calories": 300, "protein_g": 15,   "carbs_g": 20,   "fat_g": 18},
    "stir fry":        {"calories": 250, "protein_g": 18,   "carbs_g": 15,   "fat_g": 12},

    # ── Korean foods ───────────────────────────────
    "kimchi":          {"calories": 15,  "protein_g": 1.1,  "carbs_g": 2.4,  "fat_g": 0.5},
    "bibimbap":        {"calories": 490, "protein_g": 22,   "carbs_g": 70,   "fat_g": 13},
    "bulgogi":         {"calories": 256, "protein_g": 23,   "carbs_g": 9,    "fat_g": 14},
    "japchae":         {"calories": 210, "protein_g": 5,    "carbs_g": 35,   "fat_g": 6},
    "tteokbokki":      {"calories": 330, "protein_g": 7,    "carbs_g": 68,   "fat_g": 3},
    "samgyeopsal":     {"calories": 330, "protein_g": 18,   "carbs_g": 0,    "fat_g": 28},
    "doenjang jjigae": {"calories": 120, "protein_g": 8,    "carbs_g": 10,   "fat_g": 5},
    "gimbap":          {"calories": 320, "protein_g": 10,   "carbs_g": 48,   "fat_g": 9},

    # ── Snacks / Beverages ─────────────────────────
    "granola bar":     {"calories": 190, "protein_g": 3,    "carbs_g": 29,   "fat_g": 7},
    "protein shake":   {"calories": 150, "protein_g": 25,   "carbs_g": 8,    "fat_g": 2},
    "smoothie":        {"calories": 210, "protein_g": 4,    "carbs_g": 45,   "fat_g": 2},
    "coffee":          {"calories": 2,   "protein_g": 0.3,  "carbs_g": 0,    "fat_g": 0},
    "orange juice":    {"calories": 112, "protein_g": 1.7,  "carbs_g": 26,   "fat_g": 0.5},
}


def _fuzzy_lookup(name: str) -> dict[str, float] | None:
    """Try exact match, then substring match against NUTRITION_DB."""
    key = name.lower().strip()

    # Exact
    if key in NUTRITION_DB:
        return NUTRITION_DB[key]

    # Substring (prefer shorter DB key = more specific match)
    candidates: list[tuple[str, dict[str, float]]] = []
    for db_name, db_nutrition in NUTRITION_DB.items():
        if db_name in key or key in db_name:
            candidates.append((db_name, db_nutrition))

    if candidates:
        # Pick best match: prefer exact substring length closest to query
        candidates.sort(key=lambda c: abs(len(c[0]) - len(key)))
        return candidates[0][1]

    return None


def analyze_meal(request: AnalyzeMealRequest) -> AnalyzeMealResponse:
    """Analyse nutritional content of food items."""
    results: list[FoodNutrition] = []

    for item in request.items:
        nutrition = _fuzzy_lookup(item.name)

        if nutrition:
            results.append(FoodNutrition(
                name=item.name,
                calories=nutrition["calories"],
                protein_g=nutrition["protein_g"],
                carbs_g=nutrition["carbs_g"],
                fat_g=nutrition["fat_g"],
            ))
        else:
            results.append(FoodNutrition(
                name=item.name,
                calories=None,
                protein_g=None,
                carbs_g=None,
                fat_g=None,
                note=f"'{item.name}' not found in database – try a more common name",
            ))

    return AnalyzeMealResponse(items=results)