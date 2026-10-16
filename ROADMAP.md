# Possible next steps

Short list of what could come next. None of it is promised; each item says why it is not done yet.

## Engine and data

- **Persist engine state.** Readings, consent state, and privacy budgets live in process memory and reset on restart. Accounts and logged days are already in the database; the engine stores are next.
- **Scope engine endpoints by token.** `/engine/*` still takes a `user_id` behind the shared API key. Moving it behind the bearer token (and a server-side proxy for the web app) would make every route per-user.
- **Validate lag parameters on real CGM data.** The public OhioT1DM dataset needs a data use agreement; the loader exists in `apps/api/app/services/ohio_t1dm_loader.py`.
- **Larger food table.** The meal planner and analyzer use about 90 typical servings. A USDA FoodData Central import would add fibre, sodium, and potassium so more medical limits could be checked.

## Image analysis (issues #5 and #10)

- **Trained food detection.** The image path is a colour-histogram heuristic with optional OCR. A YOLO-family detector would need downloaded weights (tens of MB, AGPL-licensed for YOLOv8) and a labelled food dataset, which do not fit this repository.
- **Serving-size estimation.** Needs depth or a reference object in the photo to be more than a guess.

## Machine learning (issues #8 and #15)

- **Real-data personalization.** The gradient-boosting model in `apps/api/ml/` is trained on simulated meals only. Using it for recommendations would need consented real data, a validation study, and clinical review. Production-scale serving and model optimization only make sense after that.

## Out of scope for a single-person portfolio project

- **Social and community features (#12)**, **device and partner integrations (#13)**, and **enterprise compliance and SLAs (#14)** need users, partners, or an operations team. Consent scopes for household and provider sharing exist in `consent_manager.py` as a starting point.
