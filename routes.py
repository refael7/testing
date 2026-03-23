from fastapi import APIRouter, HTTPException
from services import average_from_front_input

router = APIRouter()


@router.get("/cities-stats")
def get_cities_stats():
    try:

        result = average_from_front_input("2026-03-23T09:41:05.623Z", "ירושלים")
        print(result)
        return {"status": "ok", "data": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

