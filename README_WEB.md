# MakeReady Report Generator - Web Frontend

A modern, minimal web interface for the Barebones Utility Data Processor that allows users to upload JSON files and generate Excel reports via a browser.

## Overview

This web application provides a user-friendly interface for the existing `barebones.py` processor. It allows users to:

1. Upload JSON files via drag-and-drop or file browsing
2. Process the data to generate Excel reports and processing logs
3. Download the generated files directly from the browser

## Features

- **Modern, Minimal UI**: Clean design with intuitive user experience
- **Drag & Drop**: Easy file uploading with visual feedback
- **Progress Tracking**: Visual indication of processing status
- **Responsive Design**: Works on desktop and mobile devices
- **Background Processing**: Handles large files without blocking the UI
- **Error Handling**: Provides clear feedback on processing errors

## Setup and Installation

### Prerequisites

- Python 3.7 or higher
- Flask
- All dependencies required by the original `barebones.py` processor (pandas, xlsxwriter, etc.)

### Installation

1. Make sure you have all the necessary dependencies installed:

```bash
pip install flask pandas xlsxwriter
```

2. The application structure should look like this:

```
barebones/
├── app.py                  # Flask web server
├── barebones.py            # Original processor
├── templates/
│   └── index.html          # HTML template
├── static/
│   ├── style.css           # CSS styling
│   └── script.js           # Frontend JavaScript
├── uploads/                # Temporary upload storage
├── outputs/                # Generated file storage
└── README_WEB.md           # This file
```

## Running the Application

1. Start the Flask server:

```bash
python app.py
```

2. Open a web browser and navigate to:

```
http://localhost:5000
```

3. Use the interface to upload JSON files and generate reports

## How It Works

1. **File Upload**: JSON files are uploaded to the server and stored in the `uploads/` directory
2. **Processing**: Files are processed using the existing `FileProcessor` class from `barebones.py`
3. **Background Tasks**: Processing happens in a background thread to prevent UI blocking
4. **Output Generation**: Excel reports and processing logs are generated in the `outputs/` directory
5. **Download**: Users can download the generated files directly from the web interface

## Technical Implementation

- **Backend**: Flask web server with RESTful endpoints for file handling
- **Frontend**: Vanilla JavaScript with modern ES6 features
- **Styling**: CSS with variables for easy theming
- **Communication**: Fetch API for AJAX requests

## Security Considerations

- File uploads are validated to ensure only JSON files are processed
- File sizes are limited to prevent abuse
- Unique IDs are generated for each task to prevent file name collisions
- Files in the uploads directory are cleaned up after processing

## Future Enhancements

- Add user authentication for multi-user environments
- Implement file compression for large outputs
- Add preview capability for generated Excel files
- Create a dark mode theme option
- Add batch processing capabilities for multiple files
