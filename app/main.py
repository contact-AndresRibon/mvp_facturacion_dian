import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.web.router import web_router

settings = get_settings()


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="MVP SaaS facturacion electronica Colombia (DIAN-ready)",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)

    register_exception_handlers(app)

    app.include_router(api_router)
    app.include_router(web_router)

    static_path = "app/web/static"
    try:
        app.mount("/static", StaticFiles(directory=static_path), name="static")
    except RuntimeError:
        pass

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
