# Wall-Finishing Robot Coverage System

A comprehensive autonomous wall-finishing robot control system featuring intelligent path planning, real-time trajectory visualization, and optimized database management.

## Features

- **Boustrophedon Coverage Planning** – Efficient back-and-forth path generation
- **Obstacle Avoidance** – Handles rectangular obstacles using cellular decomposition
- **FastAPI Backend** – High-performance RESTful API with comprehensive logging
- **SQLite Database** – Optimized storage with advanced indexing strategies
- **Interactive Visualization** – Real-time 2D canvas-based trajectory playback
- **Comprehensive Testing** – Full test suite with pytest

## Project Structure

```
wall-robot-coverage/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── database.py
│   │   ├── crud.py
│   │   ├── coverage_planner.py
│   │   └── middleware.py
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_api.py
│   ├── requirements.txt
│   └── README.md
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
└── README.md
```

## Quick Start

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### Frontend

```bash
cd frontend
python -m http.server 8080
```

Open your browser to `http://localhost:8080`

## API Endpoints

### Walls
- `POST /walls/` – Create wall with obstacles
- `GET /walls/` – List all walls
- `GET /walls/{id}` – Get specific wall
- `DELETE /walls/{id}` – Delete wall

### Trajectories
- `POST /trajectories/` – Generate coverage trajectory
- `GET /trajectories/{id}` – Get specific trajectory
- `POST /trajectories/query` – Query trajectories with filters
- `DELETE /trajectories/{id}` – Delete trajectory

### Example Request

```json
POST /walls/
{
  "width": 5.0,
  "height": 5.0,
  "obstacles": [
    {"x": 2.0, "y": 2.0, "width": 0.25, "height": 0.25}
  ]
}
```

```json
POST /trajectories/
{
  "wall_id": 1,
  "tool_width": 0.1,
  "overlap": 0.02
}
```

## Testing

```bash
cd backend
pytest tests/ -v
```

## Algorithm

The system implements the Boustrophedon (ox-plowing) cellular decomposition algorithm for optimal wall coverage. For obstacle-free walls, it generates horizontal sweeps. For walls with obstacles, it divides the workspace at obstacle boundaries and creates serpentine patterns with optimal connections between cells.

**Complexity:** O(n log n) time, O(m) space

## Documentation

Full API documentation available at `http://localhost:8000/docs`
