from fastapi import APIRouter, HTTPException
from services import fetch_city_data

router = APIRouter()


@router.get("/cities-stats")
def get_cities_stats():
    try:
        data = fetch_city_data()
        return {"status": "ok", "data": data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

