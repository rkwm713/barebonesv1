import os
import uuid
from flask import Flask, request, render_template, redirect, url_for, jsonify, send_from_directory
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
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['ALLOWED_EXTENSIONS'] = {'json'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Create necessary directories if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Track processing status
processing_tasks = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def process_file(file_path, task_id):
    """Process the JSON file using the FileProcessor class"""
    try:
        # Update status to processing
        processing_tasks[task_id]['status'] = 'processing'
        
        # Initialize the processor
        processor = FileProcessor()
        
        # Get filename without extension for output naming
        base_filename = os.path.splitext(os.path.basename(file_path))[0]
        
        # Process the file
        success = processor.process_files(file_path)
        
        if success:
            # Find the generated Excel file
            downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
            excel_files = [f for f in os.listdir(downloads_path) if f.startswith(f"{base_filename}_") and f.endswith(".xlsx")]
            log_files = [f for f in os.listdir(downloads_path) if f.startswith(f"{base_filename}_") and f.endswith("_Log.txt")]
            
            # Copy files to output folder
            output_files = []
            
            if excel_files:
                latest_excel = max(excel_files, key=lambda f: os.path.getmtime(os.path.join(downloads_path, f)))
                # Copy to output folder with a new filename
                output_excel = f"{base_filename}_{task_id}.xlsx"
                output_excel_path = os.path.join(app.config['OUTPUT_FOLDER'], output_excel)
                with open(os.path.join(downloads_path, latest_excel), 'rb') as src_file:
                    with open(output_excel_path, 'wb') as dest_file:
                        dest_file.write(src_file.read())
                output_files.append({'type': 'excel', 'filename': output_excel})
            
            if log_files:
                latest_log = max(log_files, key=lambda f: os.path.getmtime(os.path.join(downloads_path, f)))
                # Copy to output folder with a new filename
                output_log = f"{base_filename}_{task_id}_Log.txt"
                output_log_path = os.path.join(app.config['OUTPUT_FOLDER'], output_log)
                with open(os.path.join(downloads_path, latest_log), 'rb') as src_file:
                    with open(output_log_path, 'wb') as dest_file:
                        dest_file.write(src_file.read())
                output_files.append({'type': 'log', 'filename': output_log})
            
            # Update status to complete
            processing_tasks[task_id]['status'] = 'complete'
            processing_tasks[task_id]['files'] = output_files
        else:
            # Update status to failed
            processing_tasks[task_id]['status'] = 'failed'
            processing_tasks[task_id]['error'] = 'Processing failed'
    
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
        
        # Save the file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{task_id}_{filename}")
        file.save(file_path)
        
        # Create task entry
        processing_tasks[task_id] = {
            'filename': filename,
            'status': 'queued',
            'created': time.time()
        }
        
        # Start processing in a separate thread
        thread = threading.Thread(target=process_file, args=(file_path, task_id))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'task_id': task_id,
            'filename': filename,
            'status': 'queued'
        })
    
    return jsonify({'error': 'Invalid file type. Only JSON files are allowed.'}), 400

@app.route('/status/<task_id>')
def task_status(task_id):
    """Check the status of a processing task"""
    if task_id in processing_tasks:
        return jsonify(processing_tasks[task_id])
    return jsonify({'error': 'Task not found'}), 404

@app.route('/download/<filename>')
def download_file(filename):
    """Download a processed file"""
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)

@app.route('/cleanup/<task_id>', methods=['POST'])
def cleanup_task(task_id):
    """Remove task and associated files after processing"""
    if task_id in processing_tasks:
        # Remove uploaded file
        upload_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.startswith(f"{task_id}_")]
        for file in upload_files:
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], file))
            except:
                pass
        
        # Clean up task entry (keep files for download)
        processing_tasks.pop(task_id, None)
        
        return jsonify({'status': 'cleaned'})
    
    return jsonify({'error': 'Task not found'}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
