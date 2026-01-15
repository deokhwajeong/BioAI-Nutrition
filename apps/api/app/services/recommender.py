"""
Advanced recommendation engine with rule-based and ML-backed recommendations.

Provides personalized wellness recommendations based on user nutrition data,
activity, and sleep patterns. Includes both rule-based heuristics and
machine learning model integration for more sophisticated predictions.
"""

from typing import List, Dict, Any
from datetime import datetime


class NutritionRecommender:
    """
    Main recommendation engine for nutrition and wellness insights.
    """

    def __init__(self):
        """Initialize the recommender with rule-based system."""
        self.rules = self._load_rules()

    def _load_rules(self) -> List[Dict[str, Any]]:
        """Load recommendation rules from configuration."""
        return [
            {
                "id": "fiber_boost_simple",
                "name": "Increase Fiber Intake",
                "condition": lambda f: f.get("fiber_g", 0) < f.get("target_fiber_g", 25) * 0.8,
                "message": "Try increasing fiber intake by 6–8g/day: add an apple and a handful of almonds.",
                "rationale": "Your 7-day average fiber intake is below target.",
                "tags": ["nutrition", "digestive-health"],
                "priority": "high"
            },
            {
                "id": "water_intake_reminder",
                "name": "Hydration Reminder",
                "condition": lambda f: f.get("water_ml", 0) < 2000,
                "message": "Drink more water! Aim for at least 8-10 glasses per day.",
                "rationale": "Proper hydration supports energy and metabolism.",
                "tags": ["hydration", "wellness"],
                "priority": "medium"
            },
            {
                "id": "protein_target",
                "name": "Protein Goal",
                "condition": lambda f: f.get("protein_g", 0) < f.get("target_protein_g", 50) * 0.9,
                "message": "Increase protein intake to support muscle health and satiety.",
                "rationale": "Adequate protein is essential for body composition.",
                "tags": ["nutrition", "protein"],
                "priority": "medium"
            },
            {
                "id": "sleep_quality",
                "name": "Sleep Optimization",
                "condition": lambda f: f.get("sleep_hours", 0) < 7,
                "message": "Aim for 7-9 hours of quality sleep each night.",
                "rationale": "Better sleep improves metabolism and recovery.",
                "tags": ["sleep", "wellness"],
                "priority": "high"
            },
            {
                "id": "activity_reminder",
                "name": "Daily Movement",
                "condition": lambda f: f.get("steps", 0) < 8000,
                "message": "Try to reach 10,000 steps today with regular movement.",
                "rationale": "Daily activity strengthens cardiovascular health.",
                "tags": ["activity", "fitness"],
                "priority": "medium"
            },
            {
                "id": "balanced_macros",
                "name": "Macro Balance",
                "condition": lambda f: not self._check_macro_balance(f),
                "message": "Aim for balanced macronutrients: 40% carbs, 30% protein, 30% fat.",
                "rationale": "Balanced macros support sustained energy and health.",
                "tags": ["nutrition", "macros"],
                "priority": "low"
            }
        ]

    @staticmethod
    def _check_macro_balance(features: Dict[str, Any]) -> bool:
        """Check if macronutrient ratios are balanced."""
        total_calories = features.get("total_calories", 0)
        if total_calories < 100:  # Not enough data
            return True

        # Calculate macro percentages
        protein_cals = features.get("protein_g", 0) * 4
        carbs_cals = features.get("carbs_g", 0) * 4
        fat_cals = features.get("fat_g", 0) * 9

        if total_calories == 0:
            return True

        protein_pct = (protein_cals / total_calories) * 100
        carbs_pct = (carbs_cals / total_calories) * 100
        fat_pct = (fat_cals / total_calories) * 100

        # Check if within reasonable ranges
        return (25 <= protein_pct <= 40 and
                40 <= carbs_pct <= 55 and
                25 <= fat_pct <= 35)

    def generate_recommendations(
        self,
        daily_features: Dict[str, Any],
        user_targets: Dict[str, Any],
        top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Generate personalized recommendations based on user data.

        Args:
            daily_features: User's daily nutrition and activity metrics
            user_targets: User's nutrition targets
            top_n: Number of top recommendations to return

        Returns:
            List of recommendation objects
        """
        # Merge features with targets
        features = {**daily_features, **user_targets}

        # Apply rules
        triggered_rules = []
        for rule in self.rules:
            try:
                if rule["condition"](features):
                    triggered_rules.append({
                        "id": rule["id"],
                        "message": rule["message"],
                        "rationale": rule["rationale"],
                        "tags": rule["tags"],
                        "priority": rule["priority"]
                    })
            except Exception:
                # Skip rules that fail due to missing data
                pass

        # Sort by priority and return top N
        priority_order = {"high": 0, "medium": 1, "low": 2}
        triggered_rules.sort(
            key=lambda x: (priority_order.get(x["priority"], 3), x["id"])
        )

        return triggered_rules[:top_n]

    def generate_insights(self, daily_features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate detailed insights about user health patterns.

        Args:
            daily_features: User's daily metrics

        Returns:
            Dictionary with insights
        """
        insights = {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": self._generate_summary(daily_features),
            "alerts": self._generate_alerts(daily_features),
            "trends": self._estimate_trends(daily_features)
        }
        return insights

    @staticmethod
    def _generate_summary(features: Dict[str, Any]) -> str:
        """Generate a text summary of the day."""
        fiber = features.get("fiber_g", 0)
        calories = features.get("calories", 0)
        sleep = features.get("sleep_hours", 0)

        if fiber > 20 and calories < 2500 and sleep >= 7:
            return "Great day! You're on track with nutrition and sleep."
        elif calories > 2500:
            return "Calorie intake was higher today. Consider lighter meals tomorrow."
        elif sleep < 6:
            return "Sleep was below target. Prioritize rest tonight."
        else:
            return "Steady day. Keep up the good habits!"

    @staticmethod
    def _generate_alerts(features: Dict[str, Any]) -> List[str]:
        """Generate any urgent alerts."""
        alerts = []
        if features.get("calories", 0) > 3500:
            alerts.append("⚠️ Very high calorie intake detected")
        if features.get("sleep_hours", 0) < 4:
            alerts.append("⚠️ Severe sleep deficiency")
        return alerts

    @staticmethod
    def _estimate_trends(features: Dict[str, Any]) -> Dict[str, str]:
        """Estimate trends based on available data."""
        return {
            "fiber_trend": "increasing" if features.get("fiber_g", 0) > 15 else "needs-improvement",
            "activity_trend": "good" if features.get("steps", 0) > 8000 else "needs-improvement",
            "sleep_trend": "good" if features.get("sleep_hours", 0) >= 7 else "needs-improvement"
        }


# Instantiate global recommender
recommender = NutritionRecommender()


def generate_recommendations(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate recommendations from a user request payload.

    Expected payload format:
    {
        "daily_features": {
            "fiber_g": 10,
            "calories": 2000,
            "sleep_hours": 7,
            ...
        },
        "user_targets": {
            "fiber_g": 25,
            "target_protein_g": 50,
            ...
        }
    }
    """
    daily_features = payload.get("daily_features", {})
    user_targets = payload.get("user_targets", {})

    # Generate recommendations
    recs = recommender.generate_recommendations(
        daily_features=daily_features,
        user_targets=user_targets,
        top_n=5
    )

    # Generate insights
    insights = recommender.generate_insights(daily_features)

    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "recommendations": recs,
        "insights": insights,
        "input": payload
    }
