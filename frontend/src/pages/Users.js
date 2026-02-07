import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Users as UsersIcon, Trash2, Shield, CreditCard, Plus, X, DollarSign, Edit, Upload, FileSpreadsheet, AlertCircle, CheckCircle, Download } from 'lucide-react';
import { formatCOP } from '../utils/currency';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function Users() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // User Modal State
  const [showUserModal, setShowUserModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [userForm, setUserForm] = useState({
    name: '',
    email: '',
    password: '',
    role: 'user',
    rfid_card_number: '',
    rfid_balance: 0,
    placa: ''
  });
  
  // Top Up Modal State
  const [showTopUpModal, setShowTopUpModal] = useState(false);
  const [topUpUser, setTopUpUser] = useState(null);
  const [topUpAmount, setTopUpAmount] = useState('');
  
  // Import Modal State
  const [showImportModal, setShowImportModal] = useState(false);
  const [importFile, setImportFile] = useState(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await axios.get(`${API}/users`);
      setUsers(response.data);
    } catch (error) {
      console.error('Failed to fetch users:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async () => {
    try {
      if (editingUser) {
        const updateData = { ...userForm };
        if (!updateData.password) delete updateData.password;
        await axios.patch(`${API}/users/${editingUser.id}`, updateData);
      } else {
        await axios.post(`${API}/users`, userForm);
      }
      setShowUserModal(false);
      setEditingUser(null);
      setUserForm({ name: '', email: '', password: '', role: 'user', rfid_card_number: '', rfid_balance: 0 });
      fetchUsers();
    } catch (error) {
      alert(error.response?.data?.detail || 'Operation failed');
    }
  };

  const handleDeleteUser = async (userId) => {
    if (!window.confirm('Are you sure you want to delete this user?')) return;
    try {
      await axios.delete(`${API}/users/${userId}`);
      fetchUsers();
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to delete user');
    }
  };

  const handleTopUp = async () => {
    const amount = parseFloat(topUpAmount);
    if (isNaN(amount) || amount <= 0) {
      alert('Please enter a valid amount');
      return;
    }
    try {
      await axios.post(`${API}/users/${topUpUser.id}/topup`, { amount });
      setShowTopUpModal(false);
      setTopUpUser(null);
      setTopUpAmount('');
      fetchUsers();
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to top up balance');
    }
  };

  const openEditModal = (user) => {
    setEditingUser(user);
    setUserForm({
      name: user.name,
      email: user.email,
      password: '',
      role: user.role,
      rfid_card_number: user.rfid_card_number || '',
      rfid_balance: user.rfid_balance || 0
    });
    setShowUserModal(true);
  };

  const openTopUpModal = (user) => {
    setTopUpUser(user);
    setTopUpAmount('');
    setShowTopUpModal(true);
  };

  const handleImport = async () => {
    if (!importFile) return;
    setImporting(true);
    setImportResult(null);
    
    const formData = new FormData();
    formData.append('file', importFile);
    
    try {
      const response = await axios.post(`${API}/users/import`, formData);
      setImportResult(response.data);
      fetchUsers();
    } catch (error) {
      setImportResult({
        imported: 0,
        skipped: 0,
        errors: [{ row: 0, message: error.response?.data?.detail || 'Import failed' }]
      });
    } finally {
      setImporting(false);
    }
  };

  const downloadTemplate = () => {
    const template = 'Name,Email,Password,Role,RFID Card Number,RFID Balance\nJohn Doe,john@example.com,password123,user,RFID001,10000\n';
    const blob = new Blob([template], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'users_template.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  const getRoleColor = (role) => {
    switch (role) {
      case 'admin': return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
      case 'user': return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400';
      case 'viewer': return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400';
      case 'inactive': return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400';
      case 'blocked': return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" style={{ fontFamily: 'IBM Plex Sans, sans-serif' }}>
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-4xl md:text-5xl font-black tracking-tight mb-2" style={{ fontFamily: 'Chivo, sans-serif' }} data-testid="users-title">
            User Management
          </h1>
          <p className="text-slate-500 dark:text-slate-400">Manage users and their RFID cards</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowImportModal(true)}
            className="flex items-center gap-2 px-4 py-2 border border-slate-300 dark:border-slate-700 rounded-md hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
            data-testid="import-users-btn"
          >
            <Upload className="w-4 h-4" />
            Import
          </button>
          <button
            onClick={() => {
              setEditingUser(null);
              setUserForm({ name: '', email: '', password: '', role: 'user', rfid_card_number: '', rfid_balance: 0 });
              setShowUserModal(true);
            }}
            className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-md transition-colors font-medium"
            data-testid="add-user-btn"
          >
            <Plus className="w-4 h-4" />
            Add User
          </button>
        </div>
      </div>

      {/* Users Table */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
                <th className="text-left px-6 py-4 text-sm font-semibold text-slate-600 dark:text-slate-300">User</th>
                <th className="text-left px-6 py-4 text-sm font-semibold text-slate-600 dark:text-slate-300">Role</th>
                <th className="text-left px-6 py-4 text-sm font-semibold text-slate-600 dark:text-slate-300">RFID Card</th>
                <th className="text-right px-6 py-4 text-sm font-semibold text-slate-600 dark:text-slate-300">Balance</th>
                <th className="text-center px-6 py-4 text-sm font-semibold text-slate-600 dark:text-slate-300">Status</th>
                <th className="text-right px-6 py-4 text-sm font-semibold text-slate-600 dark:text-slate-300">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user, index) => (
                <tr key={user.id} className={index % 2 === 0 ? 'bg-white dark:bg-slate-900' : 'bg-slate-50/50 dark:bg-slate-800/50'}>
                  <td className="px-6 py-4">
                    <div>
                      <p className="font-medium text-slate-900 dark:text-slate-100">{user.name}</p>
                      <p className="text-sm text-slate-500 dark:text-slate-400">{user.email}</p>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRoleColor(user.role)}`}>
                      {user.role}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    {user.rfid_card_number ? (
                      <div className="flex items-center gap-2">
                        <CreditCard className="w-4 h-4 text-orange-500" />
                        <span className="font-mono text-sm">{user.rfid_card_number}</span>
                      </div>
                    ) : (
                      <span className="text-slate-400 text-sm">No card assigned</span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <span className="font-semibold text-slate-900 dark:text-slate-100">
                      {formatCOP(user.rfid_balance || 0)}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-center">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(user.rfid_status || 'active')}`}>
                      {user.rfid_status || 'active'}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => openTopUpModal(user)}
                        className="p-2 hover:bg-emerald-100 dark:hover:bg-emerald-900/30 rounded-lg text-emerald-600 dark:text-emerald-400 transition-colors"
                        title="Top Up Balance"
                        data-testid={`topup-${user.id}`}
                      >
                        <DollarSign className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => openEditModal(user)}
                        className="p-2 hover:bg-blue-100 dark:hover:bg-blue-900/30 rounded-lg text-blue-600 dark:text-blue-400 transition-colors"
                        title="Edit User"
                        data-testid={`edit-${user.id}`}
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteUser(user.id)}
                        className="p-2 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-lg text-red-600 dark:text-red-400 transition-colors"
                        title="Delete User"
                        data-testid={`delete-${user.id}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr>
                  <td colSpan="6" className="px-6 py-12 text-center text-slate-500 dark:text-slate-400">
                    No users found. Click "Add User" to create one.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* User Modal */}
      {showUserModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-900 rounded-xl p-6 w-full max-w-md shadow-2xl">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>
                {editingUser ? 'Edit User' : 'Add New User'}
              </h3>
              <button onClick={() => setShowUserModal(false)} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Name *</label>
                <input
                  type="text"
                  value={userForm.name}
                  onChange={(e) => setUserForm({ ...userForm, name: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 dark:border-slate-700 rounded-md dark:bg-slate-800"
                  data-testid="user-name-input"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Email *</label>
                <input
                  type="email"
                  value={userForm.email}
                  onChange={(e) => setUserForm({ ...userForm, email: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 dark:border-slate-700 rounded-md dark:bg-slate-800"
                  data-testid="user-email-input"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">
                  Password {editingUser ? '(leave blank to keep current)' : '*'}
                </label>
                <input
                  type="password"
                  value={userForm.password}
                  onChange={(e) => setUserForm({ ...userForm, password: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 dark:border-slate-700 rounded-md dark:bg-slate-800"
                  data-testid="user-password-input"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Role</label>
                <select
                  value={userForm.role}
                  onChange={(e) => setUserForm({ ...userForm, role: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 dark:border-slate-700 rounded-md dark:bg-slate-800"
                  data-testid="user-role-select"
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                  <option value="viewer">Viewer</option>
                </select>
              </div>
              <div className="border-t border-slate-200 dark:border-slate-700 pt-4 mt-4">
                <h4 className="font-medium mb-3 flex items-center gap-2">
                  <CreditCard className="w-4 h-4 text-orange-500" />
                  RFID Card Details
                </h4>
                <div className="space-y-3">
                  <div>
                    <label className="block text-sm font-medium mb-1">RFID Card Number</label>
                    <input
                      type="text"
                      value={userForm.rfid_card_number}
                      onChange={(e) => setUserForm({ ...userForm, rfid_card_number: e.target.value })}
                      className="w-full px-3 py-2 border border-slate-300 dark:border-slate-700 rounded-md dark:bg-slate-800"
                      placeholder="e.g., RFID001"
                      data-testid="user-rfid-input"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Initial Balance (COP)</label>
                    <input
                      type="number"
                      value={userForm.rfid_balance}
                      onChange={(e) => setUserForm({ ...userForm, rfid_balance: parseFloat(e.target.value) || 0 })}
                      className="w-full px-3 py-2 border border-slate-300 dark:border-slate-700 rounded-md dark:bg-slate-800"
                      placeholder="0"
                      data-testid="user-balance-input"
                    />
                  </div>
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowUserModal(false)}
                className="px-4 py-2 border border-slate-300 dark:border-slate-700 rounded-md hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateUser}
                className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-md"
                data-testid="save-user-btn"
              >
                {editingUser ? 'Update User' : 'Create User'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Top Up Modal */}
      {showTopUpModal && topUpUser && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-900 rounded-xl p-6 w-full max-w-sm shadow-2xl">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>
                Top Up Balance
              </h3>
              <button onClick={() => setShowTopUpModal(false)} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="space-y-4">
              <div className="p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
                <p className="text-sm text-slate-500 dark:text-slate-400">User</p>
                <p className="font-medium">{topUpUser.name}</p>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-2">Current Balance</p>
                <p className="text-2xl font-bold text-orange-600">{formatCOP(topUpUser.rfid_balance || 0)}</p>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Amount to Add (COP)</label>
                <input
                  type="number"
                  value={topUpAmount}
                  onChange={(e) => setTopUpAmount(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 dark:border-slate-700 rounded-md dark:bg-slate-800"
                  placeholder="Enter amount"
                  data-testid="topup-amount-input"
                />
              </div>
              <div className="flex gap-2">
                {[5000, 10000, 20000, 50000].map((amt) => (
                  <button
                    key={amt}
                    onClick={() => setTopUpAmount(String(amt))}
                    className="flex-1 px-2 py-1 text-xs border border-slate-300 dark:border-slate-700 rounded hover:bg-slate-50 dark:hover:bg-slate-800"
                  >
                    {formatCOP(amt)}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowTopUpModal(false)}
                className="px-4 py-2 border border-slate-300 dark:border-slate-700 rounded-md hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                onClick={handleTopUp}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md"
                data-testid="confirm-topup-btn"
              >
                Add Funds
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Import Modal */}
      {showImportModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-900 rounded-xl p-6 w-full max-w-md shadow-2xl">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>
                Import Users
              </h3>
              <button onClick={() => { setShowImportModal(false); setImportResult(null); }} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="space-y-4">
              <button
                onClick={downloadTemplate}
                className="flex items-center gap-2 text-sm text-orange-600 hover:text-orange-700"
              >
                <Download className="w-4 h-4" />
                Download CSV Template
              </button>
              
              <div className="border-2 border-dashed border-slate-300 dark:border-slate-700 rounded-lg p-6 text-center">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={(e) => setImportFile(e.target.files[0])}
                  className="hidden"
                />
                {importFile ? (
                  <div className="flex items-center justify-center gap-2">
                    <FileSpreadsheet className="w-5 h-5 text-orange-500" />
                    <span>{importFile.name}</span>
                    <button onClick={() => setImportFile(null)} className="text-red-500">
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="text-slate-500 hover:text-slate-700"
                  >
                    <Upload className="w-8 h-8 mx-auto mb-2" />
                    <p>Click to select file</p>
                    <p className="text-xs mt-1">CSV or Excel</p>
                  </button>
                )}
              </div>
              
              {importResult && (
                <div className={`p-4 rounded-lg ${importResult.errors?.length > 0 ? 'bg-amber-50 dark:bg-amber-900/20' : 'bg-emerald-50 dark:bg-emerald-900/20'}`}>
                  <div className="flex items-center gap-2 mb-2">
                    {importResult.errors?.length > 0 ? (
                      <AlertCircle className="w-5 h-5 text-amber-600" />
                    ) : (
                      <CheckCircle className="w-5 h-5 text-emerald-600" />
                    )}
                    <span className="font-medium">Import Complete</span>
                  </div>
                  <p className="text-sm">Imported: {importResult.imported}</p>
                  <p className="text-sm">Skipped: {importResult.skipped}</p>
                  {importResult.errors?.length > 0 && (
                    <div className="mt-2 max-h-32 overflow-y-auto text-sm text-red-600">
                      {importResult.errors.map((err, i) => (
                        <p key={i}>Row {err.row}: {err.message}</p>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
            
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => { setShowImportModal(false); setImportResult(null); }}
                className="px-4 py-2 border border-slate-300 dark:border-slate-700 rounded-md hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                Close
              </button>
              <button
                onClick={handleImport}
                disabled={!importFile || importing}
                className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-md disabled:opacity-50"
              >
                {importing ? 'Importing...' : 'Import'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Users;
