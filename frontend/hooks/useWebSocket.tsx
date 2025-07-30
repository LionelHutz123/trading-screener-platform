'use client'

import { createContext, useContext, useEffect, useRef, useState, ReactNode } from 'react'
import { io, Socket } from 'socket.io-client'
import toast from 'react-hot-toast'

interface WebSocketContextType {
  socket: Socket | null
  isConnected: boolean
  subscribe: (event: string, callback: (data: any) => void) => void
  unsubscribe: (event: string, callback?: (data: any) => void) => void
  emit: (event: string, data?: any) => void
}

const WebSocketContext = createContext<WebSocketContextType | null>(null)

interface WebSocketProviderProps {
  children: ReactNode
}

export function WebSocketProvider({ children }: WebSocketProviderProps) {
  const [socket, setSocket] = useState<Socket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()
  const reconnectAttemptsRef = useRef(0)
  const maxReconnectAttempts = 5

  useEffect(() => {
    // Initialize socket connection
    const socketInstance = io(process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8080', {
      transports: ['websocket'],
      autoConnect: true,
    })

    // Connection events
    socketInstance.on('connect', () => {
      console.log('WebSocket connected')
      setIsConnected(true)
      reconnectAttemptsRef.current = 0
      toast.success('Connected to real-time data feed')
    })

    socketInstance.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason)
      setIsConnected(false)
      toast.error('Disconnected from real-time data feed')
      
      // Attempt to reconnect
      if (reason === 'io server disconnect') {
        // Server initiated disconnect, don't reconnect automatically
        return
      }
      
      attemptReconnect(socketInstance)
    })

    socketInstance.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error)
      setIsConnected(false)
      attemptReconnect(socketInstance)
    })

    // Global event handlers
    socketInstance.on('signal_alert', (data) => {
      handleSignalAlert(data)
    })

    socketInstance.on('market_update', (data) => {
      handleMarketUpdate(data)
    })

    socketInstance.on('system_alert', (data) => {
      handleSystemAlert(data)
    })

    setSocket(socketInstance)

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      socketInstance.disconnect()
    }
  }, [])

  const attemptReconnect = (socketInstance: Socket) => {
    if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
      toast.error('Failed to reconnect. Please refresh the page.')
      return
    }

    const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000)
    reconnectAttemptsRef.current += 1

    reconnectTimeoutRef.current = setTimeout(() => {
      console.log(`Reconnection attempt ${reconnectAttemptsRef.current}`)
      socketInstance.connect()
    }, delay)
  }

  const handleSignalAlert = (data: any) => {
    const { priority, title, symbol, signal_type } = data
    
    let toastFn = toast
    if (priority === 1) toastFn = toast.error      // Critical
    else if (priority === 2) toastFn = toast        // High
    else if (priority === 3) toastFn = toast.success // Medium
    else toastFn = toast                            // Low

    toastFn(`${signal_type.toUpperCase()} Signal: ${symbol}`, {
      duration: 6000,
      icon: signal_type === 'bullish' ? '📈' : '📉',
    })
  }

  const handleMarketUpdate = (data: any) => {
    // Handle real-time market data updates
    // This will be used by chart components
    console.log('Market update:', data)
  }

  const handleSystemAlert = (data: any) => {
    const { title, message, priority } = data
    
    if (priority <= 2) {
      toast.error(`${title}: ${message}`)
    } else {
      toast(`${title}: ${message}`)
    }
  }

  const subscribe = (event: string, callback: (data: any) => void) => {
    if (socket) {
      socket.on(event, callback)
    }
  }

  const unsubscribe = (event: string, callback?: (data: any) => void) => {
    if (socket) {
      if (callback) {
        socket.off(event, callback)
      } else {
        socket.off(event)
      }
    }
  }

  const emit = (event: string, data?: any) => {
    if (socket && isConnected) {
      socket.emit(event, data)
    }
  }

  const value: WebSocketContextType = {
    socket,
    isConnected,
    subscribe,
    unsubscribe,
    emit,
  }

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  )
}

export function useWebSocket() {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider')
  }
  return context
}