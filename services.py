
import requests

def fetch_city_data(city_name="קריית שמונה"):
    url = "https://redalert.orielhaim.com/api/stats/cities"
    headers = {
        "Authorization": "Bearer pr_TwGtUQvnMgnWbYTRHOnwrGcKuZvDqppALWqwWdoJLSpfvsUYGNiyOfVwWoPBrOdr",
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }
    params = {
        "city": city_name,
        "limit": 1
    }

    response = requests.get(url, headers=headers, params=params, timeout=5)
    response.raise_for_status()
    return response.json()