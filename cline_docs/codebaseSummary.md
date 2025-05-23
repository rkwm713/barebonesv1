# Codebase Summary

## Overview
This project is a web application designed to process uploaded JSON files and generate Excel reports and text-based log files. It features a Python backend with data processing capabilities and a React/TypeScript frontend for user interaction. The backend exposes APIs through both Flask and FastAPI, with FastAPI appearing to be the more modern and actively developed part.

## Key Components and Their Interactions

### 1. `barebones.py` (Core Processing Logic)
   - **Purpose:** Handles the core data parsing from input JSON, complex data transformations, and generation of Excel (`.xlsx`) reports using Pandas and XlsxWriter. It also produces a text-based processing log.
   - **Key Class:** `FileProcessor`
     - `__init__(self, output_dir=None)`: Initializes with a specified output directory, centralizing where generated files are stored. Detects Heroku/Render environments to use `/tmp`, otherwise uses a system temporary subdirectory.
     - `process_files(self, job_json_path, geojson_path=None)`: Main entry point for processing. Loads JSON, calls `process_data` to get a DataFrame, then calls `create_output_excel` and `logger.write_summary`. Generates uniquely timestamped output filenames.
     - `create_output_excel(self, path, df, job_data)`: Takes a Pandas DataFrame and writes it to an Excel file with specific formatting. Uses a `try...finally` block for robust writer closing. Updated to use new header text for reference spans. **Further updated (2025-05-23) to conditionally populate the "Mid-Span (same span as existing)" column for main pole attachers only if the pole attacher is new or has moved.**
     - `process_data(self, job_data, geojson_data)`: Transforms the input JSON data into a structured Pandas DataFrame suitable for the Excel report. Contains significant domain-specific logic for handling nodes, connections, attachers, heights, bearings, etc.
     - `get_reference_attachers(self, job_data, current_node_id)`: Overhauled to correctly identify true reference spans using `is_reference_connection`. Builds "Ref (...)" blocks with accurate bearing, node type, and filtered/sorted attachers as per new playbook.
     - Helper methods for data extraction (e.g., `get_attachers_for_node`, `get_lowest_heights_for_connection`, `get_neutral_wire_height`) and formatting (e.g., `format_height_feet_inches`).
   - **Helper Functions (module-level in `barebones.py`):**
     - `get_scid_from_node_data(node_data)`: Extracts SCID from node data reliably.
     - `is_reference_connection(conn, nodes_data, this_node_id)`: Implements a two-step check (button="ref", target SCID contains ".") to identify true reference connections.
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
    - `ProcessingLogger` generates a `.txt` log file, also saved to the `downloads_path` with a unique, timestamped name.
4.  **Result Storage (In-Memory):**
    - The Flask/FastAPI app (in `process_file` or `process_file_sync`) lists files in the `FileProcessor`'s output directory.
    - It identifies the newly generated (timestamped) Excel and log files.
    - Reads these files into `io.BytesIO` objects.
    - Stores these `io.BytesIO` objects in the `processing_tasks` dictionary, associated with the `task_id`.
5.  **Status Update & Download:**
    - Frontend polls `/status/<task_id>` (Flask) or `/api/tasks/{task_id}/status` (FastAPI), or receives WebSocket updates (FastAPI).
    - Once processing is 'complete', download links are presented.
    - Clicking a download link hits `/download/<filename>` (Flask) or `/api/tasks/{task_id}/download/{file_type}` (FastAPI).
    - The server retrieves the corresponding `io.BytesIO` object from `processing_tasks`, seeks to the beginning, and streams it as a file download with appropriate headers (including `Content-Length`).

## External Dependencies
- **Python:** `pandas`, `XlsxWriter` (for Excel), `Flask`, `Werkzeug`, `FastAPI`, `uvicorn`, `python-multipart` (for FastAPI file uploads), `websockets`. Managed via `requirements.txt`.
- **Node.js (Frontend):** `react`, `typescript`, `vite`, `tailwindcss`, etc. Managed via `frontend/package.json`.

