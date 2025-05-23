import axios from 'axios'

const API_BASE_URL = import.meta.env.DEV ? '' : '/api'

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface UploadResponse {
  task_id: string
  filename: string
  status: string
}

export interface TaskStatus {
  task_id: string
  filename: string
  status: 'queued' | 'processing' | 'complete' | 'failed'
  created: string
  progress?: number
  files?: Array<{
    type: 'excel' | 'log'
    filename: string
  }>
  error?: string
}

export const uploadFile = async (file: File): Promise<UploadResponse> => {
  const formData = new FormData()
  formData.append('file', file)
  
  const response = await api.post<UploadResponse>('/api/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  
  return response.data
}

export const getTaskStatus = async (taskId: string): Promise<TaskStatus> => {
  const response = await api.get<TaskStatus>(`/api/tasks/${taskId}/status`)
  return response.data
}

export const downloadFile = (taskId: string, fileType: 'excel' | 'log'): string => {
  return `/api/tasks/${taskId}/download/${fileType}`
}

export const cleanupTask = async (taskId: string): Promise<void> => {
  await api.delete(`/api/tasks/${taskId}`)
}
