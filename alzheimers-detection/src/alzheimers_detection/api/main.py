"""FastAPI application entry point.

Run locally with: uvicorn alzheimers_detection.api.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from alzheimers_detection import __version__
from alzheimers_detection.api.routes import auth, results, speech
from alzheimers_detection.core import disclaimers
from alzheimers_detection.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Alzheimer's Digital Biomarker Platform",
        description=disclaimers.GENERAL_DISCLAIMER,
        version=__version__,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(results.router, prefix="/api/v1/results", tags=["results"])
    app.include_router(speech.router, prefix="/api/v1/speech", tags=["speech"])

    @app.get("/health", tags=["meta"])
    def health() -> dict:
        return {"status": "ok", "version": __version__}

    @app.get("/", tags=["meta"])
    def root() -> dict:
        return {
            "name": "alzheimers-detection",
            "version": __version__,
            "disclaimer": disclaimers.GENERAL_DISCLAIMER,
            "docs": "/docs",
        }

    return app


app = create_app()
