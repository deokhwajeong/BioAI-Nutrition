from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import httpx

#from app.routers import recommendations
from .routers import recommendations


# ---------------------------------------------------------
# FastAPI 기본 설정
# ---------------------------------------------------------
app = FastAPI(
    title="BioAI Nutrition API",
    version="0.1.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 개발 시에는 * 허용, 나중에 웹 도메인으로 제한 가능
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# 기본 라우트
# ---------------------------------------------------------
@app.get("/")
def root():
    return RedirectResponse(url="/docs", status_code=307)


@app.get("/health")
def health():
    return {"ok": True}


# 기존 recommendations router 포함
app.include_router(recommendations.router)


# ---------------------------------------------------------
# Nutrition API 데이터 모델
# ---------------------------------------------------------
class FoodItem(BaseModel):
    name: str


class FoodNutrition(BaseModel):
    name: str
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    note: Optional[str] = None


class AnalyzeMealRequest(BaseModel):
    items: List[FoodItem]


class AnalyzeMealResponse(BaseModel):
    items: List[FoodNutrition]


# ---------------------------------------------------------
# USDA Nutrition API 설정
# ---------------------------------------------------------
USDA_API_KEY = os.getenv("USDA_API_KEY", "")
USDA_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"


async def fetch_nutrition_from_usda(query: str) -> FoodNutrition:
    """
    USDA FoodData Central 검색 후 영양 정보를 추출하는 함수.
    키가 없으면 dummy response 반환하게 되어 있어 개발할 때 깨지지 않음.
    """
    if not USDA_API_KEY:
        # API 키 없으면 기본 응답 반환 (앱 깨지지 않도록)
        return FoodNutrition(
            name=query,
            note="USDA_API_KEY is not set. Returning placeholder values."
        )

    params = {
        "api_key": USDA_API_KEY,
        "query": query,
        "pageSize": 1,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(USDA_SEARCH_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    foods = data.get("foods", [])
    if not foods:
        return FoodNutrition(
            name=query,
            note="No matching food found in USDA database."
        )

    food = foods[0]
    nutrients = {n["nutrientName"]: n for n in food.get("foodNutrients", [])}

    def get_amount(name_substring: str):
        for n_name, n in nutrients.items():
            if name_substring.lower() in n_name.lower():
                return n.get("value")
        return None

    return FoodNutrition(
        name=query,
        calories=get_amount("Energy"),
        protein_g=get_amount("Protein"),
        carbs_g=get_amount("Carbohydrate"),
        fat_g=get_amount("Total lipid"),
        note=f"Matched USDA item: {food.get('description', '')[:80]}"
    )


# ---------------------------------------------------------
# /analyze-meal 엔드포인트
# ---------------------------------------------------------
@app.post("/analyze-meal", response_model=AnalyzeMealResponse)
async def analyze_meal(payload: AnalyzeMealRequest) -> AnalyzeMealResponse:
    results: List[FoodNutrition] = []

    for item in payload.items:
        nutrition = await fetch_nutrition_from_usda(item.name)
        results.append(nutrition)

    return AnalyzeMealResponse(items=results)


from fastapi.responses import HTMLResponse

@app.get("/", include_in_schema=False)
def root():
    return HTMLResponse("""
    <html>
      <head><title>BioAI Nutrition API</title></head>
      <body style="font-family:system-ui; padding:24px;">
        <h1>BioAI Nutrition API</h1>
        <p>Developer docs:</p>
        <ul>
          <li><a href="/docs">Swagger UI</a></li>
          <li><a href="/redoc">ReDoc</a></li>
          <li><a href="/health">Health check</a></li>
        </ul>
      </body>
    </html>
    """)
