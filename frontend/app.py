import os
import requests

from flask import Flask, render_template, request

app = Flask(__name__)

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "http://localhost:5000"
)


@app.route("/", methods=["GET", "POST"])
def index():
    weather = None
    error = None

    if request.method == "POST":
        city = request.form.get("city")

        try:
            response = requests.get(
                f"{BACKEND_URL}/weather",
                params={"city": city},
                timeout=15
            )

            if response.status_code == 200:
                weather = response.json()
            else:
                try:
                    data = response.json()
                    error = data.get("error", f"HTTP {response.status_code} error")
                except ValueError:
                    error = f"Service unavailable (HTTP {response.status_code})"

        except Exception as e:
            error = str(e)

    return render_template(
        "index.html",
        weather=weather,
        error=error
    )


@app.route("/health")
def health():
    return {"status": "healthy"}, 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8080
    )
