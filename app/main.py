from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import Settings
from app.db.session import create_engine_for, migrate_database
from app.web.routes.leads import router as leads_router
from app.web.routes.progress import router as progress_router
from app.web.routes.runs import router as runs_router
from app.web.security import SecurityMiddleware


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="Zero-Money Restaurant Lead Generator")
    app.state.settings = settings if settings is not None else Settings.load()
    app.state.engine = create_engine_for(app.state.settings)
    migrate_database(app.state.engine)
    app.add_middleware(SecurityMiddleware)
    app.mount("/static", StaticFiles(directory="app/web/static"), name="static")
    app.include_router(runs_router)
    app.include_router(progress_router)
    app.include_router(leads_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
