# Sensor Network — Docker Compose Lab

Three containers on a private bridge network (`172.20.0.0/24`).

## Network map

```
172.20.0.0/24  (sensor-net)
│
├── 172.20.0.10  control-panel   nginx · serves dashboard + proxies /sensor
├── 172.20.0.20  sensor          FastAPI · simulates temp / humidity / gas
└── 172.20.0.30  ubuntu-node     plain Ubuntu · empty lab machine
```

## Quick start

```bash
# Build all images and start
docker compose up --build

# Or detached
docker compose up --build -d
```

| URL | What you see |
|-----|-------------|
| http://localhost | Control panel dashboard |
| http://localhost:8000/sensor | Raw sensor JSON (direct) |
| http://localhost:8000/docs | FastAPI Swagger UI |

## Exec into the Ubuntu node

```bash
docker exec -it ubuntu-node bash

# From inside ubuntu-node you can:
ping sensor                          # resolve by hostname
ping control-panel
curl http://172.20.0.20:8000/sensor  # hit the sensor API directly
curl http://172.20.0.10/             # fetch the dashboard HTML
```

## Stop everything

```bash
docker compose down
```

## File structure

```
sensor-network/
├── docker-compose.yml
├── sensor/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py
├── control-panel/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── index.html
└── ubuntu-node/
    ├── DoS.py
    └── Dockerfile
```

## DoS Attack ##

The script *DoS.py* inside the ubuntu machine performs a DoS attacks (slowloris) on the sensor server.
