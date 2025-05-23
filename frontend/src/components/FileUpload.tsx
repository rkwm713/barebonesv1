import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { uploadFile } from '../api/client'

interface FileUploadProps {
  onUploadSuccess: (taskId: string) => void
  onUploadError: (error: string) => void
}

export default function FileUpload({ onUploadSuccess, onUploadError }: FileUploadProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0]
      if (file.type === 'application/json' || file.name.endsWith('.json')) {
        setSelectedFile(file)
      } else {
        onUploadError('Please select a JSON file.')
      }
    }
  }, [onUploadError])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/json': ['.json']
    },
    maxFiles: 1,
    disabled: isUploading
  })

  const handleUpload = async () => {
    if (!selectedFile) {
      onUploadError('Please select a file first.')
      return
    }

    setIsUploading(true)
    
    try {
      const response = await uploadFile(selectedFile)
      onUploadSuccess(response.task_id)
    } catch (error) {
      console.error('Upload error:', error)
      onUploadError('Failed to upload file. Please try again.')
      setIsUploading(false)
    }
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  return (
    <div className="space-y-6">
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-xl p-12 text-center cursor-pointer
          transition-all duration-300 ease-in-out
          ${isDragActive 
            ? 'border-primary-500 bg-primary-50 scale-105' 
            : 'border-gray-300 hover:border-primary-400 hover:bg-gray-50'
          }
          ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input {...getInputProps()} />
        
        <div className="flex flex-col items-center space-y-4">
          <div className={`p-4 rounded-full ${isDragActive ? 'bg-primary-100' : 'bg-gray-100'}`}>
            <svg 
              className={`w-12 h-12 ${isDragActive ? 'text-primary-600' : 'text-gray-400'}`}
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" 
              />
            </svg>
          </div>
          
          <div>
            <p className="text-lg font-medium text-gray-700">
              {isDragActive 
                ? 'Drop your JSON file here' 
                : 'Drag and drop your JSON file here'
              }
            </p>
            <p className="text-sm text-gray-500 mt-1">
              or <span className="text-primary-600 font-medium">browse</span> to select
            </p>
          </div>
        </div>
      </div>

      {selectedFile && (
        <div className="bg-gray-50 rounded-lg p-4 animate-fade-in">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-primary-100 rounded">
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
              </div>
              <div>
                <p className="font-medium text-gray-900">{selectedFile.name}</p>
                <p className="text-sm text-gray-500">{formatFileSize(selectedFile.size)}</p>
              </div>
            </div>
            
            <button
              onClick={handleUpload}
              disabled={isUploading}
              className={`
                px-6 py-2 rounded-lg font-medium text-white
                transition-all duration-300 ease-in-out
                ${isUploading 
                  ? 'bg-gray-400 cursor-not-allowed' 
                  : 'bg-gradient-to-r from-primary-600 to-secondary-600 hover:shadow-lg hover:scale-105'
                }
              `}
            >
              {isUploading ? 'Uploading...' : 'Generate Reports'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
