from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
from datetime import datetime

def map_weather_condition(code):
    if code in [0, 1, 2, 3]:
        return "sunny"
    elif code in [45, 48]:
        return "foggy"
    elif code in [95, 96, 99]:
        return "thunderstorm"
    elif code in [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82]:
        return "rainy"
    else:
        return "sunny"

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return render_template('index.html')

def get_coordinates(city_name):
    # Switched to Open-Meteo's direct Geocoding API (Render friendly & fast!)
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}&count=1&language=en&format=json"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "results" in data and len(data["results"]) > 0:
                result = data["results"][0]
                return {
                    "lat": float(result["latitude"]),
                    "lon": float(result["longitude"]),
                    "name": result["name"]
                }
        return None
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None

def get_weather(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code&timezone=auto"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Weather fetch error: {e}")
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

    current = data.get("current_weather", {})
    hourly = data.get("hourly", {})

    current_condition = map_weather_condition(current.get("weathercode", current.get("weather_code", 0)))

    current_datetime = datetime.fromisoformat(current.get("time", "").replace('Z', ''))
    formatted_date = current_datetime.strftime('%A, %B %d, %Y')
    formatted_time = current_datetime.strftime('%I:%M %p')

    forecast = []
    hourly_codes = hourly.get("weather_code", hourly.get("weathercode", []))
    times = hourly.get("time", [])

    for i in range(3, 13, 3):
        if i < len(times):
            raw_time = datetime.fromisoformat(times[i].replace('Z', ''))
            code = hourly_codes[i] if i < len(hourly_codes) else 0

            forecast.append({
                "date": raw_time.strftime('%Y-%m-%d'),
                "time": raw_time.strftime('%I:%M %p'),
                "temp": hourly.get("temperature_2m", [0]*15)[i],
                "humidity": hourly.get("relative_humidity_2m", [0]*15)[i],
                "wind": hourly.get("wind_speed_10m", [0]*15)[i],
                "condition": map_weather_condition(code)
            })

    return jsonify({
        "location": loc['name'],
        "lat": loc['lat'],
        "lon": loc['lon'],
        "current": {
            "date": formatted_date,
            "time": formatted_time,
            "temp": current.get("temperature"),
            "wind": current.get("windspeed"),
            "condition": current_condition
        },
        "forecast": forecast
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
