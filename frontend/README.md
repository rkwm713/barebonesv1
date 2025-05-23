# Frontend - MakeReady Report Generator

A modern React-based web interface for uploading utility inspection JSON files and monitoring processing progress in real-time.

## Overview

The frontend provides an intuitive drag-and-drop interface for users to upload JSON files, monitor processing progress via WebSocket connections, and download generated Excel reports and processing logs.

## Technology Stack

- **React 18**: Modern React with hooks and functional components
- **TypeScript**: Type-safe JavaScript for better development experience
- **Vite**: Fast build tool and development server
- **Tailwind CSS**: Utility-first CSS framework for styling
- **WebSocket**: Real-time communication with the backend

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    React Application                        │
├─────────────────────────────────────────────────────────────┤
│  Components Layer                                           │
│  ├─ FileUpload        (Drag & drop interface)              │
│  ├─ ProcessingStatus  (Real-time progress display)         │
│  ├─ Results           (Download links and file info)       │
│  └─ ErrorDisplay      (Error handling and messages)        │
├─────────────────────────────────────────────────────────────┤
│  Services Layer                                             │
│  ├─ API Client        (HTTP requests to backend)           │
│  ├─ WebSocket Hook    (Real-time status updates)           │
│  └─ Task Management   (Status tracking and cleanup)        │
├─────────────────────────────────────────────────────────────┤
│  State Management                                           │
│  ├─ React State      (Component-level state)               │
│  ├─ Custom Hooks     (Reusable state logic)                │
│  └─ Context API      (Global state where needed)           │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
frontend/
├── src/
│   ├── components/          # React components
│   │   ├── FileUpload.tsx  # File upload interface
│   │   ├── ProcessingStatus.tsx  # Progress display
│   │   ├── Results.tsx     # Download interface
│   │   └── ErrorDisplay.tsx  # Error handling
│   ├── hooks/              # Custom React hooks
│   │   └── useTaskStatus.ts  # WebSocket task monitoring
│   ├── api/                # API client services
│   │   └── client.ts       # HTTP client for backend
│   ├── App.tsx             # Main application component
│   ├── main.tsx            # Application entry point
│   └── index.css           # Global styles (Tailwind)
├── public/                 # Static assets
├── dist/                   # Built application (production)
├── package.json            # Dependencies and scripts
├── tsconfig.json           # TypeScript configuration
├── vite.config.ts          # Vite build configuration
├── tailwind.config.js      # Tailwind CSS configuration
└── postcss.config.js       # PostCSS configuration
```

## Components

### 1. FileUpload Component

**File**: `src/components/FileUpload.tsx`

Provides drag-and-drop file upload functionality with validation.

```typescript
interface FileUploadProps {
  onFileSelect: (file: File) => void;
  isUploading: boolean;
}
```

**Features:**
- **Drag & Drop Interface**: Intuitive file dropping zone
- **File Validation**: JSON file type checking
- **Visual Feedback**: Upload states and progress indication
- **Error Handling**: Invalid file type notifications

**Key Functionality:**
- File type validation (JSON only)
- Drag enter/leave/drop event handling
- File size validation
- Upload progress indication

### 2. ProcessingStatus Component

**File**: `src/components/ProcessingStatus.tsx`

Displays real-time processing progress using WebSocket updates.

```typescript
interface ProcessingStatusProps {
  taskId: string;
  onComplete: (files: ProcessedFile[]) => void;
  onError: (error: string) => void;
}
```

**Features:**
- **Real-time Updates**: WebSocket-based progress monitoring
- **Progress Bar**: Visual progress indication (0-100%)
- **Status Messages**: Detailed status information
- **Automatic Polling**: Fallback HTTP polling if WebSocket fails

**Processing Stages:**
1. **Queued**: File uploaded, waiting for processing
2. **Processing**: Data analysis in progress
3. **Complete**: Processing finished successfully
4. **Failed**: Error occurred during processing

### 3. Results Component

**File**: `src/components/Results.tsx`

Handles display and download of processed files.

```typescript
interface ResultsProps {
  taskId: string;
  files: ProcessedFile[];
  onReset: () => void;
}

