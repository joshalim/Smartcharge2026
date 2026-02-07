import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import { BarChart3, PieChart, TrendingUp, Download, Filter, FileText, Users, Zap } from 'lucide-react';
import { formatCOP, formatNumber } from '../utils/currency';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Simple Bar Chart Component
const SimpleBarChart = ({ data, labelKey, valueKey, title, color = '#EA580C' }) => {
  const maxValue = Math.max(...data.map(d => d[valueKey]), 1);
  
  return (
    <div className="space-y-3">
      <h4 className="font-semibold text-slate-700 dark:text-slate-300">{title}</h4>
      <div className="space-y-2">
        {data.slice(0, 8).map((item, idx) => (
          <div key={idx} className="space-y-1">
            <div className="flex justify-between text-sm">
              <span className="text-slate-600 dark:text-slate-400 truncate max-w-[60%]">{item[labelKey]}</span>
              <span className="font-medium text-slate-900 dark:text-slate-100">
                {typeof item[valueKey] === 'number' && valueKey.includes('revenue') 
                  ? formatCOP(item[valueKey])
                  : formatNumber(item[valueKey])}
              </span>
            </div>
            <div className="h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
              <div 
                className="h-full rounded-full transition-all duration-500"
                style={{ 
                  width: `${(item[valueKey] / maxValue) * 100}%`,
                  backgroundColor: color
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// Pie Chart Component (CSS-based)
const SimplePieChart = ({ data, labelKey, valueKey, title }) => {
  const total = data.reduce((sum, d) => sum + d[valueKey], 0) || 1;
  const colors = ['#EA580C', '#10B981', '#3B82F6', '#8B5CF6', '#F59E0B'];
  
  let currentAngle = 0;
  const segments = data.map((item, idx) => {
    const percentage = (item[valueKey] / total) * 100;
    const angle = (item[valueKey] / total) * 360;
    const segment = {
      ...item,
      percentage,
      startAngle: currentAngle,
      endAngle: currentAngle + angle,
      color: colors[idx % colors.length]
    };
    currentAngle += angle;
    return segment;
  });

  // Create conic-gradient
  const gradientStops = segments.map((seg, idx) => {
    if (idx === 0) {
      return `${seg.color} 0deg ${seg.endAngle}deg`;
    }
    return `${seg.color} ${seg.startAngle}deg ${seg.endAngle}deg`;
  }).join(', ');

  return (
    <div className="space-y-4">
      <h4 className="font-semibold text-slate-700 dark:text-slate-300">{title}</h4>
      <div className="flex items-center gap-6">
        <div 
          className="w-32 h-32 rounded-full flex-shrink-0"
          style={{ 
            background: data.length > 0 
              ? `conic-gradient(${gradientStops})` 
              : '#e2e8f0'
          }}
        />
        <div className="space-y-2 flex-1">
          {segments.slice(0, 5).map((item, idx) => (
            <div key={idx} className="flex items-center gap-2 text-sm">
              <div 
                className="w-3 h-3 rounded-full flex-shrink-0"
                style={{ backgroundColor: item.color }}
              />
              <span className="text-slate-600 dark:text-slate-400 truncate">{item[labelKey]}</span>
              <span className="font-medium text-slate-900 dark:text-slate-100 ml-auto">
                {item.percentage.toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

function Reports() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [reportData, setReportData] = useState(null);
  const [filters, setFilters] = useState({
    start_date: '',
    end_date: '',
    account: '',
    connector_type: '',
    payment_type: '',
    payment_status: '',
  });

  const generateReport = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API}/reports/generate`, filters);
      if (response.data) {
        setReportData(response.data);
      } else {
        alert('No data returned from server');
      }
    } catch (error) {
      console.error('Failed to generate report:', error);
      alert('Failed to generate report: ' + (error.response?.data?.detail || error.message));
      setReportData(null);
    } finally {
      setLoading(false);
    }
  };

  const exportToCSV = () => {
    if (!reportData || !reportData.transactions) return;
    
    const headers = ['Tx ID', 'Account', 'Station', 'Connector', 'Type', 'Start Time', 'End Time', 'Duration', 'Energy (kWh)', 'Cost (COP)', 'Status', 'Payment Type', 'Payment Date'];
    const rows = reportData.transactions.map(tx => [
      tx.tx_id,
      tx.account,
      tx.station,
      tx.connector,
      tx.connector_type || '',
      tx.start_time,
      tx.end_time,
      tx.charging_duration || '',
      tx.meter_value,
      tx.cost,
      tx.payment_status,
      tx.payment_type || '',
      tx.payment_date || '',
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers, ...rows].map(row => row.join(',')).join('\n');
    const link = document.createElement('a');
    link.href = encodeURI(csvContent);
    link.download = `report_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
  };

  return (
    <div className="space-y-6" style={{ fontFamily: 'IBM Plex Sans, sans-serif' }}>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-4xl md:text-5xl font-black tracking-tight mb-2" style={{ fontFamily: 'Chivo, sans-serif' }} data-testid="reports-title">
            Reports & Analytics
          </h1>
          <p className="text-slate-500 dark:text-slate-400">Generate comprehensive reports with charts and custom filters</p>
        </div>
        {reportData && (
          <button
            onClick={exportToCSV}
            className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-md transition-colors font-medium"
            data-testid="export-report-btn"
          >
            <Download className="w-4 h-4" />
            Export CSV
          </button>
        )}
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6" data-testid="report-filters">
        <h3 className="text-lg font-bold mb-4 flex items-center gap-2" style={{ fontFamily: 'Chivo, sans-serif' }}>
          <Filter className="w-5 h-5" />
          Report Filters
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium mb-2">Start Date</label>
            <input
              type="date"
              value={filters.start_date}
              onChange={(e) => setFilters({...filters, start_date: e.target.value})}
              className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
              data-testid="filter-start-date"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">End Date</label>
            <input
              type="date"
              value={filters.end_date}
              onChange={(e) => setFilters({...filters, end_date: e.target.value})}
              className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
              data-testid="filter-end-date"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Account</label>
            <input
              type="text"
              value={filters.account}
              onChange={(e) => setFilters({...filters, account: e.target.value})}
              placeholder="All accounts"
              className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
              data-testid="filter-account"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Connector Type</label>
            <select
              value={filters.connector_type}
              onChange={(e) => setFilters({...filters, connector_type: e.target.value})}
              className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
              data-testid="filter-connector-type"
            >
              <option value="">All Types</option>
              <option value="CCS2">CCS2</option>
              <option value="CHADEMO">CHADEMO</option>
              <option value="J1772">J1772</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Payment Type</label>
            <select
              value={filters.payment_type}
              onChange={(e) => setFilters({...filters, payment_type: e.target.value})}
              className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
              data-testid="filter-payment-type"
            >
              <option value="">All Types</option>
              <option value="NEQUI">NEQUI</option>
              <option value="DAVIPLATA">DAVIPLATA</option>
              <option value="EFECTIVO">EFECTIVO</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Payment Status</label>
            <select
              value={filters.payment_status}
              onChange={(e) => setFilters({...filters, payment_status: e.target.value})}
              className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
              data-testid="filter-payment-status"
            >
              <option value="">All Status</option>
              <option value="PAID">PAID</option>
              <option value="UNPAID">UNPAID</option>
            </select>
          </div>
        </div>
        <button
          onClick={generateReport}
          disabled={loading}
          className="px-6 py-3 bg-orange-600 hover:bg-orange-700 text-white rounded-md transition-colors font-medium disabled:opacity-50"
          data-testid="generate-report-btn"
        >
          {loading ? 'Generating...' : 'Generate Report'}
        </button>
      </div>

      {reportData && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6" data-testid="report-summary">
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 bg-orange-50 dark:bg-orange-950/30 rounded-lg">
                  <TrendingUp className="w-5 h-5 text-orange-600" />
                </div>
                <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Total Transactions</p>
              </div>
              <p className="text-3xl font-bold text-slate-900 dark:text-slate-100">{reportData.summary.total_transactions}</p>
            </div>
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 bg-emerald-50 dark:bg-emerald-950/30 rounded-lg">
                  <Zap className="w-5 h-5 text-emerald-600" />
                </div>
                <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Total Energy</p>
              </div>
              <p className="text-3xl font-bold text-slate-900 dark:text-slate-100">{formatNumber(reportData.summary.total_energy)} kWh</p>
            </div>
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 bg-blue-50 dark:bg-blue-950/30 rounded-lg">
                  <BarChart3 className="w-5 h-5 text-blue-600" />
                </div>
                <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Total Revenue</p>
              </div>
              <p className="text-3xl font-bold text-slate-900 dark:text-slate-100">{formatCOP(reportData.summary.total_revenue)}</p>
            </div>
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
              <p className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">Paid Transactions</p>
              <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{reportData.summary.paid_transactions}</p>
              <p className="text-sm text-slate-600 dark:text-slate-400">{formatCOP(reportData.summary.paid_revenue)}</p>
            </div>
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
              <p className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">Unpaid Revenue</p>
              <p className="text-2xl font-bold text-rose-600 dark:text-rose-400">{formatCOP(reportData.summary.unpaid_revenue)}</p>
            </div>
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
              <p className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">Unique Accounts</p>
              <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">{reportData.by_account.length}</p>
            </div>
          </div>

          {/* Charts Section */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Revenue by Account Bar Chart */}
            {reportData.by_account.length > 0 && (
              <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6" data-testid="chart-revenue-by-account">
                <SimpleBarChart 
                  data={reportData.by_account}
                  labelKey="account"
                  valueKey="revenue"
                  title="Revenue by Account"
                  color="#EA580C"
                />
              </div>
            )}

            {/* Energy by Account Bar Chart */}
            {reportData.by_account.length > 0 && (
              <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6" data-testid="chart-energy-by-account">
                <SimpleBarChart 
                  data={reportData.by_account}
                  labelKey="account"
                  valueKey="energy"
                  title="Energy Consumption by Account (kWh)"
                  color="#10B981"
                />
              </div>
            )}

            {/* Connector Type Distribution Pie Chart */}
            {reportData.by_connector.length > 0 && (
              <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6" data-testid="chart-connector-distribution">
                <SimplePieChart 
                  data={reportData.by_connector}
                  labelKey="connector_type"
                  valueKey="revenue"
                  title="Revenue by Connector Type"
                />
              </div>
            )}

            {/* Payment Method Distribution Pie Chart */}
            {reportData.by_payment_type.length > 0 && (
              <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6" data-testid="chart-payment-distribution">
                <SimplePieChart 
                  data={reportData.by_payment_type}
                  labelKey="payment_type"
                  valueKey="revenue"
                  title="Revenue by Payment Method"
                />
              </div>
            )}
          </div>

          {/* By Account Table */}
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6" data-testid="table-by-account">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2" style={{ fontFamily: 'Chivo, sans-serif' }}>
              <Users className="w-5 h-5 text-orange-600" />
              Revenue by Account
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="text-left py-3 px-4 text-sm font-semibold">Account</th>
                    <th className="text-left py-3 px-4 text-sm font-semibold">Transactions</th>
                    <th className="text-left py-3 px-4 text-sm font-semibold">Energy (kWh)</th>
                    <th className="text-left py-3 px-4 text-sm font-semibold">Revenue</th>
                  </tr>
                </thead>
                <tbody>
                  {reportData.by_account.map((item, idx) => (
                    <tr key={idx} className="border-b border-slate-100 dark:border-slate-800">
                      <td className="py-3 px-4 font-medium">{item.account}</td>
                      <td className="py-3 px-4">{item.transactions}</td>
                      <td className="py-3 px-4 text-emerald-600">{formatNumber(item.energy)}</td>
                      <td className="py-3 px-4 text-orange-600 font-semibold">{formatCOP(item.revenue)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* By Connector Type */}
          {reportData.by_connector.length > 0 && (
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6" data-testid="table-by-connector">
              <h3 className="text-xl font-bold mb-4 flex items-center gap-2" style={{ fontFamily: 'Chivo, sans-serif' }}>
                <Zap className="w-5 h-5 text-purple-600" />
                Performance by Connector Type
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {reportData.by_connector.map((item, idx) => (
                  <div key={idx} className="p-4 bg-purple-50 dark:bg-purple-950/20 rounded-lg">
                    <p className="text-sm font-medium text-purple-700 dark:text-purple-400 mb-2">{item.connector_type}</p>
                    <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">{formatCOP(item.revenue)}</p>
                    <p className="text-sm text-slate-600 dark:text-slate-400">{item.transactions} transactions | {formatNumber(item.energy)} kWh</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* By Payment Type */}
          {reportData.by_payment_type.length > 0 && (
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6" data-testid="table-by-payment">
              <h3 className="text-xl font-bold mb-4 flex items-center gap-2" style={{ fontFamily: 'Chivo, sans-serif' }}>
                <FileText className="w-5 h-5 text-emerald-600" />
                Revenue by Payment Method
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {reportData.by_payment_type.map((item, idx) => (
                  <div key={idx} className="p-4 bg-emerald-50 dark:bg-emerald-950/20 rounded-lg">
                    <p className="text-sm font-medium text-emerald-700 dark:text-emerald-400 mb-2">{item.payment_type}</p>
                    <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">{formatCOP(item.revenue)}</p>
                    <p className="text-sm text-slate-600 dark:text-slate-400">{item.transactions} payments</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Transactions Table */}
          {reportData.transactions.length > 0 && (
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6" data-testid="transactions-table">
              <h3 className="text-xl font-bold mb-4" style={{ fontFamily: 'Chivo, sans-serif' }}>
                Transaction Details (First 100)
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="border-b border-slate-200 dark:border-slate-800">
                    <tr>
                      <th className="text-left py-3 px-3 text-xs font-semibold">Tx ID</th>
                      <th className="text-left py-3 px-3 text-xs font-semibold">Account</th>
                      <th className="text-left py-3 px-3 text-xs font-semibold">Connector</th>
                      <th className="text-left py-3 px-3 text-xs font-semibold">Type</th>
                      <th className="text-left py-3 px-3 text-xs font-semibold">Energy</th>
                      <th className="text-left py-3 px-3 text-xs font-semibold">Cost</th>
                      <th className="text-left py-3 px-3 text-xs font-semibold">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reportData.transactions.slice(0, 20).map((tx, idx) => (
                      <tr key={idx} className="border-b border-slate-100 dark:border-slate-800">
                        <td className="py-2 px-3 font-medium">{tx.tx_id}</td>
                        <td className="py-2 px-3 text-slate-600 dark:text-slate-400">{tx.account}</td>
                        <td className="py-2 px-3 text-slate-600 dark:text-slate-400">{tx.connector}</td>
                        <td className="py-2 px-3">
                          {tx.connector_type && (
                            <span className="px-2 py-0.5 bg-purple-100 dark:bg-purple-950/30 text-purple-700 dark:text-purple-400 rounded-full text-xs">
                              {tx.connector_type}
                            </span>
                          )}
                        </td>
                        <td className="py-2 px-3 text-emerald-600 font-medium">{formatNumber(tx.meter_value)} kWh</td>
                        <td className="py-2 px-3 text-orange-600 font-medium">{formatCOP(tx.cost)}</td>
                        <td className="py-2 px-3">
                          <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${
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
              {reportData.transactions.length > 20 && (
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-4 text-center">
                  Showing 20 of {reportData.transactions.length} transactions. Export CSV for full data.
                </p>
              )}
            </div>
          )}
        </>
      )}

      {!reportData && (
        <div className="bg-slate-50 dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-12 text-center">
          <BarChart3 className="w-16 h-16 text-slate-300 dark:text-slate-700 mx-auto mb-4" />
          <h3 className="text-lg font-bold text-slate-700 dark:text-slate-300 mb-2">No Report Generated</h3>
          <p className="text-slate-500 dark:text-slate-400">
            Select your filters above and click "Generate Report" to view analytics
          </p>
        </div>
      )}
    </div>
  );
}

export default Reports;
