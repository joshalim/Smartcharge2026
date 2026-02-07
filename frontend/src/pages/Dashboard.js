import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import { Zap, Battery, MapPin, Users, DollarSign, TrendingUp, TrendingDown } from 'lucide-react';
import { formatCOP, formatNumber } from '../utils/currency';
import OCPPLiveStatus from '../components/OCPPLiveStatus';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function Dashboard() {
  const { t } = useTranslation();
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
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600"></div>
      </div>
    );
  }

  const metrics = [
    {
      name: t('dashboard.totalTransactions'),
      value: stats?.total_transactions || 0,
      icon: Zap,
      color: 'text-orange-600 dark:text-orange-400',
      bg: 'bg-orange-50 dark:bg-orange-950/30',
    },
    {
      name: t('dashboard.totalEnergy'),
      value: formatNumber(stats?.total_energy || 0),
      icon: Battery,
      color: 'text-emerald-600 dark:text-emerald-400',
      bg: 'bg-emerald-50 dark:bg-emerald-950/30',
    },
    {
      name: t('dashboard.totalRevenue'),
      value: formatCOP(stats?.total_revenue || 0),
      icon: DollarSign,
      color: 'text-blue-600 dark:text-blue-400',
      bg: 'bg-blue-50 dark:bg-blue-950/30',
    },
    {
      name: t('dashboard.paidRevenue'),
      value: formatCOP(stats?.paid_revenue || 0),
      icon: TrendingUp,
      color: 'text-emerald-600 dark:text-emerald-400',
      bg: 'bg-emerald-50 dark:bg-emerald-950/30',
    },
    {
      name: t('dashboard.unpaidRevenue'),
      value: formatCOP(stats?.unpaid_revenue || 0),
      icon: TrendingDown,
      color: 'text-rose-600 dark:text-rose-400',
      bg: 'bg-rose-50 dark:bg-rose-950/30',
    },
    {
      name: t('dashboard.activeStations'),
      value: stats?.active_stations || 0,
      icon: MapPin,
      color: 'text-amber-600 dark:text-amber-400',
      bg: 'bg-amber-50 dark:bg-amber-950/30',
    },
    {
      name: t('dashboard.uniqueAccounts'),
      value: stats?.unique_accounts || 0,
      icon: Users,
      color: 'text-purple-600 dark:text-purple-400',
      bg: 'bg-purple-50 dark:bg-purple-950/30',
    },
  ];

  const paymentBreakdown = stats?.payment_breakdown || {};

  return (
    <div className="space-y-8" style={{ fontFamily: 'IBM Plex Sans, sans-serif' }}>
      <div>
        <h1 className="text-4xl md:text-5xl font-black tracking-tight mb-2" style={{ fontFamily: 'Chivo, sans-serif' }} data-testid="dashboard-title">
          {t('dashboard.title')}
        </h1>
        <p className="text-slate-500 dark:text-slate-400">{t('dashboard.subtitle')}</p>
      </div>

      {/* Main Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 gap-4">
        {metrics.map((metric) => (
          <div
            key={metric.name}
            className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm hover:shadow-md transition-all duration-200"
            data-testid={`metric-${metric.name.toLowerCase().replace(/\s+/g, '-')}`}
          >
            <div className="flex items-start justify-between mb-4">
              <div className={`p-3 rounded-lg ${metric.bg}`}>
                <metric.icon className={`w-5 h-5 ${metric.color}`} />
              </div>
            </div>
            <p className="text-xl font-bold text-slate-900 dark:text-slate-100 mb-1">{metric.value}</p>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">{metric.name}</p>
          </div>
        ))}
      </div>

      {/* OCPP Live Status */}
      <OCPPLiveStatus />

      {/* Payment Methods Breakdown */}
      {Object.keys(paymentBreakdown).length > 0 && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
          <h2 className="text-2xl font-bold mb-4" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Payment Methods
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {Object.entries(paymentBreakdown).map(([method, data]) => (
              <div key={method} className="p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
                <p className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">{method}</p>
                <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">{formatCOP(data.amount)}</p>
                <p className="text-sm text-slate-600 dark:text-slate-400">{data.count} transactions</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Transactions */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
        <h2 className="text-2xl font-bold mb-4" style={{ fontFamily: 'Chivo, sans-serif' }} data-testid="recent-transactions-title">
          {t('dashboard.recentTransactions')}
        </h2>
        {stats?.recent_transactions && stats.recent_transactions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800">
                  <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">{t('transactions.txId')}</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">{t('transactions.account')}</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">{t('transactions.energy')}</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">{t('transactions.duration')}</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">{t('transactions.cost')}</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">Status</th>
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
                    <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-400">{tx.account}</td>
                    <td className="py-3 px-4 text-sm font-semibold text-emerald-600 dark:text-emerald-400">
                      {formatNumber(tx.meter_value)}
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-400">{tx.charging_duration || 'N/A'}</td>
                    <td className="py-3 px-4 text-sm font-semibold text-orange-600 dark:text-orange-400">
                      {formatCOP(tx.cost)}
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                        tx.payment_status === 'PAID' 
                          ? 'bg-emerald-100 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-400'
                          : 'bg-rose-100 dark:bg-rose-950/30 text-rose-700 dark:text-rose-400'
                      }`}>
                        {tx.payment_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-slate-500 dark:text-slate-400 text-center py-8" data-testid="no-transactions-message">
            {t('dashboard.noTransactions')}
          </p>
        )}
      </div>
    </div>
  );
}

export default Dashboard;