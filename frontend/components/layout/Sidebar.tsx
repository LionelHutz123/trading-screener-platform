'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  ChartBarIcon,
  BellIcon,
  CogIcon,
  HomeIcon,
  ChartPieIcon,
  DocumentTextIcon,
  CurrencyDollarIcon,
  ClockIcon,
} from '@heroicons/react/24/outline'
import clsx from 'clsx'

const navigation = [
  { name: 'Dashboard', href: '/', icon: HomeIcon },
  { name: 'Signals', href: '/signals', icon: BellIcon },
  { name: 'Charts', href: '/charts', icon: ChartBarIcon },
  { name: 'Portfolio', href: '/portfolio', icon: CurrencyDollarIcon },
  { name: 'Backtesting', href: '/backtesting', icon: ClockIcon },
  { name: 'Analytics', href: '/analytics', icon: ChartPieIcon },
  { name: 'Reports', href: '/reports', icon: DocumentTextIcon },
  { name: 'Settings', href: '/settings', icon: CogIcon },
]

export function Sidebar() {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div
      className={clsx(
        'bg-gray-900 flex flex-col transition-all duration-300',
        collapsed ? 'w-16' : 'w-64'
      )}
    >
      {/* Logo */}
      <div className="flex items-center justify-between p-4">
        {!collapsed && (
          <div className="flex items-center">
            <div className="w-8 h-8 bg-primary-500 rounded-lg flex items-center justify-center">
              <ChartBarIcon className="h-5 w-5 text-white" />
            </div>
            <span className="ml-3 text-white font-semibold">TradingScreener</span>
          </div>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="text-gray-400 hover:text-white transition-colors"
        >
          <svg
            className={clsx('h-6 w-6 transition-transform', collapsed && 'rotate-180')}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M11 19l-7-7 7-7m8 14l-7-7 7-7"
            />
          </svg>
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 pb-4 space-y-1">
        {navigation.map((item) => {
          const isActive = pathname === item.href
          return (
            <Link
              key={item.name}
              href={item.href}
              className={clsx(
                'group flex items-center px-2 py-2 text-sm font-medium rounded-md transition-colors',
                isActive
                  ? 'bg-primary-600 text-white'
                  : 'text-gray-300 hover:bg-gray-700 hover:text-white'
              )}
              title={collapsed ? item.name : undefined}
            >
              <item.icon
                className={clsx(
                  'flex-shrink-0 h-6 w-6',
                  isActive ? 'text-white' : 'text-gray-400 group-hover:text-white'
                )}
              />
              {!collapsed && <span className="ml-3">{item.name}</span>}
            </Link>
          )
        })}
      </nav>

      {/* Bottom section */}
      <div className="p-4 border-t border-gray-700">
        {!collapsed && (
          <div className="text-xs text-gray-400 space-y-1">
            <div className="flex justify-between">
              <span>Active Signals:</span>
              <span className="text-success-400 font-medium">12</span>
            </div>
            <div className="flex justify-between">
              <span>P&L Today:</span>
              <span className="text-success-400 font-medium">+$2,345</span>
            </div>
            <div className="flex justify-between">
              <span>Win Rate:</span>
              <span className="text-primary-400 font-medium">68%</span>
            </div>
          </div>
        )}
        
        {collapsed && (
          <div className="flex flex-col items-center space-y-2 text-xs text-gray-400">
            <div className="w-2 h-2 bg-success-400 rounded-full"></div>
            <div className="w-2 h-2 bg-primary-400 rounded-full"></div>
            <div className="w-2 h-2 bg-warning-400 rounded-full"></div>
          </div>
        )}
      </div>
    </div>
  )
}