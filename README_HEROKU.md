# MakeReady Report Generator - Web Application

This is a web version of the MakeReady Report Generator that can be deployed to Heroku. It allows users to upload JSON files and generate Excel reports through a web interface.

## Features

- Web-based user interface with drag-and-drop file upload
- Real-time processing status updates
- Download generated reports directly from the browser
- Built with Flask, modern HTML/CSS, and JavaScript
- Designed for deployment on Heroku

## Local Development

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- Git

### Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd makeready-report-generator
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   python app.py
   ```

5. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

## Heroku Deployment

This application has been configured for deployment on Heroku. See [HEROKU_DEPLOYMENT.md](HEROKU_DEPLOYMENT.md) for detailed deployment instructions.

### Key Files for Heroku

- `Procfile`: Tells Heroku how to run the application
- `runtime.txt`: Specifies the Python version
- `requirements.txt`: Lists all dependencies including gunicorn
- `.gitignore`: Configured for Python and Heroku

## Application Structure

- `app.py`: Main Flask application
- `barebones.py`: Core processing logic
- `templates/`: HTML templates
  - `index.html`: Main page with file upload interface
- `static/`: Static assets
  - `style.css`: Application styling
  - `script.js`: Client-side JavaScript

## How It Works

1. User uploads a JSON file through the web interface
2. File is processed in memory using background thread
3. Progress and status are tracked and reported to the user
4. Generated reports (Excel files and logs) are stored in memory
5. User can download the generated files directly from the browser

## Limitations on Heroku

- Files are processed in memory and not persisted between requests
- Free tier has limited resources and will "sleep" after 30 minutes of inactivity
- Processing large files might be constrained by the memory limits of the dyno

## Future Improvements

- Add authentication for secure access
- Implement cloud storage (AWS S3, etc.) for file persistence
- Add more detailed processing logs
- Implement a job queue for handling larger files
- Add email notifications when processing is complete


## Credits

- Backend: Python/Flask
- Frontend: HTML, CSS, JavaScript
- Deployment: Heroku
