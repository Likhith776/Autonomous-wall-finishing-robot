from sqlalchemy import Column, Integer, Float, String, DateTime, JSON, Index, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Wall(Base):
    """Wall configuration model with optimization indices"""
    __tablename__ = "walls"
    
    id = Column(Integer, primary_key=True, index=True)
    width = Column(Float, nullable=False)
    height = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    obstacles = relationship("Obstacle", back_populates="wall", cascade="all, delete-orphan")
    trajectories = relationship("Trajectory", back_populates="wall", cascade="all, delete-orphan")
    
    # Composite index for common queries
    __table_args__ = (
        Index('idx_wall_dimensions', 'width', 'height'),
    )


class Obstacle(Base):
    """Obstacle model for rectangular obstacles on walls"""
    __tablename__ = "obstacles"
    
    id = Column(Integer, primary_key=True, index=True)
    wall_id = Column(Integer, ForeignKey("walls.id"), nullable=False, index=True)
    x = Column(Float, nullable=False)  # Bottom-left x coordinate
    y = Column(Float, nullable=False)  # Bottom-left y coordinate
    width = Column(Float, nullable=False)
    height = Column(Float, nullable=False)
    
    # Relationship
    wall = relationship("Wall", back_populates="obstacles")
    
    # Composite index for spatial queries
    __table_args__ = (
        Index('idx_obstacle_position', 'wall_id', 'x', 'y'),
        Index('idx_obstacle_bounds', 'x', 'y', 'width', 'height'),
    )


class Trajectory(Base):
    """Trajectory storage with optimized indexing for queries"""
    __tablename__ = "trajectories"
    
    id = Column(Integer, primary_key=True, index=True)
    wall_id = Column(Integer, ForeignKey("walls.id"), nullable=False, index=True)
    path_data = Column(JSON, nullable=False)  # Stores list of [x, y] coordinates
    total_distance = Column(Float, nullable=False)
    computation_time = Column(Float)  # Time taken to compute in seconds
    algorithm = Column(String, default="boustrophedon")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Metadata
    coverage_percentage = Column(Float, default=100.0)
    path_efficiency = Column(Float)  # Ratio of actual path to theoretical minimum
    
    # Relationship
    wall = relationship("Wall", back_populates="trajectories")
    
    # Composite indices for performance optimization
    __table_args__ = (
        Index('idx_trajectory_wall_created', 'wall_id', 'created_at'),
        Index('idx_trajectory_performance', 'total_distance', 'computation_time'),
    )