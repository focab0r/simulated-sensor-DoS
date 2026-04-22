import random
import math
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(title="Sensor Node API")

# Allow the control-panel (and any host on the Docker network) to call us
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

_start_time = time.time()


def _noise(scale: float) -> float:
    return random.gauss(0, scale)


def get_sensor_readings() -> dict:
    t = time.time() - _start_time

    temperature = 26 + 8 * math.sin(t / 60) + _noise(0.3)
    temperature = round(max(0, min(80, temperature)), 2)

    humidity = 50 - 15 * math.sin(t / 60) + _noise(0.5)
    humidity = round(max(0, min(100, humidity)), 2)

    gas = 700 + 250 * math.sin(t / 20) + _noise(10)
    gas = round(max(300, min(5000, gas)), 2)

    if temperature > 35 or gas > 1000:
        status = "WARNING"
    elif temperature > 30 or gas > 800:
        status = "ELEVATED"
    else:
        status = "NOMINAL"

    return {
        "timestamp": round(t, 2),
        "temperature": {"value": temperature, "unit": "°C"},
        "humidity":    {"value": humidity,    "unit": "%"},
        "gas":         {"value": gas,         "unit": "ppm"},
        "status": status,
    }


@app.get("/sensor", response_class=JSONResponse)
def read_sensor():
    return get_sensor_readings()


@app.get("/health")
def health():
    return {"ok": True}
