import React from 'react';
import { Activity, Wifi, WifiOff, Zap, Server, Radio } from 'lucide-react';
import useOCPPWebSocket from '../hooks/useOCPPWebSocket';

/**
 * Real-time OCPP status widget for the dashboard
 * Shows live WebSocket connection status, online chargers, and active transactions
 */
export function OCPPLiveStatus({ compact = false }) {
  const { 
    connected, 
    onlineChargers, 
    chargerStatuses, 
    activeTransactions,
    lastEvent 
  } = useOCPPWebSocket();

  const activeCount = activeTransactions?.length || 0;
  const chargersArray = Object.values(chargerStatuses || {});
  const chargingCount = chargersArray.filter(c => c.status === 'Charging').length;

  if (compact) {
    return (
      <div className="flex items-center gap-4 text-sm">
        <div className={`flex items-center gap-1 ${connected ? 'text-green-600' : 'text-red-500'}`}>
          {connected ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
          <span>{connected ? 'Live' : 'Offline'}</span>
        </div>
        <div className="flex items-center gap-1 text-slate-600 dark:text-slate-400">
          <Server className="w-4 h-4" />
          <span>{onlineChargers} online</span>
        </div>
        {activeCount > 0 && (
          <div className="flex items-center gap-1 text-orange-600">
            <Zap className="w-4 h-4" />
            <span>{activeCount} charging</span>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
          OCPP Live Status
        </h3>
        <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm ${
          connected 
            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' 
            : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
        }`}>
          {connected ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
          {connected ? 'Connected' : 'Disconnected'}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {/* Online Chargers */}
        <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4 text-center">
          <div className="flex justify-center mb-2">
            <Server className="w-8 h-8 text-blue-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            {onlineChargers}
          </div>
          <div className="text-sm text-slate-500 dark:text-slate-400">
            Online Chargers
          </div>
        </div>

        {/* Active Transactions */}
        <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4 text-center">
          <div className="flex justify-center mb-2">
            <Zap className="w-8 h-8 text-orange-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            {activeCount}
          </div>
          <div className="text-sm text-slate-500 dark:text-slate-400">
            Active Sessions
          </div>
        </div>

        {/* Charging */}
        <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4 text-center">
          <div className="flex justify-center mb-2">
            <Activity className="w-8 h-8 text-green-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            {chargingCount}
          </div>
          <div className="text-sm text-slate-500 dark:text-slate-400">
            Charging Now
          </div>
        </div>
      </div>

      {/* Live Event Feed */}
      {lastEvent && lastEvent.event !== 'status' && (
        <div className="mt-4 p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg border border-orange-200 dark:border-orange-800">
          <div className="flex items-center gap-2">
            <Radio className="w-4 h-4 text-orange-500 animate-pulse" />
            <span className="text-sm font-medium text-orange-700 dark:text-orange-400">
              Live Event
            </span>
          </div>
          <div className="mt-1 text-sm text-orange-600 dark:text-orange-300">
            {lastEvent.event === 'charger_connected' && `Charger ${lastEvent.data?.charger_id} connected`}
            {lastEvent.event === 'charger_disconnected' && `Charger ${lastEvent.data?.charger_id} disconnected`}
            {lastEvent.event === 'transaction_started' && `Transaction started on ${lastEvent.data?.charger_id}`}
            {lastEvent.event === 'transaction_stopped' && `Transaction completed on ${lastEvent.data?.charger_id}`}
          </div>
        </div>
      )}

      {/* Charger Status List */}
      {chargersArray.length > 0 && (
        <div className="mt-4">
          <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
            Connected Chargers
          </h4>
          <div className="space-y-2">
            {chargersArray.map(charger => (
              <div 
                key={charger.charger_id}
                className="flex items-center justify-between p-2 bg-slate-50 dark:bg-slate-700/50 rounded-lg"
              >
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${
                    charger.connected ? 'bg-green-500' : 'bg-red-500'
                  }`} />
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                    {charger.charger_id}
                  </span>
                </div>
                <span className={`text-xs px-2 py-1 rounded-full ${
                  charger.status === 'Charging' 
                    ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400'
                    : charger.status === 'Available'
                    ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                    : 'bg-slate-100 text-slate-700 dark:bg-slate-600 dark:text-slate-300'
                }`}>
                  {charger.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default OCPPLiveStatus;