interface ProcessedFile {
  type: 'excel' | 'log';
  filename: string;
}
```

**Features:**
- **Download Management**: Secure file download links
- **File Information**: File types and sizes
- **Cleanup Options**: Reset interface for new uploads
- **Error Handling**: Download failure notifications

### 4. ErrorDisplay Component

**File**: `src/components/ErrorDisplay.tsx`

Centralized error handling and user notifications.

```typescript
interface ErrorDisplayProps {
  error: string | null;
  onDismiss: () => void;
}
```

**Features:**
- **Error Categorization**: Different error types and styles
- **User-friendly Messages**: Clear error descriptions
- **Dismissible Notifications**: User-controlled error clearing
- **Retry Options**: Suggestions for error resolution

## Custom Hooks

### useTaskStatus Hook

**File**: `src/hooks/useTaskStatus.ts`

Manages WebSocket connections and task status monitoring.

```typescript
interface TaskStatus {
  task_id: string;
  filename: string;
  status: 'queued' | 'processing' | 'complete' | 'failed';
  progress: number;
  files: ProcessedFile[];
  error?: string;
}

function useTaskStatus(taskId: string | null): {
  status: TaskStatus | null;
  error: string | null;
  isConnected: boolean;
}
```

**Functionality:**
- **WebSocket Management**: Automatic connection/disconnection
- **Reconnection Logic**: Automatic reconnection on connection loss
- **Error Handling**: Connection error management
- **Status Caching**: Maintains last known status

**Connection Lifecycle:**
1. **Connection**: Establishes WebSocket when taskId provided
2. **Monitoring**: Receives real-time status updates
3. **Error Handling**: Manages connection failures
4. **Cleanup**: Closes connection when component unmounts

## API Client

### HTTP Client Service

**File**: `src/api/client.ts`

Handles all HTTP communication with the FastAPI backend.

```typescript
interface UploadResponse {
  task_id: string;
  filename: string;
  status: string;
}

class ApiClient {
  async uploadFile(file: File): Promise<UploadResponse>
  async getTaskStatus(taskId: string): Promise<TaskStatus>
  async downloadFile(taskId: string, fileType: string): Promise<Blob>
  async cleanupTask(taskId: string): Promise<void>
}
```

**Methods:**

#### uploadFile()
- **Purpose**: Upload JSON file to backend
- **Parameters**: File object from user selection
- **Returns**: Task ID and initial status
- **Error Handling**: File validation and upload errors

#### getTaskStatus()
- **Purpose**: Poll task status (fallback for WebSocket)
- **Parameters**: Task ID from upload response
- **Returns**: Current task status and progress
- **Usage**: Backup status checking when WebSocket unavailable

#### downloadFile()
- **Purpose**: Download processed Excel or log files
- **Parameters**: Task ID and file type ('excel' or 'log')
- **Returns**: File blob for download
- **Features**: Handles binary file downloads with proper headers

#### cleanupTask()
- **Purpose**: Clean up server resources after download
- **Parameters**: Task ID to cleanup
- **Returns**: Success confirmation
- **Usage**: Called automatically after successful downloads

## User Interface Flow

### 1. Initial State
```
┌─────────────────────────────────────┐
│            File Upload              │
│                                     │
│     [Drag & Drop JSON File]         │
│                                     │
│        Or Click to Browse           │
└─────────────────────────────────────┘
```

### 2. File Upload Process
```
User Selects File
       ↓
File Validation (JSON type check)
       ↓
Upload to Backend (/api/upload)
       ↓
Receive Task ID
       ↓
Establish WebSocket Connection
       ↓
Display Processing Status
```

### 3. Real-time Processing Updates
```
WebSocket Message Received
       ↓
Update Progress Bar (0-100%)
       ↓
Display Current Status
       ↓
Update File List (when complete)
       ↓
Show Download Options
```

### 4. File Download Process
```
User Clicks Download
       ↓
Request File from Backend
       ↓
Stream File to Browser
       ↓
Trigger Browser Download
       ↓
Cleanup Task (optional)
```

## Styling and Design

### Tailwind CSS Configuration

The application uses Tailwind CSS for styling with custom configuration:

```javascript
// tailwind.config.js
module.exports = {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#3B82F6',    // Blue
        secondary: '#6B7280',  // Gray
        success: '#10B981',    // Green
        error: '#EF4444',      // Red
        warning: '#F59E0B',    // Yellow
      }
    }
  }
}
```

### Component Design Patterns

#### Consistent Color Scheme
- **Primary Blue**: Action buttons, links, active states
- **Secondary Gray**: Text, borders, inactive elements
- **Success Green**: Completed states, success messages
- **Error Red**: Error states, validation failures
- **Warning Yellow**: Warnings, pending states

#### Responsive Design
```css
/* Mobile-first approach */
.container {
  @apply w-full px-4;
}