## Recent Significant Changes (as of 2025-05-23)
- **Centralized Path Management:** `FileProcessor` constructor updated to accept an `output_dir` and use a consistent strategy for determining output paths across different environments (Heroku, Render, local).
- **Unique File Naming:** `FileProcessor.process_files` now generates Excel and log files with unique, timestamped names to prevent conflicts and improve traceability.
- **Robust Excel Writer Handling:** `FileProcessor.create_output_excel` now uses a `try...finally` block to ensure the `pd.ExcelWriter` is always closed, even if errors occur during generation.
- **App Updates for FileProcessor:** Both Flask (`app.py`) and FastAPI (`backend/app.py`) updated to:
    - Instantiate `FileProcessor` with the correct output directory.
    - Correctly locate and load the uniquely named output files generated by `FileProcessor`.
- **Content-Length Header:** Added to download responses in both Flask and FastAPI apps to improve download reliability.
- **Logging Improvements:** Clarified log messages in `FileProcessor` and removed debug prints from `format_height_feet_inches`.
- **Local Testing Enhancement:** `main()` function in `barebones.py` improved for easier local testing.
- **Reference Span Logic Overhaul (2025-05-23):**
    - Added `get_scid_from_node_data` and `is_reference_connection` helper functions to `barebones.py`.
    - Rewrote `FileProcessor.get_reference_attachers` to accurately identify and process true reference spans based on new playbook rules (button type and target SCID format). This rewrite includes logic to ensure reference spans are processed only when originating from `node_id_1` (the subject pole), skipping reverse connections. Crucially, the heights for these reference span attachers are now sourced from the main pole's attacher data, not the reference span's midpoint photo data, ensuring accurate comparison points. This includes correct header generation, attacher filtering (communication/guy wires below neutral), data capture (description, existing/proposed heights), and sorting (attachers by height, multiple ref spans by bearing).
    - Updated `FileProcessor.create_output_excel` to use the new "Ref (...)" header format.
    - This change addresses issues like the PL410620 bug where non-reference spans were incorrectly labeled.
- **Midspan Proposed Height Logic (2025-05-23):**
    - Modified `FileProcessor.create_output_excel` so that the "Mid-Span (same span as existing)" column for main pole attachers is populated only if the pole attacher has a non-empty `proposed_height` (i.e., it's new or has moved). Otherwise, this midspan column is left blank for that attacher.
- **"Refs" Sheet Data Population Fixes (2025-05-23):**
    - In `FileProcessor.create_output_excel` (for the "refs" sheet generation):
        - Ensured `attacher_data` is fetched fresh for each main pole being processed, providing correct context for `main_pole_attachers_lookup`.
        - Implemented a `data_actually_written_for_pole_refs` flag to accurately control the fallback logic for "002.A" poles, ensuring the placeholder row is added only when no other reference data from that pole is written.
        - Adjusted data mapping for `Ref_Span_Attacher` rows: Column P (index 6) now gets `mid_span_proposed_h`, and Column Q (index 7) gets `mid_span_existing_h`.

## User Feedback Integration and Its Impact on Development
- The primary driver for recent changes was user reports of "corrupted Excel files."
- Investigation revealed that the issue was likely multifaceted, stemming from:
    - Inconsistent file path management between `barebones.py` and the web app components.
    - Potential race conditions or incorrect file selection due to non-unique filenames and reliance on modification times.
    - Lack of robust error handling in Excel generation (e.g., writer not closing).
    - Missing `Content-Length` headers potentially leading to incomplete downloads.
- The implemented changes directly address these suspected root causes to enhance reliability.

## Additional Documentation
- `cline_docs/projectRoadmap.md`: Tracks high-level goals, features, and progress.
- `cline_docs/currentTask.md`: Details the current development focus and next steps.
- `cline_docs/techStack.md`: Outlines the technologies and architectural decisions.
- `userInstructions/local_testing_setup.md`: Provides detailed instructions for setting up and running the application locally for testing.
