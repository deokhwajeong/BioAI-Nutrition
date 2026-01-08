from ..schemas.user_input import AnalyzeMealRequest, AnalyzeMealResponse, FoodItem, FoodNutrition

# Mock nutritional database - in production, use a real API or database
NUTRITION_DB = {
    "apple": {"calories": 95, "protein_g": 0.5, "carbs_g": 25, "fat_g": 0.3},
    "banana": {"calories": 105, "protein_g": 1.3, "carbs_g": 27, "fat_g": 0.4},
    "chicken breast": {"calories": 165, "protein_g": 31, "carbs_g": 0, "fat_g": 3.6},
    "rice": {"calories": 130, "protein_g": 2.7, "carbs_g": 28, "fat_g": 0.3},
    "broccoli": {"calories": 55, "protein_g": 3.7, "carbs_g": 11.2, "fat_g": 0.6},
    "salmon": {"calories": 206, "protein_g": 22, "carbs_g": 0, "fat_g": 12},
    "yogurt": {"calories": 150, "protein_g": 10, "carbs_g": 12, "fat_g": 5},
    "bread": {"calories": 79, "protein_g": 2.7, "carbs_g": 14.7, "fat_g": 1},
    "egg": {"calories": 70, "protein_g": 6, "carbs_g": 0.6, "fat_g": 5},
    "potato": {"calories": 77, "protein_g": 2, "carbs_g": 17, "fat_g": 0.1},
}

def analyze_meal(request: AnalyzeMealRequest) -> AnalyzeMealResponse:
    """
    Analyze nutritional content of food items.
    """
    results = []

    for item in request.items:
        name = item.name.lower().strip()

        # Try exact match first
        nutrition = NUTRITION_DB.get(name)

        if not nutrition:
            # Try partial match
            for db_name, db_nutrition in NUTRITION_DB.items():
                if db_name in name or name in db_name:
                    nutrition = db_nutrition
                    break

        if nutrition:
            results.append(FoodNutrition(
                name=item.name,
                calories=nutrition["calories"],
                protein_g=nutrition["protein_g"],
                carbs_g=nutrition["carbs_g"],
                fat_g=nutrition["fat_g"]
            ))
        else:
            results.append(FoodNutrition(
                name=item.name,
                note="Nutrition data not found"
            ))

    return AnalyzeMealResponse(items=results)