/* Tablet and above */
@screen md {
  .container {
    @apply max-w-2xl mx-auto px-6;
  }
}

/* Desktop */
@screen lg {
  .container {
    @apply max-w-4xl px-8;
  }
}
```

## State Management

### Component State Structure

```typescript
// Main App State
interface AppState {
  currentStep: 'upload' | 'processing' | 'results' | 'error';
  taskId: string | null;
  uploadedFile: File | null;
  error: string | null;
}

// Processing State (from useTaskStatus)
interface ProcessingState {
  status: TaskStatus | null;
  progress: number;
  isConnected: boolean;
  error: string | null;
}
```

### State Transitions

```
Initial State (upload)
       ↓
File Selected → Uploading
       ↓
Upload Success → Processing
       ↓
Processing Complete → Results
       ↓
User Reset → Initial State

Error can occur at any stage → Error State
```

## Error Handling

### Error Categories

1. **File Validation Errors**
   - Invalid file type (not JSON)
   - File too large
   - Empty file

2. **Upload Errors**
   - Network connectivity issues
   - Server errors (5xx)
   - Timeout errors

3. **Processing Errors**
   - Invalid JSON structure
   - Missing required data
   - Processing timeout

4. **Download Errors**
   - File not found
   - Network issues during download
   - File corruption

### Error Display Strategy

```typescript
interface ErrorState {
  type: 'validation' | 'upload' | 'processing' | 'download';
  message: string;
  details?: string;
  recoverable: boolean;
}
```

**Error UI Components:**
- **Toast Notifications**: Brief, dismissible messages
- **Inline Errors**: Contextual error messages near form elements
- **Error Pages**: Full-page errors for critical failures
- **Retry Buttons**: For recoverable errors

## Development

### Prerequisites
```bash
Node.js 16+ 
npm or yarn
```

### Development Setup

1. **Install Dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Start Development Server**
   ```bash
   npm run dev
   ```
   Opens browser to `http://localhost:5173`

3. **Development with Backend**
   ```bash
   # Terminal 1: Start backend
   cd backend && python app.py
   
   # Terminal 2: Start frontend
   cd frontend && npm run dev
   ```

### Available Scripts

```bash
npm run dev          # Start development server
npm run build        # Build for production
npm run preview      # Preview production build
npm run lint         # Run ESLint
npm run type-check   # Run TypeScript checks
```

### Build Configuration

**Vite Configuration** (`vite.config.ts`):
```typescript
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',  # Proxy API calls to backend
      '/ws': {
        target: 'ws://localhost:8000',  # Proxy WebSocket connections
        ws: true
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom']  # Separate vendor bundle
        }
      }
    }
  }
})
```

## Testing

### Testing Strategy

1. **Unit Tests**: Component logic and utilities
2. **Integration Tests**: API client and hooks
3. **E2E Tests**: Full user workflows

### Test Setup

```bash
npm install --save-dev @testing-library/react @testing-library/jest-dom vitest
```

**Example Component Test:**
```typescript
import { render, screen } from '@testing-library/react';
import { FileUpload } from './FileUpload';

test('displays drag and drop area', () => {
  render(<FileUpload onFileSelect={jest.fn()} isUploading={false} />);
  expect(screen.getByText(/drag.*drop/i)).toBeInTheDocument();
});
```

## Production Build

### Build Process

```bash
npm run build
```

**Output Structure:**
```
dist/
├── index.html          # Main HTML file
├── assets/
│   ├── index-[hash].js # Main JavaScript bundle
│   ├── index-[hash].css # Compiled CSS
│   └── vendor-[hash].js # Third-party libraries
└── [other static assets]
```

### Deployment Considerations

1. **Static File Serving**: Built files served by FastAPI backend
2. **API Proxying**: All API calls proxied through backend
3. **WebSocket Support**: Ensure WebSocket proxy configuration
4. **Caching**: Proper cache headers for static assets

## Performance Optimizations

### Bundle Optimization
- **Code Splitting**: Vendor libraries separated
- **Tree Shaking**: Unused code elimination
- **Minification**: JavaScript and CSS compression

### Runtime Optimization
- **Lazy Loading**: Components loaded on demand
- **Memoization**: React.memo for expensive components
- **Debounced API Calls**: Reduced server requests

### WebSocket Optimization
- **Connection Pooling**: Reuse connections where possible
- **Automatic Reconnection**: Handle network interruptions
- **Message Batching**: Reduce message frequency

---

**Version**: 2.0.0  
**Last Updated**: January 2025  
**Framework**: React 18 + TypeScript + Vite
