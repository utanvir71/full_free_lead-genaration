from fastapi import FastAPI

from app.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="Zero-Money Restaurant Lead Generator")
    app.state.settings = settings if settings is not None else Settings.load()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
