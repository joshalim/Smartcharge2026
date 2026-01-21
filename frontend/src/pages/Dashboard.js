import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Zap, Battery, MapPin, Users } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/dashboard/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96" data-testid="dashboard-loading">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  const metrics = [
    {
      name: 'Total Transactions',
      value: stats?.total_transactions || 0,
      icon: Zap,
      color: 'text-indigo-600 dark:text-indigo-400',
      bg: 'bg-indigo-50 dark:bg-indigo-950/30',
    },
    {
      name: 'Total Energy (kWh)',
      value: stats?.total_energy?.toFixed(2) || '0.00',
      icon: Battery,
      color: 'text-emerald-600 dark:text-emerald-400',
      bg: 'bg-emerald-50 dark:bg-emerald-950/30',
    },
    {
      name: 'Active Stations',
      value: stats?.active_stations || 0,
      icon: MapPin,
      color: 'text-amber-600 dark:text-amber-400',
      bg: 'bg-amber-50 dark:bg-amber-950/30',
    },
    {
      name: 'Unique Accounts',
      value: stats?.unique_accounts || 0,
      icon: Users,
      color: 'text-purple-600 dark:text-purple-400',
      bg: 'bg-purple-50 dark:bg-purple-950/30',
    },
  ];

  return (
    <div className="space-y-8" style={{ fontFamily: 'IBM Plex Sans, sans-serif' }}>
      <div>
        <h1 className="text-4xl md:text-5xl font-black tracking-tight mb-2" style={{ fontFamily: 'Chivo, sans-serif' }} data-testid="dashboard-title">
          Dashboard
        </h1>
        <p className="text-slate-500 dark:text-slate-400">Overview of your EV charging operations</p>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {metrics.map((metric) => (
          <div
            key={metric.name}
            className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm hover:shadow-md transition-all duration-200"
            data-testid={`metric-${metric.name.toLowerCase().replace(/\s+/g, '-')}`}
          >
            <div className="flex items-start justify-between mb-4">
              <div className={`p-3 rounded-lg ${metric.bg}`}>
                <metric.icon className={`w-6 h-6 ${metric.color}`} />
              </div>
            </div>
            <p className="text-3xl font-bold text-slate-900 dark:text-slate-100 mb-1">{metric.value}</p>
            <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">{metric.name}</p>
          </div>
        ))}
      </div>

      {/* Recent Transactions */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
        <h2 className="text-2xl font-bold mb-4" style={{ fontFamily: 'Chivo, sans-serif' }} data-testid="recent-transactions-title">
          Recent Transactions
        </h2>
        {stats?.recent_transactions && stats.recent_transactions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800">
                  <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">Tx ID</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">Station</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">Account</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">Energy (kWh)</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">Start Time</th>
                </tr>
              </thead>
              <tbody>
                {stats.recent_transactions.map((tx) => (
                  <tr
                    key={tx.id}
                    className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                    data-testid="recent-transaction-row"
                  >
                    <td className="py-3 px-4 text-sm font-medium text-slate-900 dark:text-slate-100">{tx.tx_id}</td>
                    <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-400">{tx.station}</td>
                    <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-400">{tx.account}</td>
                    <td className="py-3 px-4 text-sm font-semibold text-emerald-600 dark:text-emerald-400">
                      {tx.meter_value.toFixed(2)}
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-400">{tx.start_time}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-slate-500 dark:text-slate-400 text-center py-8" data-testid="no-transactions-message">
            No transactions yet. Import data to get started.
          </p>
        )}
      </div>
    </div>
  );
}

export default Dashboard;