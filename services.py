# services.py
import requests
from datetime import datetime, timezone

def fetch_all_alarms_for_month(year: int, month: int):
    """
    מושך את כל האזעקות של החודש הנבחר, בצורה יעילה עם pagination.
    """
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

    params = {
        "limit": limit,
        "offset": offset,
        "start": start_date.isoformat(),
        "end": end_date.isoformat()
    }

    while True:
        params["offset"] = offset
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        alarms = data.get("data", [])
        if not alarms:
            break

        for alarm in alarms:
            alarm_dt = datetime.fromisoformat(alarm["timestamp"].replace("Z", "+00:00")).astimezone(timezone.utc)
            if start_date <= alarm_dt < end_date:
                all_alarms.append(alarm)

        offset += limit
        if not data.get("pagination", {}).get("hasMore", False):
            break

    return all_alarms


def average_from_front_input(target_timestamp: str, city_name: str):
    """
    מחשב ממוצע יומי של אזעקות לפי שעה לעיר מסוימת.
    """
    dt = datetime.fromisoformat(target_timestamp.replace("Z", "+00:00")).astimezone(timezone.utc)
    year = dt.year
    month = dt.month
    hour = dt.hour

    alarms = fetch_all_alarms_for_month(year, month)
    daily_counts = {}

    for alarm in alarms:
        alarm_dt = datetime.fromisoformat(alarm["timestamp"].replace("Z", "+00:00")).astimezone(timezone.utc)
        if alarm_dt.hour != hour:
            continue
        if not any(city["name"] == city_name for city in alarm.get("cities", [])):
            continue
        day = alarm_dt.day
        daily_counts[day] = daily_counts.get(day, 0) + 1

    start_month = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        next_month = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        next_month = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    days_in_month = (next_month - start_month).days

    counts_list = [daily_counts.get(day, 0) for day in range(1, days_in_month + 1)]
    average = sum(counts_list) / len(counts_list) if counts_list else 0

    return {"average": average, "daily_counts": counts_list}