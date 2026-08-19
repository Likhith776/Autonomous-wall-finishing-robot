import redis.asyncio as redis
from fastapi import WebSocket, WebSocketDisconnect
import json
import asyncio
import logging

logger = logging.getLogger(__name__)

# Redis connection pool
redis_pool = None


async def get_redis_connection():
    """Get Redis connection from pool"""
    global redis_pool
    if redis_pool is None:
        redis_pool = redis.ConnectionPool.from_url(
            "redis://localhost:6379",
            decode_responses=True
        )
    return redis.Redis(connection_pool=redis_pool)


async def websocket_trajectory_stream(websocket: WebSocket, wall_id: int):
    """Stream real-time trajectory generation updates via WebSocket"""
    await websocket.accept()
    
    rdb = await get_redis_connection()
    
    async def listen_redis():
        """Listen to Redis pub/sub for trajectory updates"""
        ps = rdb.pubsub()
        await ps.subscribe(f"trajectory:{wall_id}")
        
        try:
            while True:
                message = await ps.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message['data']:
                    try:
                        data = json.loads(message['data'])
                        await websocket.send_json(data)
                        logger.info(f"Sent WebSocket message: {data}")
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to decode message: {e}")
                await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Redis listener error: {e}")
        finally:
            await ps.unsubscribe(f"trajectory:{wall_id}")
            await ps.close()
    
    async def listen_websocket():
        """Listen to WebSocket for client messages"""
        try:
            while True:
                data = await websocket.receive_text()
                if data == "close":
                    break
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for wall {wall_id}")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
    
    # Run both listeners concurrently
    try:
        await asyncio.gather(listen_redis(), listen_websocket())
    finally:
        await websocket.close()
