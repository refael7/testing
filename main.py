import requests
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pymongo import MongoClient
from datetime import datetime, timedelta
import threading
import time
import uvicorn
import pytz

app = FastAPI()

# הגדרת אזור זמן ישראל (חשוב לחישובי שעות)
israel_tz = pytz.timezone('Asia/Jerusalem')

# הגדרת ה-Token
API_TOKEN = "pr_TwGtUQvnMgnWbYTRHOnwrGcKuZvDqppALWqwWdoJLSpfvsUYGNiyOfVwWoPBrOdr"

# חיבור ל-MongoDB
try:
    client = MongoClient("mongodb://mongodb:27017/", serverSelectionTimeoutMS=2000)
    db = client.red_alert_db
    alerts_col = db.alerts
    client.server_info()
except:
    print("Warning: Could not connect to MongoDB.")

# מילון ערי מעבר לחישוב סיכון
AXES = {
    "כביש_4_מרכז": ["אשקלון", "אשדוד", "יבנה", "ראשון לציון", "חולון", "תל אביב", "רמת גן", "בני ברק"],
    "כביש_1_ירושלים": ["ירושלים", "מבשרת ציון", "מעלה החמישה", "לטרון", "מודיעין", "נתבג", "לוד", "תל אביב"],
    "כביש_5_שומרון": ["אריאל", "ברקן", "אלעד", "ראש העין", "פתח תקווה", "גבעת שמואל", "בני ברק", "תל אביב"],
    "כביש_2_חוף": ["חיפה", "טירת כרמל", "עתלית", "חדרה", "נתניה", "הרצליה", "תל אביב"],
    "דרום_מרכז": ["באר שבע", "להבים", "קרית גת", "רחובות", "נס ציונה", "ראשון לציון"]
}


def get_route_cities(origin, destination):
    cities_to_check = {origin, destination}
    for axis_name, axis_cities in AXES.items():
        if any(origin in c for c in axis_cities) and any(destination in c for c in axis_cities):
            try:
                idx1 = next(i for i, c in enumerate(axis_cities) if origin in c)
                idx2 = next(i for i, c in enumerate(axis_cities) if destination in c)
                start_idx, end_idx = min(idx1, idx2), max(idx1, idx2)
                cities_to_check.update(axis_cities[start_idx:end_idx + 1])
            except StopIteration:
                continue
    return list(cities_to_check)


def fetch_alerts_loop():
    API_URL = "https://redalert.orielhaim.com/api/stats/history?limit=100"
    print("Background Fetcher Started - Archiving 30 days (Israel Time Zone)...")
    while True:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Authorization': f'Bearer {API_TOKEN}',
                'Accept': 'application/json'
            }
            response = requests.get(API_URL, headers=headers, timeout=15)
            if response.status_code == 200:
                result = response.json()
                alerts_data = result.get('data', [])
                new_alerts_count = 0
                for alert_entry in alerts_data:
                    alert_id_base = alert_entry.get('id')
                    timestamp_str = alert_entry.get('timestamp')  # מגיע בפורמט ISO
                    category = alert_entry.get('type', 'missiles')

                    for city_info in alert_entry.get('cities', []):
                        city_name = city_info.get('name')
                        if not city_name or not timestamp_str: continue

                        unique_id = f"{alert_id_base}_{city_name}"

                        if not alerts_col.find_one({"_id": unique_id}):
                            try:
                                # 1. ניקוי המחרוזת והפיכה לאובייקט datetime
                                clean_time = timestamp_str.split('.')[0].replace('Z', '')
                                dt_utc = datetime.fromisoformat(clean_time)

                                # 2. הוספת מידע שמדובר ב-UTC והמרה לישראל
                                dt_utc = pytz.utc.localize(dt_utc)
                                dt_israel = dt_utc.astimezone(israel_tz)

                                # 3. הסרת המידע על אזור הזמן לפני השמירה (MongoDB מעדיף אובייקטים נאיביים בזמן מקומי)
                                dt_final = dt_israel.replace(tzinfo=None)

                            except Exception as e:
                                print(f"Time conversion error: {e}")
                                dt_final = datetime.now(israel_tz).replace(tzinfo=None)

                            alerts_col.insert_one({
                                "_id": unique_id,
                                "city": city_name,
                                "date": dt_final,
                                "category": category
                            })
                            new_alerts_count += 1

                # ניקוי ישן (גם לפי זמן ישראל)
                one_month_ago = datetime.now(israel_tz).replace(tzinfo=None) - timedelta(days=30)
                alerts_col.delete_many({"date": {"$lt": one_month_ago}})

                if new_alerts_count > 0:
                    print(f"✅ סונכרנו {new_alerts_count} אזעקות חדשות בשעון ישראל.")

            time.sleep(60)
        except Exception as e:
            print(f"Fetcher Error: {e}")
            time.sleep(60)


