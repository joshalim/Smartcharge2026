import React, { useState } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import { BarChart, PieChart, TrendingUp, Download, Filter } from 'lucide-react';
import { formatCOP, formatNumber } from '../utils/currency';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

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
      setReportData(response.data);
    } catch (error) {
      console.error('Failed to generate report:', error);
      alert('Failed to generate report');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6" style={{ fontFamily: 'IBM Plex Sans, sans-serif' }}>
      <div>
        <h1 className="text-4xl md:text-5xl font-black tracking-tight mb-2" style={{ fontFamily: 'Chivo, sans-serif' }}>
          Reports & Analytics
        </h1>
        <p className="text-slate-500 dark:text-slate-400">Generate comprehensive reports with custom filters</p>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
        <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
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
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">End Date</label>
            <input
              type="date"
              value={filters.end_date}
              onChange={(e) => setFilters({...filters, end_date: e.target.value})}
              className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
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
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Connector Type</label>
            <select
              value={filters.connector_type}
              onChange={(e) => setFilters({...filters, connector_type: e.target.value})}
              className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
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
        >
          {loading ? 'Generating...' : 'Generate Report'}
        </button>
      </div>

      {reportData && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
              <div className="flex items-center gap-3 mb-2">
                <TrendingUp className="w-5 h-5 text-orange-600" />
                <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Total Transactions</p>
              </div>
              <p className="text-3xl font-bold text-slate-900 dark:text-slate-100">{reportData.summary.total_transactions}</p>
            </div>
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
              <div className="flex items-center gap-3 mb-2">
                <BarChart className="w-5 h-5 text-emerald-600" />
                <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Total Energy</p>
              </div>
              <p className="text-3xl font-bold text-slate-900 dark:text-slate-100">{formatNumber(reportData.summary.total_energy)} kWh</p>
            </div>
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
              <div className="flex items-center gap-3 mb-2">
                <PieChart className="w-5 h-5 text-blue-600" />
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
          </div>

          {/* By Account */}
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
            <h3 className="text-xl font-bold mb-4">Revenue by Account</h3>
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
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
              <h3 className="text-xl font-bold mb-4">Performance by Connector Type</h3>
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
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
              <h3 className="text-xl font-bold mb-4">Revenue by Payment Method</h3>
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
        </>
      )}
    </div>
  );
}

export default Reports;
