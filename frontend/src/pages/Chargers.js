import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import { Zap, Plus, Edit, Trash2, X, MapPin, Activity } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function Chargers() {
  const { t } = useTranslation();
  const [chargers, setChargers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [formData, setFormData] = useState({
    charger_id: '',
    name: '',
    location: '',
    model: '',
    serial_number: '',
    connector_types: [],
    max_power: '',
    status: 'Available',
  });

  useEffect(() => {
    fetchChargers();
  }, []);

  const fetchChargers = async () => {
    try {
      const response = await axios.get(`${API}/chargers`);
      setChargers(response.data);
    } catch (error) {
      console.error('Failed to fetch chargers:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        charger_id: formData.charger_id,
        name: formData.name,
        location: formData.location,
        connectors: formData.connector_types.filter(t => t),
        status: formData.status
      };

      if (editingId) {
        await axios.patch(`${API}/chargers/${editingId}`, payload);
      } else {
        await axios.post(`${API}/chargers`, payload);
      }
      
      resetForm();
      fetchChargers();
    } catch (error) {
      console.error('Failed to save charger:', error);
      alert('Failed to save charger: ' + (error.response?.data?.detail || error.message));
    }
  };

  const startEdit = (charger) => {
    setEditingId(charger.id);
    setFormData({
      charger_id: charger.charger_id || '',
      name: charger.name || '',
      location: charger.location || '',
      model: charger.model || '',
      serial_number: charger.serial_number || '',
      connector_types: charger.connectors || charger.connector_types || [],
      max_power: charger.max_power?.toString() || '',
      status: charger.status || 'Available',
    });
    setShowForm(true);
  };

  const deleteCharger = async (id) => {
    if (!window.confirm('Are you sure you want to delete this charger?')) return;
    try {
      await axios.delete(`${API}/chargers/${id}`);
      fetchChargers();
    } catch (error) {
      console.error('Failed to delete charger:', error);
      alert('Failed to delete charger');
    }
  };

  const resetForm = () => {
    setFormData({
      charger_id: '',
      name: '',
      location: '',
      model: '',
      serial_number: '',
      connector_types: [],
      max_power: '',
      status: 'Available',
    });
    setEditingId(null);
    setShowForm(false);
  };

  const toggleConnectorType = (type) => {
    setFormData(prev => ({
      ...prev,
      connector_types: prev.connector_types.includes(type)
        ? prev.connector_types.filter(t => t !== type)
        : [...prev.connector_types, type]
    }));
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'Available':
        return 'bg-emerald-100 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-400';
      case 'Charging':
        return 'bg-orange-100 dark:bg-orange-950/30 text-orange-700 dark:text-orange-400';
      case 'Faulted':
        return 'bg-rose-100 dark:bg-rose-950/30 text-rose-700 dark:text-rose-400';
      case 'Unavailable':
        return 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300';
      default:
        return 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300';
    }
  };

  return (
    <div className="space-y-6" style={{ fontFamily: 'IBM Plex Sans, sans-serif' }}>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-4xl md:text-5xl font-black tracking-tight mb-2" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Chargers
          </h1>
          <p className="text-slate-500 dark:text-slate-400">Manage EV charging stations</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-md transition-colors font-medium"
        >
          <Plus className="w-4 h-4" />
          Add Charger
        </button>
      </div>

      {showForm && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>
              {editingId ? 'Edit Charger' : 'Add New Charger'}
            </h3>
            <button onClick={resetForm} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded">
              <X className="w-5 h-5" />
            </button>
          </div>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Charger ID *</label>
                <input
                  type="text"
                  required
                  value={formData.charger_id}
                  onChange={(e) => setFormData({...formData, charger_id: e.target.value})}
                  className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                  placeholder="CHG-001"
                  disabled={!!editingId}
                />
                {!editingId && <p className="text-xs text-slate-500 mt-1">Unique identifier for OCPP</p>}
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Name *</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                  placeholder="Station A"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Location</label>
                <input
                  type="text"
                  value={formData.location}
                  onChange={(e) => setFormData({...formData, location: e.target.value})}
                  className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                  placeholder="Building B, Floor 1"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Status</label>
                <select
                  value={formData.status}
                  onChange={(e) => setFormData({...formData, status: e.target.value})}
                  className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                >
                  <option value="Available">Available</option>
                  <option value="Charging">Charging</option>
                  <option value="Faulted">Faulted</option>
                  <option value="Unavailable">Unavailable</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Connector Types</label>
              <div className="flex flex-wrap gap-2">
                {['CCS2', 'CHADEMO', 'J1772', 'Type 2'].map(type => (
                  <button
                    key={type}
                    type="button"
                    onClick={() => toggleConnectorType(type)}
                    className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      formData.connector_types.includes(type)
                        ? 'bg-orange-600 text-white'
                        : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
                    }`}
                  >
                    {type}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex gap-2">
              <button
                type="submit"
                className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-md transition-colors font-medium"
              >
                {editingId ? 'Update' : 'Create'}
              </button>
              <button
                type="button"
                onClick={resetForm}
                className="px-4 py-2 border border-slate-300 dark:border-slate-700 rounded-md hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors font-medium"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          <div className="col-span-full flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600"></div>
          </div>
        ) : chargers.length > 0 ? (
          chargers.map((charger) => (
            <div
              key={charger.id}
              className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm hover:shadow-md transition-all"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="p-3 bg-orange-50 dark:bg-orange-950/30 rounded-lg">
                    <Zap className="w-6 h-6 text-orange-600 dark:text-orange-400" />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-900 dark:text-slate-100">{charger.name}</h3>
                  </div>
                </div>
                <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(charger.status)}`}>
                  {charger.status}
                </span>
              </div>
              
              <div className="space-y-2 mb-4">
                <div className="flex items-center gap-2 text-sm">
                  <Activity className="w-4 h-4 text-slate-400" />
                  <span className="text-slate-600 dark:text-slate-400">ID: {charger.charger_id}</span>
                </div>
                {charger.location && (
                  <div className="flex items-center gap-2 text-sm">
                    <MapPin className="w-4 h-4 text-slate-400" />
                    <span className="text-slate-600 dark:text-slate-400">{charger.location}</span>
                  </div>
                )}
              </div>

              <div className="flex flex-wrap gap-1 mb-4">
                {(charger.connectors || []).map(type => (
                  <span key={type} className="px-2 py-1 bg-purple-100 dark:bg-purple-950/30 text-purple-700 dark:text-purple-400 text-xs font-medium rounded-full">
                    {type}
                  </span>
                ))}
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => startEdit(charger)}
                  className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm bg-blue-50 dark:bg-blue-950/30 text-blue-600 dark:text-blue-400 rounded-md hover:bg-blue-100 dark:hover:bg-blue-950/50 transition-colors"
                >
                  <Edit className="w-4 h-4" />
                  Edit
                </button>
                <button
                  onClick={() => deleteCharger(charger.id)}
                  className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm bg-rose-50 dark:bg-rose-950/30 text-rose-600 dark:text-rose-400 rounded-md hover:bg-rose-100 dark:hover:bg-rose-950/50 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete
                </button>
              </div>
            </div>
          ))
        ) : (
          <div className="col-span-full text-center py-12">
            <Zap className="w-12 h-12 text-slate-300 dark:text-slate-700 mx-auto mb-4" />
            <p className="text-slate-500 dark:text-slate-400">No chargers configured yet</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default Chargers;