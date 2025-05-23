# Local Testing Setup for Your Application

These instructions will guide you through setting up and running your application (both backend and frontend components) locally for testing purposes. This allows you to verify changes without impacting your Heroku deployment.

## Prerequisites
1.  **Python 3.x**: Ensure Python is installed on your system. You can download it from [python.org](https://www.python.org/).
2.  **Node.js and npm**: Ensure Node.js (which includes npm) is installed. You can download it from [nodejs.org](https://nodejs.org/). This is required if you want to run and test the frontend.
3.  **Project Code**: You should have the project code available in your local directory (e.g., `c:/Users/casey/Downloads/barebonesv1`).

## 1. Backend Setup

   a. **Open your terminal or command prompt.**

   b. **Navigate to the project root directory:**
      ```bash
      cd path/to/your/project/barebonesv1 
      ```
      (Replace `path/to/your/project` with the actual path, e.g., `c:/Users/casey/Downloads`)

   c. **Create a Python virtual environment (recommended):**
      ```bash
      python -m venv venv
      ```

   d. **Activate the virtual environment:**
      *   On Windows (in Command Prompt or PowerShell):
          ```bash
          venv\Scripts\activate
          ```
      *   On macOS/Linux:
          ```bash
          source venv/bin/activate
          ```
      **CRITICAL CONFIRMATION:** After running the activation command, your terminal prompt **MUST** change to show `(venv)` at the beginning (e.g., `(venv) PS C:\Users\casey\Downloads\barebonesv1>`). If you do not see `(venv)`, the virtual environment is NOT active. Do not proceed until it is.

   e. **Install Python dependencies (while venv is active):**
      **IMPORTANT**: Confirm `(venv)` is visible in your prompt. Then, in the **SAME terminal window**, run:
      ```bash
      pip install -r requirements.txt
      ```
      This command installs all necessary packages, including Flask, FastAPI, Pandas, etc., *into your active virtual environment*.

## 2. Testing Core Logic (`barebones.py`) Directly

This method allows you to test the main data processing and Excel generation logic without running the web servers.

   a. **Ensure your virtual environment is active.** (Confirm `(venv)` is at the start of your prompt).

   b. **Prepare your test JSON file:**
      *   The `main()` function in `barebones.py` is currently configured to look for `CPS_6457E_03.json` or use `test_job_data.json` if the former is not found. Make sure one of these files (or your desired test file, by modifying `barebones.py`'s `main` function) is present in the project root.

   c. **Run the script from the project root directory (while venv is active):**
      In the **SAME terminal window** where `(venv)` is active, run:
      ```bash
      python barebones.py
      ```

   d. **Check for output:**
      *   The script will create an `outputs` subdirectory in your project root (e.g., `c:/Users/casey/Downloads/barebonesv1/outputs`).
      *   Inside this `outputs` directory, you will find the generated Excel report and the processing log file. Review these to verify your changes.

## 3. Running the Flask Backend (Optional)

If you need to test the Flask API endpoints (`app.py`):

   a. **Ensure your virtual environment is active.** (Confirm `(venv)` is at the start of your prompt).

   b. **Run the Flask application from the project root directory (while venv is active):**
      In the **SAME terminal window** where `(venv)` is active, run:
      ```bash
      python app.py
      ```
      (Using `python app.py` is generally more reliable within an active venv than `py app.py`)

   c. **Access the application:**
      *   The Flask development server will typically start on `http://127.0.0.1:5000/`.
      *   You can use a tool like Postman or `curl` to send requests to its API endpoints (e.g., `/upload`, `/status/<task_id>`, `/download/<filename>`).

## 4. Running the FastAPI Backend (Recommended for full API testing)

The FastAPI backend (`backend/app.py`) provides the more modern API, including WebSocket support.

   a. **Ensure your virtual environment is active.** (Confirm `(venv)` is at the start of your prompt).

   b. **Run the FastAPI application using Uvicorn from the project root directory (while venv is active):**
      In the **SAME terminal window** where `(venv)` is active, run:
      ```bash
      python -m uvicorn backend.app:app --reload --port 8000
      ```
      (Using `python -m uvicorn` ensures you're using the uvicorn installed in your venv).
      *   `--reload` enables auto-reloading when code changes.
      *   `--port 8000` specifies the port (you can change this if 8000 is in use).

   c. **Access the API:**
      *   The FastAPI server will be available at `http://127.0.0.1:8000/`.
      *   API endpoints are prefixed with `/api` (e.g., `http://127.0.0.1:8000/api/upload`).
      *   Interactive API documentation (Swagger UI) is available at `http://127.0.0.1:8000/docs`.
      *   Alternative API documentation (ReDoc) is available at `http://127.0.0.1:8000/redoc`.

## 5. Running the Frontend (Optional - for full end-to-end testing)

If you want to test the user interface and its interaction with the FastAPI backend:

   a. **Ensure the FastAPI backend is running (see step 4).** The frontend will try to connect to it.

   b. **Open a new terminal or command prompt window/tab.**

   c. **Navigate to the `frontend` directory:**
      ```bash
      cd path/to/your/project/barebonesv1/frontend
      ```

   d. **Install Node.js dependencies:**
      ```bash
      npm install
      ```
      (If you prefer `yarn`, use `yarn install`)

   e. **Start the Vite development server:**
      ```bash
      npm run dev
      ```
      (If you prefer `yarn`, use `yarn dev`)

   f. **Access the frontend:**
      *   The terminal will display a local URL, typically `http://localhost:5173/` (the port might vary). Open this URL in your web browser.
      *   The frontend should now be able to interact with your locally running FastAPI backend.

## Important Notes:
*   **File Paths:** When running locally, `FileProcessor` in `barebones.py` is designed to save output files to a subdirectory within your system's temporary folder (e.g., `barebones_outputs`) or to the `outputs/` directory in your project root if you run `barebones.py` directly using its `main()` function. This is different from Heroku, which uses `/tmp`. This behavior is intentional for local testing and keeps test files separate.
*   **Environment Variables:** This local setup does not replicate all Heroku environment variables. However, the application logic for path handling is designed to work locally without `DYNO` or `RENDER` variables being set.
*   **Server Differences:** This setup uses Python's built-in development server for Flask and Uvicorn for FastAPI. Heroku uses Gunicorn (as per your `Procfile` for the Flask app). While development servers are great for testing, Gunicorn is a production-grade server. This difference is generally fine for local functional testing.

## Troubleshooting

*   **`ModuleNotFoundError: No module named 'flask'` (or similar for other packages):**
    *   This is the most common issue and usually means the Python packages were not installed into your active virtual environment, or you are trying to run the script from a terminal where the virtual environment is not active.
    *   **Solution Steps:**
        1.  **Open your terminal** (e.g., PowerShell or Command Prompt on Windows).
        2.  **Navigate to your project root directory:** `cd C:\Users\casey\Downloads\barebonesv1`
        3.  **Activate the virtual environment:**
            *   Run: `venv\Scripts\activate`
            *   **VERIFY:** Your prompt MUST now start with `(venv)`. For example: `(venv) PS C:\Users\casey\Downloads\barebonesv1>`. If it doesn't, the venv is not active. Stop and troubleshoot venv activation.
        4.  **Re-install dependencies (within the active venv):**
            *   In the SAME terminal where `(venv)` is visible, run: `pip install -r requirements.txt`
            *   Watch for any errors during installation.
        5.  **Run the application (within the active venv):**
            *   To run Flask app: In the SAME terminal where `(venv)` is visible, run: `python app.py`
            *   To run FastAPI app: In the SAME terminal where `(venv)` is visible, run: `python -m uvicorn backend.app:app --reload --port 8000`

    *   **If the `(venv)` prefix disappears or you open a new terminal, you MUST reactivate the virtual environment in that new terminal session before running `pip install` or your Python application.** Each terminal window/session maintains its own environment state.

By following these steps, you can create a robust local testing environment that allows you to verify application functionality thoroughly before deploying to Heroku.
