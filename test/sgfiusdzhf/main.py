import asyncio
import mimetypes
import os
import uuid
from datetime import datetime

import aiofiles
import pandas as pd
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
os.makedirs(name=DATA_DIR, exist_ok=True)

latest_metadata: dict | None = None

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
    global latest_metadata

    if latest_metadata and "path" in latest_metadata:
        old_path = latest_metadata["path"]
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception as e:
                print(f"Cleanup warning: {e}")

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

    latest_metadata = {
        "filename": original_filename,
        "content_type": file.content_type or mime_type or "application/octet-stream",
        "size_bytes": file_size,
        "size_human": _human_size(num=file_size),
        "description": description.strip() or "No description provided.",
        "tags": [t.strip() for t in tags.split(",") if t.strip()],
        "uploaded_at": datetime.now().strftime("%B %d, %Y at %H:%M:%S"),
        "path": dest_path,
    }

    return RedirectResponse(url="/results", status_code=303)

@app.get("/results", response_class=HTMLResponse)
async def results_page(request: Request) -> HTMLResponse:
    if latest_metadata is None:
        return RedirectResponse(url="/")

    gps_data, imu_data = get_data_from_file(latest_metadata["path"])
    gps_data = convertGPS_to_ENU(gps_data)
    imu_data = process_imu_data(imu_data)

    gps_data = pd.merge_asof(gps_data, imu_data[["TimeUS", "VelH"]], on="TimeUS", direction="nearest")
    gps_data.rename(columns={"TimeUS": "color"}, inplace=True)

    data_path = os.path.join(DATA_DIR, "data.csv")
    gps_data[["x", "y", "z", "color"]].to_csv(data_path)
    latest_metadata["data_path"] = data_path

    return templates.TemplateResponse(
        name="results.html",
        request=request,
        context={"data": latest_metadata},
    )

@app.get("/data-endpoint")
async def get_data():
    file_path = os.path.join(DATA_DIR, "data.csv")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Data file not found.")
        
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
