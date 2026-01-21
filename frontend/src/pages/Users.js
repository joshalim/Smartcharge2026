import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Users as UsersIcon, Trash2, Shield, CreditCard, Plus, X, DollarSign, Edit, Power, History, ExternalLink, Settings, Upload, FileSpreadsheet, AlertCircle, CheckCircle } from 'lucide-react';
import { formatCOP } from '../utils/currency';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function Users() {
  const [users, setUsers] = useState([]);
  const [rfidCards, setRfidCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('users');
  
  // User Modal State
  const [showUserModal, setShowUserModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [userForm, setUserForm] = useState({
    name: '',
    email: '',
    password: '',
    role: 'user'
  });
  
  // RFID Card Modal State
  const [showCardModal, setShowCardModal] = useState(false);
  const [editingCard, setEditingCard] = useState(null);
  const [cardForm, setCardForm] = useState({
    card_number: '',
    user_id: '',
    balance: 0,
    status: 'active'
  });
  
  // Top Up Modal State
  const [showTopUpModal, setShowTopUpModal] = useState(false);
  const [topUpCard, setTopUpCard] = useState(null);
  const [topUpAmount, setTopUpAmount] = useState('');
  const [topUpMethod, setTopUpMethod] = useState('manual');
  
  // PayU Form State
  const [payuFormData, setPayuFormData] = useState(null);
  const [buyerInfo, setBuyerInfo] = useState({ name: '', email: '', phone: '' });
  
  // History Modal State
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [historyCard, setHistoryCard] = useState(null);
  const [cardHistory, setCardHistory] = useState([]);
  
  // Import Modal State
  const [showImportModal, setShowImportModal] = useState(false);
  const [importFile, setImportFile] = useState(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchUsers();
    fetchRfidCards();
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

  const fetchRfidCards = async () => {
    try {
      const response = await axios.get(`${API}/rfid-cards`);
      setRfidCards(response.data);
    } catch (error) {
      console.error('Failed to fetch RFID cards:', error);
    }
  };

  // User Import
  const openImportModal = () => {
    setImportFile(null);
    setImportResult(null);
    setShowImportModal(true);
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      const validTypes = ['.xlsx', '.xls', '.csv'];
      const isValid = validTypes.some(ext => file.name.toLowerCase().endsWith(ext));
      if (!isValid) {
        alert('Please select an Excel (.xlsx, .xls) or CSV file');
        return;
      }
      setImportFile(file);
      setImportResult(null);
    }
  };

  const handleImportUsers = async () => {
    if (!importFile) return;
    
    setImporting(true);
    setImportResult(null);
    
    try {
      const formData = new FormData();
      formData.append('file', importFile);
      
      const response = await axios.post(`${API}/users/import`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setImportResult(response.data);
      if (response.data.imported > 0) {
        fetchUsers();
      }
    } catch (error) {
      console.error('Failed to import users:', error);
      setImportResult({
        imported: 0,
        skipped: 0,
        errors: [{ row: 0, field: 'File', message: error.response?.data?.detail || 'Failed to import users' }]
      });
    } finally {
      setImporting(false);
    }
  };

  // User CRUD
  const openCreateUser = () => {
    setEditingUser(null);
    setUserForm({ name: '', email: '', password: '', role: 'user' });
    setShowUserModal(true);
  };

  const openEditUser = (user) => {
    setEditingUser(user);
    setUserForm({ name: user.name, email: user.email, password: '', role: user.role });
    setShowUserModal(true);
  };

  const handleSaveUser = async (e) => {
    e.preventDefault();
    try {
      if (editingUser) {
        const updateData = { name: userForm.name, email: userForm.email };
        if (userForm.password) updateData.password = userForm.password;
        await axios.patch(`${API}/users/${editingUser.id}`, updateData);
      } else {
        await axios.post(`${API}/users`, userForm);
      }
      setShowUserModal(false);
      fetchUsers();
    } catch (error) {
      console.error('Failed to save user:', error);
      alert(error.response?.data?.detail || 'Failed to save user');
    }
  };

  const deleteUser = async (userId) => {
    if (!window.confirm('Are you sure you want to delete this user?')) return;
    try {
      await axios.delete(`${API}/users/${userId}`);
      fetchUsers();
    } catch (error) {
      console.error('Failed to delete user:', error);
      alert(error.response?.data?.detail || 'Failed to delete user');
    }
  };

  const updateRole = async (userId, newRole) => {
    try {
      await axios.patch(`${API}/users/${userId}/role?role=${newRole}`);
      fetchUsers();
    } catch (error) {
      console.error('Failed to update role:', error);
      alert('Failed to update user role');
    }
  };

  const getRoleBadgeClass = (role) => {
    switch (role) {
      case 'admin': return 'bg-indigo-100 dark:bg-indigo-950/30 text-indigo-700 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800';
      case 'user': return 'bg-emerald-100 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800';
      case 'viewer': return 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700';
      default: return 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300';
    }
  };

  const getStatusBadgeClass = (status) => {
    switch (status) {
      case 'active': return 'bg-emerald-100 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-400';
      case 'inactive': return 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400';
      case 'blocked': return 'bg-rose-100 dark:bg-rose-950/30 text-rose-700 dark:text-rose-400';
      default: return 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400';
    }
  };

  // RFID Card Functions
  const openCreateCard = () => {
    setEditingCard(null);
    setCardForm({
      card_number: '',
      user_id: users.length > 0 ? users[0].id : '',
      balance: 0,
      status: 'active',
      low_balance_threshold: 10000
    });
    setShowCardModal(true);
  };

  const openEditCard = (card) => {
    setEditingCard(card);
    setCardForm({
      card_number: card.card_number,
      user_id: card.user_id,
      balance: card.balance,
      status: card.status,
      low_balance_threshold: card.low_balance_threshold || 10000
    });
    setShowCardModal(true);
  };

  const handleSaveCard = async (e) => {
    e.preventDefault();
    try {
      if (editingCard) {
        await axios.patch(`${API}/rfid-cards/${editingCard.id}`, {
          card_number: cardForm.card_number,
          status: cardForm.status,
          low_balance_threshold: cardForm.low_balance_threshold
        });
      } else {
        await axios.post(`${API}/rfid-cards`, cardForm);
      }
      setShowCardModal(false);
      fetchRfidCards();
    } catch (error) {
      console.error('Failed to save RFID card:', error);
      alert(error.response?.data?.detail || 'Failed to save RFID card');
    }
  };

  const deleteCard = async (cardId) => {
    if (!window.confirm('Are you sure you want to delete this RFID card?')) return;
    try {
      await axios.delete(`${API}/rfid-cards/${cardId}`);
      fetchRfidCards();
    } catch (error) {
      console.error('Failed to delete RFID card:', error);
      alert(error.response?.data?.detail || 'Failed to delete RFID card');
    }
  };

  // Top Up Functions
  const openTopUp = (card) => {
    setTopUpCard(card);
    setTopUpAmount('');
    setTopUpMethod('manual');
    setBuyerInfo({ name: card.user_name || '', email: card.user_email || '', phone: '' });
    setPayuFormData(null);
    setShowTopUpModal(true);
  };

  const handleManualTopUp = async (e) => {
    e.preventDefault();
    const amount = parseFloat(topUpAmount);
    if (isNaN(amount) || amount <= 0) {
      alert('Please enter a valid amount');
      return;
    }
    try {
      await axios.post(`${API}/rfid-cards/${topUpCard.id}/topup`, { amount });
      setShowTopUpModal(false);
      fetchRfidCards();
    } catch (error) {
      console.error('Failed to top up:', error);
      alert(error.response?.data?.detail || 'Failed to top up');
    }
  };

  const initiatePayUTopUp = async () => {
    const amount = parseFloat(topUpAmount);
    if (isNaN(amount) || amount < 10000) {
      alert('Minimum amount for online payment is $10,000 COP');
      return;
    }
    if (!buyerInfo.name || !buyerInfo.email || !buyerInfo.phone) {
      alert('Please fill all buyer information');
      return;
    }
    
    try {
      const response = await axios.post(`${API}/payu/initiate-topup`, {
        rfid_card_id: topUpCard.id,
        amount: amount,
        buyer_name: buyerInfo.name,
        buyer_email: buyerInfo.email,
        buyer_phone: buyerInfo.phone
      });
      
      setPayuFormData(response.data);
    } catch (error) {
      console.error('Failed to initiate PayU payment:', error);
      alert(error.response?.data?.detail || 'Failed to initiate payment');
    }
  };

  // History Functions
  const openHistory = async (card) => {
    setHistoryCard(card);
    setShowHistoryModal(true);
    try {
      const response = await axios.get(`${API}/rfid-cards/${card.id}/history`);
      setCardHistory(response.data);
    } catch (error) {
      console.error('Failed to fetch history:', error);
      setCardHistory([]);
    }
  };

  const presetAmounts = [10000, 25000, 50000, 100000, 200000];

  return (
    <div className="space-y-6" style={{ fontFamily: 'IBM Plex Sans, sans-serif' }}>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-4xl md:text-5xl font-black tracking-tight mb-2" style={{ fontFamily: 'Chivo, sans-serif' }} data-testid="users-title">
            User Management
          </h1>
          <p className="text-slate-500 dark:text-slate-400">Manage user accounts, permissions, and RFID cards</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-200 dark:border-slate-800">
        <button
          onClick={() => setActiveTab('users')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'users'
              ? 'border-orange-600 text-orange-600'
              : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
          }`}
          data-testid="tab-users"
        >
          <div className="flex items-center gap-2">
            <UsersIcon className="w-4 h-4" />
            Users ({users.length})
          </div>
        </button>
        <button
          onClick={() => setActiveTab('rfid')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'rfid'
              ? 'border-orange-600 text-orange-600'
              : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
          }`}
          data-testid="tab-rfid"
        >
          <div className="flex items-center gap-2">
            <CreditCard className="w-4 h-4" />
            RFID Cards ({rfidCards.length})
          </div>
        </button>
      </div>

      {/* Users Tab */}
      {activeTab === 'users' && (
        <div className="space-y-4">
          <div className="flex justify-end gap-2">
            <button
              onClick={openImportModal}
              className="flex items-center gap-2 px-4 py-2 border border-slate-300 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-md transition-colors font-medium"
              data-testid="import-users-btn"
            >
              <Upload className="w-4 h-4" />
              Import Users
            </button>
            <button
              onClick={openCreateUser}
              className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-md transition-colors font-medium"
              data-testid="add-user-btn"
            >
              <Plus className="w-4 h-4" />
              Add User
            </button>
          </div>
          
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
              </div>
            ) : users.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full" data-testid="users-table">
                  <thead className="bg-slate-50 dark:bg-slate-800">
                    <tr>
                      <th className="text-left py-4 px-6 text-sm font-semibold text-slate-700 dark:text-slate-300">Name</th>
                      <th className="text-left py-4 px-6 text-sm font-semibold text-slate-700 dark:text-slate-300">Email</th>
                      <th className="text-left py-4 px-6 text-sm font-semibold text-slate-700 dark:text-slate-300">Role</th>
                      <th className="text-left py-4 px-6 text-sm font-semibold text-slate-700 dark:text-slate-300">RFID Cards</th>
                      <th className="text-left py-4 px-6 text-sm font-semibold text-slate-700 dark:text-slate-300">Created</th>
                      <th className="text-left py-4 px-6 text-sm font-semibold text-slate-700 dark:text-slate-300">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((user) => {
                      const userCards = rfidCards.filter(c => c.user_id === user.id);
                      return (
                        <tr key={user.id} className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors">
                          <td className="py-4 px-6 text-sm font-medium text-slate-900 dark:text-slate-100">{user.name}</td>
                          <td className="py-4 px-6 text-sm text-slate-600 dark:text-slate-400">{user.email}</td>
                          <td className="py-4 px-6">
                            <select
                              value={user.role}
                              onChange={(e) => updateRole(user.id, e.target.value)}
                              className={`px-3 py-1 rounded-full text-xs font-semibold border ${getRoleBadgeClass(user.role)}`}
                            >
                              <option value="admin">Admin</option>
                              <option value="user">User</option>
                              <option value="viewer">Viewer</option>
                            </select>
                          </td>
                          <td className="py-4 px-6">
                            <span className="px-2 py-1 bg-purple-100 dark:bg-purple-950/30 text-purple-700 dark:text-purple-400 rounded-full text-xs font-medium">
                              {userCards.length} cards
                            </span>
                          </td>
                          <td className="py-4 px-6 text-sm text-slate-600 dark:text-slate-400">
                            {new Date(user.created_at).toLocaleDateString()}
                          </td>
                          <td className="py-4 px-6">
                            <div className="flex gap-2">
                              <button
                                onClick={() => openEditUser(user)}
                                className="p-2 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-950/30 rounded transition-colors"
                                data-testid={`edit-user-btn-${user.id}`}
                              >
                                <Edit className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => deleteUser(user.id)}
                                className="p-2 text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30 rounded transition-colors"
                                data-testid={`delete-user-btn-${user.id}`}
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-12">
                <UsersIcon className="w-12 h-12 text-slate-300 dark:text-slate-700 mx-auto mb-4" />
                <p className="text-slate-500 dark:text-slate-400">No users found</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* RFID Cards Tab */}
      {activeTab === 'rfid' && (
        <div className="space-y-6">
          <div className="flex justify-end">
            <button
              onClick={openCreateCard}
              className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-md transition-colors font-medium"
              data-testid="add-rfid-btn"
            >
              <Plus className="w-4 h-4" />
              Add RFID Card
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {rfidCards.length > 0 ? (
              rfidCards.map((card) => (
                <div
                  key={card.id}
                  className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm hover:shadow-md transition-all"
                  data-testid={`rfid-card-${card.id}`}
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="p-3 bg-purple-50 dark:bg-purple-950/30 rounded-lg">
                        <CreditCard className="w-6 h-6 text-purple-600 dark:text-purple-400" />
                      </div>
                      <div>
                        <h3 className="font-bold text-slate-900 dark:text-slate-100 font-mono">{card.card_number}</h3>
                        <p className="text-sm text-slate-500 dark:text-slate-400">{card.user_name || 'Unknown User'}</p>
                      </div>
                    </div>
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusBadgeClass(card.status)}`}>
                      {card.status}
                    </span>
                  </div>
                  
                  <div className="mb-4 p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
                    <p className="text-xs text-slate-500 dark:text-slate-400 mb-1">Balance</p>
                    <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{formatCOP(card.balance)}</p>
                  </div>

                  <div className="text-xs text-slate-500 dark:text-slate-400 mb-4">
                    {card.user_email}
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={() => openTopUp(card)}
                      className="flex items-center justify-center gap-2 px-3 py-2 text-sm bg-emerald-50 dark:bg-emerald-950/30 text-emerald-600 dark:text-emerald-400 rounded-md hover:bg-emerald-100 dark:hover:bg-emerald-950/50 transition-colors font-medium"
                      data-testid={`topup-btn-${card.id}`}
                    >
                      <DollarSign className="w-4 h-4" />
                      Top Up
                    </button>
                    <button
                      onClick={() => openHistory(card)}
                      className="flex items-center justify-center gap-2 px-3 py-2 text-sm bg-purple-50 dark:bg-purple-950/30 text-purple-600 dark:text-purple-400 rounded-md hover:bg-purple-100 dark:hover:bg-purple-950/50 transition-colors font-medium"
                      data-testid={`history-btn-${card.id}`}
                    >
                      <History className="w-4 h-4" />
                      History
                    </button>
                    <button
                      onClick={() => openEditCard(card)}
                      className="flex items-center justify-center gap-2 px-3 py-2 text-sm bg-blue-50 dark:bg-blue-950/30 text-blue-600 dark:text-blue-400 rounded-md hover:bg-blue-100 dark:hover:bg-blue-950/50 transition-colors"
                      data-testid={`edit-btn-${card.id}`}
                    >
                      <Edit className="w-4 h-4" />
                      Edit
                    </button>
                    <button
                      onClick={() => deleteCard(card.id)}
                      className="flex items-center justify-center gap-2 px-3 py-2 text-sm bg-rose-50 dark:bg-rose-950/30 text-rose-600 dark:text-rose-400 rounded-md hover:bg-rose-100 dark:hover:bg-rose-950/50 transition-colors"
                      data-testid={`delete-btn-${card.id}`}
                    >
                      <Trash2 className="w-4 h-4" />
                      Delete
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <div className="col-span-full text-center py-12">
                <CreditCard className="w-12 h-12 text-slate-300 dark:text-slate-700 mx-auto mb-4" />
                <p className="text-slate-500 dark:text-slate-400">No RFID cards configured yet</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* User Create/Edit Modal */}
      {showUserModal && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50" onClick={() => setShowUserModal(false)}>
          <div className="bg-white dark:bg-slate-900 rounded-xl p-6 max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>
                {editingUser ? 'Edit User' : 'Create User'}
              </h3>
              <button onClick={() => setShowUserModal(false)} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <form onSubmit={handleSaveUser} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Full Name</label>
                <input
                  type="text"
                  required
                  value={userForm.name}
                  onChange={(e) => setUserForm({...userForm, name: e.target.value})}
                  className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                  placeholder="John Doe"
                  data-testid="user-name-input"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-2">Email</label>
                <input
                  type="email"
                  required
                  value={userForm.email}
                  onChange={(e) => setUserForm({...userForm, email: e.target.value})}
                  className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                  placeholder="john@example.com"
                  data-testid="user-email-input"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-2">
                  Password {editingUser && <span className="text-slate-400">(leave blank to keep current)</span>}
                </label>
                <input
                  type="password"
                  required={!editingUser}
                  value={userForm.password}
                  onChange={(e) => setUserForm({...userForm, password: e.target.value})}
                  className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                  placeholder="••••••••"
                  data-testid="user-password-input"
                />
              </div>
              
              {!editingUser && (
                <div>
                  <label className="block text-sm font-medium mb-2">Role</label>
                  <select
                    value={userForm.role}
                    onChange={(e) => setUserForm({...userForm, role: e.target.value})}
                    className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                    data-testid="user-role-select"
                  >
                    <option value="admin">Admin</option>
                    <option value="user">User</option>
                    <option value="viewer">Viewer</option>
                  </select>
                </div>
              )}
              
              <div className="flex gap-2 pt-2">
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-md transition-colors font-medium"
                  data-testid="save-user-btn"
                >
                  {editingUser ? 'Update' : 'Create'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowUserModal(false)}
                  className="flex-1 px-4 py-2 border border-slate-300 dark:border-slate-700 rounded-md hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors font-medium"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* RFID Card Create/Edit Modal */}
      {showCardModal && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50" onClick={() => setShowCardModal(false)}>
          <div className="bg-white dark:bg-slate-900 rounded-xl p-6 max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>
                {editingCard ? 'Edit RFID Card' : 'Add RFID Card'}
              </h3>
              <button onClick={() => setShowCardModal(false)} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <form onSubmit={handleSaveCard} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Card Number</label>
                <input
                  type="text"
                  required
                  value={cardForm.card_number}
                  onChange={(e) => setCardForm({...cardForm, card_number: e.target.value.toUpperCase()})}
                  className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm font-mono"
                  placeholder="RFID-001-2024"
                  data-testid="card-number-input"
                />
              </div>
              
              {!editingCard && (
                <>
                  <div>
                    <label className="block text-sm font-medium mb-2">Assign to User</label>
                    <select
                      required
                      value={cardForm.user_id}
                      onChange={(e) => setCardForm({...cardForm, user_id: e.target.value})}
                      className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                      data-testid="user-select"
                    >
                      {users.map(user => (
                        <option key={user.id} value={user.id}>{user.name} ({user.email})</option>
                      ))}
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium mb-2">Initial Balance (COP)</label>
                    <input
                      type="number"
                      min="0"
                      step="1000"
                      value={cardForm.balance}
                      onChange={(e) => setCardForm({...cardForm, balance: parseFloat(e.target.value) || 0})}
                      className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                      data-testid="balance-input"
                    />
                  </div>
                </>
              )}
              
              <div>
                <label className="block text-sm font-medium mb-2">Status</label>
                <select
                  value={cardForm.status}
                  onChange={(e) => setCardForm({...cardForm, status: e.target.value})}
                  className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                  data-testid="status-select"
                >
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                  <option value="blocked">Blocked</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-2">Low Balance Alert Threshold (COP)</label>
                <input
                  type="number"
                  min="0"
                  step="1000"
                  value={cardForm.low_balance_threshold}
                  onChange={(e) => setCardForm({...cardForm, low_balance_threshold: parseFloat(e.target.value) || 10000})}
                  className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                  data-testid="threshold-input"
                />
                <p className="text-xs text-slate-500 mt-1">Email notification sent when balance falls below this amount</p>
              </div>
              
              <div className="flex gap-2 pt-2">
                <button type="submit" className="flex-1 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-md transition-colors font-medium">
                  {editingCard ? 'Update' : 'Create'}
                </button>
                <button type="button" onClick={() => setShowCardModal(false)} className="flex-1 px-4 py-2 border border-slate-300 dark:border-slate-700 rounded-md hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors font-medium">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Top Up Modal with PayU */}
      {showTopUpModal && topUpCard && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50 overflow-y-auto" onClick={() => setShowTopUpModal(false)}>
          <div className="bg-white dark:bg-slate-900 rounded-xl p-6 max-w-lg w-full mx-4 my-8" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>
                Top Up RFID Card
              </h3>
              <button onClick={() => setShowTopUpModal(false)} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="mb-4 p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
              <div className="flex items-center gap-3 mb-2">
                <CreditCard className="w-5 h-5 text-purple-600" />
                <span className="font-mono font-bold">{topUpCard.card_number}</span>
              </div>
              <p className="text-sm text-slate-600 dark:text-slate-400">{topUpCard.user_name}</p>
              <p className="text-lg font-bold text-emerald-600 mt-2">
                Current Balance: {formatCOP(topUpCard.balance)}
              </p>
            </div>
            
            {/* Method Selection */}
            <div className="flex gap-2 mb-4">
              <button
                onClick={() => { setTopUpMethod('manual'); setPayuFormData(null); }}
                className={`flex-1 px-3 py-2 text-sm font-medium rounded-md border transition-colors ${
                  topUpMethod === 'manual'
                    ? 'bg-orange-600 text-white border-orange-600'
                    : 'bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-700'
                }`}
              >
                Manual Top-Up
              </button>
              <button
                onClick={() => setTopUpMethod('payu')}
                className={`flex-1 px-3 py-2 text-sm font-medium rounded-md border transition-colors ${
                  topUpMethod === 'payu'
                    ? 'bg-orange-600 text-white border-orange-600'
                    : 'bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-700'
                }`}
              >
                PayU Online
              </button>
            </div>
            
            {topUpMethod === 'manual' ? (
              <form onSubmit={handleManualTopUp} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Amount (COP)</label>
                  <input
                    type="number"
                    min="1000"
                    step="1000"
                    required
                    value={topUpAmount}
                    onChange={(e) => setTopUpAmount(e.target.value)}
                    className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                    data-testid="topup-amount-input"
                  />
                </div>
                
                <div className="grid grid-cols-3 gap-2">
                  {presetAmounts.map(amount => (
                    <button
                      key={amount}
                      type="button"
                      onClick={() => setTopUpAmount(amount.toString())}
                      className={`px-3 py-2 text-sm font-medium rounded-md border transition-colors ${
                        topUpAmount === amount.toString()
                          ? 'bg-orange-600 text-white border-orange-600'
                          : 'bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-700 hover:border-orange-400'
                      }`}
                    >
                      {formatCOP(amount)}
                    </button>
                  ))}
                </div>
                
                {topUpAmount && (
                  <div className="p-3 bg-emerald-50 dark:bg-emerald-950/30 rounded-lg">
                    <p className="text-sm text-emerald-700 dark:text-emerald-400">
                      New Balance: <span className="font-bold">{formatCOP(topUpCard.balance + parseFloat(topUpAmount || 0))}</span>
                    </p>
                  </div>
                )}
                
                <button type="submit" className="w-full px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md transition-colors font-medium">
                  Confirm Manual Top Up
                </button>
              </form>
            ) : (
              <div className="space-y-4">
                {!payuFormData ? (
                  <>
                    <div>
                      <label className="block text-sm font-medium mb-2">Amount (COP) - Min $10,000</label>
                      <input
                        type="number"
                        min="10000"
                        step="1000"
                        value={topUpAmount}
                        onChange={(e) => setTopUpAmount(e.target.value)}
                        className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                      />
                    </div>
                    
                    <div className="grid grid-cols-3 gap-2">
                      {[50000, 100000, 200000].map(amount => (
                        <button
                          key={amount}
                          type="button"
                          onClick={() => setTopUpAmount(amount.toString())}
                          className={`px-3 py-2 text-sm font-medium rounded-md border transition-colors ${
                            topUpAmount === amount.toString()
                              ? 'bg-orange-600 text-white border-orange-600'
                              : 'bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-700'
                          }`}
                        >
                          {formatCOP(amount)}
                        </button>
                      ))}
                    </div>
                    
                    <div className="space-y-3">
                      <p className="text-sm font-medium text-slate-700 dark:text-slate-300">Buyer Information</p>
                      <input
                        type="text"
                        placeholder="Full Name"
                        value={buyerInfo.name}
                        onChange={(e) => setBuyerInfo({...buyerInfo, name: e.target.value})}
                        className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                      />
                      <input
                        type="email"
                        placeholder="Email"
                        value={buyerInfo.email}
                        onChange={(e) => setBuyerInfo({...buyerInfo, email: e.target.value})}
                        className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                      />
                      <input
                        type="tel"
                        placeholder="Phone (+57 300 1234567)"
                        value={buyerInfo.phone}
                        onChange={(e) => setBuyerInfo({...buyerInfo, phone: e.target.value})}
                        className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                      />
                    </div>
                    
                    <button
                      onClick={initiatePayUTopUp}
                      className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors font-medium"
                    >
                      <ExternalLink className="w-4 h-4" />
                      Proceed to PayU Checkout
                    </button>
                    
                    <p className="text-xs text-slate-500 text-center">
                      You will be redirected to PayU&apos;s secure payment page (Sandbox Mode)
                    </p>
                  </>
                ) : (
                  <div className="space-y-4">
                    <div className="p-4 bg-blue-50 dark:bg-blue-950/30 rounded-lg">
                      <p className="text-sm text-blue-700 dark:text-blue-400 font-medium mb-2">Payment Ready!</p>
                      <p className="text-sm text-slate-600 dark:text-slate-400">
                        Reference: <span className="font-mono">{payuFormData.reference_code}</span>
                      </p>
                      <p className="text-sm text-slate-600 dark:text-slate-400">
                        Amount: <span className="font-bold">{formatCOP(parseFloat(topUpAmount))}</span>
                      </p>
                    </div>
                    
                    <form action={payuFormData.payu_url} method="POST" target="_blank">
                      {Object.entries(payuFormData.form_data).map(([key, value]) => (
                        <input key={key} type="hidden" name={key} value={value} />
                      ))}
                      <button
                        type="submit"
                        className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-green-600 hover:bg-green-700 text-white rounded-md transition-colors font-medium"
                      >
                        <ExternalLink className="w-4 h-4" />
                        Open PayU Checkout
                      </button>
                    </form>
                    
                    <p className="text-xs text-slate-500 text-center">
                      After payment, balance will be updated automatically via webhook
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* History Modal */}
      {showHistoryModal && historyCard && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50" onClick={() => setShowHistoryModal(false)}>
          <div className="bg-white dark:bg-slate-900 rounded-xl p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>
                Transaction History - {historyCard.card_number}
              </h3>
              <button onClick={() => setShowHistoryModal(false)} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="overflow-y-auto flex-1">
              {cardHistory.length > 0 ? (
                <div className="space-y-3">
                  {cardHistory.map((entry) => (
                    <div key={entry.id} className={`p-4 rounded-lg border ${
                      entry.type === 'topup' 
                        ? 'bg-emerald-50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-800'
                        : 'bg-rose-50 dark:bg-rose-950/20 border-rose-200 dark:border-rose-800'
                    }`}>
                      <div className="flex items-start justify-between">
                        <div>
                          <p className={`font-semibold ${entry.type === 'topup' ? 'text-emerald-700 dark:text-emerald-400' : 'text-rose-700 dark:text-rose-400'}`}>
                            {entry.type === 'topup' ? '+' : ''}{formatCOP(entry.amount)}
                          </p>
                          <p className="text-sm text-slate-600 dark:text-slate-400">{entry.description}</p>
                        </div>
                        <div className="text-right text-sm">
                          <p className="text-slate-500 dark:text-slate-400">
                            {new Date(entry.created_at).toLocaleString()}
                          </p>
                          <p className="text-xs text-slate-400">
                            Balance: {formatCOP(entry.balance_before)} → {formatCOP(entry.balance_after)}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <History className="w-12 h-12 text-slate-300 dark:text-slate-700 mx-auto mb-4" />
                  <p className="text-slate-500 dark:text-slate-400">No transaction history yet</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Role Permissions Info */}
      {activeTab === 'users' && (
        <div className="bg-slate-50 dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
          <h3 className="text-lg font-bold mb-3" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Role Permissions
          </h3>
          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <Shield className="w-5 h-5 text-indigo-600 dark:text-indigo-400 mt-0.5" />
              <div>
                <p className="font-semibold text-sm text-slate-900 dark:text-slate-100">Admin</p>
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  Full access: Manage users, RFID cards, chargers, transactions, and invoicing
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Shield className="w-5 h-5 text-emerald-600 dark:text-emerald-400 mt-0.5" />
              <div>
                <p className="font-semibold text-sm text-slate-900 dark:text-slate-100">User</p>
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  View, import, export transactions and start/stop charging sessions
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Shield className="w-5 h-5 text-slate-600 dark:text-slate-400 mt-0.5" />
              <div>
                <p className="font-semibold text-sm text-slate-900 dark:text-slate-100">Viewer</p>
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  Read-only: View transactions and reports only
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Import Users Modal */}
      {showImportModal && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50" onClick={() => setShowImportModal(false)}>
          <div className="bg-white dark:bg-slate-900 rounded-xl p-6 max-w-lg w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>
                Import Users
              </h3>
              <button onClick={() => setShowImportModal(false)} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded" data-testid="close-import-modal">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            {/* File Upload Area */}
            <div 
              className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                importFile 
                  ? 'border-emerald-400 bg-emerald-50 dark:bg-emerald-950/20' 
                  : 'border-slate-300 dark:border-slate-700 hover:border-orange-400 hover:bg-orange-50 dark:hover:bg-orange-950/20'
              }`}
              onClick={() => fileInputRef.current?.click()}
              data-testid="import-dropzone"
            >
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileSelect}
                accept=".xlsx,.xls,.csv"
                className="hidden"
                data-testid="import-file-input"
              />
              {importFile ? (
                <div className="flex flex-col items-center gap-2">
                  <FileSpreadsheet className="w-12 h-12 text-emerald-600 dark:text-emerald-400" />
                  <p className="font-medium text-slate-900 dark:text-slate-100">{importFile.name}</p>
                  <p className="text-sm text-slate-500">Click to change file</p>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-2">
                  <Upload className="w-12 h-12 text-slate-400" />
                  <p className="font-medium text-slate-700 dark:text-slate-300">Click to select file</p>
                  <p className="text-sm text-slate-500">Excel (.xlsx, .xls) or CSV</p>
                </div>
              )}
            </div>

            {/* Required Format Info */}
            <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-950/20 rounded-lg border border-blue-200 dark:border-blue-800">
              <h4 className="font-semibold text-sm text-blue-700 dark:text-blue-400 mb-2">Required Excel Format</h4>
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-blue-200 dark:border-blue-700">
                    <th className="text-left py-1 text-blue-600 dark:text-blue-400">Name</th>
                    <th className="text-left py-1 text-blue-600 dark:text-blue-400">Email</th>
                    <th className="text-left py-1 text-blue-600 dark:text-blue-400">Role</th>
                    <th className="text-left py-1 text-blue-600 dark:text-blue-400">Group</th>
                  </tr>
                </thead>
                <tbody className="text-slate-600 dark:text-slate-400">
                  <tr>
                    <td className="py-1">John Doe</td>
                    <td className="py-1">john@example.com</td>
                    <td className="py-1">user</td>
                    <td className="py-1">Premium</td>
                  </tr>
                  <tr>
                    <td className="py-1">Jane Smith</td>
                    <td className="py-1">jane@example.com</td>
                    <td className="py-1">admin</td>
                    <td className="py-1"></td>
                  </tr>
                </tbody>
              </table>
              <p className="text-xs text-blue-600 dark:text-blue-400 mt-2">
                * Role (admin/user/viewer) and Group columns are optional. Default password: ChangeMeNow123!
              </p>
            </div>

            {/* Import Result */}
            {importResult && (
              <div className={`mt-4 p-4 rounded-lg ${
                importResult.errors.length > 0 && importResult.imported === 0
                  ? 'bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-800'
                  : importResult.errors.length > 0
                  ? 'bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800'
                  : 'bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800'
              }`}>
                <div className="flex items-start gap-3">
                  {importResult.imported > 0 ? (
                    <CheckCircle className="w-5 h-5 text-emerald-600 dark:text-emerald-400 mt-0.5" />
                  ) : (
                    <AlertCircle className="w-5 h-5 text-rose-600 dark:text-rose-400 mt-0.5" />
                  )}
                  <div>
                    <p className="font-semibold text-sm">
                      {importResult.imported > 0 ? 'Import Completed' : 'Import Failed'}
                    </p>
                    <ul className="text-sm mt-1 space-y-0.5">
                      <li className="text-emerald-700 dark:text-emerald-400">✓ {importResult.imported} users imported</li>
                      {importResult.skipped > 0 && (
                        <li className="text-slate-600 dark:text-slate-400">→ {importResult.skipped} skipped (duplicates)</li>
                      )}
                      {importResult.errors.length > 0 && (
                        <li className="text-rose-700 dark:text-rose-400">✗ {importResult.errors.length} errors</li>
                      )}
                    </ul>
                    {importResult.errors.length > 0 && importResult.errors.length <= 5 && (
                      <div className="mt-2 text-xs text-rose-600 dark:text-rose-400">
                        {importResult.errors.map((err, i) => (
                          <p key={i}>Row {err.row}: {err.message}</p>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-2 mt-4">
              <button
                onClick={handleImportUsers}
                disabled={!importFile || importing}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white rounded-md transition-colors font-medium"
                data-testid="confirm-import-btn"
              >
                {importing ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Importing...
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4" />
                    Import Users
                  </>
                )}
              </button>
              <button
                onClick={() => setShowImportModal(false)}
                className="flex-1 px-4 py-2 border border-slate-300 dark:border-slate-700 rounded-md hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors font-medium"
                data-testid="cancel-import-btn"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Users;
