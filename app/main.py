from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Zero-Money Restaurant Lead Generator")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
