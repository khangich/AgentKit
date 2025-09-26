"""FastAPI server for AgentKit."""

from __future__ import annotations

import json
import os
import runpy
from pathlib import Path
from typing import Any, Dict, List

from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sse_starlette.sse import EventSourceResponse

from . import ui
from .config import data_dir, load_config
from .state import store


def create_app(agent_path: str | Path | None = None) -> FastAPI:
    agent_path = Path(agent_path or Path.cwd() / "agent_app.py").resolve()
    templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # pragma: no cover - lifecycle wiring
        data_dir()
        load_config()
        yield

    app = FastAPI(title="AgentKit", lifespan=lifespan)
    static_dir = Path(__file__).parent / "static"

    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    app.state.agent_path = agent_path
    app.state.templates = templates

    def execute_app(runtime: ui.RuntimeContext) -> ui.RuntimeContext:
        with ui.use_runtime(runtime):
            runpy.run_path(str(app.state.agent_path), run_name="__agentkit__")
        return runtime

    def render_page(request: Request) -> HTMLResponse:
        runtime = ui.RuntimeContext(mode="render")
        execute_app(runtime)
        page_spec = runtime.rendered_page
        if not page_spec:
            raise HTTPException(status_code=500, detail="Agent page did not render any content.")
        return app.state.templates.TemplateResponse(
            request,
            "index.html",
            {
                "title": page_spec.title,
                "description": page_spec.description,
                "page": page_spec,
            },
        )

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        return render_page(request)

    async def _persist_uploads(files: Dict[str, List[UploadFile]]) -> Dict[str, List[Dict[str, Any]]]:
        saved: Dict[str, List[Dict[str, Any]]] = {}
        upload_root = data_dir() / "uploads"
        upload_root.mkdir(parents=True, exist_ok=True)
        for field, uploads in files.items():
            saved[field] = []
            for upload in uploads:
                destination = upload_root / f"{upload.filename or 'upload'}"
                # Ensure unique name
                counter = 1
                while destination.exists():
                    destination = upload_root / f"{destination.stem}-{counter}{destination.suffix}"
                    counter += 1
                content = await upload.read()
                destination.write_bytes(content)
                await upload.close()
                file_id = store.save_upload(
                    destination,
                    original_name=upload.filename or "upload",
                    mime=upload.content_type or "application/octet-stream",
                    size=len(content),
                )
                saved[field].append({"path": destination, "id": file_id})
        return saved

    @app.post("/run")
    async def start_run(request: Request) -> JSONResponse:
        form = await request.form()
        trigger = form.get("_trigger")
        inputs: Dict[str, Any] = {}
        raw_files: Dict[str, List[UploadFile]] = {}
        for key, value in form.multi_items():
            if key == "_trigger":
                continue
            if isinstance(value, UploadFile):
                raw_files.setdefault(key, []).append(value)
            else:
                inputs[key] = str(value)
        saved_files = await _persist_uploads(raw_files)
        runtime = ui.RuntimeContext(
            mode="execute",
            inputs=inputs,
            files={k: [item["path"] for item in items] for k, items in saved_files.items()},
            trigger=trigger,
        )
        execute_app(runtime)
        run_id = runtime.run_ids[-1] if runtime.run_ids else None
        if not run_id:
            raise HTTPException(status_code=400, detail="Agent did not start a run.")
        return JSONResponse({"run_id": run_id})

    @app.get("/stream/{run_id}")
    async def stream(run_id: str):
        queue = store.subscribe(run_id)

        async def event_generator():
            try:
                for event in store.iter_events(run_id):
                    yield format_sse(event)
                while True:
                    event = await queue.get()
                    yield format_sse(event)
            finally:
                store.unsubscribe(run_id, queue)

        return EventSourceResponse(event_generator())

    @app.get("/logs/{run_id}")
    async def logs(run_id: str) -> PlainTextResponse:
        events = list(store.iter_events(run_id))
        content = "\n".join(json.dumps(event) for event in events)
        return PlainTextResponse(content, media_type="application/jsonl")

    @app.get("/run/{run_id}")
    async def get_run(run_id: str) -> JSONResponse:
        run = store.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        return JSONResponse(run)

    @app.post("/upload")
    async def upload(file: UploadFile = File(...)) -> JSONResponse:
        saved = await _persist_uploads({"file": [file]})
        entries = saved.get("file") or []
        if not entries:
            raise HTTPException(status_code=500, detail="Upload failed")
        entry = entries[0]
        return JSONResponse({"file_id": entry["id"], "path": str(entry["path"])})

    return app


def format_sse(event: Dict[str, Any]) -> Dict[str, str]:
    return {
        "event": event.get("type", "message"),
        "data": json.dumps(event.get("payload", {})),
    }


AGENT_PATH = Path(__file__).resolve().parent.parent / "agent_app.py"
app = create_app(Path(os.getenv("AGENTKIT_APP", str(AGENT_PATH))))


__all__ = ["app", "create_app"]
