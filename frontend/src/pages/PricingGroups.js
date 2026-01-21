import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Users, Plus, Edit, Trash2, X, DollarSign, UserPlus, UserMinus } from 'lucide-react';
import { formatCOP } from '../utils/currency';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function PricingGroups() {
  const [groups, setGroups] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Group Modal
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [editingGroup, setEditingGroup] = useState(null);
  const [groupForm, setGroupForm] = useState({
    name: '',
    description: '',
    connector_pricing: { CCS2: 2500, CHADEMO: 2000, J1772: 1500 }
  });
  
  // User Assignment Modal
  const [showUserModal, setShowUserModal] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [groupUsers, setGroupUsers] = useState([]);
  const [availableUsers, setAvailableUsers] = useState([]);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [groupsRes, usersRes] = await Promise.all([
        axios.get(`${API}/pricing-groups`),
        axios.get(`${API}/users`)
      ]);
      setGroups(groupsRes.data);
      setUsers(usersRes.data);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  const openCreateGroup = () => {
    setEditingGroup(null);
    setGroupForm({
      name: '',
      description: '',
      connector_pricing: { CCS2: 2500, CHADEMO: 2000, J1772: 1500 }
    });
    setShowGroupModal(true);
  };

  const openEditGroup = (group) => {
    setEditingGroup(group);
    setGroupForm({
      name: group.name,
      description: group.description || '',
      connector_pricing: group.connector_pricing || { CCS2: 2500, CHADEMO: 2000, J1772: 1500 }
    });
    setShowGroupModal(true);
  };

  const handleSaveGroup = async (e) => {
    e.preventDefault();
    try {
      if (editingGroup) {
        await axios.patch(`${API}/pricing-groups/${editingGroup.id}`, groupForm);
      } else {
        await axios.post(`${API}/pricing-groups`, groupForm);
      }
      setShowGroupModal(false);
      fetchData();
    } catch (error) {
      console.error('Failed to save group:', error);
      alert(error.response?.data?.detail || 'Failed to save group');
    }
  };

  const deleteGroup = async (groupId) => {
    if (!window.confirm('Are you sure you want to delete this pricing group?')) return;
    try {
      await axios.delete(`${API}/pricing-groups/${groupId}`);
      fetchData();
    } catch (error) {
      console.error('Failed to delete group:', error);
      alert(error.response?.data?.detail || 'Failed to delete group');
    }
  };

  const openUserManagement = async (group) => {
    setSelectedGroup(group);
    try {
      const usersInGroup = await axios.get(`${API}/pricing-groups/${group.id}/users`);
      setGroupUsers(usersInGroup.data);
      
      // Filter users not in any group or in different groups
      const usersNotInGroup = users.filter(u => 
        !u.pricing_group_id || u.pricing_group_id !== group.id
      );
      setAvailableUsers(usersNotInGroup);
      setShowUserModal(true);
    } catch (error) {
      console.error('Failed to fetch group users:', error);
    }
  };

  const assignUser = async (userId) => {
    try {
      await axios.post(`${API}/pricing-groups/${selectedGroup.id}/users/${userId}`);
      
      // Refresh data
      const usersInGroup = await axios.get(`${API}/pricing-groups/${selectedGroup.id}/users`);
      setGroupUsers(usersInGroup.data);
      setAvailableUsers(prev => prev.filter(u => u.id !== userId));
      fetchData(); // Refresh groups to update counts
    } catch (error) {
      console.error('Failed to assign user:', error);
      alert(error.response?.data?.detail || 'Failed to assign user');
    }
  };

  const removeUser = async (userId) => {
    try {
      await axios.delete(`${API}/pricing-groups/${selectedGroup.id}/users/${userId}`);
      
      // Refresh data
      const removedUser = groupUsers.find(u => u.id === userId);
      setGroupUsers(prev => prev.filter(u => u.id !== userId));
      if (removedUser) {
        setAvailableUsers(prev => [...prev, removedUser]);
      }
      fetchData(); // Refresh groups to update counts
    } catch (error) {
      console.error('Failed to remove user:', error);
      alert(error.response?.data?.detail || 'Failed to remove user');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" style={{ fontFamily: 'IBM Plex Sans, sans-serif' }}>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-4xl md:text-5xl font-black tracking-tight mb-2" style={{ fontFamily: 'Chivo, sans-serif' }} data-testid="pricing-groups-title">
            Pricing Groups
          </h1>
          <p className="text-slate-500 dark:text-slate-400">Create user groups with custom connector pricing</p>
        </div>
        <button
          onClick={openCreateGroup}
          className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-md transition-colors font-medium"
          data-testid="add-group-btn"
        >
          <Plus className="w-4 h-4" />
          Create Group
        </button>
      </div>

      {/* Groups Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {groups.length > 0 ? (
          groups.map((group) => (
            <div
              key={group.id}
              className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm hover:shadow-md transition-all"
              data-testid={`group-${group.id}`}
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">{group.name}</h3>
                  {group.description && (
                    <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{group.description}</p>
                  )}
                </div>
                <span className="px-2 py-1 bg-purple-100 dark:bg-purple-950/30 text-purple-700 dark:text-purple-400 rounded-full text-xs font-medium flex items-center gap-1">
                  <Users className="w-3 h-3" />
                  {group.user_count} users
                </span>
              </div>
              
              <div className="space-y-2 mb-4">
                <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Connector Pricing</p>
                <div className="grid grid-cols-3 gap-2">
                  <div className="p-2 bg-blue-50 dark:bg-blue-950/30 rounded-lg text-center">
                    <p className="text-xs text-blue-600 dark:text-blue-400 font-medium">CCS2</p>
                    <p className="text-sm font-bold text-slate-900 dark:text-slate-100">
                      {formatCOP(group.connector_pricing?.CCS2 || 2500)}/kWh
                    </p>
                  </div>
                  <div className="p-2 bg-emerald-50 dark:bg-emerald-950/30 rounded-lg text-center">
                    <p className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">CHADEMO</p>
                    <p className="text-sm font-bold text-slate-900 dark:text-slate-100">
                      {formatCOP(group.connector_pricing?.CHADEMO || 2000)}/kWh
                    </p>
                  </div>
                  <div className="p-2 bg-orange-50 dark:bg-orange-950/30 rounded-lg text-center">
                    <p className="text-xs text-orange-600 dark:text-orange-400 font-medium">J1772</p>
                    <p className="text-sm font-bold text-slate-900 dark:text-slate-100">
                      {formatCOP(group.connector_pricing?.J1772 || 1500)}/kWh
                    </p>
                  </div>
                </div>
              </div>
              
              <div className="flex gap-2">
                <button
                  onClick={() => openUserManagement(group)}
                  className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm bg-purple-50 dark:bg-purple-950/30 text-purple-600 dark:text-purple-400 rounded-md hover:bg-purple-100 dark:hover:bg-purple-950/50 transition-colors font-medium"
                  data-testid={`manage-users-btn-${group.id}`}
                >
                  <Users className="w-4 h-4" />
                  Manage Users
                </button>
                <button
                  onClick={() => openEditGroup(group)}
                  className="flex items-center justify-center gap-2 px-3 py-2 text-sm bg-blue-50 dark:bg-blue-950/30 text-blue-600 dark:text-blue-400 rounded-md hover:bg-blue-100 dark:hover:bg-blue-950/50 transition-colors"
                  data-testid={`edit-group-btn-${group.id}`}
                >
                  <Edit className="w-4 h-4" />
                </button>
                <button
                  onClick={() => deleteGroup(group.id)}
                  className="flex items-center justify-center gap-2 px-3 py-2 text-sm bg-rose-50 dark:bg-rose-950/30 text-rose-600 dark:text-rose-400 rounded-md hover:bg-rose-100 dark:hover:bg-rose-950/50 transition-colors"
                  data-testid={`delete-group-btn-${group.id}`}
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))
        ) : (
          <div className="col-span-full text-center py-12 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800">
            <DollarSign className="w-12 h-12 text-slate-300 dark:text-slate-700 mx-auto mb-4" />
            <h3 className="text-lg font-bold text-slate-700 dark:text-slate-300 mb-2">No Pricing Groups</h3>
            <p className="text-slate-500 dark:text-slate-400 mb-4">
              Create pricing groups to apply custom connector rates to users
            </p>
            <button
              onClick={openCreateGroup}
              className="inline-flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-md transition-colors font-medium"
            >
              <Plus className="w-4 h-4" />
              Create First Group
            </button>
          </div>
        )}
      </div>

      {/* Info Box */}
      <div className="bg-slate-50 dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
        <h3 className="text-lg font-bold mb-3" style={{ fontFamily: 'Chivo, sans-serif' }}>
          How Pricing Groups Work
        </h3>
        <ul className="space-y-2 text-sm text-slate-600 dark:text-slate-400">
          <li className="flex items-start gap-2">
            <span className="text-orange-600 font-bold">1.</span>
            Create a pricing group with custom rates per connector type (CCS2, CHADEMO, J1772)
          </li>
          <li className="flex items-start gap-2">
            <span className="text-orange-600 font-bold">2.</span>
            Assign users to the group - each user can belong to only one group
          </li>
          <li className="flex items-start gap-2">
            <span className="text-orange-600 font-bold">3.</span>
            When users charge, their group's pricing is automatically applied
          </li>
          <li className="flex items-start gap-2">
            <span className="text-orange-600 font-bold">4.</span>
            Users without a group use default connector pricing
          </li>
        </ul>
      </div>

      {/* Group Create/Edit Modal */}
      {showGroupModal && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50" onClick={() => setShowGroupModal(false)}>
          <div className="bg-white dark:bg-slate-900 rounded-xl p-6 max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>
                {editingGroup ? 'Edit Pricing Group' : 'Create Pricing Group'}
              </h3>
              <button onClick={() => setShowGroupModal(false)} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <form onSubmit={handleSaveGroup} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Group Name</label>
                <input
                  type="text"
                  required
                  value={groupForm.name}
                  onChange={(e) => setGroupForm({...groupForm, name: e.target.value})}
                  className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                  placeholder="e.g., Premium Users"
                  data-testid="group-name-input"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-2">Description (Optional)</label>
                <input
                  type="text"
                  value={groupForm.description}
                  onChange={(e) => setGroupForm({...groupForm, description: e.target.value})}
                  className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                  placeholder="e.g., Discounted rates for VIP customers"
                  data-testid="group-description-input"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-3">Connector Pricing (COP per kWh)</label>
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <span className="w-24 text-sm font-medium text-blue-600">CCS2</span>
                    <input
                      type="number"
                      min="0"
                      step="100"
                      value={groupForm.connector_pricing.CCS2}
                      onChange={(e) => setGroupForm({
                        ...groupForm, 
                        connector_pricing: {...groupForm.connector_pricing, CCS2: parseFloat(e.target.value) || 0}
                      })}
                      className="flex-1 h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                      data-testid="ccs2-price-input"
                    />
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="w-24 text-sm font-medium text-emerald-600">CHADEMO</span>
                    <input
                      type="number"
                      min="0"
                      step="100"
                      value={groupForm.connector_pricing.CHADEMO}
                      onChange={(e) => setGroupForm({
                        ...groupForm, 
                        connector_pricing: {...groupForm.connector_pricing, CHADEMO: parseFloat(e.target.value) || 0}
                      })}
                      className="flex-1 h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                      data-testid="chademo-price-input"
                    />
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="w-24 text-sm font-medium text-orange-600">J1772</span>
                    <input
                      type="number"
                      min="0"
                      step="100"
                      value={groupForm.connector_pricing.J1772}
                      onChange={(e) => setGroupForm({
                        ...groupForm, 
                        connector_pricing: {...groupForm.connector_pricing, J1772: parseFloat(e.target.value) || 0}
                      })}
                      className="flex-1 h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                      data-testid="j1772-price-input"
                    />
                  </div>
                </div>
              </div>
              
              <div className="flex gap-2 pt-2">
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-md transition-colors font-medium"
                  data-testid="save-group-btn"
                >
                  {editingGroup ? 'Update' : 'Create'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowGroupModal(false)}
                  className="flex-1 px-4 py-2 border border-slate-300 dark:border-slate-700 rounded-md hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors font-medium"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* User Management Modal */}
      {showUserModal && selectedGroup && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50" onClick={() => setShowUserModal(false)}>
          <div className="bg-white dark:bg-slate-900 rounded-xl p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>
                  Manage Users - {selectedGroup.name}
                </h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  {groupUsers.length} users in this group
                </p>
              </div>
              <button onClick={() => setShowUserModal(false)} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto space-y-4">
              {/* Users in Group */}
              <div>
                <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2 flex items-center gap-2">
                  <Users className="w-4 h-4 text-purple-600" />
                  Users in Group
                </h4>
                {groupUsers.length > 0 ? (
                  <div className="space-y-2">
                    {groupUsers.map((user) => (
                      <div key={user.id} className="flex items-center justify-between p-3 bg-purple-50 dark:bg-purple-950/30 rounded-lg">
                        <div>
                          <p className="font-medium text-slate-900 dark:text-slate-100">{user.name}</p>
                          <p className="text-sm text-slate-500 dark:text-slate-400">{user.email}</p>
                        </div>
                        <button
                          onClick={() => removeUser(user.id)}
                          className="flex items-center gap-1 px-3 py-1 text-sm bg-rose-100 dark:bg-rose-950/30 text-rose-600 dark:text-rose-400 rounded-md hover:bg-rose-200 dark:hover:bg-rose-950/50 transition-colors"
                        >
                          <UserMinus className="w-4 h-4" />
                          Remove
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-500 dark:text-slate-400 text-center py-4">
                    No users in this group yet
                  </p>
                )}
              </div>
              
              {/* Available Users */}
              <div>
                <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2 flex items-center gap-2">
                  <UserPlus className="w-4 h-4 text-emerald-600" />
                  Available Users
                </h4>
                {availableUsers.length > 0 ? (
                  <div className="space-y-2">
                    {availableUsers.map((user) => (
                      <div key={user.id} className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                        <div>
                          <p className="font-medium text-slate-900 dark:text-slate-100">{user.name}</p>
                          <p className="text-sm text-slate-500 dark:text-slate-400">{user.email}</p>
                          {user.pricing_group_id && (
                            <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">
                              Currently in another group
                            </p>
                          )}
                        </div>
                        <button
                          onClick={() => assignUser(user.id)}
                          className="flex items-center gap-1 px-3 py-1 text-sm bg-emerald-100 dark:bg-emerald-950/30 text-emerald-600 dark:text-emerald-400 rounded-md hover:bg-emerald-200 dark:hover:bg-emerald-950/50 transition-colors"
                        >
                          <UserPlus className="w-4 h-4" />
                          Add
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-500 dark:text-slate-400 text-center py-4">
                    All users are assigned to groups
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default PricingGroups;
