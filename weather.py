from flask import Flask, request, jsonify, render_template  # Added render_template
from flask_cors import CORS
import requests
from datetime import datetime

# Configured to look for index.html and style.css in the current directory
app = Flask(__name__, template_folder='.', static_folder='.', static_url_path='')
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
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m&timezone=auto"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None

@app.route('/api/weather', methods=['GET'])
def weather_endpoint():
    city = request.args.get('city', '').strip()
    if not city:
        return jsonify({"error": "City name cannot be empty"}), 400

    loc = get_coordinates(city)
    if not loc:
        return jsonify({"error": "Location not found"}), 404

    data = get_weather(loc['lat'], loc['lon'])
    if not data:
        return jsonify({"error": "Failed to retrieve weather data"}), 500

    current = data["current_weather"]
    hourly = data["hourly"]
    forecast = []
    
    for i in range(1, 5):
        raw_time = datetime.fromisoformat(hourly["time"][i])
        forecast.append({
            "time": raw_time.strftime('%I:%M %p'),
            "temp": hourly["temperature_2m"][i],
            "humidity": hourly["relative_humidity_2m"][i],
            "wind": hourly["wind_speed_10m"][i]
        })

    return jsonify({
        "location": loc['name'],
        "lat": loc['lat'],
        "lon": loc['lon'],
        "current": {
            "time": datetime.fromisoformat(current["time"]).strftime('%Y-%m-%d %I:%M %p'),
            "temp": current["temperature"],
            "wind": current["windspeed"]
        },
        "forecast": forecast
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)