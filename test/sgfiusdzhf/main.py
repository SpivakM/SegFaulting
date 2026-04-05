import asyncio
from contextlib import asynccontextmanager
import mimetypes
import os
import uuid
from datetime import datetime

import aiofiles
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from log_parser import get_data_from_file
from integrator import process_imu_data
from gps_to_enu import calculate_distance, convertGPS_to_ENU

app = FastAPI(title="FileFlow", version="1.0.1")

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = "uploads"
DATA_DIR = "data"
CHUNK_SIZE = 1024 * 64  # 64 KB
os.makedirs(name=UPLOAD_DIR, exist_ok=True)

# Словник у пам'яті. В однопотоковому asyncio базові операції зі словником (get, set)
# є атомарними. Lock не потрібен, оскільки контекст перемикається лише на `await`.
uploads: dict[str, dict] = {}


@app.get("/", response_class=HTMLResponse)
async def upload_page(request: Request) -> HTMLResponse:
    """Page 1: File upload form."""
    return templates.TemplateResponse(
        name="upload.html",
        request=request,
    )


@app.post("/upload")
async def handle_upload(
        request: Request,
        file: UploadFile = File(...),
        description: str = Form(default=""),
        tags: str = Form(default=""),
) -> RedirectResponse:
    """Stream the upload to disk with aiofiles (non-blocking) and calculate size."""
    upload_id = str(uuid.uuid4())

    # 1. Безпека: захист від Path Traversal та обробка None
    original_filename = file.filename or "unknown_file"
    safe_filename = os.path.basename(original_filename)
    dest_path = os.path.join(UPLOAD_DIR, f"{upload_id}_{safe_filename}")

    # 2. Продуктивність: рахуємо розмір під час запису, щоб уникнути os.path.getsize()
    file_size = 0
    async with aiofiles.open(file=dest_path, mode="wb") as buffer:
        while chunk := await file.read(CHUNK_SIZE):
            await buffer.write(chunk)
            file_size += len(chunk)

    mime_type, _ = mimetypes.guess_type(url=safe_filename)

    metadata = {
        "filename": original_filename,
        "content_type": file.content_type or mime_type or "application/octet-stream",
        "size_bytes": file_size,
        "size_human": _human_size(num=file_size),
        "description": description.strip() or "No description provided.",
        "tags": [t.strip() for t in tags.split(",") if t.strip()],
        "uploaded_at": datetime.now().strftime("%B %d, %Y at %H:%M:%S"),
        "path": dest_path,
    }

    # Атомарний запис завдяки GIL. Ніяких гонитов даних тут не буде.
    uploads[upload_id] = metadata

    return RedirectResponse(url=f"/results/{upload_id}", status_code=303)


@app.get("/results/{upload_id}", response_class=HTMLResponse)
async def results_page(request: Request, upload_id: str) -> HTMLResponse:
    """Page 2: Show metadata for the upload identified by upload_id."""
    data = uploads.get(upload_id)
    print(data)

    if data is None:
        raise HTTPException(
            status_code=404,
            detail="Upload not found. It may have expired.",
        )

    gps_data, imu_data = get_data_from_file(data["path"])
    gps_data = convertGPS_to_ENU(gps_data)
    imu_data = process_imu_data(imu_data)

    gps_data["color"] = imu_data["VelH"]

    data_path = os.path.join(DATA_DIR, "data.csv")
    gps_data[["x", "y", "z", "color"]].to_csv(data_path)
    data["data_path"] = data_path

    return templates.TemplateResponse(
        name="results.html",
        request=request,
        context={"data": data},
    )

@app.get("/data-endpoint")
async def get_data():
    file_path = "data/data.csv"

    # Optional: Logic to create/update the CSV file here

    return FileResponse(
        path=file_path,
        filename="data.csv",
        media_type="text/csv"
    )


def _human_size(num: int | float) -> str:
    """Convert a byte count to a human-readable string (B → TB)."""
    for unit in ["B", "KB", "MB", "GB"]:
        if num < 1024:
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} TB"
