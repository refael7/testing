import requests
from datetime import datetime, timedelta


def count_alarms_for_city_optimized(target_timestamp: str, city_name: str):
    target_dt = datetime.fromisoformat(target_timestamp.replace("Z", "+00:00")).replace(
        minute=0, second=0, microsecond=0
    )

    url = "https://redalert.orielhaim.com/api/stats/history"
    headers = {
        "Authorization": "Bearer pr_TwGtUQvnMgnWbYTRHOnwrGcKuZvDqppALWqwWdoJLSpfvsUYGNiyOfVwWoPBrOdr",
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    limit = 100
    offset = 0
    count = 0
    done = False

    while not done:
        params = {"city": city_name, "limit": limit, "offset": offset}
        response = requests.get(url, headers=headers, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        alarms = data.get("data", [])

        if not alarms:
            break

        for alarm in alarms:
            alarm_dt = datetime.fromisoformat(alarm["timestamp"].replace("Z", "+00:00")).replace(
                minute=0, second=0, microsecond=0
            )

            if alarm_dt < target_dt:
                done = True
                break

            if alarm_dt == target_dt:
                for city in alarm.get("cities", []):
                    if city["name"] == city_name:
                        count += 1

        offset += limit
        if not data.get("pagination", {}).get("hasMore", False):
            break

    return count


# 👇 הפונקציה החדשה שמשתמשת בקיימת
def average_from_front_input(target_timestamp: str, city_name: str):
    dt = datetime.fromisoformat(target_timestamp.replace("Z", "+00:00"))

    year = dt.year
    month = dt.month
    hour = dt.hour

    counts = []

    day = datetime(year, month, 1)
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)

    delta = timedelta(days=1)

    while day < next_month:
        daily_timestamp = day.replace(
            hour=hour, minute=0, second=0, microsecond=0
        ).isoformat() + "Z"

        count = count_alarms_for_city_optimized(daily_timestamp, city_name)
        counts.append(count)

        day += delta

    average = sum(counts) / len(counts) if counts else 0

    return {
        "average": average,
        "daily_counts": counts
    }

