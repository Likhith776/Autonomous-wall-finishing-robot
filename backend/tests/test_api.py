import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db
from app.models import Base

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


class TestWallEndpoints:
    """Test wall CRUD operations"""
    
    def test_create_wall_simple(self):
        """Test creating a wall without obstacles"""
        response = client.post(
            "/walls/",
            json={"width": 5.0, "height": 5.0, "obstacles": []}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["width"] == 5.0
        assert data["height"] == 5.0
        assert len(data["obstacles"]) == 0
    
    def test_create_wall_with_obstacle(self):
        """Test creating a wall with obstacles"""
        response = client.post(
            "/walls/",
            json={
                "width": 5.0,
                "height": 5.0,
                "obstacles": [
                    {"x": 2.0, "y": 2.0, "width": 0.25, "height": 0.25}
                ]
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["obstacles"]) == 1
        assert data["obstacles"][0]["width"] == 0.25
    
    def test_create_wall_invalid_dimensions(self):
        """Test validation for invalid wall dimensions"""
        response = client.post(
            "/walls/",
            json={"width": -1.0, "height": 5.0, "obstacles": []}
        )
        assert response.status_code == 422
    
    def test_create_wall_obstacle_exceeds_bounds(self):
        """Test validation for obstacles exceeding wall bounds"""
        response = client.post(
            "/walls/",
            json={
                "width": 5.0,
                "height": 5.0,
                "obstacles": [
                    {"x": 4.0, "y": 4.0, "width": 2.0, "height": 2.0}
                ]
            }
        )
        assert response.status_code == 422
    
    def test_get_wall(self):
        """Test retrieving a wall by ID"""
        # Create wall first
        create_response = client.post(
            "/walls/",
            json={"width": 3.0, "height": 4.0, "obstacles": []}
        )
        wall_id = create_response.json()["id"]
        
        # Get wall
        response = client.get(f"/walls/{wall_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["width"] == 3.0
        assert data["height"] == 4.0
    
    def test_get_wall_not_found(self):
        """Test getting non-existent wall"""
        response = client.get("/walls/99999")
        assert response.status_code == 404
    
    def test_list_walls(self):
        """Test listing all walls"""
        # Create multiple walls
        for i in range(3):
            client.post(
                "/walls/",
                json={"width": float(i+1), "height": float(i+1), "obstacles": []}
            )
        
        response = client.get("/walls/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3
    
    def test_delete_wall(self):
        """Test deleting a wall"""
        # Create wall
        create_response = client.post(
            "/walls/",
            json={"width": 5.0, "height": 5.0, "obstacles": []}
        )
        wall_id = create_response.json()["id"]
        
        # Delete wall
        response = client.delete(f"/walls/{wall_id}")
        assert response.status_code == 204
        
        # Verify deletion
        get_response = client.get(f"/walls/{wall_id}")
        assert get_response.status_code == 404


class TestTrajectoryEndpoints:
    """Test trajectory operations"""
    
    def test_create_trajectory_simple(self):
        """Test creating a trajectory for a wall without obstacles"""
        # Create wall first
        wall_response = client.post(
            "/walls/",
            json={"width": 5.0, "height": 5.0, "obstacles": []}
        )
        wall_id = wall_response.json()["id"]
        
        # Create trajectory
        response = client.post(
            "/trajectories/",
            json={"wall_id": wall_id, "tool_width": 0.1, "overlap": 0.02}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["wall_id"] == wall_id
        assert data["total_distance"] > 0
        assert data["algorithm"] == "boustrophedon"
        assert len(data["path_data"]) > 0
    
    def test_create_trajectory_with_obstacles(self):
        """Test creating a trajectory for a wall with obstacles"""
        # Create wall with obstacle
        wall_response = client.post(
            "/walls/",
            json={
                "width": 5.0,
                "height": 5.0,
                "obstacles": [
                    {"x": 2.0, "y": 2.0, "width": 0.5, "height": 0.5}
                ]
            }
        )
        wall_id = wall_response.json()["id"]
        
        # Create trajectory
        response = client.post(
            "/trajectories/",
            json={"wall_id": wall_id, "tool_width": 0.1, "overlap": 0.02}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["total_distance"] > 0
        assert data["computation_time"] is not None
    
    def test_create_trajectory_invalid_wall(self):
        """Test creating trajectory for non-existent wall"""
        response = client.post(
            "/trajectories/",
            json={"wall_id": 99999, "tool_width": 0.1, "overlap": 0.02}
        )
        assert response.status_code == 404
    
    def test_get_trajectory(self):
        """Test retrieving a trajectory"""
        # Create wall and trajectory
        wall_response = client.post(
            "/walls/",
            json={"width": 3.0, "height": 3.0, "obstacles": []}
        )
        wall_id = wall_response.json()["id"]
        
        traj_response = client.post(
            "/trajectories/",
            json={"wall_id": wall_id, "tool_width": 0.1, "overlap": 0.02}
        )
        traj_id = traj_response.json()["id"]
        
        # Get trajectory
        response = client.get(f"/trajectories/{traj_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == traj_id
    
    def test_query_trajectories(self):
        """Test querying trajectories with filters"""
        # Create wall and trajectories
        wall_response = client.post(
            "/walls/",
            json={"width": 5.0, "height": 5.0, "obstacles": []}
        )
        wall_id = wall_response.json()["id"]
        
        client.post(
            "/trajectories/",
            json={"wall_id": wall_id, "tool_width": 0.1, "overlap": 0.02}
        )
        
        # Query trajectories
        response = client.post(
            "/trajectories/query",
            json={"wall_id": wall_id, "limit": 10, "offset": 0}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
    
    def test_delete_trajectory(self):
        """Test deleting a trajectory"""
        # Create wall and trajectory
        wall_response = client.post(
            "/walls/",
            json={"width": 5.0, "height": 5.0, "obstacles": []}
        )
        wall_id = wall_response.json()["id"]
        
        traj_response = client.post(
            "/trajectories/",
            json={"wall_id": wall_id, "tool_width": 0.1, "overlap": 0.02}
        )
        traj_id = traj_response.json()["id"]
        
        # Delete trajectory
        response = client.delete(f"/trajectories/{traj_id}")
        assert response.status_code == 204


class TestPerformance:
    """Test API performance and response times"""
    
    def test_wall_creation_performance(self):
        """Test wall creation response time"""
        response = client.post(
            "/walls/",
            json={"width": 10.0, "height": 10.0, "obstacles": []}
        )
        assert response.status_code == 201
        process_time = float(response.headers.get("X-Process-Time", "0"))
        assert process_time < 1.0  # Should complete in under 1 second
    
    def test_trajectory_generation_performance(self):
        """Test trajectory generation response time"""
        # Create wall
        wall_response = client.post(
            "/walls/",
            json={"width": 10.0, "height": 10.0, "obstacles": []}
        )
        wall_id = wall_response.json()["id"]
        
        # Generate trajectory
        response = client.post(
            "/trajectories/",
            json={"wall_id": wall_id, "tool_width": 0.1, "overlap": 0.02}
        )
        assert response.status_code == 201
        process_time = float(response.headers.get("X-Process-Time", "0"))
        assert process_time < 5.0  # Should complete in under 5 seconds


class TestHealthCheck:
    """Test application health endpoints"""
    
    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
