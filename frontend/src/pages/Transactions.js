import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import { Search, Filter, X, Download, Trash2 } from 'lucide-react';
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
  });
  const [stations, setStations] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [showFilters, setShowFilters] = useState(false);

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

      const response = await axios.get(`${API}/transactions`, { params });
      setTransactions(response.data);
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

  const exportToCSV = () => {
    const headers = ['Tx ID', 'Station', 'Connector', 'Account', 'Start Time', 'End Time', 'Energy (kWh)', 'Cost (COP)'];
    const rows = transactions.map((tx) => [
      tx.tx_id,
      tx.station,
      tx.connector,
      tx.account,
      tx.start_time,
      tx.end_time,
      tx.meter_value,
      tx.cost,
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

      {showFilters && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6" data-testid="filters-panel">
          <h3 className="text-lg font-bold mb-4" style={{ fontFamily: 'Chivo, sans-serif' }}>
            {t('transactions.filterTitle')}
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
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
                  <th className="text-left py-4 px-6 text-sm font-semibold text-slate-700 dark:text-slate-300">{t('transactions.txId')}</th>
                  <th className="text-left py-4 px-6 text-sm font-semibold text-slate-700 dark:text-slate-300">{t('transactions.station')}</th>
                  <th className="text-left py-4 px-6 text-sm font-semibold text-slate-700 dark:text-slate-300">{t('transactions.connector')}</th>
                  <th className="text-left py-4 px-6 text-sm font-semibold text-slate-700 dark:text-slate-300">{t('transactions.account')}</th>
                  <th className="text-left py-4 px-6 text-sm font-semibold text-slate-700 dark:text-slate-300">{t('transactions.startTime')}</th>
                  <th className="text-left py-4 px-6 text-sm font-semibold text-slate-700 dark:text-slate-300">{t('transactions.endTime')}</th>
                  <th className="text-left py-4 px-6 text-sm font-semibold text-slate-700 dark:text-slate-300">{t('transactions.energy')}</th>
                  <th className="text-left py-4 px-6 text-sm font-semibold text-slate-700 dark:text-slate-300">{t('transactions.cost')}</th>
                  {user?.role === 'admin' && (
                    <th className="text-left py-4 px-6 text-sm font-semibold text-slate-700 dark:text-slate-300">{t('transactions.actions')}</th>
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
                    <td className="py-4 px-6 text-sm font-medium text-slate-900 dark:text-slate-100">{tx.tx_id}</td>
                    <td className="py-4 px-6 text-sm text-slate-600 dark:text-slate-400">{tx.station}</td>
                    <td className="py-4 px-6 text-sm text-slate-600 dark:text-slate-400">{tx.connector}</td>
                    <td className="py-4 px-6 text-sm text-slate-600 dark:text-slate-400">{tx.account}</td>
                    <td className="py-4 px-6 text-sm text-slate-600 dark:text-slate-400">{tx.start_time}</td>
                    <td className="py-4 px-6 text-sm text-slate-600 dark:text-slate-400">{tx.end_time}</td>
                    <td className="py-4 px-6 text-sm font-semibold text-emerald-600 dark:text-emerald-400">
                      {formatNumber(tx.meter_value)}
                    </td>
                    <td className="py-4 px-6 text-sm font-semibold text-orange-600 dark:text-orange-400">
                      {formatCOP(tx.cost)}
                    </td>
                    {user?.role === 'admin' && (
                      <td className="py-4 px-6">
                        <button
                          onClick={() => deleteTransaction(tx.id)}
                          className="p-2 text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30 rounded transition-colors"
                          data-testid="delete-transaction-btn"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
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