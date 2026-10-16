# Working in this repo

Monorepo: `apps/api` (FastAPI, Python 3.13, uv) and `apps/web` (Next.js 16, pnpm). Use the Makefile targets.

- Before finishing any change: `make check` (ruff, pytest, tsc, eslint, next build) must pass.
- Changed an API request/response model? Run `make gen-api` and commit `apps/web/lib/openapi.json` and `apps/web/lib/api-schema.d.ts`; CI fails on drift. Never edit `api-schema.d.ts` by hand.
- UI components consume view models from `apps/web/lib/types.ts`; map wire responses in `lib/api.ts`, not in components.
- The web app calls the API same-origin via rewrites in `next.config.ts`. Adding a router prefix means adding a rewrite there too.
- All data is synthetic. Never commit real health data, `.env` files, or `*.db` files.
- Recommendations stay non-diagnostic; medical constraints always override genetic optimization in `nutrient_calculator.py`.
