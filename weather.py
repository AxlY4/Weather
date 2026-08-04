from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
from datetime import datetime

def map_weather_condition(code):
    try:
        code = int(code)
    except (ValueError, TypeError):
        code = 0
        
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
    # Open-Meteo Geocoding API (Fast and reliable)
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
                    "name": result.get("name", city_name)
                }
        return None
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None

def get_weather(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code,weathercode&timezone=auto"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Weather error: {e}")
        return None

@app.route('/get-weather-data', methods=['GET'])
def weather_endpoint():
    try:
        city = request.args.get('country', '').strip()
        if not city:
            return jsonify({"error": "Location cannot be empty"}), 400

        loc = get_coordinates(city)
        if loc is None:
            return jsonify({"error": f"Could not find location '{city}'"}), 404

        data = get_weather(loc['lat'], loc['lon'])
        if data is None:
            return jsonify({"error": "Failed to fetch weather data from API"}), 500

        current = data.get("current_weather", {})
        hourly = data.get("hourly", {})

        # Extract current weather safely
        current_code = current.get("weathercode", current.get("weather_code", 0))
        current_condition = map_weather_condition(current_code)

        # Parse current date and time safely
        raw_current_time = current.get("time", "")
        if raw_current_time:
            try:
                current_dt = datetime.fromisoformat(raw_current_time.replace('Z', ''))
                formatted_date = current_dt.strftime('%A, %B %d, %Y')
                formatted_time = current_dt.strftime('%I:%M %p')
            except Exception:
                formatted_date = "Today"
                formatted_time = "Now"
        else:
            formatted_date = "Today"
            formatted_time = "Now"

        # Parse hourly forecast data safely
        forecast = []
        hourly_times = hourly.get("time", [])
        hourly_temps = hourly.get("temperature_2m", [])
        hourly_humidity = hourly.get("relative_humidity_2m", [])
        hourly_wind = hourly.get("wind_speed_10m", hourly.get("windspeed_10m", []))
        hourly_codes = hourly.get("weather_code", hourly.get("weathercode", []))

        for i in range(3, 13, 3):
            if i < len(hourly_times):
                t_str = hourly_times[i]
                try:
                    dt = datetime.fromisoformat(t_str.replace('Z', ''))
                    f_date = dt.strftime('%Y-%m-%d')
                    f_time = dt.strftime('%I:%M %p')
                except Exception:
                    f_date = t_str
                    f_time = ""

                temp_val = hourly_temps[i] if i < len(hourly_temps) else "N/A"
                hum_val = hourly_humidity[i] if i < len(hourly_humidity) else "N/A"
                wind_val = hourly_wind[i] if i < len(hourly_wind) else "N/A"
                code_val = hourly_codes[i] if i < len(hourly_codes) else 0

                forecast.append({
                    "date": f_date,
                    "time": f_time,
                    "temp": temp_val,
                    "humidity": hum_val,
                    "wind": wind_val,
                    "condition": map_weather_condition(code_val)
                })

        return jsonify({
            "location": loc['name'],
            "lat": loc['lat'],
            "lon": loc['lon'],
            "current": {
                "date": formatted_date,
                "time": formatted_time,
                "temp": current.get("temperature", "N/A"),
                "wind": current.get("windspeed", "N/A"),
                "condition": current_condition
            },
            "forecast": forecast
        })

    except Exception as err:
        # Prevents quiet 500 crashes and prints full error
        print(f"Server Error: {err}")
        return jsonify({"error": f"Internal Error: {str(err)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)