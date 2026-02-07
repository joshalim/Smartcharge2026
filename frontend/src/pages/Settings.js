import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Settings as SettingsIcon, CreditCard, Webhook, Mail, Save, TestTube, Eye, EyeOff, Check, X, AlertCircle, User, Key } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function Settings() {
  const { user, token } = useAuth();
  const [activeTab, setActiveTab] = useState('account');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [showApiKey, setShowApiKey] = useState({});
  const [message, setMessage] = useState(null);
  
  // Password Change
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [showPassword, setShowPassword] = useState({});
  
  // PayU Settings
  const [payuSettings, setPayuSettings] = useState({
    api_key: '',
    api_login: '',
    merchant_id: '',
    account_id: '',
    test_mode: true
  });
  
  // SendGrid Settings
  const [sendgridSettings, setSendgridSettings] = useState({
    api_key: '',
    sender_email: '',
    sender_name: 'EV Charging System',
    enabled: false
  });
  const [testEmail, setTestEmail] = useState('');
  
  // Invoice Webhook Settings
  const [webhookSettings, setWebhookSettings] = useState({
    webhook_url: '',
    api_key: '',
    enabled: false
  });

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    setLoading(true);
    try {
      const [payuRes, sendgridRes, webhookRes] = await Promise.all([
        axios.get(`${API}/settings/payu`),
        axios.get(`${API}/settings/sendgrid`),
        axios.get(`${API}/invoice-webhook/config`)
      ]);
      
      setPayuSettings(prev => ({ ...prev, ...payuRes.data }));
      setSendgridSettings(prev => ({ ...prev, ...sendgridRes.data }));
      setWebhookSettings(prev => ({ ...prev, ...webhookRes.data }));
    } catch (error) {
      console.error('Failed to fetch settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const showMessage = (type, text) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 5000);
  };

  const savePayuSettings = async () => {
    setSaving(true);
    try {
      await axios.post(`${API}/settings/payu`, payuSettings);
      showMessage('success', 'PayU settings saved successfully');
    } catch (error) {
      showMessage('error', error.response?.data?.detail || 'Failed to save PayU settings');
    } finally {
      setSaving(false);
    }
  };

  const saveSendgridSettings = async () => {
    setSaving(true);
    try {
      await axios.post(`${API}/settings/sendgrid`, sendgridSettings);
      showMessage('success', 'SendGrid settings saved successfully');
    } catch (error) {
      showMessage('error', error.response?.data?.detail || 'Failed to save SendGrid settings');
    } finally {
      setSaving(false);
    }
  };

  const testSendgridEmail = async () => {
    if (!testEmail) {
      showMessage('error', 'Please enter a test email address');
      return;
    }
    setTesting(true);
    try {
      const response = await axios.post(`${API}/settings/sendgrid/test?test_email=${encodeURIComponent(testEmail)}`);
      if (response.data.success) {
        showMessage('success', 'Test email sent successfully!');
      } else {
        showMessage('error', 'Failed to send test email');
      }
    } catch (error) {
      showMessage('error', error.response?.data?.detail || 'Failed to send test email');
    } finally {
      setTesting(false);
    }
  };

  const saveWebhookSettings = async () => {
    setSaving(true);
    try {
      await axios.post(`${API}/invoice-webhook/config`, webhookSettings);
      showMessage('success', 'Webhook settings saved successfully');
    } catch (error) {
      showMessage('error', error.response?.data?.detail || 'Failed to save webhook settings');
    } finally {
      setSaving(false);
    }
  };

  const testWebhook = async () => {
    setTesting(true);
    try {
      const response = await axios.post(`${API}/invoice-webhook/test`);
      if (response.data.success) {
        showMessage('success', `Webhook test successful! Status: ${response.data.status_code}`);
      } else {
        showMessage('error', `Webhook test failed. Status: ${response.data.status_code}`);
      }
    } catch (error) {
      showMessage('error', error.response?.data?.detail || 'Webhook test failed');
    } finally {
      setTesting(false);
    }
  };

  const changePassword = async () => {
    if (!passwordData.current_password || !passwordData.new_password) {
      showMessage('error', 'Please fill in all password fields');
      return;
    }
    if (passwordData.new_password !== passwordData.confirm_password) {
      showMessage('error', 'New passwords do not match');
      return;
    }
    if (passwordData.new_password.length < 6) {
      showMessage('error', 'New password must be at least 6 characters');
      return;
    }
    
    setSaving(true);
    try {
      await axios.post(`${API}/auth/change-password`, {
        current_password: passwordData.current_password,
        new_password: passwordData.new_password
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      showMessage('success', 'Password changed successfully!');
      setPasswordData({ current_password: '', new_password: '', confirm_password: '' });
    } catch (error) {
      showMessage('error', error.response?.data?.detail || 'Failed to change password');
    } finally {
      setSaving(false);
    }
  };

  const tabs = [
    { id: 'account', name: 'Account', icon: User },
    { id: 'payu', name: 'PayU Colombia', icon: CreditCard },
    { id: 'sendgrid', name: 'Email (SendGrid)', icon: Mail },
    { id: 'webhook', name: 'FullColombia', icon: Webhook },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" style={{ fontFamily: 'IBM Plex Sans, sans-serif' }}>
      <div>
        <h1 className="text-4xl md:text-5xl font-black tracking-tight mb-2" style={{ fontFamily: 'Chivo, sans-serif' }} data-testid="settings-title">
          Settings
        </h1>
        <p className="text-slate-500 dark:text-slate-400">Configure integrations and system settings</p>
      </div>

      {/* Message */}
      {message && (
        <div className={`p-4 rounded-lg flex items-center gap-3 ${
          message.type === 'success' 
            ? 'bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800'
            : 'bg-rose-50 dark:bg-rose-950/30 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-800'
        }`}>
          {message.type === 'success' ? <Check className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
          {message.text}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-200 dark:border-slate-800 overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
              activeTab === tab.id
                ? 'border-orange-600 text-orange-600'
                : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
            }`}
            data-testid={`tab-${tab.id}`}
          >
            <div className="flex items-center gap-2">
              <tab.icon className="w-4 h-4" />
              {tab.name}
            </div>
          </button>
        ))}
      </div>

      {/* Account Settings */}
      {activeTab === 'account' && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-3 bg-orange-50 dark:bg-orange-950/30 rounded-lg">
              <User className="w-6 h-6 text-orange-600 dark:text-orange-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>Account Settings</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">Manage your account security</p>
            </div>
          </div>
          
          {/* User Info */}
          <div className="p-4 bg-slate-50 dark:bg-slate-800 rounded-lg mb-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-slate-500 dark:text-slate-400">Email</p>
                <p className="font-medium">{user?.email || 'N/A'}</p>
              </div>
              <div>
                <p className="text-sm text-slate-500 dark:text-slate-400">Name</p>
                <p className="font-medium">{user?.name || 'N/A'}</p>
              </div>
              <div>
                <p className="text-sm text-slate-500 dark:text-slate-400">Role</p>
                <p className="font-medium capitalize">{user?.role || 'N/A'}</p>
              </div>
            </div>
          </div>
          
          {/* Change Password Section */}
          <div className="border-t border-slate-200 dark:border-slate-800 pt-6">
            <div className="flex items-center gap-2 mb-4">
              <Key className="w-5 h-5 text-slate-600 dark:text-slate-400" />
              <h3 className="font-medium">Change Password</h3>
            </div>
            
            <div className="space-y-4 max-w-md">
              <div>
                <label className="block text-sm font-medium mb-2">Current Password</label>
                <div className="relative">
                  <input
                    type={showPassword.current ? 'text' : 'password'}
                    value={passwordData.current_password}
                    onChange={(e) => setPasswordData({...passwordData, current_password: e.target.value})}
                    className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm pr-10"
                    placeholder="Enter current password"
                    data-testid="current-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword({...showPassword, current: !showPassword.current})}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600"
                  >
                    {showPassword.current ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-2">New Password</label>
                <div className="relative">
                  <input
                    type={showPassword.new ? 'text' : 'password'}
                    value={passwordData.new_password}
                    onChange={(e) => setPasswordData({...passwordData, new_password: e.target.value})}
                    className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm pr-10"
                    placeholder="Enter new password (min 6 characters)"
                    data-testid="new-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword({...showPassword, new: !showPassword.new})}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600"
                  >
                    {showPassword.new ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-2">Confirm New Password</label>
                <div className="relative">
                  <input
                    type={showPassword.confirm ? 'text' : 'password'}
                    value={passwordData.confirm_password}
                    onChange={(e) => setPasswordData({...passwordData, confirm_password: e.target.value})}
                    className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm pr-10"
                    placeholder="Confirm new password"
                    data-testid="confirm-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword({...showPassword, confirm: !showPassword.confirm})}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600"
                  >
                    {showPassword.confirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              
              <button
                onClick={changePassword}
                disabled={saving}
                className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-md transition-colors font-medium disabled:opacity-50"
                data-testid="change-password-btn"
              >
                <Key className="w-4 h-4" />
                {saving ? 'Changing...' : 'Change Password'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* PayU Settings */}
      {activeTab === 'payu' && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-3 bg-green-50 dark:bg-green-950/30 rounded-lg">
              <CreditCard className="w-6 h-6 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>PayU Colombia</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">Configure PayU payment gateway for RFID top-ups</p>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <div>
              <label className="block text-sm font-medium mb-2">API Key</label>
              <div className="relative">
                <input
                  type={showApiKey.payu ? 'text' : 'password'}
                  value={payuSettings.api_key}
                  onChange={(e) => setPayuSettings({...payuSettings, api_key: e.target.value})}
                  className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm pr-10"
                  placeholder="Your PayU API Key"
                  data-testid="payu-api-key"
                />
                <button
                  type="button"
                  onClick={() => setShowApiKey({...showApiKey, payu: !showApiKey.payu})}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600"
                >
                  {showApiKey.payu ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-2">API Login</label>
              <input
                type="text"
                value={payuSettings.api_login}
                onChange={(e) => setPayuSettings({...payuSettings, api_login: e.target.value})}
                className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                placeholder="Your PayU API Login"
                data-testid="payu-api-login"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-2">Merchant ID</label>
              <input
                type="text"
                value={payuSettings.merchant_id}
                onChange={(e) => setPayuSettings({...payuSettings, merchant_id: e.target.value})}
                className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                placeholder="Your Merchant ID"
                data-testid="payu-merchant-id"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-2">Account ID</label>
              <input
                type="text"
                value={payuSettings.account_id}
                onChange={(e) => setPayuSettings({...payuSettings, account_id: e.target.value})}
                className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                placeholder="Your Account ID"
                data-testid="payu-account-id"
              />
            </div>
          </div>
          
          <div className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-800 rounded-lg mb-6">
            <div>
              <p className="font-medium">Test Mode (Sandbox)</p>
              <p className="text-sm text-slate-500 dark:text-slate-400">Use sandbox environment for testing</p>
            </div>
            <button
              onClick={() => setPayuSettings({...payuSettings, test_mode: !payuSettings.test_mode})}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                payuSettings.test_mode ? 'bg-orange-600' : 'bg-slate-300 dark:bg-slate-600'
              }`}
              data-testid="payu-test-mode"
            >
              <span className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                payuSettings.test_mode ? 'translate-x-7' : 'translate-x-1'
              }`} />
            </button>
          </div>
          
          <button
            onClick={savePayuSettings}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-md transition-colors font-medium disabled:opacity-50"
            data-testid="save-payu-btn"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save PayU Settings'}
          </button>
        </div>
      )}

      {/* SendGrid Settings */}
      {activeTab === 'sendgrid' && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-3 bg-blue-50 dark:bg-blue-950/30 rounded-lg">
              <Mail className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>SendGrid Email</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">Configure email notifications for low balance alerts</p>
            </div>
          </div>
          
          <div className="flex items-center justify-between p-4 bg-blue-50 dark:bg-blue-950/30 rounded-lg mb-6">
            <div>
              <p className="font-medium">Enable Email Notifications</p>
              <p className="text-sm text-slate-500 dark:text-slate-400">Send alerts when RFID card balance is low</p>
            </div>
            <button
              onClick={() => setSendgridSettings({...sendgridSettings, enabled: !sendgridSettings.enabled})}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                sendgridSettings.enabled ? 'bg-blue-600' : 'bg-slate-300 dark:bg-slate-600'
              }`}
              data-testid="sendgrid-enabled"
            >
              <span className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                sendgridSettings.enabled ? 'translate-x-7' : 'translate-x-1'
              }`} />
            </button>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-2">SendGrid API Key</label>
              <div className="relative">
                <input
                  type={showApiKey.sendgrid ? 'text' : 'password'}
                  value={sendgridSettings.api_key}
                  onChange={(e) => setSendgridSettings({...sendgridSettings, api_key: e.target.value})}
                  className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm pr-10"
                  placeholder="SG.xxxxxxxxxxxx"
                  data-testid="sendgrid-api-key"
                />
                <button
                  type="button"
                  onClick={() => setShowApiKey({...showApiKey, sendgrid: !showApiKey.sendgrid})}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600"
                >
                  {showApiKey.sendgrid ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              <p className="text-xs text-slate-500 mt-1">Get your API key from SendGrid Dashboard → Settings → API Keys</p>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-2">Sender Email</label>
              <input
                type="email"
                value={sendgridSettings.sender_email}
                onChange={(e) => setSendgridSettings({...sendgridSettings, sender_email: e.target.value})}
                className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                placeholder="noreply@yourcompany.com"
                data-testid="sendgrid-sender-email"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-2">Sender Name</label>
              <input
                type="text"
                value={sendgridSettings.sender_name}
                onChange={(e) => setSendgridSettings({...sendgridSettings, sender_name: e.target.value})}
                className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                placeholder="EV Charging System"
                data-testid="sendgrid-sender-name"
              />
            </div>
          </div>
          
          <div className="flex gap-3 mb-6">
            <button
              onClick={saveSendgridSettings}
              disabled={saving}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors font-medium disabled:opacity-50"
              data-testid="save-sendgrid-btn"
            >
              <Save className="w-4 h-4" />
              {saving ? 'Saving...' : 'Save Email Settings'}
            </button>
          </div>
          
          {/* Test Email Section */}
          <div className="border-t border-slate-200 dark:border-slate-800 pt-6">
            <h3 className="font-medium mb-4">Test Email Configuration</h3>
            <div className="flex gap-3">
              <input
                type="email"
                value={testEmail}
                onChange={(e) => setTestEmail(e.target.value)}
                placeholder="Enter email to send test"
                className="flex-1 h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                data-testid="test-email-input"
              />
              <button
                onClick={testSendgridEmail}
                disabled={testing}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md transition-colors font-medium disabled:opacity-50"
                data-testid="test-sendgrid-btn"
              >
                <TestTube className="w-4 h-4" />
                {testing ? 'Sending...' : 'Send Test'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Invoice Webhook Settings */}
      {activeTab === 'webhook' && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-3 bg-purple-50 dark:bg-purple-950/30 rounded-lg">
              <Webhook className="w-6 h-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>Invoice Webhook</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">Send transaction data to 3rd party invoicing systems</p>
            </div>
          </div>
          
          <div className="flex items-center justify-between p-4 bg-purple-50 dark:bg-purple-950/30 rounded-lg mb-6">
            <div>
              <p className="font-medium">Enable Webhook</p>
              <p className="text-sm text-slate-500 dark:text-slate-400">Send data when transactions complete</p>
            </div>
            <button
              onClick={() => setWebhookSettings({...webhookSettings, enabled: !webhookSettings.enabled})}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                webhookSettings.enabled ? 'bg-purple-600' : 'bg-slate-300 dark:bg-slate-600'
              }`}
              data-testid="webhook-enabled"
            >
              <span className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                webhookSettings.enabled ? 'translate-x-7' : 'translate-x-1'
              }`} />
            </button>
          </div>
          
          <div className="space-y-4 mb-6">
            <div>
              <label className="block text-sm font-medium mb-2">Webhook URL</label>
              <input
                type="url"
                value={webhookSettings.webhook_url}
                onChange={(e) => setWebhookSettings({...webhookSettings, webhook_url: e.target.value})}
                className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                placeholder="https://your-invoice-system.com/webhook"
                data-testid="webhook-url"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-2">API Key (Optional)</label>
              <div className="relative">
                <input
                  type={showApiKey.webhook ? 'text' : 'password'}
                  value={webhookSettings.api_key}
                  onChange={(e) => setWebhookSettings({...webhookSettings, api_key: e.target.value})}
                  className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm pr-10"
                  placeholder="Your webhook API key"
                  data-testid="webhook-api-key"
                />
                <button
                  type="button"
                  onClick={() => setShowApiKey({...showApiKey, webhook: !showApiKey.webhook})}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600"
                >
                  {showApiKey.webhook ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              <p className="text-xs text-slate-500 mt-1">Will be sent as X-API-Key header</p>
            </div>
          </div>
          
          <div className="flex gap-3 mb-6">
            <button
              onClick={saveWebhookSettings}
              disabled={saving}
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-md transition-colors font-medium disabled:opacity-50"
              data-testid="save-webhook-btn"
            >
              <Save className="w-4 h-4" />
              {saving ? 'Saving...' : 'Save Webhook Settings'}
            </button>
            
            <button
              onClick={testWebhook}
              disabled={testing || !webhookSettings.webhook_url}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md transition-colors font-medium disabled:opacity-50"
              data-testid="test-webhook-btn"
            >
              <TestTube className="w-4 h-4" />
              {testing ? 'Testing...' : 'Test Webhook'}
            </button>
          </div>
          
          {/* Webhook Payload Info */}
          <div className="border-t border-slate-200 dark:border-slate-800 pt-6">
            <h3 className="font-medium mb-4">Webhook Payload Format</h3>
            <pre className="p-4 bg-slate-800 text-slate-100 rounded-lg text-xs overflow-x-auto">
{`{
  "event_type": "transaction_completed",
  "transaction_id": "12345678",
  "tx_id": "OCPP-12345678",
  "account": "RFID-001-2024",
  "station": "charger-id",
  "connector": "1",
  "connector_type": "CCS2",
  "start_time": "2026-01-21T10:00:00Z",
  "end_time": "2026-01-21T10:30:00Z",
  "meter_value": 25.5,
  "cost": 63750,
  "payment_status": "PAID",
  "payment_type": "RFID",
  "rfid_card_number": "RFID-001-2024",
  "user_email": "user@example.com",
  "created_at": "2026-01-21T10:30:00Z"
}`}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

export default Settings;
