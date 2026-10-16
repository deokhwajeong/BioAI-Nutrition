"""Synthetic glucose-response model: the workflow runs and beats carb counting on held-out people."""

import numpy as np

from ml.glycemic_response import FEATURES, evaluate, holdout_mask, simulate


def test_simulation_is_reproducible_and_plausible() -> None:
    a, b = simulate(people=50, seed=1), simulate(people=50, seed=1)
    assert np.array_equal(a.X, b.X) and np.array_equal(a.y, b.y)
    assert a.X.shape == (50 * 20, len(FEATURES))
    assert (a.y >= 0).all() and 20 < np.median(a.y) < 120


def test_split_holds_out_whole_people() -> None:
    data = simulate(people=80, seed=2)
    test = holdout_mask(data, seed=2)
    assert not set(data.person[test]) & set(data.person[~test])


def test_boosting_beats_the_carb_baseline_on_unseen_people() -> None:
    r = evaluate(simulate(people=200, seed=3), seed=3)
    assert r["gradient_boosting"]["mae_mg_dl"] < r["carb_baseline"]["mae_mg_dl"]
    assert r["gradient_boosting"]["r2"] > r["carb_baseline"]["r2"]
    assert r["permutation_importance"][0][0] == "carbs_g"
