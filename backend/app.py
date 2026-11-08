from flask import Flask, request, jsonify
import requests
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/weather", methods=["GET"])
def weather():
    city = request.args.get("city", "").strip()

    if not city:
        app.logger.warning("Weather request received without city parameter")
        return jsonify({"error": "city parameter is required"}), 400

    app.logger.info(f"Weather lookup requested for city: {city}")

    try:
        # Step 1: Get coordinates for the city
        geo_response = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={
                "name": city,
                "count": 1
            },
            timeout=5
        )

        geo_response.raise_for_status()
        geo_data = geo_response.json()

        if "results" not in geo_data or not geo_data["results"]:
            app.logger.warning(f"City not found: {city}")
            return jsonify({"error": "city not found"}), 404

        location = geo_data["results"][0]

        latitude = location["latitude"]
        longitude = location["longitude"]
        city_name = location["name"]

        app.logger.info(
            f"Resolved city '{city}' "
            f"to lat={latitude}, lon={longitude}"
        )

        # Step 2: Get current weather
        weather_response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,wind_speed_10m"
            },
            timeout=15
        )

        weather_response.raise_for_status()
        weather_data = weather_response.json()

        current = (
            weather_data.get("current")
            or weather_data.get("current_weather")
        )

        if not current:
            app.logger.error(
                f"No weather data returned for city: {city_name}"
            )
            return jsonify({"error": "weather data unavailable"}), 500

        temperature = current.get(
            "temperature_2m",
            current.get("temperature")
        )
        windspeed = current.get(
            "wind_speed_10m",
            current.get("windspeed")
        )

        if temperature is None or windspeed is None:
            app.logger.error(
                f"Incomplete weather metrics for city: {city_name}"
            )
            return jsonify({"error": "weather data unavailable"}), 500

        result = {
            "city": city_name,
            "temperature": temperature,
            "windspeed": windspeed
        }

        app.logger.info(
            f"Successfully returned weather data for {city_name}"
        )

        return jsonify(result), 200

    except requests.exceptions.RequestException as e:
        app.logger.error(f"Open-Meteo request failed: {str(e)}")
        return jsonify({"error": "weather provider unavailable"}), 503

    except Exception:
        app.logger.exception("Unexpected error occurred")
        return jsonify({"error": "internal server error"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
