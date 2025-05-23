import { useState, useCallback } from 'react'
import FileUpload from './components/FileUpload'
import ProcessingStatus from './components/ProcessingStatus'
import Results from './components/Results'
import ErrorDisplay from './components/ErrorDisplay'
import { useTaskStatus } from './hooks/useTaskStatus'

export type AppState = 'idle' | 'processing' | 'complete' | 'error'

function App() {
  const [taskId, setTaskId] = useState<string | null>(null)
  const [appState, setAppState] = useState<AppState>('idle')
  const [errorMessage, setErrorMessage] = useState<string>('')
  
  const handleTaskComplete = useCallback(() => {
    setAppState('complete')
  }, [])
  
  const handleTaskError = useCallback((error: string) => {
    setAppState('error')
    setErrorMessage(error)
  }, [])
  
  const { status, progress, files } = useTaskStatus(taskId, {
    onComplete: handleTaskComplete,
    onError: handleTaskError
  })

  const handleUploadSuccess = (newTaskId: string) => {
    setTaskId(newTaskId)
    setAppState('processing')
    setErrorMessage('')
  }

  const handleUploadError = (error: string) => {
    setAppState('error')
    setErrorMessage(error)
  }

  const handleReset = () => {
    setTaskId(null)
    setAppState('idle')
    setErrorMessage('')
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="background-gradient" />
      
      <header className="text-center py-8 animate-slide-down">
        <h1 className="text-5xl font-bold bg-gradient-to-r from-primary-600 to-secondary-600 bg-clip-text text-transparent mb-2">
          MakeReady Report Generator
        </h1>
        <p className="text-gray-600 text-lg">Upload your JSON file to generate professional reports</p>
      </header>

      <main className="max-w-4xl mx-auto px-4 pb-8">
        <div className="bg-white rounded-2xl shadow-lg p-8 relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-primary-600 to-secondary-600" />
          
          {appState === 'idle' && (
            <FileUpload 
              onUploadSuccess={handleUploadSuccess}
              onUploadError={handleUploadError}
            />
          )}
          
          {appState === 'processing' && taskId && (
            <ProcessingStatus 
              taskId={taskId}
              status={status}
              progress={progress}
            />
          )}
          
          {appState === 'complete' && taskId && (
            <Results 
              taskId={taskId}
              files={files}
              onReset={handleReset}
            />
          )}
          
          {appState === 'error' && (
            <ErrorDisplay 
              message={errorMessage}
              onReset={handleReset}
            />
          )}
        </div>
      </main>

      <footer className="text-center py-6 text-gray-500 text-sm">
        <p>MakeReady Report Generator © 2025 | Built with FastAPI + React</p>
      </footer>
    </div>
  )
}

export default App
