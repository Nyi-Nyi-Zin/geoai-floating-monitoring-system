import asyncio
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.schemas.health import HealthResponse
from app.services.health import get_health
from app.services.mqtt_bridge import mqtt_bridge


@asynccontextmanager
async def lifespan(_app: FastAPI):
    mqtt_bridge.start(asyncio.get_running_loop())
    try:
        yield
    finally:
        mqtt_bridge.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description=(
            "GeoAI decision-support API for managing reusable WGS84 spatial "
            "assets and future auditable prediction workflows."
        ),
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request.state.request_id = request.headers.get(
            "X-Request-ID",
            str(uuid.uuid4()),
        )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    def service_health() -> HealthResponse:
        return get_health()

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    register_exception_handlers(app)
    return app


app = create_app()
