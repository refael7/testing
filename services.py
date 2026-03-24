# services.py
import requests
from datetime import datetime, timezone

def fetch_alarms_for_month(year: int, month: int):
    url = "https://redalert.orielhaim.com/api/stats/history"
    headers = {
        "Authorization": "Bearer pr_TwGtUQvnMgnWbYTRHOnwrGcKuZvDqppALWqwWdoJLSpfvsUYGNiyOfVwWoPBrOdr",
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    limit = 100
    offset = 0
    all_alarms = []

    start_date = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end_date = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end_date = datetime(year, month + 1, 1, tzinfo=timezone.utc)

    while True:
        params = {
            "limit": limit,
            "offset": offset
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)
        print(response.status_code)
        print(response.text)

        response.raise_for_status()

        data = response.json()
        alarms = data.get("data", [])

        if not alarms:
            break

        stop = False

        for alarm in alarms:
            alarm_dt = datetime.fromisoformat(
                alarm["timestamp"].replace("Z", "+00:00")
            ).astimezone(timezone.utc)

            # עצירה כשעברנו את החודש
            if alarm_dt < start_date:
                stop = True
                break

            if start_date <= alarm_dt < end_date:
                all_alarms.append(alarm)

        if stop:
            break

        offset += limit

        if not data.get("pagination", {}).get("hasMore", False):
            break

    return all_alarms


def average_from_front_input(target_timestamp: str, city_name: str):
    dt = datetime.fromisoformat(
        target_timestamp.replace("Z", "+00:00")
    ).astimezone(timezone.utc)

    year = dt.year
    month = dt.month
    hour = dt.hour

    alarms = fetch_alarms_for_month(year, month)

    # day -> [60 דקות]
    daily_minute_counts = {}

    for alarm in alarms:
        alarm_dt = datetime.fromisoformat(
            alarm["timestamp"].replace("Z", "+00:00")
        ).astimezone(timezone.utc)

        # סינון לפי שעה
        if alarm_dt.hour != hour:
            continue

        # סינון עיר
        if not any(city_name in city.get("name", "") for city in alarm.get("cities", [])):
            continue

        day = alarm_dt.day
        minute = alarm_dt.minute

        if day not in daily_minute_counts:
            daily_minute_counts[day] = [0] * 60

        daily_minute_counts[day][minute] += 1

    # חישוב ימים בחודש
    if month == 12:
        next_month = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        next_month = datetime(year, month + 1, 1, tzinfo=timezone.utc)

    days_in_month = (next_month - datetime(year, month, 1, tzinfo=timezone.utc)).days

    # בניית תוצאה מלאה
    result = []
    for day in range(1, days_in_month + 1):
        result.append(daily_minute_counts.get(day, [0] * 60))

    # חישוב ממוצע אזעקות לפי ימים
    daily_totals = [sum(day_minutes) for day_minutes in result]  # סיכום כל הדקות ביום
    average_per_day = sum(daily_totals) / len(daily_totals) if daily_totals else 0

    return {
        "hour": hour,
        "data": result,
        "average_per_day": average_per_day  # <-- שדה חדש
    }