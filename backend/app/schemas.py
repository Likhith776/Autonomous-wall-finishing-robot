from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime


class ObstacleCreate(BaseModel):
    x: float = Field(..., ge=0, description="X coordinate of obstacle bottom-left corner (meters)")
    y: float = Field(..., ge=0, description="Y coordinate of obstacle bottom-left corner (meters)")
    width: float = Field(..., gt=0, description="Obstacle width (meters)")
    height: float = Field(..., gt=0, description="Obstacle height (meters)")


class ObstacleResponse(ObstacleCreate):
    id: int
    wall_id: int
    
    class Config:
        from_attributes = True


class WallCreate(BaseModel):
    width: float = Field(..., gt=0, le=100, description="Wall width in meters")
    height: float = Field(..., gt=0, le=100, description="Wall height in meters")
    obstacles: List[ObstacleCreate] = Field(default_factory=list)
    
    @validator('obstacles')
    def validate_obstacles(cls, obstacles, values):
        if 'width' in values and 'height' in values:
            wall_width = values['width']
            wall_height = values['height']
            for obs in obstacles:
                if obs.x + obs.width > wall_width:
                    raise ValueError(f"Obstacle exceeds wall width")
                if obs.y + obs.height > wall_height:
                    raise ValueError(f"Obstacle exceeds wall height")
        return obstacles


class WallResponse(BaseModel):
    id: int
    width: float
    height: float
    created_at: datetime
    obstacles: List[ObstacleResponse] = []
    
    class Config:
        from_attributes = True


class TrajectoryCreate(BaseModel):
    wall_id: int
    tool_width: float = Field(default=0.1, gt=0, description="Width of the finishing tool (meters)")
    overlap: float = Field(default=0.02, ge=0, lt=1, description="Overlap percentage between passes")


class TrajectoryResponse(BaseModel):
    id: int
    wall_id: int
    path_data: List[List[float]]
    total_distance: float
    computation_time: Optional[float]
    algorithm: str
    created_at: datetime
    coverage_percentage: float
    path_efficiency: Optional[float]
    
    class Config:
        from_attributes = True


class TrajectoryQuery(BaseModel):
    wall_id: Optional[int] = None
    min_distance: Optional[float] = None
    max_distance: Optional[float] = None
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0, ge=0)