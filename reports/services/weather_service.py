import requests


WEATHER_CODE_MAP = {
    0: "Clear Sky",
    1: "Mainly Clear",
    2: "Partly Cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing Rime Fog",
    51: "Light Drizzle",
    53: "Moderate Drizzle",
    55: "Dense Drizzle",
    56: "Freezing Drizzle",
    57: "Dense Freezing Drizzle",
    61: "Slight Rain",
    63: "Moderate Rain",
    65: "Heavy Rain",
    66: "Freezing Rain",
    67: "Heavy Freezing Rain",
    71: "Slight Snow",
    73: "Moderate Snow",
    75: "Heavy Snow",
    77: "Snow Grains",
    80: "Rain Showers",
    81: "Heavy Rain Showers",
    82: "Violent Rain Showers",
    85: "Snow Showers",
    86: "Heavy Snow Showers",
    95: "Thunderstorm",
    96: "Thunderstorm with Hail",
    99: "Severe Thunderstorm with Hail",
}


def fetch_weather(latitude, longitude):
    """
    Fetch current weather from Open-Meteo API.
    """

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}"
        f"&longitude={longitude}"
        "&current=temperature_2m,weather_code"
    )

    response = requests.get(url, timeout=10)

    if response.status_code != 200:
        raise Exception("Weather API request failed.")

    data = response.json()

    current = data.get("current", {})

    temperature = current.get("temperature_2m")
    weather_code = current.get("weather_code")

    weather_condition = WEATHER_CODE_MAP.get(
        weather_code,
        "Unknown"
    )

    return {
        "temperature": temperature,
        "weather_condition": weather_condition,
        "weather_code": weather_code,
    }