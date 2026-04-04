# FileFlow — FastAPI Two-Page App

A minimal, production-ready FastAPI app with two pages:

1. **`/`** — Upload page: accepts any file + optional description & tags
2. **`/results`** — Results page: displays file metadata after upload

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the server
uvicorn main:app --reload

# 3. Open in browser
# http://127.0.0.1:8000
```

## Project Structure

```
fastapi_app/
├── main.py              # FastAPI app & routes
├── requirements.txt     # Python dependencies
├── templates/
│   ├── upload.html      # Page 1: file upload form
│   └── results.html     # Page 2: upload summary
└── uploads/             # Saved files (auto-created)
```

## Routes

| Method | Path      | Description                          |
|--------|-----------|--------------------------------------|
| GET    | `/`       | File upload form                     |
| POST   | `/upload` | Handle upload, redirect to results   |
| GET    | `/results`| Show uploaded file metadata          |

## Features

- Drag-and-drop file upload
- Optional description & comma-separated tags
- File metadata display (size, MIME type, timestamp)
- POST → Redirect → GET pattern (PRG) to prevent double-submission
- Clean dark industrial UI with Jinja2 templates

> **Production note**: Replace the in-memory `last_upload` dict with a proper database (SQLite, PostgreSQL, etc.) for multi-user use.
