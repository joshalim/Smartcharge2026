import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Users as UsersIcon, Trash2, Shield, CreditCard, Plus, X, DollarSign, Edit, Power } from 'lucide-react';
import { formatCOP } from '../utils/currency';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function Users() {
  const [users, setUsers] = useState([]);
  const [rfidCards, setRfidCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('users');
  
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
      case 'admin':
        return 'bg-indigo-100 dark:bg-indigo-950/30 text-indigo-700 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800';
      case 'user':
        return 'bg-emerald-100 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800';
      case 'viewer':
        return 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700';
      default:
        return 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700';
    }
  };

  const getStatusBadgeClass = (status) => {
    switch (status) {
      case 'active':
        return 'bg-emerald-100 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-400';
      case 'inactive':
        return 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400';
      case 'blocked':
        return 'bg-rose-100 dark:bg-rose-950/30 text-rose-700 dark:text-rose-400';
      default:
        return 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400';
    }
  };

  // RFID Card Functions
  const openCreateCard = () => {
    setEditingCard(null);
    setCardForm({
      card_number: '',
      user_id: users.length > 0 ? users[0].id : '',
      balance: 0,
      status: 'active'
    });
    setShowCardModal(true);
  };

  const openEditCard = (card) => {
    setEditingCard(card);
    setCardForm({
      card_number: card.card_number,
      user_id: card.user_id,
      balance: card.balance,
      status: card.status
    });
    setShowCardModal(true);
  };

  const handleSaveCard = async (e) => {
    e.preventDefault();
    try {
      if (editingCard) {
        await axios.patch(`${API}/rfid-cards/${editingCard.id}`, {
          card_number: cardForm.card_number,
          status: cardForm.status
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

  const openTopUp = (card) => {
    setTopUpCard(card);
    setTopUpAmount('');
    setShowTopUpModal(true);
  };

  const handleTopUp = async (e) => {
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
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-12" data-testid="users-loading">
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
                      <tr
                        key={user.id}
                        className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                        data-testid="user-row"
                      >
                        <td className="py-4 px-6 text-sm font-medium text-slate-900 dark:text-slate-100">{user.name}</td>
                        <td className="py-4 px-6 text-sm text-slate-600 dark:text-slate-400">{user.email}</td>
                        <td className="py-4 px-6">
                          <select
                            value={user.role}
                            onChange={(e) => updateRole(user.id, e.target.value)}
                            className={`px-3 py-1 rounded-full text-xs font-semibold border ${getRoleBadgeClass(user.role)}`}
                            data-testid="role-select"
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
                          <button
                            onClick={() => deleteUser(user.id)}
                            className="p-2 text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30 rounded transition-colors"
                            data-testid="delete-user-btn"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-12" data-testid="no-users">
              <UsersIcon className="w-12 h-12 text-slate-300 dark:text-slate-700 mx-auto mb-4" />
              <p className="text-slate-500 dark:text-slate-400">No users found</p>
            </div>
          )}
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

                  <div className="flex gap-2">
                    <button
                      onClick={() => openTopUp(card)}
                      className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm bg-emerald-50 dark:bg-emerald-950/30 text-emerald-600 dark:text-emerald-400 rounded-md hover:bg-emerald-100 dark:hover:bg-emerald-950/50 transition-colors font-medium"
                      data-testid={`topup-btn-${card.id}`}
                    >
                      <DollarSign className="w-4 h-4" />
                      Top Up
                    </button>
                    <button
                      onClick={() => openEditCard(card)}
                      className="flex items-center justify-center gap-2 px-3 py-2 text-sm bg-blue-50 dark:bg-blue-950/30 text-blue-600 dark:text-blue-400 rounded-md hover:bg-blue-100 dark:hover:bg-blue-950/50 transition-colors"
                      data-testid={`edit-btn-${card.id}`}
                    >
                      <Edit className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => deleteCard(card.id)}
                      className="flex items-center justify-center gap-2 px-3 py-2 text-sm bg-rose-50 dark:bg-rose-950/30 text-rose-600 dark:text-rose-400 rounded-md hover:bg-rose-100 dark:hover:bg-rose-950/50 transition-colors"
                      data-testid={`delete-btn-${card.id}`}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <div className="col-span-full text-center py-12">
                <CreditCard className="w-12 h-12 text-slate-300 dark:text-slate-700 mx-auto mb-4" />
                <p className="text-slate-500 dark:text-slate-400">No RFID cards configured yet</p>
                <p className="text-sm text-slate-400 dark:text-slate-500 mt-2">
                  Add RFID cards to enable contactless charging
                </p>
              </div>
            )}
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
                  Full access: View, import, export, delete transactions, manage users and RFID cards
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Shield className="w-5 h-5 text-emerald-600 dark:text-emerald-400 mt-0.5" />
              <div>
                <p className="font-semibold text-sm text-slate-900 dark:text-slate-100">User</p>
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  Can view, import, and export transactions
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Shield className="w-5 h-5 text-slate-600 dark:text-slate-400 mt-0.5" />
              <div>
                <p className="font-semibold text-sm text-slate-900 dark:text-slate-100">Viewer</p>
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  Read-only access: Can only view transactions and reports
                </p>
              </div>
            </div>
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
                      placeholder="0"
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
              
              <div className="flex gap-2 pt-2">
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-md transition-colors font-medium"
                  data-testid="save-card-btn"
                >
                  {editingCard ? 'Update' : 'Create'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowCardModal(false)}
                  className="flex-1 px-4 py-2 border border-slate-300 dark:border-slate-700 rounded-md hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors font-medium"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Top Up Modal */}
      {showTopUpModal && topUpCard && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50" onClick={() => setShowTopUpModal(false)}>
          <div className="bg-white dark:bg-slate-900 rounded-xl p-6 max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>
                Top Up RFID Card
              </h3>
              <button onClick={() => setShowTopUpModal(false)} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="mb-6 p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
              <div className="flex items-center gap-3 mb-2">
                <CreditCard className="w-5 h-5 text-purple-600" />
                <span className="font-mono font-bold">{topUpCard.card_number}</span>
              </div>
              <p className="text-sm text-slate-600 dark:text-slate-400">{topUpCard.user_name}</p>
              <p className="text-lg font-bold text-emerald-600 mt-2">
                Current Balance: {formatCOP(topUpCard.balance)}
              </p>
            </div>
            
            <form onSubmit={handleTopUp} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Top Up Amount (COP)</label>
                <input
                  type="number"
                  min="1000"
                  step="1000"
                  required
                  value={topUpAmount}
                  onChange={(e) => setTopUpAmount(e.target.value)}
                  className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                  placeholder="Enter amount"
                  data-testid="topup-amount-input"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-2">Quick Select</label>
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
                      data-testid={`preset-${amount}`}
                    >
                      {formatCOP(amount)}
                    </button>
                  ))}
                </div>
              </div>
              
              {topUpAmount && (
                <div className="p-3 bg-emerald-50 dark:bg-emerald-950/30 rounded-lg">
                  <p className="text-sm text-emerald-700 dark:text-emerald-400">
                    New Balance: <span className="font-bold">{formatCOP(topUpCard.balance + parseFloat(topUpAmount || 0))}</span>
                  </p>
                </div>
              )}
              
              <div className="flex gap-2 pt-2">
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md transition-colors font-medium"
                  data-testid="confirm-topup-btn"
                >
                  Confirm Top Up
                </button>
                <button
                  type="button"
                  onClick={() => setShowTopUpModal(false)}
                  className="flex-1 px-4 py-2 border border-slate-300 dark:border-slate-700 rounded-md hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors font-medium"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Users;
