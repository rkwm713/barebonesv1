import os
import uuid
import io
from flask import Flask, request, render_template, jsonify, send_file
from werkzeug.utils import secure_filename
import json
import logging
import time
import threading
from barebones import FileProcessor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
app.config['ALLOWED_EXTENSIONS'] = {'json'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Track processing status and files in memory
processing_tasks = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def process_file(file_content, filename, task_id):
    """Process the JSON file using the FileProcessor class in memory"""
    # Create a temp dir if it doesn't exist
    os.makedirs('temp', exist_ok=True)
    
    # Use a path within the temp directory
    temp_file_path = os.path.join('temp', f"{task_id}_{filename}")
    
    try:
        # Update status to processing
        processing_tasks[task_id]['status'] = 'processing'
        
        # Save temp file for processing (needed for current processor implementation)
        with open(temp_file_path, 'wb') as f:
            f.write(file_content)
        
        try:
            # Initialize the processor
            processor = FileProcessor()
            
            # Get filename without extension for output naming
            base_filename = os.path.splitext(filename)[0]
            
            # Process the file
            success = processor.process_files(temp_file_path)
            
            if success:
                # Store output files in memory
                output_files = []
                
                # Find the generated Excel file
                downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
                excel_files = [f for f in os.listdir(downloads_path) if f.startswith(f"{base_filename}_") and f.endswith(".xlsx")]
                log_files = [f for f in os.listdir(downloads_path) if f.startswith(f"{base_filename}_") and f.endswith("_Log.txt")]
                
                if excel_files:
                    latest_excel = max(excel_files, key=lambda f: os.path.getmtime(os.path.join(downloads_path, f)))
                    excel_path = os.path.join(downloads_path, latest_excel)
                    excel_filename = f"{base_filename}_{task_id}.xlsx"
                    
                    # Store file data in memory
                    with open(excel_path, 'rb') as f:
                        excel_data = io.BytesIO(f.read())
                    
                    # Save to task
                    processing_tasks[task_id]['excel_data'] = excel_data
                    output_files.append({'type': 'excel', 'filename': excel_filename})
                
                if log_files:
                    latest_log = max(log_files, key=lambda f: os.path.getmtime(os.path.join(downloads_path, f)))
                    log_path = os.path.join(downloads_path, latest_log)
                    log_filename = f"{base_filename}_{task_id}_Log.txt"
                    
                    # Store file data in memory
                    with open(log_path, 'rb') as f:
                        log_data = io.BytesIO(f.read())
                    
                    # Save to task
                    processing_tasks[task_id]['log_data'] = log_data
                    output_files.append({'type': 'log', 'filename': log_filename})
                
                # Update status to complete
                processing_tasks[task_id]['status'] = 'complete'
                processing_tasks[task_id]['files'] = output_files
            else:
                # Update status to failed
                processing_tasks[task_id]['status'] = 'failed'
                processing_tasks[task_id]['error'] = 'Processing failed'
        finally:
            # Clean up temp file
            try:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
            except Exception as e:
                logger.error(f"Error removing temp file: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        processing_tasks[task_id]['status'] = 'failed'
        processing_tasks[task_id]['error'] = str(e)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    # Check if the post request has the file part
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    # If user does not select file, browser also
    # submits an empty part without filename
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        # Generate a unique ID for this task
        task_id = str(uuid.uuid4())
        
        # Get file content
        filename = secure_filename(file.filename)
        file_content = file.read()
        
        # Create task entry
        processing_tasks[task_id] = {
            'filename': filename,
            'status': 'queued',
            'created': time.time()
        }
        
        # Start processing in a separate thread
        thread = threading.Thread(target=process_file, args=(file_content, filename, task_id))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'task_id': task_id,
            'filename': filename,
            'status': 'queued'
        })
    
    return jsonify({'error': 'Invalid file type. Only JSON files are allowed.'}), 400

# Simple health check endpoint for monitoring
@app.route('/health')
def health_check():
    return jsonify({'status': 'ok', 'version': '1.0.0'}), 200

@app.route('/status/<task_id>')
def task_status(task_id):
    """Check the status of a processing task"""
    if task_id in processing_tasks:
        return jsonify(processing_tasks[task_id])
    return jsonify({'error': 'Task not found'}), 404

@app.route('/download/<filename>')
def download_file(filename):
    """Download a processed file from memory"""
    # Find which task has this file
    task_id = filename.split('_')[-1].split('.')[0]  # Extract task_id from filename
    if task_id not in processing_tasks:
        return jsonify({'error': 'File not found'}), 404
    
    task = processing_tasks[task_id]
    
    # Check if it's an Excel file
    if filename.endswith('.xlsx') and 'excel_data' in task:
        task['excel_data'].seek(0)
        return send_file(
            task['excel_data'],
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    # Check if it's a log file
    elif filename.endswith('_Log.txt') and 'log_data' in task:
        task['log_data'].seek(0)
        return send_file(
            task['log_data'],
            as_attachment=True,
            download_name=filename,
            mimetype='text/plain'
        )
    
    return jsonify({'error': 'File not found'}), 404

@app.route('/cleanup/<task_id>', methods=['POST'])
def cleanup_task(task_id):
    """Remove task and associated files from memory"""
    if task_id in processing_tasks:
        # Clean up task entry and in-memory files
        processing_tasks.pop(task_id, None)
        return jsonify({'status': 'cleaned'})
    
    return jsonify({'error': 'Task not found'}), 404

if __name__ == '__main__':
    # Get port from environment variable (for Heroku compatibility)
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
