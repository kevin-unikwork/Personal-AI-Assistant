from fastapi import APIRouter
from app.database import async_session
from sqlalchemy import text

router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check route."""
    db_status = "ok"
    error_msg = None
    diag = {}
    try:
        # Extract host and port for diagnostics
        from urllib.parse import urlparse
        # Handle asyncpg prefix
        raw_url = settings.database_url.replace("postgresql+asyncpg://", "http://")
        parsed = urlparse(raw_url)
        host = parsed.hostname
        port = parsed.port or 5432
        
        diag["target_host"] = host
        diag["target_port"] = port
        
        # 1. Test DNS
        try:
            import socket
            ip = socket.gethostbyname(host)
            diag["dns_resolved_ip"] = ip
        except Exception as de:
            diag["dns_error"] = str(de)
            
        # 2. Test Raw Socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((host, port))
            s.close()
            diag["socket_connection"] = "success"
        except Exception as se:
            diag["socket_error"] = str(se)

        # 3. Test SQLAlchemy
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        db_status = "error"
        error_msg = str(e)
        
    return {
        "status": "healthy", 
        "database": db_status,
        "debug_info": error_msg,
        "diagnostics": diag
    }
