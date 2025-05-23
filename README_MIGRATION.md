# MakeReady Report Generator - FastAPI + React Migration

This application has been migrated from Flask to FastAPI (backend) with Vite/React (frontend).

## Architecture

### Backend (FastAPI)
- **Location**: `/backend`
- **Framework**: FastAPI with async support
- **Features**:
  - Async file processing
  - WebSocket support for real-time updates
  - In-memory file storage
  - Auto-cleanup of old tasks

### Frontend (Vite/React)
- **Location**: `/frontend`
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **Features**:
  - Drag-and-drop file upload
  - Real-time progress updates
  - Modern, responsive UI
  - WebSocket support with fallback to polling

## Development Setup

### Prerequisites
- Python 3.8+
- Node.js 18+
- npm 9+

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

The frontend will run on http://localhost:3000 and proxy API requests to the backend.

## Production Deployment (Heroku)

### Environment Setup
1. Create a new Heroku app
2. Add Python buildpack: `heroku buildpacks:add heroku/python`
3. Add Node.js buildpack: `heroku buildpacks:add heroku/nodejs`

### Deploy
```bash
git add .
git commit -m "Deploy FastAPI + React app"
git push heroku main
```

The app will:
1. Install Node.js dependencies
2. Build the React frontend
3. Install Python dependencies
4. Start the FastAPI server serving both API and static files

## Key Changes from Flask Version

### Backend Changes
- **FastAPI** instead of Flask for better async support
- **WebSockets** for real-time progress updates
- **Pydantic** models for request/response validation
- **Background tasks** using asyncio instead of threading
- **Static file serving** integrated for production

### Frontend Changes
- **React with TypeScript** instead of vanilla JavaScript
- **Vite** for fast development and optimized builds
- **Tailwind CSS** for modern styling
- **Component-based** architecture
- **Custom hooks** for state management

### API Endpoints
- `POST /api/upload` - Upload JSON file
- `GET /api/tasks/{task_id}/status` - Get task status
- `GET /api/tasks/{task_id}/download/{file_type}` - Download results
- `DELETE /api/tasks/{task_id}` - Clean up task
- `WS /ws/tasks/{task_id}` - WebSocket for real-time updates

## File Structure
```
barebones/
├── backend/
│   ├── app.py           # FastAPI application
│   ├── barebones.py     # Core processing logic (unchanged)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── api/         # API client
│   │   ├── components/  # React components
│   │   └── hooks/       # Custom React hooks
│   ├── package.json
│   └── vite.config.ts
├── Procfile             # Heroku deployment
├── package.json         # Root package for Heroku
└── runtime.txt          # Python version
```

## Features Maintained
- JSON file upload and validation
- Excel report generation
- Processing log generation
- In-memory file storage
- Automatic cleanup of old tasks

## New Features
- Real-time progress updates via WebSocket
- Modern, responsive UI
- Better error handling
- Type safety with TypeScript
- Faster development with Vite HMR

## Notes
- The core processing logic in `barebones.py` remains unchanged
- Files are still stored in memory for simplicity
- The app is ready for Heroku deployment with minimal configuration
