import React, { useState, useRef } from 'react';
import axios from 'axios';
import { 
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer 
} from 'recharts';
import { 
  BarChart3, TrendingUp, Download, Filter, FileText, Users, Zap, 
  DollarSign, Calendar, RefreshCw, FileDown, Printer
} from 'lucide-react';
import { formatCOP, formatNumber } from '../utils/currency';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Color palette
const COLORS = ['#EA580C', '#10B981', '#3B82F6', '#8B5CF6', '#F59E0B', '#EC4899', '#06B6D4', '#84CC16'];

// Custom tooltip for charts
const CustomTooltip = ({ active, payload, label, valuePrefix = '', valueSuffix = '' }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white dark:bg-slate-800 p-3 rounded-lg shadow-lg border border-slate-200 dark:border-slate-700">
        <p className="font-medium text-slate-900 dark:text-slate-100">{label}</p>
        {payload.map((entry, index) => (
          <p key={index} style={{ color: entry.color }} className="text-sm">
            {entry.name}: {valuePrefix}{typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}{valueSuffix}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

function Reports() {
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [reportData, setReportData] = useState(null);
  const reportRef = useRef(null);
  
  const [filters, setFilters] = useState({
    start_date: '',
    end_date: '',
    account: '',
    station: '',
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
      alert('Failed to generate report: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const exportToCSV = () => {
    if (!reportData?.transactions) return;
    
    const headers = ['Tx ID', 'Account', 'Station', 'Connector', 'Type', 'Start Time', 'End Time', 'Energy (kWh)', 'Cost (COP)', 'Status', 'Payment Type'];
    const rows = reportData.transactions.map(tx => [
      tx.tx_id,
      tx.account,
      tx.station,
      tx.connector || '',
      tx.connector_type || '',
      tx.start_time,
      tx.end_time || '',
      tx.meter_value,
      tx.cost,
      tx.payment_status,
      tx.payment_type || '',
    ]);

    const csvContent = [headers, ...rows].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `report_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const exportToPDF = async () => {
    if (!reportRef.current || !reportData) return;
    
    setExporting(true);
    try {
      const element = reportRef.current;
      const canvas = await html2canvas(element, {
        scale: 2,
        useCORS: true,
        logging: false,
        backgroundColor: '#ffffff'
      });
      
      const imgData = canvas.toDataURL('image/png');
      const pdf = new jsPDF('p', 'mm', 'a4');
      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = pdf.internal.pageSize.getHeight();
      const imgWidth = canvas.width;
      const imgHeight = canvas.height;
      const ratio = Math.min(pdfWidth / imgWidth, pdfHeight / imgHeight);
      const imgX = (pdfWidth - imgWidth * ratio) / 2;
      
      // Add title
      pdf.setFontSize(20);
      pdf.setTextColor(234, 88, 12);
      pdf.text('SmartCharge - Analytics Report', pdfWidth / 2, 15, { align: 'center' });
      
      // Add date
      pdf.setFontSize(10);
      pdf.setTextColor(100);
      pdf.text(`Generated: ${new Date().toLocaleString()}`, pdfWidth / 2, 22, { align: 'center' });
      
      // Add filter info
      let filterText = 'Filters: ';
      if (filters.start_date) filterText += `From: ${filters.start_date} `;
      if (filters.end_date) filterText += `To: ${filters.end_date} `;
      if (filters.account) filterText += `Account: ${filters.account} `;
      if (filters.connector_type) filterText += `Connector: ${filters.connector_type} `;
      if (filterText === 'Filters: ') filterText += 'None (All Data)';
      pdf.text(filterText, pdfWidth / 2, 28, { align: 'center' });
      
      // Calculate how many pages we need
      const imgHeightInMm = (imgHeight * ratio);
      const pageContentHeight = pdfHeight - 35;
      let heightLeft = imgHeightInMm;
      let position = 35;
      
      // First page
      pdf.addImage(imgData, 'PNG', imgX, position, imgWidth * ratio, imgHeight * ratio);
      heightLeft -= pageContentHeight;
      
      // Additional pages if needed
      while (heightLeft > 0) {
        position = heightLeft - imgHeightInMm;
        pdf.addPage();
        pdf.addImage(imgData, 'PNG', imgX, position, imgWidth * ratio, imgHeight * ratio);
        heightLeft -= pageContentHeight;
      }
      
      pdf.save(`SmartCharge_Report_${new Date().toISOString().split('T')[0]}.pdf`);
    } catch (error) {
      console.error('PDF export failed:', error);
      alert('Failed to export PDF');
    } finally {
      setExporting(false);
    }
  };

  const clearFilters = () => {
    setFilters({
      start_date: '',
      end_date: '',
      account: '',
      station: '',
      connector_type: '',
      payment_type: '',
      payment_status: '',
    });
  };

  return (
    <div className="space-y-6" style={{ fontFamily: 'IBM Plex Sans, sans-serif' }}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-4xl md:text-5xl font-black tracking-tight mb-2" style={{ fontFamily: 'Chivo, sans-serif' }} data-testid="reports-title">
            Reports & Analytics
          </h1>
          <p className="text-slate-500 dark:text-slate-400">Dynamic charts, tables and exportable reports</p>
        </div>
        {reportData && (
          <div className="flex gap-2">
            <button
              onClick={exportToCSV}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition-colors font-medium"
              data-testid="export-csv-btn"
            >
              <FileDown className="w-4 h-4" />
              CSV
            </button>
            <button
              onClick={exportToPDF}
              disabled={exporting}
              className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors font-medium disabled:opacity-50"
              data-testid="export-pdf-btn"
            >
              <Printer className="w-4 h-4" />
              {exporting ? 'Exporting...' : 'PDF'}
            </button>
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6" data-testid="report-filters">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold flex items-center gap-2" style={{ fontFamily: 'Chivo, sans-serif' }}>
            <Filter className="w-5 h-5 text-orange-600" />
            Report Filters
          </h3>
          <button
            onClick={clearFilters}
            className="text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
          >
            Clear All
          </button>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium mb-2">
              <Calendar className="w-4 h-4 inline mr-1" />
              Start Date
            </label>
            <input
              type="date"
              value={filters.start_date}
              onChange={(e) => setFilters({...filters, start_date: e.target.value})}
              className="w-full h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 text-sm"
              data-testid="filter-start-date"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">
              <Calendar className="w-4 h-4 inline mr-1" />
              End Date
            </label>
            <input
              type="date"
              value={filters.end_date}
              onChange={(e) => setFilters({...filters, end_date: e.target.value})}
              className="w-full h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 text-sm"
              data-testid="filter-end-date"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Account</label>
            <input
              type="text"
              value={filters.account}
              onChange={(e) => setFilters({...filters, account: e.target.value})}
              placeholder="Search account..."
              className="w-full h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 text-sm"
              data-testid="filter-account"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Station</label>
            <input
              type="text"
              value={filters.station}
              onChange={(e) => setFilters({...filters, station: e.target.value})}
              placeholder="Search station..."
              className="w-full h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 text-sm"
              data-testid="filter-station"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Connector Type</label>
            <select
              value={filters.connector_type}
              onChange={(e) => setFilters({...filters, connector_type: e.target.value})}
              className="w-full h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 text-sm"
              data-testid="filter-connector"
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
              className="w-full h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 text-sm"
              data-testid="filter-payment-type"
            >
              <option value="">All Types</option>
              <option value="NEQUI">NEQUI</option>
              <option value="DAVIPLATA">DAVIPLATA</option>
              <option value="EFECTIVO">EFECTIVO</option>
              <option value="RFID">RFID</option>
              <option value="QR">QR</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Payment Status</label>
            <select
              value={filters.payment_status}
              onChange={(e) => setFilters({...filters, payment_status: e.target.value})}
              className="w-full h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 text-sm"
              data-testid="filter-status"
            >
              <option value="">All Status</option>
              <option value="PAID">PAID</option>
              <option value="UNPAID">UNPAID</option>
              <option value="PENDING">PENDING</option>
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={generateReport}
              disabled={loading}
              className="w-full h-10 bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors font-medium disabled:opacity-50 flex items-center justify-center gap-2"
              data-testid="generate-report-btn"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Loading...
                </>
              ) : (
                <>
                  <BarChart3 className="w-4 h-4" />
                  Generate
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Report Content */}
      {reportData && (
        <div ref={reportRef} className="space-y-6 bg-white dark:bg-slate-900 p-1">
          {/* Summary Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4" data-testid="report-summary">
            <div className="bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl p-5 text-white">
              <div className="flex items-center gap-2 mb-2 opacity-90">
                <TrendingUp className="w-5 h-5" />
                <span className="text-sm font-medium">Total Transactions</span>
              </div>
              <p className="text-3xl font-bold">{formatNumber(reportData.summary.total_transactions)}</p>
            </div>
            <div className="bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-xl p-5 text-white">
              <div className="flex items-center gap-2 mb-2 opacity-90">
                <Zap className="w-5 h-5" />
                <span className="text-sm font-medium">Total Energy</span>
              </div>
              <p className="text-3xl font-bold">{formatNumber(reportData.summary.total_energy)} <span className="text-lg">kWh</span></p>
            </div>
            <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl p-5 text-white">
              <div className="flex items-center gap-2 mb-2 opacity-90">
                <DollarSign className="w-5 h-5" />
                <span className="text-sm font-medium">Total Revenue</span>
              </div>
              <p className="text-2xl font-bold">{formatCOP(reportData.summary.total_revenue)}</p>
            </div>
            <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl p-5 text-white">
              <div className="flex items-center gap-2 mb-2 opacity-90">
                <Users className="w-5 h-5" />
                <span className="text-sm font-medium">Paid Revenue</span>
              </div>
              <p className="text-2xl font-bold">{formatCOP(reportData.summary.paid_revenue)}</p>
              <p className="text-sm opacity-80">{reportData.summary.paid_transactions} paid</p>
            </div>
          </div>

          {/* Additional Stats Row */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">Unpaid Revenue</p>
              <p className="text-xl font-bold text-rose-600">{formatCOP(reportData.summary.unpaid_revenue)}</p>
            </div>
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">Avg. Energy/Session</p>
              <p className="text-xl font-bold text-emerald-600">{formatNumber(reportData.summary.avg_session_energy)} kWh</p>
            </div>
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">Avg. Revenue/Session</p>
              <p className="text-xl font-bold text-blue-600">{formatCOP(reportData.summary.avg_session_revenue)}</p>
            </div>
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">Collection Rate</p>
              <p className="text-xl font-bold text-purple-600">
                {reportData.summary.total_transactions > 0 
                  ? Math.round(reportData.summary.paid_transactions / reportData.summary.total_transactions * 100)
                  : 0}%
              </p>
            </div>
          </div>

          {/* Charts Row 1 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Daily Trend Line Chart */}
            {reportData.daily_trend.length > 0 && (
              <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6" data-testid="chart-daily-trend">
                <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-orange-600" />
                  Daily Revenue Trend
                </h3>
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={reportData.daily_trend}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(v) => v.slice(5)} />
                    <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `$${(v/1000).toFixed(0)}k`} />
                    <Tooltip content={<CustomTooltip valuePrefix="$" />} />
                    <Line type="monotone" dataKey="revenue" stroke="#EA580C" strokeWidth={2} dot={{ r: 3 }} name="Revenue" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Energy Trend */}
            {reportData.daily_trend.length > 0 && (
              <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6" data-testid="chart-energy-trend">
                <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                  <Zap className="w-5 h-5 text-emerald-600" />
                  Daily Energy Consumption
                </h3>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={reportData.daily_trend}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(v) => v.slice(5)} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip content={<CustomTooltip valueSuffix=" kWh" />} />
                    <Bar dataKey="energy" fill="#10B981" radius={[4, 4, 0, 0]} name="Energy (kWh)" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          {/* Charts Row 2 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Revenue by Connector Pie Chart */}
            {reportData.by_connector.length > 0 && (
              <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6" data-testid="chart-connector-pie">
                <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                  <Zap className="w-5 h-5 text-purple-600" />
                  Revenue by Connector Type
                </h3>
                <div className="flex items-center">
                  <ResponsiveContainer width="50%" height={200}>
                    <PieChart>
                      <Pie
                        data={reportData.by_connector}
                        dataKey="revenue"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        innerRadius={40}
                        outerRadius={80}
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                        labelLine={false}
                      >
                        {reportData.by_connector.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(v) => formatCOP(v)} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="w-1/2 space-y-2">
                    {reportData.by_connector.map((item, idx) => (
                      <div key={idx} className="flex items-center justify-between text-sm">
                        <div className="flex items-center gap-2">
                          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[idx % COLORS.length] }} />
                          <span>{item.name}</span>
                        </div>
                        <span className="font-medium">{formatCOP(item.revenue)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Revenue by Payment Type */}
            {reportData.by_payment_type.length > 0 && (
              <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6" data-testid="chart-payment-pie">
                <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                  <DollarSign className="w-5 h-5 text-emerald-600" />
                  Revenue by Payment Method
                </h3>
                <div className="flex items-center">
                  <ResponsiveContainer width="50%" height={200}>
                    <PieChart>
                      <Pie
                        data={reportData.by_payment_type}
                        dataKey="revenue"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        innerRadius={40}
                        outerRadius={80}
                        label={({ name, percent }) => `${(percent * 100).toFixed(0)}%`}
                        labelLine={false}
                      >
                        {reportData.by_payment_type.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[(index + 2) % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(v) => formatCOP(v)} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="w-1/2 space-y-2">
                    {reportData.by_payment_type.map((item, idx) => (
                      <div key={idx} className="flex items-center justify-between text-sm">
                        <div className="flex items-center gap-2">
                          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[(idx + 2) % COLORS.length] }} />
                          <span>{item.name}</span>
                        </div>
                        <span className="font-medium">{formatCOP(item.revenue)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Top Accounts Bar Chart */}
          {reportData.by_account.length > 0 && (
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6" data-testid="chart-top-accounts">
              <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                <Users className="w-5 h-5 text-blue-600" />
                Top Accounts by Revenue
              </h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={reportData.by_account.slice(0, 10)} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={(v) => `$${(v/1000).toFixed(0)}k`} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={120} />
                  <Tooltip formatter={(v) => formatCOP(v)} />
                  <Bar dataKey="revenue" fill="#3B82F6" radius={[0, 4, 4, 0]} name="Revenue" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Data Tables */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* By Account Table */}
            {reportData.by_account.length > 0 && (
              <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6" data-testid="table-accounts">
                <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                  <Users className="w-5 h-5 text-orange-600" />
                  Revenue by Account
                </h3>
                <div className="overflow-x-auto max-h-80">
                  <table className="w-full text-sm">
                    <thead className="border-b border-slate-200 dark:border-slate-700 sticky top-0 bg-white dark:bg-slate-800">
                      <tr>
                        <th className="text-left py-2 px-2 font-semibold">Account</th>
                        <th className="text-right py-2 px-2 font-semibold">Txns</th>
                        <th className="text-right py-2 px-2 font-semibold">kWh</th>
                        <th className="text-right py-2 px-2 font-semibold">Revenue</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reportData.by_account.map((item, idx) => (
                        <tr key={idx} className="border-b border-slate-100 dark:border-slate-700">
                          <td className="py-2 px-2 truncate max-w-[150px]">{item.name}</td>
                          <td className="py-2 px-2 text-right">{item.transactions}</td>
                          <td className="py-2 px-2 text-right text-emerald-600">{formatNumber(item.energy)}</td>
                          <td className="py-2 px-2 text-right font-medium text-orange-600">{formatCOP(item.revenue)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* By Station Table */}
            {reportData.by_station.length > 0 && (
              <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6" data-testid="table-stations">
                <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                  <Zap className="w-5 h-5 text-purple-600" />
                  Revenue by Station
                </h3>
                <div className="overflow-x-auto max-h-80">
                  <table className="w-full text-sm">
                    <thead className="border-b border-slate-200 dark:border-slate-700 sticky top-0 bg-white dark:bg-slate-800">
                      <tr>
                        <th className="text-left py-2 px-2 font-semibold">Station</th>
                        <th className="text-right py-2 px-2 font-semibold">Txns</th>
                        <th className="text-right py-2 px-2 font-semibold">kWh</th>
                        <th className="text-right py-2 px-2 font-semibold">Revenue</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reportData.by_station.map((item, idx) => (
                        <tr key={idx} className="border-b border-slate-100 dark:border-slate-700">
                          <td className="py-2 px-2 truncate max-w-[150px]">{item.name}</td>
                          <td className="py-2 px-2 text-right">{item.transactions}</td>
                          <td className="py-2 px-2 text-right text-emerald-600">{formatNumber(item.energy)}</td>
                          <td className="py-2 px-2 text-right font-medium text-purple-600">{formatCOP(item.revenue)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>

          {/* Transactions Table */}
          {reportData.transactions.length > 0 && (
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6" data-testid="table-transactions">
              <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                <FileText className="w-5 h-5 text-slate-600" />
                Transaction Details
                <span className="text-sm font-normal text-slate-500">({reportData.transactions.length} shown)</span>
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="border-b border-slate-200 dark:border-slate-700">
                    <tr>
                      <th className="text-left py-3 px-2 font-semibold">Tx ID</th>
                      <th className="text-left py-3 px-2 font-semibold">Account</th>
                      <th className="text-left py-3 px-2 font-semibold">Station</th>
                      <th className="text-left py-3 px-2 font-semibold">Type</th>
                      <th className="text-right py-3 px-2 font-semibold">Energy</th>
                      <th className="text-right py-3 px-2 font-semibold">Cost</th>
                      <th className="text-center py-3 px-2 font-semibold">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reportData.transactions.slice(0, 50).map((tx, idx) => (
                      <tr key={idx} className="border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/50">
                        <td className="py-2 px-2 font-mono text-xs">{tx.tx_id}</td>
                        <td className="py-2 px-2 truncate max-w-[120px]">{tx.account}</td>
                        <td className="py-2 px-2 truncate max-w-[100px]">{tx.station}</td>
                        <td className="py-2 px-2">
                          {tx.connector_type && (
                            <span className="px-2 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 rounded-full text-xs">
                              {tx.connector_type}
                            </span>
                          )}
                        </td>
                        <td className="py-2 px-2 text-right text-emerald-600 font-medium">{formatNumber(tx.meter_value)} kWh</td>
                        <td className="py-2 px-2 text-right text-orange-600 font-medium">{formatCOP(tx.cost)}</td>
                        <td className="py-2 px-2 text-center">
                          <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${
                            tx.payment_status === 'PAID' 
                              ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400'
                              : 'bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-400'
                          }`}>
                            {tx.payment_status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {reportData.transactions.length > 50 && (
                <p className="text-sm text-slate-500 mt-4 text-center">
                  Showing 50 of {reportData.transactions.length} transactions. Export to CSV for full data.
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!reportData && !loading && (
        <div className="bg-slate-50 dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-12 text-center">
          <BarChart3 className="w-16 h-16 text-slate-300 dark:text-slate-700 mx-auto mb-4" />
          <h3 className="text-lg font-bold text-slate-700 dark:text-slate-300 mb-2">No Report Generated</h3>
          <p className="text-slate-500 dark:text-slate-400 mb-4">
            Select filters and click "Generate" to view dynamic charts and analytics
          </p>
          <button
            onClick={generateReport}
            className="px-6 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg font-medium"
          >
            Generate Report
          </button>
        </div>
      )}
    </div>
  );
}

export default Reports;