threading.Thread(target=fetch_alerts_loop, daemon=True).start()


# --- נתיב חדש לסטטיסטיקה עבור הגרף ---
@app.get("/route_stats")
def get_route_stats(origin: str, destination: str):
    cities_to_check = get_route_cities(origin.strip(), destination.strip())
    one_month_ago = datetime.now() - timedelta(days=30)
    hourly_counts = {i: 0 for i in range(24)}

    for city in cities_to_check:
        flexible_pattern = city.replace(" ", ".*").replace("-", ".*").replace("וו", "ו?ו?").replace("ו", "ו?")
        cursor = alerts_col.find({
            "city": {"$regex": flexible_pattern, "$options": "i"},
            "date": {"$gte": one_month_ago}
        })
        for alert in cursor:
            hour = alert['date'].hour
            hourly_counts[hour] += 1

    return [{"hour": f"{h:02d}:00", "count": hourly_counts[h]} for h in range(24)]


@app.get("/calculate_risk")
def calculate_risk(origin: str, destination: str, manual_time: str = None):
    now = datetime.now(israel_tz)

    # שימוש בשעה ידנית או בשעה הנוכחית
    if manual_time:
        try:
            check_time_obj = datetime.strptime(manual_time, "%H:%M").time()
            base_dt = datetime.combine(now.date(), check_time_obj)
        except:
            base_dt = now
    else:
        base_dt = now

    one_month_ago = now - timedelta(days=30)
    window_start = (base_dt - timedelta(minutes=30)).time()
    window_end = (base_dt + timedelta(minutes=30)).time()

    cities_to_check = get_route_cities(origin.strip(), destination.strip())
    total_alerts_in_window = 0
    detailed_results = []

    for city in cities_to_check:
        flexible_pattern = city.replace(" ", ".*").replace("-", ".*").replace("וו", "ו?ו?").replace("ו", "ו?")
        cursor = alerts_col.find({
            "city": {"$regex": flexible_pattern, "$options": "i"},
            "date": {"$gte": one_month_ago}
        })

        city_window_count = 0
        for alert in cursor:
            alert_time = alert['date'].time()
            if window_start <= window_end:
                is_in_window = window_start <= alert_time <= window_end
            else:
                is_in_window = alert_time >= window_start or alert_time <= window_end

            if is_in_window:
                city_window_count += 1

        if city_window_count > 0:
            detailed_results.append({"city": city, "alerts_in_this_hour": city_window_count})
            total_alerts_in_window += city_window_count

    ALERTS_THRESHOLD = 10
    risk_score_num = min(int((total_alerts_in_window / ALERTS_THRESHOLD) * 100), 100)

    current_time_str = base_dt.strftime("%H:%M")
    if risk_score_num == 0:
        recommendation = f"✅ השעה {current_time_str} סטטיסטית שקטה מאוד במסלול זה."
    elif risk_score_num <= 40:
        recommendation = f"⚠️ שים לב: בשעה {current_time_str} היו אירועים בודדים בחודש האחרון."
    else:
        recommendation = f"🚨 סיכון גבוה: השעה {current_time_str} התגלתה כשעה רווית אירועים!"

    return {
        "current_time": current_time_str,
        "risk_score": f"{risk_score_num}%",
        "risk_score_int": risk_score_num,
        "recommendation": recommendation,
        "total_alerts_found": total_alerts_in_window,
        "cities_checked": cities_to_check,
        "breakdown": detailed_results
    }


@app.get("/debug/alerts")
def get_debug_alerts():
    alerts = list(alerts_col.find().sort("date", -1).limit(10))
    for a in alerts:
        a["_id"] = str(a["_id"])
        a["date"] = a["date"].isoformat()
    return alerts


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)