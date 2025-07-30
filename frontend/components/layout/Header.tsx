'use client'

import { useState } from 'react'
import { BellIcon, CogIcon } from '@heroicons/react/24/outline'
import { useWebSocket } from '@/hooks/useWebSocket'
import { ConnectionStatus } from './ConnectionStatus'
import { NotificationCenter } from './NotificationCenter'

export function Header() {
  const { isConnected } = useWebSocket()
  const [showNotifications, setShowNotifications] = useState(false)

  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Left side - Logo and title */}
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <h1 className="text-xl font-bold text-gradient">TradingScreener</h1>
            </div>
            <div className="ml-6">
              <p className="text-sm text-gray-600">
                Real-time Market Analysis
              </p>
            </div>
          </div>

          {/* Right side - Status and controls */}
          <div className="flex items-center space-x-4">
            {/* Connection Status */}
            <ConnectionStatus isConnected={isConnected} />

            {/* Market Status */}
            <div className="flex items-center text-sm">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-success-400 rounded-full animate-pulse"></div>
                <span className="text-gray-600">Market Open</span>
              </div>
            </div>

            {/* Notifications */}
            <div className="relative">
              <button
                onClick={() => setShowNotifications(!showNotifications)}
                className="p-2 text-gray-400 hover:text-gray-600 transition-colors relative"
              >
                <BellIcon className="h-6 w-6" />
                <span className="absolute -top-1 -right-1 h-4 w-4 bg-danger-500 text-white text-xs rounded-full flex items-center justify-center">
                  3
                </span>
              </button>
              
              {showNotifications && (
                <NotificationCenter
                  isOpen={showNotifications}
                  onClose={() => setShowNotifications(false)}
                />
              )}
            </div>

            {/* Settings */}
            <button className="p-2 text-gray-400 hover:text-gray-600 transition-colors">
              <CogIcon className="h-6 w-6" />
            </button>

            {/* User Menu */}
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-primary-500 rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-medium">T</span>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">Trader</p>
                <p className="text-xs text-gray-500">Active</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}