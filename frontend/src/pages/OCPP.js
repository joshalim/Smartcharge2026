import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import { Activity, Zap, CheckCircle, XCircle, Clock, Server, Radio, Play, Square, AlertCircle, Wifi, WifiOff } from 'lucide-react';
import useOCPPWebSocket from '../hooks/useOCPPWebSocket';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function OCPP() {
  const { t } = useTranslation();
  const [status, setStatus] = useState(null);
  const [boots, setBoots] = useState([]);
  const [chargers, setChargers] = useState([]);
  const [activeTransactions, setActiveTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);
  const [startModal, setStartModal] = useState({ open: false, charger: null });
  const [idTag, setIdTag] = useState('');
  
  // WebSocket hook for real-time updates
  const { 
    connected: wsConnected, 
    onlineChargers: wsOnlineChargers,
    chargerStatuses: wsChargerStatuses,
    activeTransactions: wsActiveTransactions,
    lastEvent,
    addEventListener
  } = useOCPPWebSocket();

  // Fetch initial data
  const fetchOCPPData = useCallback(async () => {
    try {
      const [statusRes, bootsRes, txRes, chargersRes] = await Promise.all([
        axios.get(`${API}/ocpp/status`),
        axios.get(`${API}/ocpp/boots`),
        axios.get(`${API}/ocpp/active-transactions`),
        axios.get(`${API}/chargers`),
      ]);
      setStatus(statusRes.data);
      setBoots(bootsRes.data);
      setActiveTransactions(txRes.data);
      setChargers(chargersRes.data);
    } catch (error) {
      console.error('Failed to fetch OCPP data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchOCPPData();
  }, [fetchOCPPData]);

  // Listen for WebSocket events and update data
  useEffect(() => {
    const removeListener = addEventListener((event) => {
      if (event.event === 'transaction_started' || event.event === 'transaction_stopped') {
        // Refresh transactions on transaction events
        fetchOCPPData();
      } else if (event.event === 'charger_connected' || event.event === 'charger_disconnected') {
        // Update charger status
        fetchOCPPData();
      }
    });
    return removeListener;
  }, [addEventListener, fetchOCPPData]);

  // Fallback polling every 30 seconds (reduced from 5s since we have WebSocket)
  useEffect(() => {
    const interval = setInterval(fetchOCPPData, 30000);
    return () => clearInterval(interval);
  }, [fetchOCPPData]);

  const handleRemoteStart = async (charger) => {
    if (!idTag.trim()) {
      alert('Please enter an ID Tag');
      return;
    }
    
    setActionLoading(`start-${charger.id}`);
    try {
      await axios.post(`${API}/ocpp/remote-start`, {
        charger_id: charger.id,
        connector_id: 1,
        id_tag: idTag
      });
      setStartModal({ open: false, charger: null });
      setIdTag('');
      fetchOCPPData();
      alert('Remote start command sent successfully!');
    } catch (error) {
      console.error('Failed to start transaction:', error);
      alert(error.response?.data?.detail || 'Failed to start transaction');
    } finally {
      setActionLoading(null);
    }
  };

  const handleRemoteStop = async (transactionId) => {
    if (!window.confirm('Are you sure you want to stop this transaction?')) return;
    
    setActionLoading(`stop-${transactionId}`);
    try {
      const response = await axios.post(`${API}/ocpp/remote-stop`, {
        transaction_id: transactionId
      });
      fetchOCPPData();
      
      // Show result with energy consumed and cost
      const result = response.data;
      let message = `Transaction stopped!\n\nEnergy: ${result.energy_consumed?.toFixed(2)} kWh\nCost: $${result.cost?.toLocaleString()} COP`;
      if (result.rfid_deducted) {
        message += `\n\n✓ Amount deducted from RFID card\nNew Balance: $${result.new_balance?.toLocaleString()} COP`;
      }
      alert(message);
    } catch (error) {
      console.error('Failed to stop transaction:', error);
      alert(error.response?.data?.detail || 'Failed to stop transaction');
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" style={{ fontFamily: 'IBM Plex Sans, sans-serif' }}>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-4xl md:text-5xl font-black tracking-tight mb-2" style={{ fontFamily: 'Chivo, sans-serif' }}>
            OCPP Monitoring
          </h1>
          <p className="text-slate-500 dark:text-slate-400">Real-time charge point monitoring & remote control (OCPP 1.6)</p>
        </div>
        
        {/* WebSocket Connection Status */}
        <div className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium ${
          wsConnected 
            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 border border-green-200 dark:border-green-800' 
            : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 border border-red-200 dark:border-red-800'
        }`}>
          {wsConnected ? (
            <>
              <Wifi className="w-4 h-4" />
              <span>Live Updates Active</span>
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
              </span>
            </>
          ) : (
            <>
              <WifiOff className="w-4 h-4" />
              <span>Connecting...</span>
            </>
          )}
        </div>
      </div>

      {/* Live Event Notification */}
      {lastEvent && lastEvent.event !== 'status' && (
        <div className="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg p-4 flex items-center gap-3">
          <Radio className="w-5 h-5 text-orange-500 animate-pulse" />
          <div>
            <span className="font-medium text-orange-700 dark:text-orange-400">Live Event: </span>
            <span className="text-orange-600 dark:text-orange-300">
              {lastEvent.event === 'charger_connected' && `Charger ${lastEvent.data?.charger_id} connected`}
              {lastEvent.event === 'charger_disconnected' && `Charger ${lastEvent.data?.charger_id} disconnected`}
              {lastEvent.event === 'transaction_started' && `Transaction started on ${lastEvent.data?.charger_id}`}
              {lastEvent.event === 'transaction_stopped' && `Transaction completed on ${lastEvent.data?.charger_id}`}
            </span>
          </div>
        </div>
      )}

      {/* Status Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
          <div className="flex items-start justify-between mb-4">
            <div className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/30">
              <Activity className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
            </div>
            <span className="flex items-center gap-2 text-sm">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
              </span>
              Live
            </span>
          </div>
          <p className="text-3xl font-bold text-slate-900 dark:text-slate-100 mb-1">
            {status?.active_transactions || 0}
          </p>
          <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">Active Transactions</p>
        </div>

        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
          <div className="flex items-start justify-between mb-4">
            <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-950/30">
              <Server className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
          </div>
          <p className="text-3xl font-bold text-slate-900 dark:text-slate-100 mb-1">
            {status?.total_boots || 0}
          </p>
          <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">Registered Charge Points</p>
        </div>

        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
          <div className="flex items-start justify-between mb-4">
            <div className="p-3 rounded-lg bg-orange-50 dark:bg-orange-950/30">
              <Radio className="w-6 h-6 text-orange-600 dark:text-orange-400" />
            </div>
          </div>
          <p className="text-3xl font-bold text-slate-900 dark:text-slate-100 mb-1">
            {status?.ocpp_version || 'N/A'}
          </p>
          <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">OCPP Version</p>
        </div>
      </div>

      {/* Remote Control Panel */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
        <h2 className="text-2xl font-bold mb-4 flex items-center gap-3" style={{ fontFamily: 'Chivo, sans-serif' }}>
          <Zap className="w-6 h-6 text-orange-600" />
          Remote Control
        </h2>
        
        {chargers.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {chargers.map((charger) => {
              const activeTx = activeTransactions.find(tx => tx.charger_id === charger.id);
              const isCharging = charger.status === 'Charging' || activeTx;
              
              return (
                <div
                  key={charger.id}
                  className={`p-4 border rounded-lg transition-all ${
                    isCharging 
                      ? 'border-emerald-300 dark:border-emerald-700 bg-emerald-50 dark:bg-emerald-950/20'
                      : 'border-slate-200 dark:border-slate-800 hover:border-orange-300 dark:hover:border-orange-700'
                  }`}
                  data-testid={`charger-control-${charger.id}`}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="font-bold text-slate-900 dark:text-slate-100">{charger.name}</h3>
                      <p className="text-sm text-slate-500 dark:text-slate-400">{charger.location}</p>
                    </div>
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                      isCharging 
                        ? 'bg-emerald-100 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-400'
                        : charger.status === 'Available'
                          ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-400'
                          : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300'
                    }`}>
                      {isCharging ? 'Charging' : charger.status}
                    </span>
                  </div>
                  
                  <div className="text-xs text-slate-500 dark:text-slate-400 mb-3">
                    {(charger.connectors || charger.connector_types || []).join(', ')} {charger.max_power ? `| ${charger.max_power} kW` : ''}
                  </div>
                  
                  {isCharging && activeTx ? (
                    <div className="space-y-2">
                      <div className="text-xs text-slate-600 dark:text-slate-400">
                        <span className="font-medium">Transaction:</span> #{activeTx.transaction_id}
                      </div>
                      <div className="text-xs text-slate-600 dark:text-slate-400">
                        <span className="font-medium">ID Tag:</span> {activeTx.id_tag}
                      </div>
                      <button
                        onClick={() => handleRemoteStop(activeTx.transaction_id)}
                        disabled={actionLoading === `stop-${activeTx.transaction_id}`}
                        className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-md transition-colors font-medium disabled:opacity-50"
                        data-testid={`stop-btn-${charger.id}`}
                      >
                        {actionLoading === `stop-${activeTx.transaction_id}` ? (
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                        ) : (
                          <>
                            <Square className="w-4 h-4" />
                            Stop Charging
                          </>
                        )}
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setStartModal({ open: true, charger })}
                      disabled={charger.status === 'Faulted' || charger.status === 'Unavailable'}
                      className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                      data-testid={`start-btn-${charger.id}`}
                    >
                      <Play className="w-4 h-4" />
                      Start Charging
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-8">
            <AlertCircle className="w-12 h-12 text-slate-300 dark:text-slate-700 mx-auto mb-4" />
            <p className="text-slate-500 dark:text-slate-400">No chargers configured</p>
            <p className="text-sm text-slate-400 dark:text-slate-500 mt-2">
              Add chargers from the Chargers page to enable remote control
            </p>
          </div>
        )}
      </div>

      {/* Active Transactions */}
      {activeTransactions.length > 0 && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
          <h2 className="text-2xl font-bold mb-4" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Active Charging Sessions
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full" data-testid="active-transactions-table">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800">
                  <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">Transaction ID</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">Connector</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">ID Tag</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">Start Time</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">Energy (kWh)</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">Status</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">Actions</th>
                </tr>
              </thead>
              <tbody>
                {activeTransactions.map((tx) => (
                  <tr key={tx.transaction_id} className="border-b border-slate-100 dark:border-slate-800">
                    <td className="py-3 px-4 text-sm font-medium text-slate-900 dark:text-slate-100">
                      {tx.transaction_id}
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-400">
                      Connector {tx.connector_id}
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-400">{tx.id_tag}</td>
                    <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-400">
                      {new Date(tx.start_timestamp).toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-sm font-semibold text-emerald-600 dark:text-emerald-400">
                      {((tx.meter_stop || 0) - tx.meter_start) / 1000 > 0 
                        ? (((tx.meter_stop || 0) - tx.meter_start) / 1000).toFixed(2) 
                        : '0.00'}
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-1 text-xs font-semibold rounded-full bg-emerald-100 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-400">
                        {tx.status}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <button
                        onClick={() => handleRemoteStop(tx.transaction_id)}
                        disabled={actionLoading === `stop-${tx.transaction_id}`}
                        className="flex items-center gap-1 px-3 py-1 text-sm bg-rose-50 dark:bg-rose-950/30 text-rose-600 dark:text-rose-400 rounded hover:bg-rose-100 dark:hover:bg-rose-950/50 transition-colors"
                      >
                        {actionLoading === `stop-${tx.transaction_id}` ? (
                          <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-rose-600"></div>
                        ) : (
                          <>
                            <Square className="w-3 h-3" />
                            Stop
                          </>
                        )}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Charge Points */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
        <h2 className="text-2xl font-bold mb-4" style={{ fontFamily: 'Chivo, sans-serif' }}>
          Registered Charge Points
        </h2>
        {boots.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {boots.map((boot) => (
              <div
                key={boot.id}
                className="p-4 border border-slate-200 dark:border-slate-800 rounded-lg hover:border-orange-300 dark:hover:border-orange-700 transition-colors"
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="font-bold text-slate-900 dark:text-slate-100">{boot.vendor}</h3>
                    <p className="text-sm text-slate-500 dark:text-slate-400">{boot.model}</p>
                  </div>
                  {boot.status === 'Accepted' ? (
                    <CheckCircle className="w-5 h-5 text-emerald-600" />
                  ) : (
                    <XCircle className="w-5 h-5 text-rose-600" />
                  )}
                </div>
                <div className="space-y-1 text-sm">
                  {boot.serial && (
                    <p className="text-slate-600 dark:text-slate-400">
                      <span className="font-medium">Serial:</span> {boot.serial}
                    </p>
                  )}
                  {boot.firmware && (
                    <p className="text-slate-600 dark:text-slate-400">
                      <span className="font-medium">Firmware:</span> {boot.firmware}
                    </p>
                  )}
                  <p className="text-xs text-slate-400 dark:text-slate-500 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {new Date(boot.timestamp).toLocaleString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <Server className="w-12 h-12 text-slate-300 dark:text-slate-700 mx-auto mb-4" />
            <p className="text-slate-500 dark:text-slate-400">No charge points registered yet</p>
            <p className="text-sm text-slate-400 dark:text-slate-500 mt-2">
              Charge points will appear here when they connect via OCPP 1.6
            </p>
          </div>
        )}
      </div>

      {/* OCPP Endpoints Info */}
      <div className="bg-slate-50 dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
        <h3 className="text-lg font-bold mb-3" style={{ fontFamily: 'Chivo, sans-serif' }}>
          OCPP 1.6 Endpoints
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
          <div className="p-3 bg-white dark:bg-slate-800 rounded-md">
            <p className="font-medium text-slate-700 dark:text-slate-300 mb-1">BootNotification</p>
            <code className="text-xs text-orange-600 dark:text-orange-400">POST /api/ocpp/boot-notification</code>
          </div>
          <div className="p-3 bg-white dark:bg-slate-800 rounded-md">
            <p className="font-medium text-slate-700 dark:text-slate-300 mb-1">Heartbeat</p>
            <code className="text-xs text-orange-600 dark:text-orange-400">POST /api/ocpp/heartbeat</code>
          </div>
          <div className="p-3 bg-white dark:bg-slate-800 rounded-md">
            <p className="font-medium text-slate-700 dark:text-slate-300 mb-1">StartTransaction</p>
            <code className="text-xs text-orange-600 dark:text-orange-400">POST /api/ocpp/start-transaction</code>
          </div>
          <div className="p-3 bg-white dark:bg-slate-800 rounded-md">
            <p className="font-medium text-slate-700 dark:text-slate-300 mb-1">StopTransaction</p>
            <code className="text-xs text-orange-600 dark:text-orange-400">POST /api/ocpp/stop-transaction</code>
          </div>
          <div className="p-3 bg-white dark:bg-slate-800 rounded-md">
            <p className="font-medium text-slate-700 dark:text-slate-300 mb-1">RemoteStartTransaction</p>
            <code className="text-xs text-orange-600 dark:text-orange-400">POST /api/ocpp/remote-start</code>
          </div>
          <div className="p-3 bg-white dark:bg-slate-800 rounded-md">
            <p className="font-medium text-slate-700 dark:text-slate-300 mb-1">RemoteStopTransaction</p>
            <code className="text-xs text-orange-600 dark:text-orange-400">POST /api/ocpp/remote-stop</code>
          </div>
        </div>
      </div>

      {/* Start Modal */}
      {startModal.open && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50" onClick={() => setStartModal({ open: false, charger: null })}>
          <div className="bg-white dark:bg-slate-900 rounded-xl p-6 max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-bold mb-4" style={{ fontFamily: 'Chivo, sans-serif' }}>
              Start Charging Session
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
              Start a remote charging session on <strong>{startModal.charger?.name}</strong>
            </p>
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">RFID Card Number or ID Tag</label>
              <input
                type="text"
                value={idTag}
                onChange={(e) => setIdTag(e.target.value.toUpperCase())}
                placeholder="Enter RFID card number (e.g., RFID-001-2024)"
                className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-orange-500"
                data-testid="id-tag-input"
              />
              <p className="text-xs text-slate-500 mt-2">
                💳 Use an RFID card number to auto-deduct from balance when charging ends
              </p>
            </div>
            <div className="mb-4 p-3 bg-amber-50 dark:bg-amber-950/30 rounded-lg">
              <p className="text-xs text-amber-700 dark:text-amber-400">
                <strong>Note:</strong> If using RFID card, minimum balance of $5,000 COP is required. 
                Cost will be automatically deducted when session ends.
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => handleRemoteStart(startModal.charger)}
                disabled={actionLoading === `start-${startModal.charger?.id}`}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md transition-colors font-medium disabled:opacity-50"
                data-testid="confirm-start-btn"
              >
                {actionLoading === `start-${startModal.charger?.id}` ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                ) : (
                  <>
                    <Play className="w-4 h-4" />
                    Start
                  </>
                )}
              </button>
              <button
                onClick={() => setStartModal({ open: false, charger: null })}
                className="flex-1 px-4 py-2 border border-slate-300 dark:border-slate-700 rounded-md hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors font-medium"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default OCPP;
