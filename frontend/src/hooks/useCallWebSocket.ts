import { useState, useEffect } from 'react'

export interface TranscriptEntry {
  role: string
  content: string
  timestamp: string
}

export interface DataPoint {
  field_name: string
  display_name: string
  candidate_value: unknown
  employer_value: unknown
  status: string
  match: boolean | null
}

interface UseCallWebSocketResult {
  transcript: TranscriptEntry[]
  collectedData: DataPoint[]
  currentState: string
  isConnected: boolean
  callCompleted: boolean
}

export function useCallWebSocket(sessionId: string | null): UseCallWebSocketResult {
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([])
  const [collectedData, setCollectedData] = useState<DataPoint[]>([])
  const [currentState, setCurrentState] = useState('')
  const [isConnected, setIsConnected] = useState(false)
  const [callCompleted, setCallCompleted] = useState(false)

  useEffect(() => {
    if (!sessionId) return

    const wsUrl = `ws://localhost:8000/api/ws/${sessionId}`
    let ws: WebSocket
    let reconnectTimeout: ReturnType<typeof setTimeout>
    let cancelled = false

    const connect = () => {
      if (cancelled) return
      try {
        ws = new WebSocket(wsUrl)

        ws.onopen = () => setIsConnected(true)
        ws.onclose = () => {
          setIsConnected(false)
          if (!cancelled && !callCompleted) {
            reconnectTimeout = setTimeout(connect, 3000)
          }
        }
        ws.onerror = () => setIsConnected(false)

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data as string)
            if (msg.type === 'transcript') {
              setTranscript((prev) => [
                ...prev,
                { role: msg.role, content: msg.content, timestamp: new Date().toISOString() },
              ])
            } else if (msg.type === 'data_point') {
              const entry: DataPoint = {
                field_name: msg.field_name,
                display_name: msg.display_name || msg.field_name,
                candidate_value: msg.candidate_value ?? null,
                employer_value: msg.value ?? null,
                status: msg.status || 'pending',
                match: msg.match ?? null,
              }
              setCollectedData((prev) => {
                const idx = prev.findIndex((d) => d.field_name === msg.field_name)
                return idx >= 0 ? prev.map((d, i) => (i === idx ? entry : d)) : [...prev, entry]
              })
            } else if (msg.type === 'state_transition') {
              setCurrentState(msg.new_state)
            } else if (msg.type === 'call_completed') {
              setCallCompleted(true)
              setIsConnected(false)
            }
          } catch {
            // ignore parse errors
          }
        }
      } catch {
        // ignore connection errors — will retry
      }
    }

    connect()
    return () => {
      cancelled = true
      clearTimeout(reconnectTimeout)
      ws?.close()
    }
  }, [sessionId]) // eslint-disable-line react-hooks/exhaustive-deps

  return { transcript, collectedData, currentState, isConnected, callCompleted }
}
