import os
import uuid
import io
import asyncio
import json
import logging
import time
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket, WebSocketDisconnect, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from barebones import FileProcessor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="MakeReady Report Generator API")

# Create API router with prefix
api_router = APIRouter(prefix="/api")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for processing tasks
processing_tasks: Dict[str, Dict[str, Any]] = {}

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, task_id: str):
        await websocket.accept()
        self.active_connections[task_id] = websocket

    def disconnect(self, task_id: str):
        if task_id in self.active_connections:
            del self.active_connections[task_id]

    async def send_status(self, task_id: str, data: dict):
        if task_id in self.active_connections:
            try:
                # Create a JSON-serializable version of the task data
                serializable_data = {
                    "task_id": data.get("task_id"),
                    "filename": data.get("filename"),
                    "status": data.get("status"),
                    "created": data.get("created"),
                    "progress": data.get("progress", 0),
                    "files": data.get("files", []),
                    "error": data.get("error")
                }
                await self.active_connections[task_id].send_json(serializable_data)
            except Exception as e:
                logger.error(f"Error sending WebSocket message: {e}")

manager = ConnectionManager()

# Pydantic models
class TaskStatus(BaseModel):
    task_id: str
    filename: str
    status: str
    created: str
    progress: Optional[int] = 0
    files: Optional[list] = []
    error: Optional[str] = None

class UploadResponse(BaseModel):
    task_id: str
    filename: str
    status: str

# Helper functions
def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'json'

async def process_file_async(file_content: bytes, filename: str, task_id: str):
    """Process file asynchronously"""
    logger.info(f"Starting async processing for task {task_id}")
    
    try:
        # Update status to processing
        processing_tasks[task_id]['status'] = 'processing'
        processing_tasks[task_id]['progress'] = 10
        
        # Send WebSocket update
        await manager.send_status(task_id, processing_tasks[task_id])
        
        # Run processor in thread pool to not block async loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            process_file_sync, 
            file_content, 
            filename, 
            task_id
        )
        
        if result:
            processing_tasks[task_id]['status'] = 'complete'
            processing_tasks[task_id]['progress'] = 100
            await manager.send_status(task_id, processing_tasks[task_id])
        else:
            processing_tasks[task_id]['status'] = 'failed'
            processing_tasks[task_id]['error'] = 'Processing failed'
            await manager.send_status(task_id, processing_tasks[task_id])
            
    except Exception as e:
        logger.error(f"Error in async processing: {str(e)}")
        processing_tasks[task_id]['status'] = 'failed'
        processing_tasks[task_id]['error'] = str(e)
        await manager.send_status(task_id, processing_tasks[task_id])

def process_file_sync(file_content: bytes, filename: str, task_id: str) -> bool:
    """Process file synchronously using FileProcessor"""
    logger.info(f"Starting sync processing for task {task_id}")
    
    # Create a temp directory if it doesn't exist
    os.makedirs('temp', exist_ok=True)
    
    # Use a path within the temp directory
    temp_file_path = os.path.join('temp', f"{task_id}_{filename}")
    
    try:
        # Save temp file for processing
        with open(temp_file_path, 'wb') as f:
            f.write(file_content)
        
        # Update progress
        processing_tasks[task_id]['progress'] = 30
        
        # Determine output directory based on environment
        if os.environ.get('DYNO') or os.environ.get('RENDER'):  # Heroku or Render
            output_directory = "/tmp"
        else: # Local or other environments
            import tempfile
            output_directory = os.path.join(tempfile.gettempdir(), "barebones_fastapi_outputs")
            os.makedirs(output_directory, exist_ok=True)

        # Initialize the processor with the determined output directory
        processor = FileProcessor(output_dir=output_directory)
        
        # Get filename without extension for output naming
        base_filename = os.path.splitext(filename)[0]
        
        # Process the file
        success = processor.process_files(temp_file_path)
        
        if success:
            # Update progress
            processing_tasks[task_id]['progress'] = 70
            
            # Store output files in memory
            output_files = []
            
            # Use the temp directory for file storage (Heroku-compatible)
            tmp_dir = "/tmp"
            os.makedirs(tmp_dir, exist_ok=True)
            
            # Process and store files in memory directly
            excel_data = None
            log_data = None
            
            # The FileProcessor saves files with unique names (timestamped)
            # to the 'output_directory' it was initialized with.
            # We need to find these specific files from processor.downloads_path.
            
            generated_files_in_processor_path = os.listdir(processor.downloads_path)

            potential_excel_files = [
                f for f in generated_files_in_processor_path if f.startswith(f"{base_filename}_Output_") and f.endswith(".xlsx")
            ]
            potential_log_files = [
                f for f in generated_files_in_processor_path if f.startswith(f"{base_filename}_Log_") and f.endswith(".txt")
            ]

            excel_data = None
            log_data = None

            if potential_excel_files:
                potential_excel_files.sort(key=lambda f: os.path.getmtime(os.path.join(processor.downloads_path, f)), reverse=True)
                latest_excel_filename_from_processor = potential_excel_files[0]
                excel_path = os.path.join(processor.downloads_path, latest_excel_filename_from_processor)
                
                excel_download_filename = f"{base_filename}_{task_id}.xlsx"
                
                with open(excel_path, 'rb') as f:
                    excel_data = io.BytesIO(f.read())
                
                processing_tasks[task_id]['excel_data'] = excel_data
                output_files.append({'type': 'excel', 'filename': excel_download_filename})
                logger.info(f"Found and stored Excel file: {latest_excel_filename_from_processor} for task {task_id}")
            else:
                logger.warning(f"No Excel file found for task {task_id} with base_filename {base_filename} in {processor.downloads_path}")


            if potential_log_files:
                potential_log_files.sort(key=lambda f: os.path.getmtime(os.path.join(processor.downloads_path, f)), reverse=True)
                latest_log_filename_from_processor = potential_log_files[0]
                log_path = os.path.join(processor.downloads_path, latest_log_filename_from_processor)

                log_download_filename = f"{base_filename}_{task_id}_Log.txt"

                with open(log_path, 'rb') as f:
                    log_data = io.BytesIO(f.read())
                    
                processing_tasks[task_id]['log_data'] = log_data
                output_files.append({'type': 'log', 'filename': log_download_filename})
                logger.info(f"Found and stored Log file: {latest_log_filename_from_processor} for task {task_id}")
            else:
                logger.warning(f"No Log file found for task {task_id} with base_filename {base_filename} in {processor.downloads_path}")
            
            # Update task with files
            processing_tasks[task_id]['files'] = output_files
            processing_tasks[task_id]['progress'] = 90
            
            return True
        else:
            return False
            
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        return False
    finally:
        # Clean up temp file
        try:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
        except Exception as e:
            logger.error(f"Error removing temp file: {str(e)}")

