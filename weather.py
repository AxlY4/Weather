from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# Your WeatherAPI Key
WEATHER_API_KEY = "3083d196a0fd46beaa1195309260408"

def map_weather_condition(text):
    text = str(text).lower()
    if any(w in text for w in ["rain", "drizzle", "shower"]):
        return "rainy"
    elif any(w in text for w in ["thunder", "storm"]):
        return "thunderstorm"
    elif any(w in text for w in ["fog", "mist", "haze", "overcast", "cloud"]):
        return "foggy"
    else:
        return "sunny"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get-weather-data', methods=['GET'])
def weather_endpoint():
    try:
        city = request.args.get('country', '').strip() or request.args.get('city', '').strip()
        if not city:
            return jsonify({"error": "Location cannot be empty"}), 400

        # WeatherAPI handles location search + current weather + forecast in 1 request
        url = f"http://api.weatherapi.com/v1/forecast.json?key={WEATHER_API_KEY}&q={city}&days=2&aqi=no&alerts=no"
        
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return jsonify({"error": f"Could not find location '{city}'"}), 404

        data = response.json()
        location_info = data['location']
        current_data = data['current']

        # Format current date & time
        try:
            current_dt = datetime.strptime(location_info['localtime'], '%Y-%m-%d %H:%M')
            formatted_date = current_dt.strftime('%A, %B %d, %Y')
            formatted_time = current_dt.strftime('%I:%M %p')
        except Exception:
            formatted_date = "Today"
            formatted_time = "Now"

        # Build hourly forecast (sampling every 3 hours)
        forecast = []
        hours = []
        for day in data.get('forecast', {}).get('forecastday', []):
            hours.extend(day.get('hour', []))

        # Grab hours in step intervals of 3 starting from hour index 3
        for i in range(3, min(len(hours), 24), 3):
            h = hours[i]
            try:
                dt = datetime.strptime(h['time'], '%Y-%m-%d %H:%M')
                f_date = dt.strftime('%Y-%m-%d')
                f_time = dt.strftime('%I:%M %p')
            except Exception:
                f_date = h.get('time', '')
                f_time = ""

            forecast.append({
                "date": f_date,
                "time": f_time,
                "temp": h.get('temp_c', "N/A"),
                "humidity": h.get('humidity', "N/A"),
                "wind": h.get('wind_kph', "N/A"),
                "condition": map_weather_condition(h.get('condition', {}).get('text', ''))
            })

        return jsonify({
            "location": f"{location_info['name']}, {location_info['country']}",
            "lat": location_info['lat'],
            "lon": location_info['lon'],
            "current": {
                "date": formatted_date,
                "time": formatted_time,
                "temp": current_data.get("temp_c", "N/A"),
                "wind": current_data.get("wind_kph", "N/A"),
                "condition": map_weather_condition(current_data.get("condition", {}).get("text", ""))
            },
            "forecast": forecast
        })

    except Exception as err:
        print(f"Unhandled Server Exception: {err}")
        return jsonify({"error": f"Internal Error: {str(err)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
