interface ErrorDisplayProps {
  message: string
  onReset: () => void
}

export default function ErrorDisplay({ message, onReset }: ErrorDisplayProps) {
  return (
    <div className="text-center py-8 space-y-6">
      <div className="flex justify-center">
        <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center">
          <svg 
            className="w-10 h-10 text-red-600" 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={2} 
              d="M6 18L18 6M6 6l12 12" 
            />
          </svg>
        </div>
      </div>
      
      <div className="space-y-2">
        <h2 className="text-2xl font-semibold text-gray-800">
          Processing Failed
        </h2>
        <p className="text-gray-600 max-w-md mx-auto">
          {message || 'There was an error processing your file. Please ensure it\'s a valid JSON file and try again.'}
        </p>
      </div>
      
      <button
        onClick={onReset}
        className="px-6 py-2 bg-gradient-to-r from-primary-600 to-secondary-600 text-white rounded-lg font-medium hover:shadow-lg hover:scale-105 transition-all duration-300"
      >
        Try Again
      </button>
    </div>
  )
}
