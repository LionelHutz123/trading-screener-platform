'use client'

import { useEffect, useRef } from 'react'
import { XMarkIcon, BellIcon } from '@heroicons/react/24/outline'
import { format } from 'date-fns'
import clsx from 'clsx'

interface Notification {
  id: string
  type: 'signal' | 'system' | 'market'
  title: string
  message: string
  timestamp: Date
  priority: 'critical' | 'high' | 'medium' | 'low'
  read: boolean
}

interface NotificationCenterProps {
  isOpen: boolean
  onClose: () => void
}

// Mock notifications - in real app, this would come from API/WebSocket
const mockNotifications: Notification[] = [
  {
    id: '1',
    type: 'signal',
    title: 'BULLISH Signal: AAPL',
    message: 'Strong confluence signal detected with 85% confidence',
    timestamp: new Date(Date.now() - 5 * 60 * 1000),
    priority: 'high',
    read: false,
  },
  {
    id: '2',
    type: 'market',
    title: 'Market Alert',
    message: 'SPY broke above key resistance level at $420',
    timestamp: new Date(Date.now() - 15 * 60 * 1000),
    priority: 'medium',
    read: false,
  },
  {
    id: '3',
    type: 'system',
    title: 'Data Update',
    message: 'Historical data refresh completed for 500 symbols',
    timestamp: new Date(Date.now() - 30 * 60 * 1000),
    priority: 'low',
    read: true,
  },
]

export function NotificationCenter({ isOpen, onClose }: NotificationCenterProps) {
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
        onClose()
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen, onClose])

  if (!isOpen) return null

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical':
        return 'text-danger-600 bg-danger-50 border-danger-200'
      case 'high':
        return 'text-warning-600 bg-warning-50 border-warning-200'
      case 'medium':
        return 'text-primary-600 bg-primary-50 border-primary-200'
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'signal':
        return '📈'
      case 'market':
        return '📊'
      case 'system':
        return '⚙️'
      default:
        return '📋'
    }
  }

  return (
    <div className="absolute right-0 top-full mt-2 w-96 max-w-sm">
      <div
        ref={panelRef}
        className="bg-white rounded-lg shadow-lg border border-gray-200 max-h-96 overflow-hidden"
      >
        {/* Header */}
        <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center">
            <BellIcon className="h-5 w-5 text-gray-400 mr-2" />
            <h3 className="text-sm font-medium text-gray-900">Notifications</h3>
            <span className="ml-2 bg-primary-100 text-primary-800 text-xs px-2 py-0.5 rounded-full">
              {mockNotifications.filter(n => !n.read).length} new
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        {/* Notifications List */}
        <div className="max-h-80 overflow-y-auto scrollbar-thin">
          {mockNotifications.length === 0 ? (
            <div className="p-4 text-center text-gray-500">
              <BellIcon className="h-8 w-8 mx-auto mb-2 text-gray-300" />
              <p className="text-sm">No notifications</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {mockNotifications.map((notification) => (
                <div
                  key={notification.id}
                  className={clsx(
                    'p-4 hover:bg-gray-50 transition-colors cursor-pointer',
                    !notification.read && 'bg-blue-50/50'
                  )}
                >
                  <div className="flex items-start space-x-3">
                    <div className="text-lg">{getTypeIcon(notification.type)}</div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {notification.title}
                        </p>
                        <span
                          className={clsx(
                            'text-xs px-2 py-0.5 rounded-full border',
                            getPriorityColor(notification.priority)
                          )}
                        >
                          {notification.priority}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                        {notification.message}
                      </p>
                      <p className="text-xs text-gray-400 mt-2">
                        {format(notification.timestamp, 'MMM d, h:mm a')}
                      </p>
                    </div>
                    {!notification.read && (
                      <div className="w-2 h-2 bg-primary-500 rounded-full flex-shrink-0 mt-2" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-gray-200 bg-gray-50">
          <div className="flex justify-between text-xs">
            <button className="text-primary-600 hover:text-primary-800 font-medium">
              Mark all as read
            </button>
            <button className="text-gray-600 hover:text-gray-800">
              View all notifications
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}