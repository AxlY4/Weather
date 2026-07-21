from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
from datetime import datetime

def map_weather_condition(code):
    # WMO Weather interpretation codes
    if code in [0, 1, 2, 3]:
        return "sunny"
    elif code in [45, 48]:
        return "foggy"
    elif code in [95, 96, 99]:
        return "thunderstorm"
    elif code in [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82]:
        return "rainy"
    else:
        # Default fallback
        return "sunny"

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return render_template('index.html')

def get_coordinates(city_name):
    headers = {"User-Agent": "WeatherAppAPI/1.0"}
    url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data:
                return {
                    "lat": float(data[0]["lat"]),
                    "lon": float(data[0]["lon"]),
                    "name": data[0]["display_name"].split(',')[0]
                }
        return None
    except Exception:
        return None

def get_weather(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&weathercode=true&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,weathercode&timezone=auto"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None

@app.route('/get-weather-data', methods=['GET'])
def weather_endpoint():
    city = request.args.get('country', '').strip()
    if not city:
        return jsonify({"error": "Location cannot be empty"}), 400

    loc = get_coordinates(city)
    if loc is None:
        return jsonify({"error": "Location not found"}), 404

    data = get_weather(loc['lat'], loc['lon'])
    if data is None:
        return jsonify({"error": "Failed to retrieve weather data"}), 500

    current = data["current_weather"]
    hourly = data["hourly"]

    # 1. Map current condition
    current_condition = map_weather_condition(current.get("weathercode", 0))

    # 2. Parse Current Date and Time
    current_datetime = datetime.fromisoformat(current["time"].replace('Z', ''))
    formatted_date = current_datetime.strftime('%A, %B %d, %Y')  # e.g., "Tuesday, July 21, 2026"
    formatted_time = current_datetime.strftime('%I:%M %p')       # e.g., "11:42 PM"

    # 3. Parse Forecast Data
    forecast = []
    for i in range(3, 13, 3):
        if i < len(hourly["time"]):
            raw_time = datetime.fromisoformat(hourly["time"][i].replace('Z', ''))
            code = hourly["weathercode"][i] if "weathercode" in hourly else 0

            forecast.append({
                "date": raw_time.strftime('%Y-%m-%d'),
                "time": raw_time.strftime('%I:%M %p'),
                "temp": hourly["temperature_2m"][i],
                "humidity": hourly["relative_humidity_2m"][i],
                "wind": hourly["wind_speed_10m"][i],
                "condition": map_weather_condition(code)
            })

    # 4. Return JSON
    return jsonify({
        "location": loc['name'],
        "lat": loc['lat'],
        "lon": loc['lon'],
        "current": {
            "date": formatted_date,       # <--- ADDED DATE
            "time": formatted_time,       # <--- ADDED TIME
            "temp": current["temperature"],
            "wind": current["windspeed"],
            "condition": current_condition
        },
        "forecast": forecast
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)