# API Routes
@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "version": "2.0.0", "framework": "FastAPI"}

@api_router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """Upload a JSON file for processing"""
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    if not allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="Invalid file type. Only JSON files are allowed.")
    
    # Generate task ID
    task_id = str(uuid.uuid4())
    
    # Read file content
    content = await file.read()
    
    # Create task entry
    processing_tasks[task_id] = {
        'task_id': task_id,
        'filename': file.filename,
        'status': 'queued',
        'created': datetime.now().isoformat(),
        'progress': 0,
        'files': []
    }
    
    # Process file in background
    asyncio.create_task(process_file_async(content, file.filename, task_id))
    
    return UploadResponse(
        task_id=task_id,
        filename=file.filename,
        status='queued'
    )

@api_router.get("/tasks/{task_id}/status", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """Get the status of a processing task"""
    if task_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = processing_tasks[task_id]
    return TaskStatus(**task)

@api_router.get("/tasks/{task_id}/download/{file_type}")
async def download_file(task_id: str, file_type: str):
    """Download a processed file"""
    if task_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = processing_tasks[task_id]
    
    # Check file type and get appropriate data
    if file_type == "excel" and 'excel_data' in task:
        file_data = task['excel_data']
        filename = next((f['filename'] for f in task['files'] if f['type'] == 'excel'), 'output.xlsx')
        media_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    elif file_type == "log" and 'log_data' in task:
        file_data = task['log_data']
        filename = next((f['filename'] for f in task['files'] if f['type'] == 'log'), 'output.txt')
        media_type = 'text/plain'
    else:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Reset file position
    file_data.seek(0)
    
    # Get content length
    content_length = len(file_data.getbuffer())

    # Add cache-busting and version headers
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Content-Length": str(content_length), # Add Content-Length
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache", 
        "Expires": "0",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-Report-Version": "2.0.0",
        "X-Generated-At": datetime.now().isoformat()
    }
    
    return StreamingResponse(
        file_data,
        media_type=media_type,
        headers=headers
    )

@api_router.delete("/tasks/{task_id}")
async def cleanup_task(task_id: str):
    """Clean up a task and its associated files"""
    if task_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Remove task from memory
    del processing_tasks[task_id]
    
    return {"status": "cleaned"}

@app.websocket("/api/ws/tasks/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for real-time task updates"""
    await manager.connect(websocket, task_id)
    
    try:
        # Send initial status if task exists
        if task_id in processing_tasks:
            task_data = processing_tasks[task_id]
            serializable_data = {
                "task_id": task_data.get("task_id"),
                "filename": task_data.get("filename"),
                "status": task_data.get("status"),
                "created": task_data.get("created"),
                "progress": task_data.get("progress", 0),
                "files": task_data.get("files", []),
                "error": task_data.get("error")
            }
            await websocket.send_json(serializable_data)
        
        # Keep connection alive
        while True:
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        manager.disconnect(task_id)

# Cleanup old tasks periodically (every hour)
async def cleanup_old_tasks():
    """Remove tasks older than 1 hour"""
    while True:
        try:
            current_time = datetime.now()
            tasks_to_remove = []
            
            for task_id, task in processing_tasks.items():
                created_time = datetime.fromisoformat(task['created'])
                if (current_time - created_time).seconds > 3600:  # 1 hour
                    tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del processing_tasks[task_id]
                logger.info(f"Cleaned up old task: {task_id}")
            
            await asyncio.sleep(3600)  # Check every hour
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")
            await asyncio.sleep(3600)

# Include the API router in the main app
app.include_router(api_router)

# Serve static files from React build
static_files_path = Path(__file__).parent.parent / "frontend" / "dist"
if static_files_path.exists():
    app.mount("/", StaticFiles(directory=str(static_files_path), html=True), name="static")
else:
    logger.warning(f"Frontend build directory not found at {static_files_path}")

@app.on_event("startup")
async def startup_event():
    """Start background tasks on app startup"""
    asyncio.create_task(cleanup_old_tasks())

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get('PORT', 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
