import { useState, useEffect, useRef } from 'react'
import { getTaskStatus, TaskStatus } from '../api/client'

interface UseTaskStatusOptions {
  onComplete?: () => void
  onError?: (error: string) => void
}

export function useTaskStatus(taskId: string | null, options: UseTaskStatusOptions = {}) {
  const [status, setStatus] = useState<TaskStatus['status']>('queued')
  const [progress, setProgress] = useState(0)
  const [files, setFiles] = useState<TaskStatus['files']>([])
  const intervalRef = useRef<number | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const isCleanedUpRef = useRef(false)
  const optionsRef = useRef(options)

  // Update the options ref when options change, but don't trigger useEffect
  useEffect(() => {
    optionsRef.current = options
  }, [options])

  useEffect(() => {
    if (!taskId) {
      // Clean up any existing connections when taskId becomes null
      cleanup()
      return
    }

    // Reset cleanup flag for new task
    isCleanedUpRef.current = false

    // Try WebSocket first for real-time updates
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const apiBase = import.meta.env.DEV ? '' : '/api'
    const wsUrl = `${protocol}//${window.location.host}${apiBase}/ws/tasks/${taskId}`
    
    let wsConnected = false
    
    try {
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        wsConnected = true
        console.log(`WebSocket connected for task ${taskId || 'unknown'}`)
      }

      ws.onmessage = (event) => {
        if (isCleanedUpRef.current) return
        
        const data: TaskStatus = JSON.parse(event.data)
        setStatus(data.status)
        setProgress(data.progress || 0)
        setFiles(data.files || [])

        if (data.status === 'complete') {
          optionsRef.current.onComplete?.()
          cleanup()
        } else if (data.status === 'failed') {
          optionsRef.current.onError?.(data.error || 'Processing failed')
          cleanup()
        }
      }

      ws.onerror = (error) => {
        console.error(`WebSocket error for task ${taskId || 'unknown'}:`, error)
        if (!wsConnected && !isCleanedUpRef.current) {
          // Fall back to polling if WebSocket fails to connect
          startPolling()
        }
      }

      ws.onclose = (event) => {
        console.log(`WebSocket closed for task ${taskId || 'unknown'}:`, event.code, event.reason)
        if (!isCleanedUpRef.current && wsConnected && event.code !== 1000) {
          // Reconnect if connection was lost unexpectedly (not a normal close)
          setTimeout(() => {
            if (!isCleanedUpRef.current) {
              startPolling()
            }
          }, 1000)
        }
      }
    } catch (error) {
      console.error(`WebSocket creation failed for task ${taskId || 'unknown'}:`, error)
      // Fall back to polling
      startPolling()
    }

    function cleanup() {
      if (isCleanedUpRef.current) return
      
      isCleanedUpRef.current = true
      console.log(`Cleaning up task ${taskId || 'unknown'}`)
      
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      
      if (wsRef.current) {
        wsRef.current.close(1000, 'Task completed')
        wsRef.current = null
      }
    }

    function startPolling() {
      if (isCleanedUpRef.current) return
      
      // Initial check
      checkStatus()
      
      // Poll every 2 seconds
      if (!intervalRef.current) {
        intervalRef.current = setInterval(checkStatus, 2000)
      }
    }

    async function checkStatus() {
      if (isCleanedUpRef.current || !taskId) return
      
      try {
        const data = await getTaskStatus(taskId)
        
        if (isCleanedUpRef.current) return
        
        setStatus(data.status)
        setProgress(data.progress || 0)
        setFiles(data.files || [])

        if (data.status === 'complete') {
          optionsRef.current.onComplete?.()
          cleanup()
        } else if (data.status === 'failed') {
          optionsRef.current.onError?.(data.error || 'Processing failed')
          cleanup()
        }
      } catch (error: any) {
        if (isCleanedUpRef.current) return
        
        // If we get a 404, the task was deleted - stop polling
        if (error?.response?.status === 404) {
          console.log(`Task ${taskId || 'unknown'} not found (404) - stopping status checks`)
          cleanup()
          return
        }
        
        console.error('Error checking status:', error)
        
        // For other errors, continue polling but with exponential backoff
        if (intervalRef.current) {
          clearInterval(intervalRef.current)
          intervalRef.current = setTimeout(() => {
            if (!isCleanedUpRef.current) {
              startPolling()
            }
          }, 5000) // Wait 5 seconds before retrying
        }
      }
    }

    return () => {
      cleanup()
    }
  }, [taskId]) // Only depend on taskId, not options

  return { status, progress, files }
}
