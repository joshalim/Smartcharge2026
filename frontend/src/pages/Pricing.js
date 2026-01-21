import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import { DollarSign, Plus, Trash2, X } from 'lucide-react';
import { formatCOP } from '../utils/currency';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function Pricing() {
  const { t } = useTranslation();
  const [pricing, setPricing] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    account: '',
    connector: '',
    price_per_kwh: '',
  });

  useEffect(() => {
    fetchPricing();
  }, []);

  const fetchPricing = async () => {
    try {
      const response = await axios.get(`${API}/pricing`);
      setPricing(response.data);
    } catch (error) {
      console.error('Failed to fetch pricing:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/pricing`, {
        account: formData.account,
        connector: formData.connector,
        price_per_kwh: parseFloat(formData.price_per_kwh),
      });
      setFormData({ account: '', connector: '', price_per_kwh: '' });
      setShowForm(false);
      fetchPricing();
    } catch (error) {
      console.error('Failed to create pricing rule:', error);
      alert('Failed to create pricing rule');
    }
  };

  const deletePricing = async (id) => {
    if (!window.confirm(t('pricing.deleteConfirm'))) return;

    try {
      await axios.delete(`${API}/pricing/${id}`);
      fetchPricing();
    } catch (error) {
      console.error('Failed to delete pricing rule:', error);
      alert('Failed to delete pricing rule');
    }
  };

  return (
    <div className="space-y-6" style={{ fontFamily: 'IBM Plex Sans, sans-serif' }}>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-4xl md:text-5xl font-black tracking-tight mb-2" style={{ fontFamily: 'Chivo, sans-serif' }} data-testid="pricing-title">
            {t('pricing.title')}
          </h1>
          <p className="text-slate-500 dark:text-slate-400">{t('pricing.subtitle')}</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-md transition-colors font-medium"
          data-testid="add-pricing-btn"
        >
          <Plus className="w-4 h-4" />
          {t('pricing.addNew')}
        </button>
      </div>

      {showForm && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>
              {t('pricing.addNew')}
            </h3>
            <button
              onClick={() => setShowForm(false)}
              className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">{t('pricing.account')}</label>
              <input
                type="text"
                value={formData.account}
                onChange={(e) => setFormData({ ...formData, account: e.target.value })}
                required
                className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
                placeholder="ACC-001"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">{t('pricing.connector')}</label>
              <input
                type="text"
                value={formData.connector}
                onChange={(e) => setFormData({ ...formData, connector: e.target.value })}
                required
                className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
                placeholder="Connector-1"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">{t('pricing.pricePerKwh')}</label>
              <input
                type="number"
                step="0.01"
                value={formData.price_per_kwh}
                onChange={(e) => setFormData({ ...formData, price_per_kwh: e.target.value })}
                required
                className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
                placeholder="500"
              />
            </div>
            <div className="md:col-span-3 flex gap-2">
              <button
                type="submit"
                className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-md transition-colors font-medium"
              >
                {t('pricing.save')}
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="px-4 py-2 border border-slate-300 dark:border-slate-700 rounded-md hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors font-medium"
              >
                {t('pricing.cancel')}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-12" data-testid="pricing-loading">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600"></div>
          </div>
        ) : pricing.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full" data-testid="pricing-table">
              <thead className="bg-slate-50 dark:bg-slate-800">
                <tr>
                  <th className="text-left py-4 px-6 text-sm font-semibold text-slate-700 dark:text-slate-300">{t('pricing.account')}</th>
                  <th className="text-left py-4 px-6 text-sm font-semibold text-slate-700 dark:text-slate-300">{t('pricing.connector')}</th>
                  <th className="text-left py-4 px-6 text-sm font-semibold text-slate-700 dark:text-slate-300">{t('pricing.pricePerKwh')}</th>
                  <th className="text-left py-4 px-6 text-sm font-semibold text-slate-700 dark:text-slate-300">{t('pricing.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {pricing.map((rule) => (
                  <tr
                    key={rule.id}
                    className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                    data-testid="pricing-row"
                  >
                    <td className="py-4 px-6 text-sm font-medium text-slate-900 dark:text-slate-100">{rule.account}</td>
                    <td className="py-4 px-6 text-sm text-slate-600 dark:text-slate-400">{rule.connector}</td>
                    <td className="py-4 px-6 text-sm font-semibold text-orange-600 dark:text-orange-400">
                      {formatCOP(rule.price_per_kwh)}
                    </td>
                    <td className="py-4 px-6">
                      <button
                        onClick={() => deletePricing(rule.id)}
                        className="p-2 text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30 rounded transition-colors"
                        data-testid="delete-pricing-btn"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12" data-testid="no-pricing">
            <DollarSign className="w-12 h-12 text-slate-300 dark:text-slate-700 mx-auto mb-4" />
            <p className="text-slate-500 dark:text-slate-400 mb-2">{t('pricing.noPricing')}</p>
            <p className="text-sm text-slate-400 dark:text-slate-500">{t('pricing.addFirst')}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default Pricing;