import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import { Filter, Download, Trash2, Edit, X, Check, CheckSquare, Square } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { formatCOP, formatNumber } from '../utils/currency';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function Transactions() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    startDate: '',
    endDate: '',
    station: '',
    account: '',
    paymentStatus: '',
  });
  const [stations, setStations] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [showFilters, setShowFilters] = useState(false);
  const [editingTx, setEditingTx] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [selectedTxs, setSelectedTxs] = useState([]);
  const [showBulkActions, setShowBulkActions] = useState(false);
  const [bulkPaymentType, setBulkPaymentType] = useState('NEQUI');

  useEffect(() => {
    fetchTransactions();
    fetchFilterOptions();
  }, []);

  const fetchFilterOptions = async () => {
    try {
      const [stationsRes, accountsRes] = await Promise.all([
        axios.get(`${API}/filters/stations`),
        axios.get(`${API}/filters/accounts`),
      ]);
      setStations(stationsRes.data);
      setAccounts(accountsRes.data);
    } catch (error) {
      console.error('Failed to fetch filter options:', error);
    }
  };

  const fetchTransactions = async () => {
    setLoading(true);
    try {
      const params = {};
      if (filters.startDate) params.start_date = filters.startDate;
      if (filters.endDate) params.end_date = filters.endDate;
      if (filters.station) params.station = filters.station;
      if (filters.account) params.account = filters.account;
      if (filters.paymentStatus) params.payment_status = filters.paymentStatus;

      const response = await axios.get(`${API}/transactions`, { params });
      setTransactions(response.data);
      setSelectedTxs([]);
    } catch (error) {
      console.error('Failed to fetch transactions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (field, value) => {
    setFilters((prev) => ({ ...prev, [field]: value }));
  };

  const applyFilters = () => {
    fetchTransactions();
    setShowFilters(false);
  };

  const clearFilters = () => {
    setFilters({
      startDate: '',
      endDate: '',
      station: '',
      account: '',
      paymentStatus: '',
    });
    setTimeout(() => fetchTransactions(), 0);
  };

  const deleteTransaction = async (id) => {
    if (!window.confirm(t('transactions.deleteConfirm'))) return;

    try {
      await axios.delete(`${API}/transactions/${id}`);
      fetchTransactions();
    } catch (error) {
      console.error('Failed to delete transaction:', error);
      alert('Failed to delete transaction');
    }
  };

  const startEdit = (tx) => {
    setEditingTx(tx.id);
    setEditForm({
      station: tx.station,
      connector: tx.connector,
      connector_type: tx.connector_type || '',
      account: tx.account,
      start_time: tx.start_time,
      end_time: tx.end_time,
      meter_value: tx.meter_value,
      payment_status: tx.payment_status,
      payment_type: tx.payment_type || '',
      payment_date: tx.payment_date || '',
    });
  };

  const cancelEdit = () => {
    setEditingTx(null);
    setEditForm({});
  };

  const saveEdit = async (txId) => {
    try {
      await axios.patch(`${API}/transactions/${txId}`, editForm);
      setEditingTx(null);
      setEditForm({});
      fetchTransactions();
    } catch (error) {
      console.error('Failed to update transaction:', error);
      alert('Failed to update transaction');
    }
  };

  const toggleSelectTx = (txId) => {
    setSelectedTxs((prev) =>
      prev.includes(txId) ? prev.filter((id) => id !== txId) : [...prev, txId]
    );
  };

  const toggleSelectAll = () => {
    if (selectedTxs.length === transactions.length) {
      setSelectedTxs([]);
    } else {
      setSelectedTxs(transactions.map((tx) => tx.id));
    }
  };

  const handleBulkMarkAsPaid = async () => {
    if (selectedTxs.length === 0) return;
    if (!window.confirm(`Mark ${selectedTxs.length} transactions as PAID?`)) return;

    try {
      const today = new Date().toISOString().split('T')[0];
      await Promise.all(
        selectedTxs.map((txId) =>
          axios.patch(`${API}/transactions/${txId}`, {
            payment_status: 'PAID',
            payment_type: bulkPaymentType,
            payment_date: today,
          })
        )
      );
      fetchTransactions();
      setShowBulkActions(false);
    } catch (error) {
      console.error('Failed to bulk update:', error);
      alert('Failed to update transactions');
    }
  };

  const exportSelected = () => {
    const selectedTransactions = transactions.filter((tx) => selectedTxs.includes(tx.id));
    const headers = ['Tx ID', 'Station', 'Connector', 'Connector Type', 'Account', 'Start Time', 'End Time', 'Duration', 'Energy (kWh)', 'Cost (COP)', 'Payment Status', 'Payment Type', 'Payment Date'];
    const rows = selectedTransactions.map((tx) => [
      tx.tx_id,
      tx.station,
      tx.connector,
      tx.connector_type || '',
      tx.account,
      tx.start_time,
      tx.end_time,
      tx.charging_duration || '',
      tx.meter_value,
      tx.cost,
      tx.payment_status,
      tx.payment_type || '',
      tx.payment_date || '',
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,' + [headers, ...rows].map((row) => row.join(',')).join('\n');

    const link = document.createElement('a');
    link.href = encodeURI(csvContent);
    link.download = `selected_transactions_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
  };

  const exportToCSV = () => {
    const headers = ['Tx ID', 'Station', 'Connector', 'Connector Type', 'Account', 'Start Time', 'End Time', 'Duration', 'Energy (kWh)', 'Cost (COP)', 'Payment Status', 'Payment Type', 'Payment Date'];
    const rows = transactions.map((tx) => [
      tx.tx_id,
      tx.station,
      tx.connector,
      tx.connector_type || '',
      tx.account,
      tx.start_time,
      tx.end_time,
      tx.charging_duration || '',
      tx.meter_value,
      tx.cost,
      tx.payment_status,
      tx.payment_type || '',
      tx.payment_date || '',
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,' + [headers, ...rows].map((row) => row.join(',')).join('\n');

    const link = document.createElement('a');
    link.href = encodeURI(csvContent);
    link.download = `transactions_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
  };

  const activeFiltersCount = Object.values(filters).filter((v) => v).length;

  return (
    <div className="space-y-6" style={{ fontFamily: 'IBM Plex Sans, sans-serif' }}>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-4xl md:text-5xl font-black tracking-tight mb-2" style={{ fontFamily: 'Chivo, sans-serif' }} data-testid="transactions-title">
            {t('transactions.title')}
          </h1>
          <p className="text-slate-500 dark:text-slate-400">{t('transactions.subtitle')}</p>
        </div>
        <div className="flex gap-2">
          {(user?.role === 'admin' || user?.role === 'user') && selectedTxs.length > 0 && (
            <button
              onClick={() => setShowBulkActions(!showBulkActions)}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md transition-colors font-medium"
              data-testid="bulk-actions-btn"
            >
              <CheckSquare className="w-4 h-4" />
              {selectedTxs.length} Selected
            </button>
          )}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center gap-2 px-4 py-2 border border-slate-300 dark:border-slate-700 rounded-md hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors font-medium"
            data-testid="toggle-filters-btn"
          >
            <Filter className="w-4 h-4" />
            {t('transactions.filters')}
            {activeFiltersCount > 0 && (
              <span className="ml-1 px-2 py-0.5 text-xs bg-orange-600 text-white rounded-full">
                {activeFiltersCount}
              </span>
            )}
          </button>
          <button
            onClick={exportToCSV}
            disabled={transactions.length === 0}
            className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-md transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="export-csv-btn"
          >
            <Download className="w-4 h-4" />
            {t('transactions.export')}
          </button>
        </div>
      </div>

      {/* Bulk Actions Panel */}
      {showBulkActions && selectedTxs.length > 0 && (
        <div className="bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800 rounded-xl p-6" data-testid="bulk-actions-panel">
          <h3 className="text-lg font-bold mb-4" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Bulk Actions ({selectedTxs.length} transactions)
          </h3>
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium">Payment Type:</label>
              <select
                value={bulkPaymentType}
                onChange={(e) => setBulkPaymentType(e.target.value)}
                className="px-3 py-2 border border-slate-300 dark:border-slate-700 rounded-md text-sm"
              >
                <option value="NEQUI">NEQUI</option>
                <option value="DAVIPLATA">DAVIPLATA</option>
                <option value="EFECTIVO">EFECTIVO</option>
              </select>
            </div>
            <button
              onClick={handleBulkMarkAsPaid}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md transition-colors font-medium"
            >
              Mark as PAID
            </button>
            <button
              onClick={exportSelected}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors font-medium"
            >
              Export Selected
            </button>
            <button
              onClick={() => setSelectedTxs([])}
              className="px-4 py-2 border border-slate-300 dark:border-slate-700 rounded-md hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors font-medium"
            >
              Clear Selection
            </button>
          </div>
        </div>
      )}

      {showFilters && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6" data-testid="filters-panel">
          <h3 className="text-lg font-bold mb-4" style={{ fontFamily: 'Chivo, sans-serif' }}>
            {t('transactions.filterTitle')}
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium mb-2">{t('transactions.startDate')}</label>
              <input
                type="date"
                value={filters.startDate}
                onChange={(e) => handleFilterChange('startDate', e.target.value)}
                className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
                data-testid="filter-start-date"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">{t('transactions.endDate')}</label>
              <input
                type="date"
                value={filters.endDate}
                onChange={(e) => handleFilterChange('endDate', e.target.value)}
                className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
                data-testid="filter-end-date"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">{t('transactions.station')}</label>
              <select
                value={filters.station}
                onChange={(e) => handleFilterChange('station', e.target.value)}
                className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
                data-testid="filter-station"
              >
                <option value="">{t('transactions.allStations')}</option>
                {stations.map((station) => (
                  <option key={station} value={station}>
                    {station}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">{t('transactions.account')}</label>
              <select
                value={filters.account}
                onChange={(e) => handleFilterChange('account', e.target.value)}
                className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
                data-testid="filter-account"
              >
                <option value="">{t('transactions.allAccounts')}</option>
                {accounts.map((account) => (
                  <option key={account} value={account}>
                    {account}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">{t('transactions.paymentStatus')}</label>
              <select
                value={filters.paymentStatus}
                onChange={(e) => handleFilterChange('paymentStatus', e.target.value)}
                className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
                data-testid="filter-payment-status"
              >
                <option value="">{t('transactions.allStatus')}</option>
                <option value="PAID">{t('transactions.paid')}</option>
                <option value="UNPAID">{t('transactions.unpaid')}</option>
              </select>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={applyFilters}
              className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-md transition-colors font-medium"
              data-testid="apply-filters-btn"
            >
              {t('transactions.applyFilters')}
            </button>
            <button
              onClick={clearFilters}
              className="px-4 py-2 border border-slate-300 dark:border-slate-700 rounded-md hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors font-medium"
              data-testid="clear-filters-btn"
            >
              {t('transactions.clearFilters')}
            </button>
          </div>
        </div>
      )}

      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-12" data-testid="transactions-loading">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600"></div>
          </div>
        ) : transactions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full" data-testid="transactions-table">
              <thead className="bg-slate-50 dark:bg-slate-800 sticky top-0">
                <tr>
                  {(user?.role === 'admin' || user?.role === 'user') && (
                    <th className="text-left py-4 px-4 text-xs font-semibold">
                      <button onClick={toggleSelectAll} className="hover:text-orange-600">
                        {selectedTxs.length === transactions.length ? (
                          <CheckSquare className="w-5 h-5" />
                        ) : (
                          <Square className="w-5 h-5" />
                        )}
                      </button>
                    </th>
                  )}
                  <th className="text-left py-4 px-4 text-xs font-semibold text-slate-700 dark:text-slate-300">{t('transactions.txId')}</th>
                  <th className="text-left py-4 px-4 text-xs font-semibold text-slate-700 dark:text-slate-300">{t('transactions.account')}</th>
                  <th className="text-left py-4 px-4 text-xs font-semibold text-slate-700 dark:text-slate-300">{t('transactions.connector')}</th>
                  <th className="text-left py-4 px-4 text-xs font-semibold text-slate-700 dark:text-slate-300">Type</th>
                  <th className="text-left py-4 px-4 text-xs font-semibold text-slate-700 dark:text-slate-300">{t('transactions.duration')}</th>
                  <th className="text-left py-4 px-4 text-xs font-semibold text-slate-700 dark:text-slate-300">{t('transactions.energy')}</th>
                  <th className="text-left py-4 px-4 text-xs font-semibold text-slate-700 dark:text-slate-300">{t('transactions.cost')}</th>
                  <th className="text-left py-4 px-4 text-xs font-semibold text-slate-700 dark:text-slate-300">Status</th>
                  <th className="text-left py-4 px-4 text-xs font-semibold text-slate-700 dark:text-slate-300">Payment</th>
                  {(user?.role === 'admin' || user?.role === 'user') && (
                    <th className="text-left py-4 px-4 text-xs font-semibold text-slate-700 dark:text-slate-300">{t('transactions.actions')}</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {transactions.map((tx) => (
                  <tr
                    key={tx.id}
                    className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                    data-testid="transaction-row"
                  >
                    {editingTx === tx.id ? (
                      // Edit mode
                      <>
                        {(user?.role === 'admin' || user?.role === 'user') && <td className="py-4 px-4"></td>}
                        <td className="py-4 px-4 text-sm font-medium">{tx.tx_id}</td>
                        <td className="py-4 px-4">
                          <input
                            type="text"
                            value={editForm.account}
                            onChange={(e) => setEditForm({...editForm, account: e.target.value})}
                            className="w-full px-2 py-1 text-sm border rounded"
                          />
                        </td>
                        <td className="py-4 px-4">
                          <input
                            type="text"
                            value={editForm.connector}
                            onChange={(e) => setEditForm({...editForm, connector: e.target.value})}
                            className="w-full px-2 py-1 text-sm border rounded"
                          />
                        </td>
                        <td className="py-4 px-4">
                          <select
                            value={editForm.connector_type}
                            onChange={(e) => setEditForm({...editForm, connector_type: e.target.value})}
                            className="w-full px-2 py-1 text-sm border rounded"
                          >
                            <option value="">None</option>
                            <option value="CCS2">CCS2</option>
                            <option value="CHADEMO">CHADEMO</option>
                            <option value="J1772">J1772</option>
                          </select>
                        </td>
                        <td className="py-4 px-4 text-sm">{tx.charging_duration || 'N/A'}</td>
                        <td className="py-4 px-4">
                          <input
                            type="number"
                            step="0.01"
                            value={editForm.meter_value}
                            onChange={(e) => setEditForm({...editForm, meter_value: parseFloat(e.target.value)})}
                            className="w-20 px-2 py-1 text-sm border rounded"
                          />
                        </td>
                        <td className="py-4 px-4 text-sm font-semibold text-orange-600">{formatCOP(tx.cost)}</td>
                        <td className="py-4 px-4">
                          <select
                            value={editForm.payment_status}
                            onChange={(e) => setEditForm({...editForm, payment_status: e.target.value})}
                            className="px-2 py-1 text-xs border rounded"
                          >
                            <option value="UNPAID">UNPAID</option>
                            <option value="PAID">PAID</option>
                          </select>
                        </td>
                        <td className="py-4 px-4">
                          <select
                            value={editForm.payment_type}
                            onChange={(e) => setEditForm({...editForm, payment_type: e.target.value})}
                            className="w-full px-2 py-1 text-xs border rounded"
                          >
                            <option value="">None</option>
                            <option value="NEQUI">NEQUI</option>
                            <option value="DAVIPLATA">DAVIPLATA</option>
                            <option value="EFECTIVO">EFECTIVO</option>
                          </select>
                        </td>
                        <td className="py-4 px-4">
                          <div className="flex gap-1">
                            <button
                              onClick={() => saveEdit(tx.id)}
                              className="p-1 text-emerald-600 hover:bg-emerald-50 rounded"
                              data-testid="save-edit-btn"
                            >
                              <Check className="w-4 h-4" />
                            </button>
                            <button
                              onClick={cancelEdit}
                              className="p-1 text-slate-600 hover:bg-slate-100 rounded"
                              data-testid="cancel-edit-btn"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </>
                    ) : (
                      // View mode
                      <>
                        {(user?.role === 'admin' || user?.role === 'user') && (
                          <td className="py-4 px-4">
                            <button
                              onClick={() => toggleSelectTx(tx.id)}
                              className="hover:text-orange-600 transition-colors"
                            >
                              {selectedTxs.includes(tx.id) ? (
                                <CheckSquare className="w-5 h-5 text-orange-600" />
                              ) : (
                                <Square className="w-5 h-5" />
                              )}
                            </button>
                          </td>
                        )}
                        <td className="py-4 px-4 text-sm font-medium text-slate-900 dark:text-slate-100">{tx.tx_id}</td>
                        <td className="py-4 px-4 text-sm text-slate-600 dark:text-slate-400">{tx.account}</td>
                        <td className="py-4 px-4 text-sm text-slate-600 dark:text-slate-400">{tx.connector}</td>
                        <td className="py-4 px-4 text-xs">
                          {tx.connector_type && (
                            <span className="px-2 py-1 bg-purple-100 dark:bg-purple-950/30 text-purple-700 dark:text-purple-400 rounded-full font-medium">
                              {tx.connector_type}
                            </span>
                          )}
                        </td>
                        <td className="py-4 px-4 text-sm text-slate-600 dark:text-slate-400">{tx.charging_duration || 'N/A'}</td>
                        <td className="py-4 px-4 text-sm font-semibold text-emerald-600 dark:text-emerald-400">
                          {formatNumber(tx.meter_value)}
                        </td>
                        <td className="py-4 px-4 text-sm font-semibold text-orange-600 dark:text-orange-400">
                          {formatCOP(tx.cost)}
                        </td>
                        <td className="py-4 px-4">
                          <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                            tx.payment_status === 'PAID' 
                              ? 'bg-emerald-100 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-400'
                              : 'bg-rose-100 dark:bg-rose-950/30 text-rose-700 dark:text-rose-400'
                          }`}>
                            {tx.payment_status}
                          </span>
                        </td>
                        <td className="py-4 px-4 text-xs text-slate-600 dark:text-slate-400">
                          {tx.payment_type || '-'}
                          {tx.payment_date && <div className="text-xs text-slate-400">{tx.payment_date}</div>}
                        </td>
                        {(user?.role === 'admin' || user?.role === 'user') && (
                          <td className="py-4 px-4">
                            <div className="flex gap-1">
                              <button
                                onClick={() => startEdit(tx)}
                                className="p-2 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-950/30 rounded transition-colors"
                                data-testid="edit-transaction-btn"
                              >
                                <Edit className="w-4 h-4" />
                              </button>
                              {user?.role === 'admin' && (
                                <button
                                  onClick={() => deleteTransaction(tx.id)}
                                  className="p-2 text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30 rounded transition-colors"
                                  data-testid="delete-transaction-btn"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              )}
                            </div>
                          </td>
                        )}
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12" data-testid="no-transactions">
            <p className="text-slate-500 dark:text-slate-400 mb-4">{t('transactions.noTransactions')}</p>
            <p className="text-sm text-slate-400 dark:text-slate-500">{t('transactions.adjustFilters')}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default Transactions;