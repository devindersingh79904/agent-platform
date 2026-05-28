import os
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.utils.response_builder import error_response
from app.schemas.base_response import ErrorDetail

class APIAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Allow OPTIONS for CORS preflight
        if request.method == "OPTIONS":
            return await call_next(request)
            
        auth_enabled = os.getenv("API_AUTH_ENABLED", "false").lower() == "true"
        
        # Don't protect /health, /ready, /docs, /openapi.json, or root
        unprotected_paths = ["/", "/health", "/ready", "/docs", "/openapi.json"]
        if not auth_enabled or request.url.path in unprotected_paths or request.url.path.startswith("/ws/"):
            return await call_next(request)

        api_key = request.headers.get("X-API-Key")
        expected_key = os.getenv("API_KEY")

        if not expected_key:
            return JSONResponse(
                status_code=500,
                content=error_response(
                    request,
                    "Server misconfiguration: API_KEY not set",
                    [ErrorDetail(field=None, code="AUTH_ERROR", message="API_KEY must be set when API_AUTH_ENABLED is true")]
                ).model_dump(mode="json"),
            )

        if not api_key or api_key != expected_key:
            return JSONResponse(
                status_code=401,
                content=error_response(
                    request,
                    "Unauthorized",
                    [ErrorDetail(field=None, code="UNAUTHORIZED", message="Missing or invalid X-API-Key header")]
                ).model_dump(mode="json"),
            )

        return await call_next(request)
