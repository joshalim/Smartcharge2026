import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Users, Plus, Edit, Trash2, X, DollarSign, UserPlus, UserMinus, GripVertical, Search } from 'lucide-react';
import { formatCOP } from '../utils/currency';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragOverlay,
  useDroppable,
} from '@dnd-kit/core';
import {
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Droppable Zone Component
function DroppableZone({ id, children, isOver, isEmpty, emptyMessage }) {
  const { setNodeRef } = useDroppable({ id });
  
  return (
    <div
      ref={setNodeRef}
      className={`flex-1 overflow-y-auto p-3 rounded-lg border-2 border-dashed transition-colors min-h-[200px] ${
        isOver
          ? 'border-orange-400 bg-orange-50/50 dark:bg-orange-950/20'
          : 'border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50'
      }`}
      data-testid={`${id}-panel`}
    >
      {children ? (
        <div className="space-y-2">{children}</div>
      ) : (
        <div className="flex items-center justify-center h-full text-sm text-slate-500 dark:text-slate-400">
          {emptyMessage}
        </div>
      )}
    </div>
  );
}

// Draggable User Card Component
function DraggableUserCard({ user, isInGroup, onAction }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: user.id, data: { user, isInGroup } });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`flex items-center justify-between p-3 rounded-lg cursor-grab active:cursor-grabbing ${
        isInGroup 
          ? 'bg-purple-50 dark:bg-purple-950/30 border border-purple-200 dark:border-purple-800' 
          : 'bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700'
      }`}
      data-testid={`user-card-${user.id}`}
    >
      <div className="flex items-center gap-3">
        <div
          {...attributes}
          {...listeners}
          className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
        >
          <GripVertical className="w-4 h-4" />
        </div>
        <div className="w-8 h-8 rounded-full bg-orange-100 dark:bg-orange-900/50 flex items-center justify-center text-orange-600 dark:text-orange-400 text-sm font-semibold">
          {user.name?.charAt(0).toUpperCase() || '?'}
        </div>
        <div>
          <p className="font-medium text-slate-900 dark:text-slate-100 text-sm">{user.name}</p>
          <p className="text-xs text-slate-500 dark:text-slate-400">{user.email}</p>
        </div>
      </div>
      <button
        onClick={() => onAction(user)}
        className={`flex items-center gap-1 px-2 py-1 text-xs rounded-md transition-colors ${
          isInGroup
            ? 'bg-rose-100 dark:bg-rose-950/30 text-rose-600 dark:text-rose-400 hover:bg-rose-200'
            : 'bg-emerald-100 dark:bg-emerald-950/30 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-200'
        }`}
        data-testid={isInGroup ? `remove-user-${user.id}` : `add-user-${user.id}`}
      >
        {isInGroup ? <UserMinus className="w-3 h-3" /> : <UserPlus className="w-3 h-3" />}
        {isInGroup ? 'Remove' : 'Add'}
      </button>
    </div>
  );
}

