'use client'

import { useState } from 'react'
import { MarketOverview } from '@/components/dashboard/MarketOverview'
import { SignalsFeed } from '@/components/dashboard/SignalsFeed'
import { ActivePositions } from '@/components/dashboard/ActivePositions'
import { PerformanceMetrics } from '@/components/dashboard/PerformanceMetrics'
import { TradingChart } from '@/components/charts/TradingChart'
import { SymbolSelector } from '@/components/ui/SymbolSelector'

export default function Dashboard() {
  const [selectedSymbol, setSelectedSymbol] = useState('AAPL')
  const [selectedTimeframe, setSelectedTimeframe] = useState('1h')

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Trading Dashboard</h1>
          <p className="text-gray-600">Real-time market analysis and trading signals</p>
        </div>
        <div className="flex items-center gap-4">
          <SymbolSelector
            value={selectedSymbol}
            onChange={setSelectedSymbol}
          />
          <select
            value={selectedTimeframe}
            onChange={(e) => setSelectedTimeframe(e.target.value)}
            className="input"
          >
            <option value="1m">1 Minute</option>
            <option value="5m">5 Minutes</option>
            <option value="15m">15 Minutes</option>
            <option value="1h">1 Hour</option>
            <option value="4h">4 Hours</option>
            <option value="1d">1 Day</option>
          </select>
        </div>
      </div>

      {/* Market Overview */}
      <MarketOverview />

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chart Section */}
        <div className="lg:col-span-2 space-y-6">
          <TradingChart
            symbol={selectedSymbol}
            timeframe={selectedTimeframe}
          />
          <PerformanceMetrics />
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <SignalsFeed />
          <ActivePositions />
        </div>
      </div>
    </div>
  )
}