# Intervention Required: E2E Pipeline Blocked

## Timestamp

2026-07-08 15:56:30 +07:00 to 2026-07-08 15:58 +07:00

## Pipeline Status

- Step 1: Infrastructure started successfully with `docker compose up -d`.
- Step 1: PostgreSQL verified with `pg_isready`; result: accepting connections on port `5432`.
- Step 2: Database seed completed successfully after one code-level self-heal.
- Step 3: FastAPI booted successfully on `http://127.0.0.1:8000`.
- Step 4: API request reached the backend, but `/api/sync-price/8931111111111` returned `500` due to an external Apify network connection failure.

## Commands Executed

```powershell
docker compose up -d
docker exec guardian_postgres pg_isready -U postgres -p 5432
.\.venv\Scripts\python.exe backend/seed_db.py
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
.\.venv\Scripts\python.exe -c "import requests; r=requests.post('http://127.0.0.1:8000/api/sync-price/8931111111111'); print(r.status_code); print(r.text.encode('unicode_escape').decode('ascii'))"
```

Note: The Uvicorn command was run from the `backend` directory as:

```powershell
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Exact Error Log

HTTP status:

```text
500
```

Response payload:

```json
{"detail":"Scraper error: L\u1ed7i kh\xf4ng x\xe1c \u0111\u1ecbnh khi ch\u1ea1y scraper: Failed to connect to the server.\nReason: hyper_util::client::legacy::Error(\n    Connect,\n    ConnectError(\n        \"tcp connect error\",\n        100.56.108.245:443,\n        Os {\n            code: 10013,\n            kind: PermissionDenied,\n            message: \"An attempt was made to access a socket in a way forbidden by its access permissions.\",\n        },\n    ),\n)"}
```

Uvicorn access log:

```text
INFO:     127.0.0.1:65356 - "POST /api/sync-price/8931111111111 HTTP/1.1" 500 Internal Server Error
INFO:     127.0.0.1:65370 - "POST /api/sync-price/8931111111111 HTTP/1.1" 500 Internal Server Error
```

## Self-Healing Action Taken

Fixed `backend/seed_db.py` so Windows console encoding does not crash when seeded product names contain Vietnamese characters:

```python
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="backslashreplace")
```

Before the fix, the seed step failed while printing a product name:

```text
UnicodeEncodeError: 'charmap' codec can't encode character '\u1ee1' in position 32: character maps to <undefined>
```

After the fix, seed output completed:

```text
Ensuring pgvector extension is installed...
Creating database tables...
Tables created successfully.
Seeding data...
Skipped (Already exists): La Roche-Posay Anthelios XL SPF50+ PA++++ 50ml
Skipped (Already exists): Simple Purifying Gel Wash 150ml
Skipped (Already exists): S�p D�\u1ee1ng \u1ea8m Vaseline 50ml
Database seeded successfully!
```

## Required Human Action

Please allow outbound HTTPS traffic from the backend process to Apify, or run the E2E test from a network/security context where Python can open TLS connections to Apify.

The blocking OS-level socket error is:

```text
code: 10013
kind: PermissionDenied
message: "An attempt was made to access a socket in a way forbidden by its access permissions."
```

This is not a Python import, model, or SQLAlchemy bug. The backend reached the scraper call and failed when the Apify client attempted to connect externally.

## Notes

- The active interpreter for backend execution is `.\.venv\Scripts\python.exe`; the system `python` does not have backend dependencies installed.
- `backend/requirements.txt` still contains unresolved merge markers and should be cleaned before dependency reinstall or CI usage.
- Uvicorn was stopped after the blocked API test.
