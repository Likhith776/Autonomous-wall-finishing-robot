import time
from typing import List, Tuple
import math


class Point:
    """2D Point representation"""
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
    
    def __repr__(self):
        return f"Point({self.x}, {self.y})"
    
    def distance_to(self, other: 'Point') -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)


class Rectangle:
    """Rectangle representation for walls and obstacles"""
    def __init__(self, x: float, y: float, width: float, height: float):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
    
    def contains_point(self, point: Point) -> bool:
        return (self.x <= point.x <= self.x + self.width and
                self.y <= point.y <= self.y + self.height)
    
    def intersects(self, other: 'Rectangle') -> bool:
        return not (self.x + self.width < other.x or
                   other.x + other.width < self.x or
                   self.y + self.height < other.y or
                   other.y + other.height < self.y)


class BoustrophedonPlanner:
    """
    Boustrophedon (ox-plowing) coverage path planner.
    
    This algorithm generates a back-and-forth mowing pattern that efficiently
    covers rectangular areas while avoiding obstacles. The approach:
    1. Divides the workspace into cells based on obstacle boundaries
    2. Generates serpentine paths within each cell
    3. Connects cells to create a complete coverage path
    """
    
    def __init__(self, wall_width: float, wall_height: float, 
                 tool_width: float = 0.1, overlap: float = 0.02):
        self.wall = Rectangle(0, 0, wall_width, wall_height)
        self.tool_width = tool_width
        self.overlap = overlap
        self.line_spacing = tool_width * (1 - overlap)
        self.obstacles: List[Rectangle] = []
    
    def add_obstacle(self, x: float, y: float, width: float, height: float):
        """Add a rectangular obstacle"""
        self.obstacles.append(Rectangle(x, y, width, height))
    
    def is_point_valid(self, point: Point) -> bool:
        """Check if point is within wall and not inside any obstacle"""
        if not self.wall.contains_point(point):
            return False
        
        for obstacle in self.obstacles:
            if obstacle.contains_point(point):
                return False
        
        return True
    
    def generate_simple_boustrophedon(self) -> Tuple[List[List[float]], float, float]:
        """
        Generate a simple boustrophedon coverage path.
        For complex scenarios with obstacles, this uses cellular decomposition.
        """
        start_time = time.time()
        
        if not self.obstacles:
            # Simple case: no obstacles
            path = self._generate_simple_path()
        else:
            # Complex case: with obstacles using cellular decomposition
            path = self._generate_decomposed_path()
        
        computation_time = time.time() - start_time
        total_distance = self._calculate_path_distance(path)
        
        return path, total_distance, computation_time
    
    def _generate_simple_path(self) -> List[List[float]]:
        """Generate simple back-and-forth path without obstacles"""
        path = []
        y = 0
        direction = 1  # 1 for left-to-right, -1 for right-to-left
        
        while y <= self.wall.height:
            if direction == 1:
                path.append([0, y])
                path.append([self.wall.width, y])
            else:
                path.append([self.wall.width, y])
                path.append([0, y])
            
            y += self.line_spacing
            direction *= -1
        
        return path
    
    def _generate_decomposed_path(self) -> List[List[float]]:
        """Generate path using cellular decomposition for obstacle avoidance"""
        # Create vertical slices at obstacle boundaries
        critical_x = sorted(set([0, self.wall.width] + 
                              [obs.x for obs in self.obstacles] +
                              [obs.x + obs.width for obs in self.obstacles]))
        
        cells = []
        for i in range(len(critical_x) - 1):
            x_min = critical_x[i]
            x_max = critical_x[i + 1]
            
            # Find vertical segments in this slice that are obstacle-free
            segments = self._find_free_segments(x_min, x_max)
            for y_min, y_max in segments:
                cells.append((x_min, x_max, y_min, y_max))
        
        # Generate path through cells
        path = []
        for cell_idx, (x_min, x_max, y_min, y_max) in enumerate(cells):
            cell_path = self._cover_cell(x_min, x_max, y_min, y_max, cell_idx)
            
            # Connect to previous cell
            if path and cell_path:
                path.append(cell_path[0])
            
            path.extend(cell_path)
        
        return path
    
    def _find_free_segments(self, x_min: float, x_max: float) -> List[Tuple[float, float]]:
        """Find vertical segments that are free of obstacles in a slice"""
        # Sample the vertical line at x_mid
        x_mid = (x_min + x_max) / 2
        
        # Collect obstacle y-boundaries in this slice
        obstacle_ys = []
        for obs in self.obstacles:
            if obs.x < x_max and obs.x + obs.width > x_min:
                obstacle_ys.append((obs.y, obs.y + obs.height))
        
        # Sort and merge overlapping obstacles
        obstacle_ys.sort()
        merged = []
        for start, end in obstacle_ys:
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        
        # Find free segments
        segments = []
        current_y = 0
        for obs_start, obs_end in merged:
            if current_y < obs_start:
                segments.append((current_y, obs_start))
            current_y = max(current_y, obs_end)
        
        if current_y < self.wall.height:
            segments.append((current_y, self.wall.height))
        
        return segments
    
    def _cover_cell(self, x_min: float, x_max: float, 
                    y_min: float, y_max: float, cell_idx: int) -> List[List[float]]:
        """Generate boustrophedon pattern within a cell"""
        path = []
        y = y_min
        direction = 1 if cell_idx % 2 == 0 else -1
        
        while y <= y_max:
            if direction == 1:
                path.append([x_min, y])
                path.append([x_max, y])
            else:
                path.append([x_max, y])
                path.append([x_min, y])
            
            y += self.line_spacing
            direction *= -1
        
        return path
    
    def _calculate_path_distance(self, path: List[List[float]]) -> float:
        """Calculate total path distance"""
        if len(path) < 2:
            return 0.0
        
        total = 0.0
        for i in range(len(path) - 1):
            p1 = Point(path[i][0], path[i][1])
            p2 = Point(path[i+1][0], path[i+1][1])
            total += p1.distance_to(p2)
        
        return total
    
    def calculate_efficiency(self, total_distance: float) -> float:
        """Calculate path efficiency vs theoretical minimum"""
        wall_area = self.wall.width * self.wall.height
        obstacle_area = sum(obs.width * obs.height for obs in self.obstacles)
        effective_area = wall_area - obstacle_area
        
        # Theoretical minimum is area divided by tool width
        theoretical_min = effective_area / self.tool_width
        
        if theoretical_min == 0:
            return 0.0
        
        return min(theoretical_min / total_distance * 100, 100.0)
