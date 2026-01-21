import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import { Activity, Zap, CheckCircle, XCircle, Clock, Server, Radio } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function OCPP() {
  const { t } = useTranslation();
  const [status, setStatus] = useState(null);
  const [boots, setBoots] = useState([]);
  const [activeTransactions, setActiveTransactions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchOCPPData();
    const interval = setInterval(fetchOCPPData, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchOCPPData = async () => {
    try {
      const [statusRes, bootsRes, txRes] = await Promise.all([
        axios.get(`${API}/ocpp/status`),
        axios.get(`${API}/ocpp/boots`),
        axios.get(`${API}/ocpp/active-transactions`),
      ]);
      setStatus(statusRes.data);
      setBoots(bootsRes.data);
      setActiveTransactions(txRes.data);
    } catch (error) {
      console.error('Failed to fetch OCPP data:', error);
    } finally {
      setLoading(false);
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
      <div>
        <h1 className="text-4xl md:text-5xl font-black tracking-tight mb-2" style={{ fontFamily: 'Chivo, sans-serif' }}>
          OCPP Monitoring
        </h1>
        <p className="text-slate-500 dark:text-slate-400">Real-time charge point monitoring (OCPP 1.6)</p>
      </div>

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

      {/* Active Transactions */}
      {activeTransactions.length > 0 && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
          <h2 className="text-2xl font-bold mb-4" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Active Charging Sessions
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800">
                  <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">Transaction ID</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">Connector</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">ID Tag</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">Start Time</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">Energy (kWh)</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">Status</th>
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
                      {((tx.meter_stop - tx.meter_start) / 1000).toFixed(2)}
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-1 text-xs font-semibold rounded-full bg-emerald-100 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-400">
                        {tx.status}
                      </span>
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
        </div>
      </div>
    </div>
  );
}

export default OCPP;