import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import { 
  Zap, Battery, MapPin, Users, DollarSign, TrendingUp, TrendingDown, 
  Receipt, Wallet, PieChart as PieChartIcon
} from 'lucide-react';
import { 
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ComposedChart, Area
} from 'recharts';
import { formatCOP, formatNumber } from '../utils/currency';
import OCPPLiveStatus from '../components/OCPPLiveStatus';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Color palette
const COLORS = ['#EA580C', '#10B981', '#3B82F6', '#8B5CF6', '#F59E0B'];

function Dashboard() {
  const { t } = useTranslation();
  const [stats, setStats] = useState(null);
  const [financials, setFinancials] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [statsRes, financialsRes] = await Promise.all([
        axios.get(`${API}/dashboard/stats`),
        axios.get(`${API}/expenses/financials/summary?months=12`).catch(() => ({ data: null }))
      ]);
      setStats(statsRes.data);
      setFinancials(financialsRes.data);
    } catch (error) {
      console.error('Failed to fetch data:', error);
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

  // Prepare data for pie chart
  const profitData = financials ? [
    { name: t('dashboard.income'), value: financials.total_income, color: '#10B981' },
    { name: t('dashboard.expenses'), value: financials.total_expenses, color: '#EF4444' }
  ] : [];

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

      {/* Financial Summary Section */}
      {financials && (
        <div className="space-y-6" data-testid="financial-summary">
          <h2 className="text-2xl font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>
            {t('dashboard.financialOverview')}
          </h2>
          
          {/* Financial Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-xl p-5 text-white">
              <div className="flex items-center gap-2 mb-2 opacity-90">
                <Wallet className="w-5 h-5" />
                <span className="text-sm font-medium">{t('dashboard.totalIncome')}</span>
              </div>
              <p className="text-2xl font-bold">{formatCOP(financials.total_income)}</p>
            </div>
            
            <div className="bg-gradient-to-br from-rose-500 to-rose-600 rounded-xl p-5 text-white">
              <div className="flex items-center gap-2 mb-2 opacity-90">
                <Receipt className="w-5 h-5" />
                <span className="text-sm font-medium">{t('dashboard.totalExpenses')}</span>
              </div>
              <p className="text-2xl font-bold">{formatCOP(financials.total_expenses)}</p>
            </div>
            
            <div className={`bg-gradient-to-br ${financials.total_profit >= 0 ? 'from-blue-500 to-blue-600' : 'from-amber-500 to-amber-600'} rounded-xl p-5 text-white`}>
              <div className="flex items-center gap-2 mb-2 opacity-90">
                <TrendingUp className="w-5 h-5" />
                <span className="text-sm font-medium">{t('dashboard.netProfit')}</span>
              </div>
              <p className="text-2xl font-bold">{formatCOP(financials.total_profit)}</p>
            </div>
            
            <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl p-5 text-white">
              <div className="flex items-center gap-2 mb-2 opacity-90">
                <PieChartIcon className="w-5 h-5" />
                <span className="text-sm font-medium">{t('dashboard.profitMargin')}</span>
              </div>
              <p className="text-2xl font-bold">{financials.overall_profit_margin}%</p>
            </div>
          </div>

          {/* Monthly Charts */}
          {financials.monthly_data && financials.monthly_data.length > 0 && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Income vs Expenses Bar Chart */}
              <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6" data-testid="chart-income-expenses">
                <h3 className="text-lg font-bold mb-4 flex items-center gap-2" style={{ fontFamily: 'Chivo, sans-serif' }}>
                  <DollarSign className="w-5 h-5 text-orange-600" />
                  {t('dashboard.monthlyIncomeExpenses')}
                </h3>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={financials.monthly_data}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis 
                      dataKey="month" 
                      tick={{ fontSize: 11 }} 
                      tickFormatter={(v) => v.slice(5)} 
                    />
                    <YAxis 
                      tick={{ fontSize: 11 }} 
                      tickFormatter={(v) => `$${(v/1000000).toFixed(1)}M`} 
                    />
                    <Tooltip 
                      formatter={(value) => formatCOP(value)}
                      labelFormatter={(label) => `Month: ${label}`}
                    />
                    <Legend />
                    <Bar dataKey="income" name={t('dashboard.income')} fill="#10B981" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="expenses" name={t('dashboard.expenses')} fill="#EF4444" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Profit Trend Line Chart */}
              <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6" data-testid="chart-profit-trend">
                <h3 className="text-lg font-bold mb-4 flex items-center gap-2" style={{ fontFamily: 'Chivo, sans-serif' }}>
                  <TrendingUp className="w-5 h-5 text-blue-600" />
                  {t('dashboard.profitTrend')}
                </h3>
                <ResponsiveContainer width="100%" height={280}>
                  <ComposedChart data={financials.monthly_data}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis 
                      dataKey="month" 
                      tick={{ fontSize: 11 }} 
                      tickFormatter={(v) => v.slice(5)} 
                    />
                    <YAxis 
                      yAxisId="left"
                      tick={{ fontSize: 11 }} 
                      tickFormatter={(v) => `$${(v/1000000).toFixed(1)}M`} 
                    />
                    <YAxis 
                      yAxisId="right"
                      orientation="right"
                      tick={{ fontSize: 11 }}
                      tickFormatter={(v) => `${v}%`}
                    />
                    <Tooltip 
                      formatter={(value, name) => {
                        if (name === t('dashboard.profitMargin')) return `${value}%`;
                        return formatCOP(value);
                      }}
                      labelFormatter={(label) => `Month: ${label}`}
                    />
                    <Legend />
                    <Area 
                      yAxisId="left"
                      type="monotone" 
                      dataKey="profit" 
                      name={t('dashboard.profit')} 
                      fill="#3B82F6" 
                      fillOpacity={0.2}
                      stroke="#3B82F6" 
                      strokeWidth={2}
                    />
                    <Line 
                      yAxisId="right"
                      type="monotone" 
                      dataKey="profit_margin" 
                      name={t('dashboard.profitMargin')} 
                      stroke="#8B5CF6" 
                      strokeWidth={2}
                      dot={{ r: 4 }}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Income/Expense Pie Chart */}
          {profitData.length > 0 && financials.total_income > 0 && (
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6" data-testid="chart-distribution">
              <h3 className="text-lg font-bold mb-4 flex items-center gap-2" style={{ fontFamily: 'Chivo, sans-serif' }}>
                <PieChartIcon className="w-5 h-5 text-purple-600" />
                {t('dashboard.incomeExpenseDistribution')}
              </h3>
              <div className="flex flex-col md:flex-row items-center justify-center gap-8">
                <ResponsiveContainer width={250} height={250}>
                  <PieChart>
                    <Pie
                      data={profitData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={2}
                      label={({ name, percent }) => `${(percent * 100).toFixed(0)}%`}
                      labelLine={false}
                    >
                      {profitData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v) => formatCOP(v)} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="space-y-4">
                  {profitData.map((item, idx) => (
                    <div key={idx} className="flex items-center gap-3">
                      <div className="w-4 h-4 rounded-full" style={{ backgroundColor: item.color }} />
                      <div>
                        <p className="font-medium text-slate-900 dark:text-slate-100">{item.name}</p>
                        <p className="text-lg font-bold" style={{ color: item.color }}>{formatCOP(item.value)}</p>
                      </div>
                    </div>
                  ))}
                  <div className="pt-4 border-t border-slate-200 dark:border-slate-700">
                    <p className="font-medium text-slate-500 dark:text-slate-400">{t('dashboard.netProfit')}</p>
                    <p className={`text-xl font-bold ${financials.total_profit >= 0 ? 'text-blue-600' : 'text-amber-600'}`}>
                      {formatCOP(financials.total_profit)}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

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
