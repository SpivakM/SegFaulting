# FileFlow

**FileFlow** is a FastAPI web application for analysing drone telemetry logs. Upload an ArduPilot `.bin` or `.log` file and get an interactive 3-D flight trajectory and detailed flight metrics.

## Features

- **3-D trajectory visualisation** — Plotly scatter-3D coloured by time
- **GPS → ENU conversion** — geodetic coordinates translated to a local East-North-Up frame
- **IMU integration** — Madgwick AHRS filter + numerical integration to estimate velocity
- **Flight statistics** — distance, velocity, acceleration, altitude, displacement
- **Session-based storage** — each upload is isolated; expired sessions are purged automatically
- **Security headers** — `X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`

## Quick start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the development server (from the repo root)
uvicorn src.main:app --reload

# OR change to src/ first
cd src && uvicorn main:app --reload
```

Then open <http://127.0.0.1:8000> in your browser.

## Docker

```bash
docker build -t fileflow .
docker run -p 8000:8000 fileflow
```

## Running tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Project layout

```
SegFaulting/
├── src/
│   ├── main.py               # FastAPI application & routes
│   ├── db.py                 # Async SQLite session store
│   ├── log_parser.py         # MAVLink binary log parser
│   ├── gps_to_enu.py         # GPS → ENU coordinate conversion
│   ├── integrator.py         # IMU integration (Madgwick + trapezoid)
│   ├── services/
│   │   └── flight_service.py # Business logic: processing + stats
│   ├── templates/            # Jinja2 HTML templates
│   └── static/               # CSS & JavaScript
├── tests/                    # pytest test suite
│   ├── test_main.py          # Integration tests (TestClient)
│   ├── test_log_parser.py    # Unit tests
│   ├── test_gps_to_enu.py    # Unit tests
│   ├── test_integrator.py    # Unit tests
│   └── test_data/            # Sample ArduPilot binary logs
├── Dockerfile
├── pyproject.toml
├── requirements.txt
└── requirements-dev.txt
```

## API routes

| Method | Path             | Description                                    |
|--------|------------------|------------------------------------------------|
| GET    | `/`              | Upload form                                    |
| POST   | `/upload`        | Receive log file; redirect to results          |
| GET    | `/results`       | Process log and display flight metrics         |
| GET    | `/data-endpoint` | Download processed trajectory CSV              |

All upload/results routes are keyed by a `?session_id=<uuid>` query parameter so multiple users can work concurrently without interfering with each other.