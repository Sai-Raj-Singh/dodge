"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="SAP O2C Flow Engine",
        version="0.1.0",
        description="Graph + RAG document flow query engine",
    )

    # ✅ Health check endpoint (IMPORTANT)
    @app.get("/health")
    def health():
        return {"status": "ok"}

    # Existing routes
    app.include_router(router, prefix="/api")

    return app


app = create_app()