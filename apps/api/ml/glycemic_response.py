"""Gradient-boosted post-meal glucose model on synthetic data: a workflow demonstration.

READ THIS FIRST. Every number this module produces comes from a simulator written here, not
from people. The simulator encodes a handful of effects reported in the literature on
personalised glycaemic responses (for example Zeevi et al., Cell 2015, who used gradient
boosting on real cohort data): carbohydrate load, fibre, fat and protein slowing absorption,
time of day, short sleep, recent exercise, a TCF7L2-style risk allele count, and large
between-person differences. A model trained on it can only rediscover those hand-written
effects. The evaluation shows that the training and validation workflow works (grouped
split by person, a carb-counting baseline, permutation importance), and nothing about
real-world accuracy. It is not a validated or clinical model and is not used by the API.

Target: peak rise in glucose over the pre-meal value within two hours, in mg/dL.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from threadpoolctl import threadpool_limits

FEATURES = (
    "carbs_g",
    "fiber_g",
    "protein_g",
    "fat_g",
    "hour",
    "sleep_hours",
    "minutes_since_exercise",
    "risk_alleles",
    "fasting_glucose",
)
SEED = 20261016


@dataclass
class Dataset:
    X: np.ndarray  # shape (rows, len(FEATURES))
    y: np.ndarray  # peak rise, mg/dL
    person: np.ndarray  # person index per row, for grouped splits


def simulate(people: int = 400, meals_per_person: int = 20, seed: int = SEED) -> Dataset:
    """Generate synthetic meals and responses. See the module docstring for what this is."""
    rng = np.random.default_rng(seed)
    # Person-level traits. Insulin resistance is hidden; fasting glucose is a noisy proxy.
    resistance = rng.lognormal(mean=0.0, sigma=0.35, size=people)
    risk = rng.choice([0, 1, 2], size=people, p=[0.5, 0.4, 0.1])
    fasting = 85 + 12 * np.log(resistance) + rng.normal(0, 4, size=people)

    n = people * meals_per_person
    person = np.repeat(np.arange(people), meals_per_person)
    carbs = rng.gamma(shape=3.0, scale=20.0, size=n).clip(5, 180)
    fiber = (carbs * rng.uniform(0.02, 0.15, size=n)).clip(0, 25)
    protein = rng.gamma(shape=2.5, scale=10.0, size=n).clip(0, 90)
    fat = rng.gamma(shape=2.0, scale=10.0, size=n).clip(0, 80)
    hour = rng.choice([7, 8, 12, 13, 18, 19, 20, 21], size=n) + rng.uniform(0, 1, size=n)
    sleep = rng.normal(7.0, 1.0, size=n).clip(4, 10)
    # 0 to 600 minutes since exercise; 600 means "not today".
    exercised = rng.random(n) < 0.3
    since_ex = np.where(exercised, rng.uniform(10, 240, size=n), 600.0)

    available = (carbs - 0.5 * fiber).clip(0)
    absorption = 1.0 / (1.0 + 0.012 * fat + 0.006 * protein)
    evening = 1.0 + 0.25 / (1.0 + np.exp(-(hour - 17.0)))  # smooth step up after ~17:00
    short_sleep = np.where(sleep < 6.0, 1.0 + 0.04 * (6.0 - sleep) * 4, 1.0)
    exercise = np.where(since_ex < 120, 0.8, np.where(since_ex < 240, 0.9, 1.0))
    genetic = 1.0 + 0.12 * risk[person]
    rise = (
        0.9
        * available
        * absorption
        * evening
        * short_sleep
        * exercise
        * genetic
        * resistance[person]
    )
    rise = rise * rng.lognormal(0.0, 0.15, size=n) + rng.normal(0, 5, size=n)

    X = np.column_stack(
        [carbs, fiber, protein, fat, hour, sleep, since_ex, risk[person], fasting[person]]
    )
    return Dataset(X=X, y=rise.clip(0), person=person)


def holdout_mask(data: Dataset, test_fraction: float = 0.25, seed: int = SEED) -> np.ndarray:
    """Rows of held-out people: whole people are held out, never single meals."""
    rng = np.random.default_rng(seed + 1)
    people = np.unique(data.person)
    test_people = rng.choice(people, size=int(len(people) * test_fraction), replace=False)
    return np.isin(data.person, test_people)


def carb_baseline() -> LinearRegression:
    """Carb counting: response proportional to carbohydrate grams (one feature)."""
    return LinearRegression()


def boosted_model(seed: int = SEED) -> HistGradientBoostingRegressor:
    return HistGradientBoostingRegressor(
        max_iter=300,
        learning_rate=0.05,
        max_leaf_nodes=31,
        l2_regularization=1.0,
        random_state=seed,
    )


def evaluate(data: Dataset | None = None, seed: int = SEED) -> dict:
    """Train both models on the training people and score them on held-out people."""
    data = data or simulate(seed=seed)
    test = holdout_mask(data, seed=seed)
    X_tr, y_tr, X_te, y_te = data.X[~test], data.y[~test], data.X[test], data.y[test]
    carbs_col = FEATURES.index("carbs_g")

    # One thread: the data is small, results are reproducible, and OpenMP oversubscription
    # on shared CI runners can make multi-threaded fits far slower than single-threaded.
    with threadpool_limits(limits=1):
        base = carb_baseline().fit(X_tr[:, [carbs_col]], y_tr)
        base_pred = base.predict(X_te[:, [carbs_col]])
        gbm = boosted_model(seed).fit(X_tr, y_tr)
        gbm_pred = gbm.predict(X_te)
        imp = permutation_importance(gbm, X_te, y_te, n_repeats=5, random_state=seed)
    importance = sorted(
        zip(FEATURES, imp.importances_mean.round(4).tolist()), key=lambda kv: -kv[1]
    )

    def scores(pred: np.ndarray) -> dict:
        return {
            "mae_mg_dl": round(float(mean_absolute_error(y_te, pred)), 2),
            "r2": round(float(r2_score(y_te, pred)), 3),
            "pearson_r": round(float(np.corrcoef(y_te, pred)[0, 1]), 3),
        }

    return {
        "rows_train": int(len(y_tr)),
        "rows_test": int(len(y_te)),
        "people_test": int(len(np.unique(data.person[test]))),
        "carb_baseline": scores(base_pred),
        "gradient_boosting": scores(gbm_pred),
        "permutation_importance": importance,
        "seed": seed,
    }
