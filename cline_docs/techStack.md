# Tech Stack

## Backend
- **Primary Application Logic (`barebones.py`):**
  - Python
  - Pandas: For data manipulation and Excel file generation.
  - XlsxWriter: Pandas' engine for writing `.xlsx` files, used for formatting.
  - Standard Library: `os`, `json`, `datetime`, `math`, `collections`, `tempfile`.
- **Flask API (`app.py`):**
  - Flask: Micro web framework for serving the application and handling uploads/downloads.
  - Werkzeug: For security utilities like `secure_filename`.
  - Threading: For background processing of files.
- **FastAPI API (`backend/app.py`):**
  - FastAPI: Modern, fast web framework for building APIs.
  - Uvicorn: ASGI server for running FastAPI.
  - Pydantic: For data validation and settings management.
  - websockets: For real-time task status updates.
  - asyncio: For asynchronous operations.

## Frontend (`frontend/` directory)
- **Framework/Library:**
  - React (via Vite): JavaScript library for building user interfaces.
  - TypeScript: Superset of JavaScript adding static typing.
- **Build Tool:**
  - Vite: Fast frontend build tool.
- **Styling:**
  - Tailwind CSS: Utility-first CSS framework.
  - PostCSS: Tool for transforming CSS with JavaScript.
- **HTTP Client:**
  - Likely `fetch` API or a library like `axios` (to be confirmed by inspecting `frontend/src/api/client.ts` or similar).

## File Storage & Processing
- **Input Files:** JSON format.
- **Output Files:** Excel (`.xlsx`), Text Log (`.txt`).
- **Temporary File Storage:**
  - Local: System's temporary directory (e.g., `/tmp` or Windows equivalent via `tempfile.gettempdir()`), organized into subdirectories (`barebones_outputs`, `barebones_flask_outputs`, `barebones_fastapi_outputs`).
  - Heroku/Render: `/tmp` directory.
- **In-Memory File Handling:** `io.BytesIO` for holding file content before serving.

## Deployment (Inferred)
- Heroku (indicated by `DYNO` environment variable checks and `Procfile`).
- Render (indicated by `RENDER` environment variable checks).
- Procfile: Specifies commands run by the app's dynos on Heroku.
- `.buildpacks`: Likely Heroku buildpack configuration.
- `requirements.txt`: Python dependencies.
- `package.json`: Node.js dependencies (for frontend and potentially build scripts).

## Key Architectural Decisions
- **Dual API Structure:** The application appears to have both a Flask API and a FastAPI API. The FastAPI backend seems more recent and feature-rich (e.g., WebSockets, async processing).
- **Decoupled Processing Logic:** `barebones.py` contains the core data processing and Excel generation, which is called by both Flask and FastAPI apps.
- **Environment-Specific Configurations:** Path management and other settings adapt based on environment variables (e.g., `DYNO` for Heroku, `RENDER`).
- **Timestamped Unique Filenames:** Implemented to prevent file overwrites and improve traceability of generated reports and logs.
- **In-Memory Task Tracking:** Both Flask and FastAPI apps use in-memory dictionaries (`processing_tasks`) to track the status of file processing tasks. This is suitable for single-instance deployments but would need a distributed solution (e.g., Redis, database) for multi-instance scalability.
