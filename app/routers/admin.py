from fastapi import APIRouter
from datetime import datetime
from app.utils.logger import Logger

router = APIRouter(tags=["Admin & Monitoring"])


@router.api_route("/health", methods=["GET", "HEAD"])
async def get_health():
    from app.database import get_motor_client
    try:
        client = get_motor_client()
        await client.admin.command("ping")
        db_status = "healthy"
    except Exception as e:
        Logger.error(f"Health: MongoDB ping failed: {e}")
        db_status = "unhealthy"
    return {"status": "healthy", "database": db_status, "timestamp": datetime.utcnow().isoformat()}


@router.get("/metrics")
def get_metrics():
    return {"cpu_usage_pct": 1.5, "memory_usage_mb": 42.8,
            "active_websocket_connections": 0, "total_requests_processed": 104}


@router.get("/version")
def get_version():
    return {"app_name": "Safe Steps AI Backend", "version": "2.0.0", "api_environment": "production"}
