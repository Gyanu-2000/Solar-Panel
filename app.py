from flask import Flask, jsonify, render_template, request
import requests
import pandas as pd
import numpy as np

app = Flask(__name__)

# ---------- NASA API Function ----------
def get_nasa_data(lat, lon):
    """Fetch solar irradiance data from NASA POWER API."""
    lat = round(float(lat), 2)
    lon = round(float(lon), 2)

    start_year = 2024
    end_year = 2025

    nasa_url = (
        f"https://power.larc.nasa.gov/api/temporal/monthly/point?"
        f"parameters=ALLSKY_SFC_SW_DWN&start={start_year}&end={end_year}"
        f"&latitude={lat}&longitude={lon}&community=RE&format=JSON"
    )

    print(f"Fetching NASA data for lat={lat}, lon={lon}")
    response = requests.get(nasa_url)
    data = response.json()

    try:
        irradiance_data = data["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]

        df = pd.DataFrame(irradiance_data.items(), columns=["month", "irradiance_kWh_m2_day"])
        df = df[df["month"].str.match(r"^\d{6}$")]
        df = df[~df["month"].str.endswith("13")]

        df["month"] = pd.to_datetime(df["month"], format="%Y%m", errors='coerce')
        df = df.dropna(subset=["month"])
        df = df[df["irradiance_kWh_m2_day"] > 0]

        avg_irradiance = df["irradiance_kWh_m2_day"].mean()
        print(f"Avg irradiance: {avg_irradiance:.2f} kWh/m2/day")
        return avg_irradiance

    except Exception as e:
        print("Error parsing NASA data:", e)
        print("Response:", data)
        return None


# ---------- OpenWeather Function ----------
def get_weather_data(lat, lon):
    """Fetch current temperature and cloud cover from OpenWeather API."""
    OPENWEATHER_API_KEY = "5a21133496dc3525f37dc8c37aee77aa"  # 🔑 Replace with your API key
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"

    print(f"Fetching weather for lat={lat}, lon={lon}")
    res = requests.get(url)
    data = res.json()

    try:
        temp = data["main"]["temp"]
        clouds = data["clouds"]["all"]
        return temp, clouds
    except Exception as e:
        print("Weather data error:", e)
        print("Response:", data)
        return None, None


# ---------- Flask Routes ----------
@app.route('/')
def home():
    return render_template("index.html")


@app.route('/api/solar')
def get_solar_data():
    try:
        lat = float(request.args.get("lat"))
        lon = float(request.args.get("lon"))

        irradiance = get_nasa_data(lat, lon)
        temp, clouds = get_weather_data(lat, lon)

        if irradiance is None or temp is None:
            return jsonify({"error": "Data unavailable"}), 500

        # ----- Solar Power Calculations -----
        efficiency = (100 - clouds) / 100  # reduce efficiency with clouds
        adjusted_irradiance = irradiance * efficiency

        daily_generation = adjusted_irradiance * 1.6  # kWh/day per kW panel
        monthly_generation = daily_generation * 31
        cost_saving = monthly_generation * 6  # ₹6 per kWh (avg India rate)

        # simple 7-day prediction (trend + randomness)
        trend = np.linspace(daily_generation * 0.95, daily_generation * 1.05, 7)
        noise = np.random.uniform(-0.05, 0.05, 7)
        prediction = (trend * (1 + noise)).round(2).tolist()

        return jsonify({
            "irradiance": round(irradiance, 2),
            "temp": round(temp, 2),
            "clouds": clouds,
            "daily_gen": round(daily_generation, 2),
            "monthly_gen": round(monthly_generation, 2),
            "cost_saving": round(cost_saving, 2),
            "prediction": prediction
        })

    except Exception as e:
        print("Error in /api/solar:", e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
