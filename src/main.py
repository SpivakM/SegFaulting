"""FileFlow — FastAPI application for drone telemetry analysis."""

import logging
import mimetypes
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import aiofiles
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

from db import create_session, get_session, init_db, purge_expired_sessions, update_session
from services.flight_service import compute_stats, process_flight_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_DIR = os.environ.get("FILEFLOW_UPLOAD_DIR", os.path.join(_BASE_DIR, "uploads"))
DATA_DIR = os.environ.get("FILEFLOW_DATA_DIR", os.path.join(_BASE_DIR, "data"))
CHUNK_SIZE = 64 * 1024  # 64 KB
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {".bin", ".log"}

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await purge_expired_sessions()
    yield


app = FastAPI(title="FileFlow", version="1.0.1", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=os.path.join(_BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(_BASE_DIR, "templates"))


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://cdn.plot.ly https://cdnjs.cloudflare.com; "
            "style-src 'self' https://fonts.googleapis.com; "
            "font-src https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self';"
        )
        return response


app.add_middleware(SecurityHeadersMiddleware)


@app.get("/", response_class=HTMLResponse)
async def upload_page(request: Request) -> HTMLResponse:
    """Page 1: File upload form."""
    return templates.TemplateResponse(name="upload.html", request=request)


@app.post("/upload")
async def handle_upload(
    file: UploadFile = File(...),
    description: str = Form(default=""),
    tags: str = Form(default=""),
) -> RedirectResponse:
    """Stream the upload to disk (non-blocking) and persist session metadata."""
    await purge_expired_sessions()

    original_filename = file.filename or "unknown_file"
    ext = os.path.splitext(original_filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unsupported file type '{ext}'. "
                f"Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
            ),
        )

    safe_filename = os.path.basename(original_filename)
    session_id = str(uuid.uuid4())
    dest_path = os.path.join(UPLOAD_DIR, f"{session_id}_{safe_filename}")

    file_size = 0
    async with aiofiles.open(dest_path, mode="wb") as buffer:
        while chunk := await file.read(CHUNK_SIZE):
            file_size += len(chunk)
            if file_size > MAX_UPLOAD_BYTES:
                await buffer.close()
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.",
                )
            await buffer.write(chunk)

    mime_type, _ = mimetypes.guess_type(safe_filename)
    now = datetime.now(timezone.utc)

    metadata = {
        "filename": original_filename,
        "content_type": file.content_type or mime_type or "application/octet-stream",
        "size_bytes": file_size,
        "size_human": _human_size(file_size),
        "description": description.strip()[:500] or "No description provided.",
        "tags": [t.strip() for t in tags.split(",") if t.strip()][:20],
        "uploaded_at": now.strftime("%B %d, %Y at %H:%M:%S UTC"),
        "path": dest_path,
    }

    await create_session(session_id, metadata)
    logger.info(
        "Uploaded '%s' as session %s (%s)",
        original_filename,
        session_id,
        metadata["size_human"],
    )

    return RedirectResponse(url=f"/results?session_id={session_id}", status_code=303)


@app.get("/results", response_class=HTMLResponse)
async def results_page(request: Request, session_id: str = "") -> HTMLResponse:
    """Page 2: Process the uploaded log file and display flight metrics."""
    if not session_id:
        return RedirectResponse(url="/")

    metadata = await get_session(session_id)
    if metadata is None:
        logger.warning("Session '%s' not found", session_id)
        return RedirectResponse(url="/")

    file_path = metadata.get("path", "")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="Uploaded file not found. It may have expired.",
        )

    try:
        gps_data, imu_data, data_path = process_flight_data(file_path, DATA_DIR, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error(
            "Failed to process flight data for session %s: %s",
            session_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to process the flight log. Is the file a valid ArduPilot log?",
        )

    await update_session(session_id, {"data_path": data_path})

    try:
        stats = compute_stats(gps_data, imu_data)
    except Exception as exc:
        logger.error(
            "Failed to compute stats for session %s: %s",
            session_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to compute flight statistics.",
        )

    context = {
        "data": metadata | stats,
        "session_id": session_id,
    }
    return templates.TemplateResponse(name="results.html", request=request, context=context)


@app.get("/data-endpoint")
async def get_data(session_id: str = "") -> FileResponse:
    """Return the processed GPS+velocity CSV for the given session."""
    if session_id:
        metadata = await get_session(session_id)
        if metadata:
            data_path = metadata.get("data_path")
            if data_path and os.path.exists(data_path):
                return FileResponse(path=data_path, filename="data.csv", media_type="text/csv")

    raise HTTPException(status_code=404, detail="Data file not found.")


def _human_size(num: int | float) -> str:
    """Convert a byte count to a human-readable string (B → TB)."""
    for unit in ["B", "KB", "MB", "GB"]:
        if num < 1024:
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} TB"
