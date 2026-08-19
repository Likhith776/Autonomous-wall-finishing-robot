from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app import models, schemas
from app.coverage_planner import BoustrophedonPlanner
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


def create_wall(db: Session, wall: schemas.WallCreate) -> models.Wall:
    """Create a wall with obstacles"""
    db_wall = models.Wall(width=wall.width, height=wall.height)
    db.add(db_wall)
    db.flush()  # Get wall ID
    
    for obstacle in wall.obstacles:
        db_obstacle = models.Obstacle(
            wall_id=db_wall.id,
            x=obstacle.x,
            y=obstacle.y,
            width=obstacle.width,
            height=obstacle.height
        )
        db.add(db_obstacle)
    
    db.commit()
    db.refresh(db_wall)
    logger.info(f"Created wall {db_wall.id} with {len(wall.obstacles)} obstacles")
    return db_wall


def get_wall(db: Session, wall_id: int) -> Optional[models.Wall]:
    """Retrieve a wall by ID"""
    return db.query(models.Wall).filter(models.Wall.id == wall_id).first()


def get_walls(db: Session, skip: int = 0, limit: int = 100) -> List[models.Wall]:
    """Retrieve all walls with pagination"""
    return db.query(models.Wall).offset(skip).limit(limit).all()


def delete_wall(db: Session, wall_id: int) -> bool:
    """Delete a wall and its associated data"""
    wall = get_wall(db, wall_id)
    if wall:
        db.delete(wall)
        db.commit()
        logger.info(f"Deleted wall {wall_id}")
        return True
    return False


def create_trajectory(db: Session, trajectory_create: schemas.TrajectoryCreate) -> models.Trajectory:
    """Generate and store a coverage trajectory (synchronous)"""
    wall = get_wall(db, trajectory_create.wall_id)
    if not wall:
        raise ValueError(f"Wall {trajectory_create.wall_id} not found")
    
    # Initialize planner
    planner = BoustrophedonPlanner(
        wall.width, 
        wall.height,
        trajectory_create.tool_width,
        trajectory_create.overlap
    )
    
    # Add obstacles
    for obstacle in wall.obstacles:
        planner.add_obstacle(obstacle.x, obstacle.y, obstacle.width, obstacle.height)
    
    # Generate path
    path_data, total_distance, computation_time = planner.generate_simple_boustrophedon()
    path_efficiency = planner.calculate_efficiency(total_distance)
    
    # Store trajectory
    db_trajectory = models.Trajectory(
        wall_id=wall.id,
        path_data=path_data,
        total_distance=total_distance,
        computation_time=computation_time,
        algorithm="boustrophedon",
        coverage_percentage=100.0,
        path_efficiency=path_efficiency
    )
    
    db.add(db_trajectory)
    db.commit()
    db.refresh(db_trajectory)
    
    logger.info(f"Generated trajectory {db_trajectory.id} for wall {wall.id} "
                f"(distance: {total_distance:.2f}m, time: {computation_time:.3f}s)")
    
    return db_trajectory


def create_trajectory_async(db: Session, trajectory_create: schemas.TrajectoryCreate) -> dict:
    """Queue trajectory generation as background task"""
    from app.tasks import generate_trajectory_async
    
    wall = get_wall(db, trajectory_create.wall_id)
    if not wall:
        raise ValueError(f"Wall {trajectory_create.wall_id} not found")
    
    # Queue the task
    task = generate_trajectory_async.delay(
        trajectory_create.wall_id,
        trajectory_create.tool_width,
        trajectory_create.overlap
    )
    
    logger.info(f"Queued trajectory generation for wall {wall.id}, task_id: {task.id}")
    
    return {
        "task_id": task.id,
        "wall_id": wall.id,
        "status": "queued"
    }


def get_trajectory(db: Session, trajectory_id: int) -> Optional[models.Trajectory]:
    """Retrieve a trajectory by ID"""
    return db.query(models.Trajectory).filter(models.Trajectory.id == trajectory_id).first()


def query_trajectories(db: Session, query: schemas.TrajectoryQuery) -> List[models.Trajectory]:
    """Query trajectories with filters"""
    q = db.query(models.Trajectory)
    
    if query.wall_id:
        q = q.filter(models.Trajectory.wall_id == query.wall_id)
    
    if query.min_distance:
        q = q.filter(models.Trajectory.total_distance >= query.min_distance)
    
    if query.max_distance:
        q = q.filter(models.Trajectory.total_distance <= query.max_distance)
    
    return q.order_by(models.Trajectory.created_at.desc()).offset(query.offset).limit(query.limit).all()


def delete_trajectory(db: Session, trajectory_id: int) -> bool:
    """Delete a trajectory"""
    trajectory = get_trajectory(db, trajectory_id)
    if trajectory:
        db.delete(trajectory)
        db.commit()
        logger.info(f"Deleted trajectory {trajectory_id}")
        return True
    return False
