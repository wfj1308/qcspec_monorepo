"""HTTP middleware for lightweight sovereign request validation."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class SovereignContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        sovereign_path = ""
        for key, value in request.query_params.multi_items():
            if not value:
                continue
            if key == "v_uri" or key.endswith("_uri"):
                if not value.startswith("v://") and not value.startswith("http://") and not value.startswith("https://"):
                    return JSONResponse(
                        status_code=400,
                        content={"detail": f"{key} must start with v:// or an allowed public URL"},
                    )
                sovereign_path = sovereign_path or value
        request.state.sovereign_path = sovereign_path
        return await call_next(request)
