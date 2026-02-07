import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import { 
  Receipt, Plus, Edit2, Trash2, Calendar, DollarSign, 
  FileText, Search, RefreshCw, X, Check
} from 'lucide-react';
import { formatCOP, formatNumber } from '../utils/currency';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function Expenses() {
  const { t } = useTranslation();
  const [expenses, setExpenses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingExpense, setEditingExpense] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filters, setFilters] = useState({
    start_date: '',
    end_date: ''
  });
  
  const [formData, setFormData] = useState({
    name: '',
    date: new Date().toISOString().split('T')[0],
    cost: '',
    reason: ''
  });

  useEffect(() => {
    fetchExpenses();
  }, []);

  const fetchExpenses = async () => {
    setLoading(true);
    try {
      let url = `${API}/expenses`;
      const params = new URLSearchParams();
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);
      if (params.toString()) url += `?${params.toString()}`;
      
      const response = await axios.get(url);
      setExpenses(response.data);
    } catch (error) {
      console.error('Failed to fetch expenses:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingExpense) {
        await axios.put(`${API}/expenses/${editingExpense.id}`, {
          ...formData,
          cost: parseFloat(formData.cost)
        });
      } else {
        await axios.post(`${API}/expenses`, {
          ...formData,
          cost: parseFloat(formData.cost)
        });
      }
      setShowModal(false);
      setEditingExpense(null);
      setFormData({ name: '', date: new Date().toISOString().split('T')[0], cost: '', reason: '' });
      fetchExpenses();
    } catch (error) {
      console.error('Failed to save expense:', error);
      alert('Failed to save expense: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleEdit = (expense) => {
    setEditingExpense(expense);
    setFormData({
      name: expense.name,
      date: expense.date,
      cost: expense.cost.toString(),
      reason: expense.reason || ''
    });
    setShowModal(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm(t('expenses.deleteConfirm'))) return;
    try {
      await axios.delete(`${API}/expenses/${id}`);
      fetchExpenses();
    } catch (error) {
      console.error('Failed to delete expense:', error);
      alert('Failed to delete expense: ' + (error.response?.data?.detail || error.message));
    }
  };

  const openNewModal = () => {
    setEditingExpense(null);
    setFormData({ name: '', date: new Date().toISOString().split('T')[0], cost: '', reason: '' });
    setShowModal(true);
  };

  const filteredExpenses = expenses.filter(exp => 
    exp.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (exp.reason && exp.reason.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  const totalExpenses = filteredExpenses.reduce((sum, exp) => sum + exp.cost, 0);

  return (
    <div className="space-y-6" style={{ fontFamily: 'IBM Plex Sans, sans-serif' }}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-4xl md:text-5xl font-black tracking-tight mb-2" style={{ fontFamily: 'Chivo, sans-serif' }} data-testid="expenses-title">
            {t('expenses.title')}
          </h1>
          <p className="text-slate-500 dark:text-slate-400">{t('expenses.subtitle')}</p>
        </div>
        <button
          onClick={openNewModal}
          className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors font-medium"
          data-testid="add-expense-btn"
        >
          <Plus className="w-4 h-4" />
          {t('expenses.addNew')}
        </button>
      </div>

      {/* Filters & Search */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="md:col-span-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                placeholder={t('expenses.searchPlaceholder')}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full h-10 pl-10 pr-4 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm"
                data-testid="search-expenses"
              />
            </div>
          </div>
          <div>
            <input
              type="date"
              value={filters.start_date}
              onChange={(e) => setFilters({...filters, start_date: e.target.value})}
              className="w-full h-10 px-3 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm"
              data-testid="filter-start-date"
            />
          </div>
          <div className="flex gap-2">
            <input
              type="date"
              value={filters.end_date}
              onChange={(e) => setFilters({...filters, end_date: e.target.value})}
              className="flex-1 h-10 px-3 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm"
              data-testid="filter-end-date"
            />
            <button
              onClick={fetchExpenses}
              className="h-10 px-3 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors"
              data-testid="apply-filters-btn"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Summary Card */}
      <div className="bg-gradient-to-r from-rose-500 to-rose-600 rounded-xl p-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-rose-100 text-sm font-medium mb-1">{t('expenses.totalExpenses')}</p>
            <p className="text-3xl font-bold">{formatCOP(totalExpenses)}</p>
            <p className="text-rose-100 text-sm mt-1">{filteredExpenses.length} {t('expenses.entries')}</p>
          </div>
          <div className="p-4 bg-white/20 rounded-full">
            <Receipt className="w-8 h-8" />
          </div>
        </div>
      </div>

      {/* Expenses Table */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-600"></div>
          </div>
        ) : filteredExpenses.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16">
            <Receipt className="w-16 h-16 text-slate-300 dark:text-slate-700 mb-4" />
            <h3 className="text-lg font-bold text-slate-700 dark:text-slate-300 mb-2">{t('expenses.noExpenses')}</h3>
            <p className="text-slate-500 dark:text-slate-400 mb-4">{t('expenses.addFirst')}</p>
            <button
              onClick={openNewModal}
              className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg font-medium"
            >
              {t('expenses.addNew')}
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full" data-testid="expenses-table">
              <thead className="bg-slate-50 dark:bg-slate-800">
                <tr>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">{t('expenses.name')}</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">{t('expenses.date')}</th>
                  <th className="text-right py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">{t('expenses.cost')}</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">{t('expenses.reason')}</th>
                  <th className="text-center py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">{t('expenses.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {filteredExpenses.map((expense) => (
                  <tr
                    key={expense.id}
                    className="border-t border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
                    data-testid="expense-row"
                  >
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <div className="p-1.5 bg-rose-100 dark:bg-rose-900/30 rounded">
                          <Receipt className="w-4 h-4 text-rose-600 dark:text-rose-400" />
                        </div>
                        <span className="font-medium text-slate-900 dark:text-slate-100">{expense.name}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-slate-600 dark:text-slate-400">
                      <div className="flex items-center gap-1">
                        <Calendar className="w-4 h-4" />
                        {expense.date}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-right font-semibold text-rose-600 dark:text-rose-400">
                      {formatCOP(expense.cost)}
                    </td>
                    <td className="py-3 px-4 text-slate-600 dark:text-slate-400 max-w-xs truncate">
                      {expense.reason || '-'}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center justify-center gap-2">
                        <button
                          onClick={() => handleEdit(expense)}
                          className="p-2 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
                          data-testid={`edit-expense-${expense.id}`}
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(expense.id)}
                          className="p-2 text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-900/30 rounded-lg transition-colors"
                          data-testid={`delete-expense-${expense.id}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-900 rounded-xl w-full max-w-md shadow-xl" data-testid="expense-modal">
            <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-800">
              <h2 className="text-lg font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>
                {editingExpense ? t('expenses.edit') : t('expenses.addNew')}
              </h2>
              <button
                onClick={() => setShowModal(false)}
                className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <form onSubmit={handleSubmit} className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">{t('expenses.name')} *</label>
                <div className="relative">
                  <FileText className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                    required
                    placeholder={t('expenses.namePlaceholder')}
                    className="w-full h-10 pl-10 pr-4 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800"
                    data-testid="expense-name-input"
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-2">{t('expenses.date')} *</label>
                <div className="relative">
                  <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input
                    type="date"
                    value={formData.date}
                    onChange={(e) => setFormData({...formData, date: e.target.value})}
                    required
                    className="w-full h-10 pl-10 pr-4 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800"
                    data-testid="expense-date-input"
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-2">{t('expenses.cost')} (COP) *</label>
                <div className="relative">
                  <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input
                    type="number"
                    value={formData.cost}
                    onChange={(e) => setFormData({...formData, cost: e.target.value})}
                    required
                    min="0"
                    step="0.01"
                    placeholder="0"
                    className="w-full h-10 pl-10 pr-4 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800"
                    data-testid="expense-cost-input"
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-2">{t('expenses.reason')}</label>
                <textarea
                  value={formData.reason}
                  onChange={(e) => setFormData({...formData, reason: e.target.value})}
                  placeholder={t('expenses.reasonPlaceholder')}
                  rows={3}
                  className="w-full px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 resize-none"
                  data-testid="expense-reason-input"
                />
              </div>
              
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 h-10 border border-slate-300 dark:border-slate-700 rounded-lg font-medium hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                >
                  {t('common.cancel')}
                </button>
                <button
                  type="submit"
                  className="flex-1 h-10 bg-orange-600 hover:bg-orange-700 text-white rounded-lg font-medium flex items-center justify-center gap-2 transition-colors"
                  data-testid="save-expense-btn"
                >
                  <Check className="w-4 h-4" />
                  {t('common.save')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Expenses;
