# py-aas-rdf Utility Website

Full-stack utility to:
- Convert AAS JSON to RDF Turtle
- Convert RDF Turtle back to AAS JSON
- Convert AASQL text to AASQL JSON (grammar-based)
- Validate AASQL JSON against schema and convert to SPARQL
- Visualize RDF graph data using Reactodia

## Stack
- Backend: FastAPI
- Python package manager: uv
- Core converter: py-aas-rdf from GitHub (`experimental` branch)
- Frontend: React + MUI + Reactodia
- Runtime orchestration: Docker Compose

## One-line startup

```bash
docker compose up --build
```

After startup:
- UI: http://localhost:8000
- API: http://localhost:8000/api

## One-liner commands

Local setup from DockerHub:

```bash
docker run --rm -p 8000:8000 mhrimaz/aas-rdf-util:latest
```

Local full stack on one port (build UI + serve via FastAPI at :8000):

```bash
./run-local.sh
```

Production-style deploy on one port (detached):

```bash
./deploy.sh
```

Stop production stack:

```bash
docker compose down
```

## What the scripts do

- `run-local.sh`: runs `uv sync`, builds frontend, then starts FastAPI with reload on port `8000`.
- `deploy.sh`: runs `docker compose up --build -d`.