// User Card Overlay for dragging
function UserCardOverlay({ user }) {
  return (
    <div className="flex items-center gap-3 p-3 rounded-lg bg-white dark:bg-slate-800 border-2 border-orange-500 shadow-lg">
      <GripVertical className="w-4 h-4 text-slate-400" />
      <div className="w-8 h-8 rounded-full bg-orange-100 dark:bg-orange-900/50 flex items-center justify-center text-orange-600 dark:text-orange-400 text-sm font-semibold">
        {user.name?.charAt(0).toUpperCase() || '?'}
      </div>
      <div>
        <p className="font-medium text-slate-900 dark:text-slate-100 text-sm">{user.name}</p>
        <p className="text-xs text-slate-500 dark:text-slate-400">{user.email}</p>
      </div>
    </div>
  );
}

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
  const [searchTerm, setSearchTerm] = useState('');
  const [activeId, setActiveId] = useState(null);
  const [activeUser, setActiveUser] = useState(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor)
  );

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
    if (!window.confirm('Are you sure you want to delete this pricing group? Users in this group will be unassigned.')) return;
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
    setSearchTerm('');
    try {
      const usersInGroup = await axios.get(`${API}/pricing-groups/${group.id}/users`);
      setGroupUsers(usersInGroup.data);
      
      // Filter users not in this group
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
      
      // Optimistic update
      const movedUser = availableUsers.find(u => u.id === userId);
      if (movedUser) {
        setGroupUsers(prev => [...prev, { ...movedUser, pricing_group_id: selectedGroup.id }]);
        setAvailableUsers(prev => prev.filter(u => u.id !== userId));
      }
      fetchData(); // Refresh to update counts
    } catch (error) {
      console.error('Failed to assign user:', error);
      alert(error.response?.data?.detail || 'Failed to assign user');
      // Revert on error
      const usersInGroup = await axios.get(`${API}/pricing-groups/${selectedGroup.id}/users`);
      setGroupUsers(usersInGroup.data);
    }
  };

  const removeUser = async (userId) => {
    try {
      await axios.delete(`${API}/pricing-groups/${selectedGroup.id}/users/${userId}`);
      
      // Optimistic update
      const removedUser = groupUsers.find(u => u.id === userId);
      setGroupUsers(prev => prev.filter(u => u.id !== userId));
      if (removedUser) {
        setAvailableUsers(prev => [...prev, { ...removedUser, pricing_group_id: null }]);
      }
      fetchData(); // Refresh to update counts
    } catch (error) {
      console.error('Failed to remove user:', error);
      alert(error.response?.data?.detail || 'Failed to remove user');
    }
  };

  // DnD Handlers
  const handleDragStart = (event) => {
    const { active } = event;
    setActiveId(active.id);
    const userData = active.data.current?.user;
    setActiveUser(userData);
  };

  const handleDragEnd = async (event) => {
    const { active, over } = event;
    setActiveId(null);
    setActiveUser(null);

    if (!over) return;

    const isFromGroup = active.data.current?.isInGroup;
    const overArea = over.id;

    // Dropped in same area - do nothing
    if ((isFromGroup && overArea === 'group-users-drop') || 
        (!isFromGroup && overArea === 'available-users-drop')) {
      return;
    }

    // Moving from available to group
    if (!isFromGroup && overArea === 'group-users-drop') {
      await assignUser(active.id);
    }
    
    // Moving from group to available
    if (isFromGroup && overArea === 'available-users-drop') {
      await removeUser(active.id);
    }
  };

  // Filter users based on search
  const filteredGroupUsers = groupUsers.filter(u => 
    u.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    u.email?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const filteredAvailableUsers = availableUsers.filter(u => 
    u.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    u.email?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96" data-testid="loading-spinner">
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
              data-testid={`group-card-${group.id}`}
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
                  {group.user_count || 0} users
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
              data-testid="create-first-group-btn"
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
            Drag and drop users to assign them to the group - each user can belong to only one group
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
              <button onClick={() => setShowGroupModal(false)} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded" data-testid="close-group-modal">
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
                  data-testid="cancel-group-btn"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* User Management Modal with Drag & Drop */}
      {showUserModal && selectedGroup && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50" onClick={() => setShowUserModal(false)}>
          <div className="bg-white dark:bg-slate-900 rounded-xl p-6 max-w-4xl w-full mx-4 max-h-[85vh] overflow-hidden flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>
                  Manage Users - {selectedGroup.name}
                </h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  Drag users between panels or use buttons to assign/remove
                </p>
              </div>
              <button onClick={() => setShowUserModal(false)} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded" data-testid="close-user-modal">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Search */}
            <div className="relative mb-4">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search users by name or email..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full h-10 pl-10 pr-4 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm"
                data-testid="user-search-input"
              />
            </div>
            
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragStart={handleDragStart}
              onDragEnd={handleDragEnd}
            >
              <div className="flex-1 overflow-hidden grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Users in Group */}
                <div className="flex flex-col">
                  <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2 flex items-center gap-2">
                    <Users className="w-4 h-4 text-purple-600" />
                    In Group ({filteredGroupUsers.length})
                  </h4>
                  <DroppableZone
                    id="group-users-drop"
                    isOver={activeId && !groupUsers.find(u => u.id === activeId)}
                    emptyMessage={searchTerm ? 'No matching users in group' : 'Drop users here to add to group'}
                  >
                    {filteredGroupUsers.length > 0 && filteredGroupUsers.map((user) => (
                      <DraggableUserCard
                        key={user.id}
                        user={user}
                        isInGroup={true}
                        onAction={() => removeUser(user.id)}
                      />
                    ))}
                  </DroppableZone>
                </div>
                
                {/* Available Users */}
                <div className="flex flex-col">
                  <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2 flex items-center gap-2">
                    <UserPlus className="w-4 h-4 text-emerald-600" />
                    Available ({filteredAvailableUsers.length})
                  </h4>
                  <DroppableZone
                    id="available-users-drop"
                    isOver={activeId && groupUsers.find(u => u.id === activeId)}
                    emptyMessage={searchTerm ? 'No matching available users' : 'All users are assigned to groups'}
                  >
                    {filteredAvailableUsers.length > 0 && filteredAvailableUsers.map((user) => (
                      <DraggableUserCard
                        key={user.id}
                        user={user}
                        isInGroup={false}
                        onAction={() => assignUser(user.id)}
                      />
                    ))}
                  </DroppableZone>
                </div>
              </div>

              <DragOverlay>
                {activeUser ? <UserCardOverlay user={activeUser} /> : null}
              </DragOverlay>
            </DndContext>

            {/* Instructions */}
            <div className="mt-4 p-3 bg-amber-50 dark:bg-amber-950/20 rounded-lg border border-amber-200 dark:border-amber-800">
              <p className="text-xs text-amber-700 dark:text-amber-400">
                <strong>Tip:</strong> Drag users between panels or click the Add/Remove buttons. Users in other groups will be reassigned.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default PricingGroups;
