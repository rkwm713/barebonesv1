# Codebase Summary

## Overview
This project is a web application designed to process uploaded JSON files and generate Excel reports and text-based log files. It features a Python backend with data processing capabilities and a React/TypeScript frontend for user interaction. The backend exposes APIs through both Flask and FastAPI, with FastAPI appearing to be the more modern and actively developed part.

## Key Components and Their Interactions

### 1. `barebones.py` (Core Processing Logic)
   - **Purpose:** Handles the core data parsing from input JSON, complex data transformations, and generation of Excel (`.xlsx`) reports using Pandas and XlsxWriter. It also produces a text-based processing log.
   - **Key Class:** `FileProcessor`
     - `__init__(self, output_dir=None)`: Initializes with a specified output directory, centralizing where generated files are stored. Detects Heroku/Render environments to use `/tmp`, otherwise uses a system temporary subdirectory.
     - `process_files(self, job_json_path, geojson_path=None)`: Main entry point for processing. Loads JSON, calls `process_data` to get a DataFrame, then calls `create_output_excel` and `logger.write_summary`. Generates uniquely timestamped output filenames.
     - `create_output_excel(self, path, df, job_data)`: Takes a Pandas DataFrame and writes it to an Excel file with specific formatting, including merged cells and auto-fitted columns. Uses a `try...finally` block to ensure the `ExcelWriter` is closed.
     - `process_data(self, job_data, geojson_data)`: Transforms the input JSON data into a structured Pandas DataFrame suitable for the Excel report. Contains significant domain-specific logic for handling nodes, connections, attachers, heights, bearings, etc.
     - Helper methods for data extraction (e.g., `get_attachers_for_node`, `get_lowest_heights_for_connection`, `get_neutral_wire_height`) and formatting (e.g., `format_height_feet_inches`).
   - **Logging:** `ProcessingLogger` class for detailed per-node and summary statistics.

### 2. `app.py` (Flask Web Application)
   - **Purpose:** Provides a web interface (likely `index.html`) for file uploads and a set of HTTP API endpoints for file processing and download.
   - **Endpoints:**
     - `/`: Serves the main HTML page.
     - `/upload` (POST): Accepts JSON file uploads, stores the file temporarily, and initiates background processing via a new thread calling `process_file`.
     - `/status/<task_id>` (GET): Returns the status of a processing task.
     - `/download/<filename>` (GET): Allows download of generated Excel or log files. Reads file data into an `io.BytesIO` object and serves it. Includes `Content-Length` header.
     - `/health` (GET): Basic health check.
     - `/cleanup/<task_id>` (POST): Removes task data from memory.
   - **File Handling:**
     - `process_file()`: Orchestrates file processing. Initializes `FileProcessor` with an appropriate output directory. After processing, it locates the uniquely named output files from the `FileProcessor`'s output path and stores their content in `io.BytesIO` objects associated with the task ID.
   - **Task Management:** Uses an in-memory dictionary `processing_tasks` to track file processing jobs.

### 3. `backend/app.py` (FastAPI Web Application)
   - **Purpose:** Provides a more modern API (prefixed with `/api`) for similar functionalities as the Flask app, including WebSockets for real-time updates.
   - **Endpoints (under `/api`):**
     - `/health` (GET): Health check.
     - `/upload` (POST): Accepts JSON file uploads, initiates asynchronous background processing via `asyncio.create_task(process_file_async(...))`.
     - `/tasks/{task_id}/status` (GET): Returns task status.
     - `/tasks/{task_id}/download/{file_type}` (GET): Allows download of Excel or log files. Includes `Content-Length` header.
     - `/tasks/{task_id}` (DELETE): Cleans up a task.
     - `/ws/tasks/{task_id}` (WebSocket): Provides real-time status updates for a task.
   - **File Handling:**
     - `process_file_async()` and `process_file_sync()`: Manage asynchronous and synchronous file processing. `process_file_sync` initializes `FileProcessor` with an appropriate output directory. Similar to the Flask app, it locates unique output files and stores them in `io.BytesIO`.
   - **Task Management:** Uses an in-memory dictionary `processing_tasks` and a `ConnectionManager` for WebSockets. Includes a periodic task to clean up old tasks.
   - **Static Files:** Configured to serve a React frontend build from `frontend/dist`.

### 4. `frontend/` (React/TypeScript Frontend)
   - **Purpose:** Provides the user interface for uploading files and viewing processing status/results.
   - **Technology:** React, TypeScript, Vite, Tailwind CSS.
   - **Interaction:** Communicates with the backend (likely FastAPI due to WebSocket usage) to upload files, poll for status, and trigger downloads.

## Data Flow
1.  **Upload:** User uploads a JSON file via the frontend.
    - Frontend sends the file to either Flask's `/upload` or FastAPI's `/api/upload`.
2.  **Processing Initiation:**
    - The receiving app (Flask or FastAPI) saves the uploaded JSON to a temporary local path (e.g., `temp/{task_id}_{filename}`).
    - A unique `task_id` is generated.
    - An instance of `FileProcessor` is created, configured with an appropriate output directory (e.g., `/tmp` on Heroku/Render, or a system temp subfolder locally).
    - The `FileProcessor.process_files()` method is called with the path to the temporary input JSON.
3.  **Core Processing (`barebones.py`):**
    - `FileProcessor` loads the input JSON.
    - `process_data()` transforms the JSON into a Pandas DataFrame.
    - `create_output_excel()` generates an `.xlsx` file from the DataFrame, saving it to the `FileProcessor`'s configured `downloads_path` with a unique, timestamped name.
