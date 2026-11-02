"""Application factory. Start it with: uvicorn app.main:create_app --factory"""
import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import sessionmaker

from . import auth
from .config import DEFAULT_ENV_FILE, Settings, load_settings
from .database import make_engine

logger = logging.getLogger("pillbrook")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings(env_file=DEFAULT_ENV_FILE)

    engine = make_engine(settings.database_url) if settings.database_url else None

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        if engine is not None:
            engine.dispose()

    # Every API address starts with /api, so it can never collide with a screen address in the
    # React app. The interactive docs list every endpoint, so they exist only in development.
    app = FastAPI(
        title="Pill Brook Facility Maintenance API",
        docs_url="/api/docs" if settings.is_development else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = (
        sessionmaker(bind=engine, expire_on_commit=False) if engine is not None else None
    )

    # CORS is only needed when the frontend runs on a different origin. With none configured,
    # no CORS headers are sent and browsers block cross-origin calls.
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_credentials=True,
            allow_methods=["GET", "POST", "PATCH", "DELETE"],
            allow_headers=["Content-Type", "X-CSRF-Token"],
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        # The default response echoes the submitted values, which could include a password.
        # Return only which field failed and why (this also serves FR12).
        problems = [
            {"field": ".".join(str(p) for p in err["loc"] if p != "body"), "message": err["msg"]}
            for err in exc.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": problems})

    @app.exception_handler(Exception)
    async def unexpected_error(_request: Request, exc: Exception) -> JSONResponse:
        # Details go to the server log only; the caller learns nothing about the failure.
        logger.error("Unhandled error", exc_info=exc)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    api = APIRouter(prefix="/api")
    api.include_router(auth.router)

    @api.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(api)
    return app