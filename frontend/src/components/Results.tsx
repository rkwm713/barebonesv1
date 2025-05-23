import { TaskStatus, downloadFile, cleanupTask } from '../api/client'

interface ResultsProps {
  taskId: string
  files?: TaskStatus['files']
  onReset: () => void
}

export default function Results({ taskId, files, onReset }: ResultsProps) {
  const handleDownload = (fileType: 'excel' | 'log') => {
    const url = downloadFile(taskId, fileType)
    window.open(url, '_blank')
  }

  const handleReset = async () => {
    try {
      await cleanupTask(taskId)
    } catch (error) {
      console.error('Error cleaning up task:', error)
    }
    onReset()
  }

  return (
    <div className="text-center py-8 space-y-6">
      <div className="flex justify-center">
        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
          <svg 
            className="w-10 h-10 text-green-600" 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={2} 
              d="M5 13l4 4L19 7" 
            />
          </svg>
        </div>
      </div>
      
      <div className="space-y-2">
        <h2 className="text-2xl font-semibold text-gray-800">
          Reports Generated Successfully!
        </h2>
        <p className="text-gray-600">
          Your reports are ready for download:
        </p>
      </div>
      
      <div className="space-y-3 max-w-md mx-auto">
        {files && files.map((file) => (
          <button
            key={file.type}
            onClick={() => handleDownload(file.type)}
            className="w-full flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors duration-200 group"
          >
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-primary-100 rounded group-hover:bg-primary-200 transition-colors">
                {file.type === 'excel' ? (
                  <svg 
                    className="w-6 h-6 text-primary-600" 
                    fill="none" 
                    stroke="currentColor" 
                    viewBox="0 0 24 24"
                  >
                    <path 
                      strokeLinecap="round" 
                      strokeLinejoin="round" 
                      strokeWidth={2} 
                      d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" 
                    />
                  </svg>
                ) : (
                  <svg 
                    className="w-6 h-6 text-primary-600" 
                    fill="none" 
                    stroke="currentColor" 
                    viewBox="0 0 24 24"
                  >
                    <path 
                      strokeLinecap="round" 
                      strokeLinejoin="round" 
                      strokeWidth={2} 
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" 
                    />
                  </svg>
                )}
              </div>
              <div className="text-left">
                <p className="font-medium text-gray-900">{file.filename}</p>
                <p className="text-sm text-gray-500">
                  {file.type === 'excel' ? 'Excel Report' : 'Processing Log'}
                </p>
              </div>
            </div>
            
            <svg 
              className="w-5 h-5 text-gray-400 group-hover:text-primary-600 transition-colors" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" 
              />
            </svg>
          </button>
        ))}
      </div>
      
      <button
        onClick={handleReset}
        className="px-6 py-2 border-2 border-primary-600 text-primary-600 rounded-lg font-medium hover:bg-primary-50 transition-colors duration-200"
      >
        Process Another File
      </button>
    </div>
  )
}
