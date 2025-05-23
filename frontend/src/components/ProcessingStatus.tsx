import { TaskStatus } from '../api/client'

interface ProcessingStatusProps {
  taskId: string
  status: TaskStatus['status']
  progress: number
}

export default function ProcessingStatus({ taskId, status, progress }: ProcessingStatusProps) {
  return (
    <div className="text-center py-8 space-y-6">
      <div className="flex justify-center">
        <div className="spinner" />
      </div>
      
      <div className="space-y-2">
        <h2 className="text-2xl font-semibold text-gray-800">
          Processing your file...
        </h2>
        <p className="text-gray-600">
          {status === 'queued' 
            ? 'Your file is queued for processing' 
            : 'Analyzing data and generating reports'
          }
        </p>
      </div>
      
      <div className="max-w-md mx-auto">
        <div className="bg-gray-200 rounded-full h-3 overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-primary-600 to-secondary-600 rounded-full transition-all duration-500 ease-out relative progress-shimmer"
            style={{ width: `${progress}%` }}
          />
        </div>
        <p className="text-sm text-gray-500 mt-2">{progress}% complete</p>
      </div>
      
      <div className="text-xs text-gray-400">
        Task ID: {taskId}
      </div>
    </div>
  )
}
