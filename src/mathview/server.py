"""FastAPI app: the API, plus the static frontend.

Importing the topic modules is what registers them, so the imports below are
load-bearing rather than incidental.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from mathview.core.parse import ParseError
from mathview.core.registry import UnknownTopicError, available_topics, get_topic
from mathview.topics import functions as _functions  # noqa: F401  (registers topic)
from mathview.topics import growth as _growth  # noqa: F401  (registers topic)

WEB_ROOT = Path(__file__).resolve().parents[2] / "web"


class SequenceRequest(BaseModel):
    topic: str
    rows: list[str]
    params: dict[str, float] = {}


def create_app() -> FastAPI:
    app = FastAPI(title="MathView")

    @app.get("/api/topics")
    def topics() -> dict[str, list[str]]:
        return {"topics": available_topics()}

    @app.post("/api/sequence")
    def sequence(request: SequenceRequest) -> dict:
        try:
            generator = get_topic(request.topic)
        except UnknownTopicError:
            raise HTTPException(status_code=404, detail=f"no topic {request.topic!r}") from None

        try:
            return generator(request.rows, request.params).to_dict()
        except ParseError as error:
            raise HTTPException(status_code=400, detail=error.to_dict()) from None

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(WEB_ROOT / "index.html")

    app.mount("/static", StaticFiles(directory=WEB_ROOT), name="static")
    return app
