'use client'

import { WifiIcon } from '@heroicons/react/24/outline'
import clsx from 'clsx'

interface ConnectionStatusProps {
  isConnected: boolean
}

export function ConnectionStatus({ isConnected }: ConnectionStatusProps) {
  return (
    <div className="flex items-center space-x-2">
      <WifiIcon
        className={clsx(
          'h-5 w-5',
          isConnected ? 'text-success-500' : 'text-danger-500'
        )}
      />
      <div className="flex flex-col">
        <span
          className={clsx(
            'text-xs font-medium',
            isConnected ? 'text-success-600' : 'text-danger-600'
          )}
        >
          {isConnected ? 'Connected' : 'Disconnected'}
        </span>
        <span className="text-xs text-gray-500">
          Real-time Data
        </span>
      </div>
      <div
        className={clsx(
          'w-2 h-2 rounded-full',
          isConnected ? 'bg-success-400 animate-pulse' : 'bg-danger-400'
        )}
      />
    </div>
  )
}