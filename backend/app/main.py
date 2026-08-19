from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List
import logging

from app import models, schemas, crud
from app.database import engine, get_db, init_db
from app.middleware import log_requests
from app.websocket import websocket_trajectory_stream
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Wall-Finishing Robot Coverage System",
    description="API for autonomous wall-finishing robot path planning and trajectory management",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.middleware("http")(log_requests)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    logger.info("Application started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Application shutting down")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Wall-Finishing Robot Coverage System API",
        "version": "1.0.0",
        "docs": "/docs",
        "metrics": "/metrics"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ====================================================================================
# WALL ENDPOINTS
# ====================================================================================

@app.post("/walls/", response_model=schemas.WallResponse, status_code=status.HTTP_201_CREATED)
async def create_wall(wall: schemas.WallCreate, db: Session = Depends(get_db)):
    """
    Create a new wall configuration with optional obstacles.
    
    - **width**: Wall width in meters (0-100m)
    - **height**: Wall height in meters (0-100m)
    - **obstacles**: List of rectangular obstacles
    """
    try:
        return crud.create_wall(db, wall)
    except Exception as e:
        logger.error(f"Error creating wall: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/walls/", response_model=List[schemas.WallResponse])
async def list_walls(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all walls with pagination"""
    return crud.get_walls(db, skip=skip, limit=limit)


@app.get("/walls/{wall_id}", response_model=schemas.WallResponse)
async def get_wall(wall_id: int, db: Session = Depends(get_db)):
    """Get a specific wall by ID"""
    wall = crud.get_wall(db, wall_id)
    if not wall:
        raise HTTPException(status_code=404, detail="Wall not found")
    return wall


@app.delete("/walls/{wall_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wall(wall_id: int, db: Session = Depends(get_db)):
    """Delete a wall and all associated trajectories"""
    if not crud.delete_wall(db, wall_id):
        raise HTTPException(status_code=404, detail="Wall not found")


# ====================================================================================
# TRAJECTORY ENDPOINTS
# ====================================================================================

@app.post("/trajectories/", status_code=status.HTTP_202_ACCEPTED)
async def create_trajectory(
    trajectory: schemas.TrajectoryCreate,
    background: bool = Query(False, description="Use background processing with Celery"),
    db: Session = Depends(get_db)
):
    """
    Generate a coverage trajectory for a wall.
    
    - **wall_id**: ID of the wall to plan for
    - **tool_width**: Width of the finishing tool in meters
    - **overlap**: Overlap percentage between passes (0-1)
    - **background**: If True, uses Celery for async processing (recommended for large walls)
    
    Returns:
    - If background=False: Complete trajectory data (sync)
    - If background=True: Task ID and status (async)
    """
    try:
        if background:
            # Async processing with Celery
            result = crud.create_trajectory_async(db, trajectory)
            return {
                "message": "Trajectory generation queued for background processing",
                "task_id": result["task_id"],
                "wall_id": result["wall_id"],
                "status": result["status"],
                "websocket_url": f"/ws/trajectory/{result['wall_id']}"
            }
        else:
            # Synchronous processing (original behavior)
            trajectory_result = crud.create_trajectory(db, trajectory)
            return {
                "message": "Trajectory generated successfully",
                "trajectory": trajectory_result,
                "status": "completed"
            }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating trajectory: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trajectories/{trajectory_id}", response_model=schemas.TrajectoryResponse)
async def get_trajectory(trajectory_id: int, db: Session = Depends(get_db)):
    """
    Get a specific trajectory by ID
    
    Returns complete trajectory data including path coordinates
    """
    trajectory = crud.get_trajectory(db, trajectory_id)
    if not trajectory:
        raise HTTPException(status_code=404, detail="Trajectory not found")
    return trajectory


@app.post("/trajectories/query", response_model=List[schemas.TrajectoryResponse])
async def query_trajectories(
    query: schemas.TrajectoryQuery,
    db: Session = Depends(get_db)
):
    """
    Query trajectories with filters.
    
    - **wall_id**: Filter by wall ID
    - **min_distance**: Minimum path distance
    - **max_distance**: Maximum path distance
    - **limit**: Maximum number of results (max 1000)
    - **offset**: Number of results to skip
    """
    return crud.query_trajectories(db, query)


@app.delete("/trajectories/{trajectory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trajectory(trajectory_id: int, db: Session = Depends(get_db)):
    """Delete a trajectory by ID"""
    if not crud.delete_trajectory(db, trajectory_id):
        raise HTTPException(status_code=404, detail="Trajectory not found")


# ====================================================================================
# CELERY TASK ENDPOINTS
# ====================================================================================

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """
    Get the status of a Celery background task
    
    - **task_id**: Task ID returned from POST /trajectories/ with background=True
    
    Returns task state and result if completed
    """
    from app.celery_app import celery_app
    
    task = celery_app.AsyncResult(task_id)
    
    response = {
        "task_id": task_id,
        "status": task.state,
        "info": None
    }
    
    if task.ready():
        # Task completed
        if task.successful():
            response["info"] = task.result
            response["result"] = task.result
        else:
            # Task failed
            response["info"] = str(task.info)
            response["error"] = str(task.info)
    else:
        # Task pending or running
        response["info"] = task.info
    
    return response


# ====================================================================================
# WEBSOCKET ENDPOINTS
# ====================================================================================

@app.websocket("/ws/trajectory/{wall_id}")
async def websocket_endpoint(websocket: WebSocket, wall_id: int):
    """
    WebSocket endpoint for real-time trajectory generation updates
    
    Connect to this endpoint to receive live updates when using background=True
    
    Messages received:
    - {"status": "started", "progress": 0}
    - {"status": "planning", "progress": 30}
    - {"status": "storing", "progress": 70}
    - {"status": "completed", "progress": 100, "trajectory_id": ..., "total_distance": ..., ...}
    - {"status": "error", "message": "..."}
    """
    await websocket_trajectory_stream(websocket, wall_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
