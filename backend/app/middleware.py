from fastapi import Request
import time
import structlog
from app.monitoring import (
    http_requests_total,
    http_request_duration_seconds,
    logger
)


async def log_requests(request: Request, call_next):
    """Enhanced middleware with structured logging and metrics"""
    start_time = time.time()
    
    # Structured logging - Request
    logger.info(
        "request_started",
        method=request.method,
        path=request.url.path,
        client_host=request.client.host if request.client else None
    )
    
    # Process request
    response = await call_next(request)
    
    # Calculate timing
    process_time = time.time() - start_time
    
    # Prometheus metrics
    http_requests_total.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    http_request_duration_seconds.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(process_time)
    
    # Structured logging - Response
    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_seconds=process_time
    )
    
    # Add timing header
    response.headers["X-Process-Time"] = str(process_time)
    
    return response
