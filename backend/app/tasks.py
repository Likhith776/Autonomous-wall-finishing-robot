from app.celery_app import celery_app
from app.coverage_planner import BoustrophedonPlanner
from app.database import SessionLocal
from app import models
import redis
import json
import logging

logger = logging.getLogger(__name__)

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)


@celery_app.task(bind=True, name="generate_trajectory_async")
def generate_trajectory_async(self, wall_id: int, tool_width: float, overlap: float):
    """
    Background task for trajectory generation with progress updates
    """
    db = SessionLocal()
    
    try:
        # Get wall data
        wall = db.query(models.Wall).filter(models.Wall.id == wall_id).first()
        if not wall:
            return {"error": "Wall not found"}
        
        # Publish progress: Starting
        redis_client.publish(
            f"trajectory:{wall_id}",
            json.dumps({"status": "started", "progress": 0})
        )
        logger.info(f"Task {self.request.id}: Started trajectory generation for wall {wall_id}")
        
        # Initialize planner
        planner = BoustrophedonPlanner(wall.width, wall.height, tool_width, overlap)
        
        # Add obstacles
        for obstacle in wall.obstacles:
            planner.add_obstacle(obstacle.x, obstacle.y, obstacle.width, obstacle.height)
        
        # Publish progress: Planning
        redis_client.publish(
            f"trajectory:{wall_id}",
            json.dumps({"status": "planning", "progress": 30})
        )
        
        # Generate path
        path_data, total_distance, computation_time = planner.generate_simple_boustrophedon()
        path_efficiency = planner.calculate_efficiency(total_distance)
        
        # Publish progress: Storing
        redis_client.publish(
            f"trajectory:{wall_id}",
            json.dumps({"status": "storing", "progress": 70})
        )
        
        # Store trajectory
        trajectory = models.Trajectory(
            wall_id=wall.id,
            path_data=path_data,
            total_distance=total_distance,
            computation_time=computation_time,
            algorithm="boustrophedon",
            coverage_percentage=100.0,
            path_efficiency=path_efficiency
        )
        
        db.add(trajectory)
        db.commit()
        db.refresh(trajectory)
        
        # Publish completion
        completion_data = {
            "status": "completed",
            "progress": 100,
            "trajectory_id": trajectory.id,
            "total_distance": total_distance,
            "computation_time": computation_time,
            "path_efficiency": path_efficiency,
            "coverage_percentage": 100.0
        }
        
        redis_client.publish(
            f"trajectory:{wall_id}",
            json.dumps(completion_data)
        )
        
        logger.info(f"Task {self.request.id}: Completed trajectory {trajectory.id} for wall {wall_id}")
        
        return {
            "trajectory_id": trajectory.id,
            "status": "completed"
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Task {self.request.id}: Error - {error_msg}")
        redis_client.publish(
            f"trajectory:{wall_id}",
            json.dumps({"status": "error", "message": error_msg})
        )
        raise
    finally:
        db.close()
