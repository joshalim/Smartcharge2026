import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Settings as SettingsIcon, CreditCard, Webhook, Mail, Save, TestTube, Eye, EyeOff, Check, X, AlertCircle, User, Key, QrCode, Copy, ExternalLink, Zap, Download } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { QRCodeSVG } from 'qrcode.react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const FRONTEND_URL = process.env.REACT_APP_BACKEND_URL?.replace('/api', '') || window.location.origin;

function Settings() {
  const { user, token } = useAuth();
  const [activeTab, setActiveTab] = useState('account');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [showApiKey, setShowApiKey] = useState({});
  const [message, setMessage] = useState(null);
  
  // Chargers for QR codes
  const [chargers, setChargers] = useState([]);
  const [copiedUrl, setCopiedUrl] = useState(null);
  
  // Password Change
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [showPassword, setShowPassword] = useState({});
  
  // BOLD.CO Settings
  const [boldSettings, setBoldSettings] = useState({
    api_key: '',
    test_mode: true
  });
  
  // Twilio WhatsApp Settings
  const [twilioSettings, setTwilioSettings] = useState({
    account_sid: '',
    auth_token: '',
    whatsapp_number: '',
    enabled: false
  });
  const [testWhatsAppPhone, setTestWhatsAppPhone] = useState('');
  const [testingWhatsApp, setTestingWhatsApp] = useState(false);
  
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
    fetchChargers();
  }, []);

  const fetchSettings = async () => {
    setLoading(true);
    try {
      const [boldRes, twilioRes, sendgridRes, webhookRes] = await Promise.all([
        axios.get(`${API}/settings/bold`),
        axios.get(`${API}/settings/twilio`),
        axios.get(`${API}/settings/sendgrid`),
        axios.get(`${API}/invoice-webhook/config`)
      ]);
      
      setBoldSettings(prev => ({ ...prev, ...boldRes.data }));
      setTwilioSettings(prev => ({ ...prev, ...twilioRes.data }));
      setSendgridSettings(prev => ({ ...prev, ...sendgridRes.data }));
      setWebhookSettings(prev => ({ ...prev, ...webhookRes.data }));
    } catch (error) {
      console.error('Failed to fetch settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchChargers = async () => {
    try {
      const response = await axios.get(`${API}/chargers`);
      setChargers(response.data || []);
    } catch (error) {
      console.error('Failed to fetch chargers:', error);
    }
  };

  const showMessage = (type, text) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 5000);
  };

  const saveBoldSettings = async () => {
    setSaving(true);
    try {
      await axios.put(`${API}/settings/bold`, boldSettings);
      showMessage('success', 'BOLD.CO settings saved successfully');
    } catch (error) {
      showMessage('error', error.response?.data?.detail || 'Failed to save BOLD.CO settings');
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

  // Generate QR code URL for a specific charger and connector
  const getQRCodeUrl = (chargerId, connector) => {
    const baseUrl = window.location.origin;
    return `${baseUrl}/charge/${chargerId}?connector=${connector}`;
  };

  // Copy URL to clipboard
  const copyToClipboard = async (url, key) => {
    try {
      await navigator.clipboard.writeText(url);
      setCopiedUrl(key);
      setTimeout(() => setCopiedUrl(null), 2000);
      showMessage('success', 'URL copied to clipboard!');
    } catch (err) {
      showMessage('error', 'Failed to copy URL');
    }
  };

  // Download QR code as PNG
  const downloadQRCode = (chargerId, connector) => {
    const url = getQRCodeUrl(chargerId, connector);
    const canvas = document.createElement('canvas');
    const svg = document.getElementById(`qr-${chargerId}-${connector}`);
    
    if (!svg) return;
    
    const svgData = new XMLSerializer().serializeToString(svg);
    const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
    const svgUrl = URL.createObjectURL(svgBlob);
    
    const img = new Image();
    img.onload = () => {
      canvas.width = 300;
      canvas.height = 300;
      const ctx = canvas.getContext('2d');
      
      // White background
      ctx.fillStyle = 'white';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      
      // Draw QR code
      ctx.drawImage(img, 0, 0, 300, 300);
      
      // Download
      const pngUrl = canvas.toDataURL('image/png');
      const downloadLink = document.createElement('a');
      downloadLink.href = pngUrl;
      downloadLink.download = `QR-${chargerId}-${connector}.png`;
      document.body.appendChild(downloadLink);
      downloadLink.click();
      document.body.removeChild(downloadLink);
      
      URL.revokeObjectURL(svgUrl);
      showMessage('success', `QR code downloaded: QR-${chargerId}-${connector}.png`);
    };
    img.src = svgUrl;
  };

  // Connector types
  const CONNECTORS = ['CCS2', 'CHADEMO', 'J1772'];

  const tabs = [
    { id: 'account', name: 'Account', icon: User },
    { id: 'qrcodes', name: 'QR Codes', icon: QrCode },
    { id: 'bold', name: 'BOLD.CO', icon: CreditCard },
    { id: 'whatsapp', name: 'WhatsApp', icon: Zap },
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

      {/* QR Codes Tab */}
      {activeTab === 'qrcodes' && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-3 bg-orange-50 dark:bg-orange-950/30 rounded-lg">
              <QrCode className="w-6 h-6 text-orange-600 dark:text-orange-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>Charger QR Codes</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">Generate QR code URLs for each connector type</p>
            </div>
          </div>

          {/* Info Banner */}
          <div className="bg-blue-50 dark:bg-blue-950/30 rounded-lg p-4 mb-6 flex items-start gap-3">
            <Zap className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm text-blue-700 dark:text-blue-400 font-medium">QR Code URLs for Charger Display</p>
              <p className="text-xs text-blue-600 dark:text-blue-500 mt-1">
                Copy these URLs to generate QR codes for your charger display. Each connector type (CCS2, CHADEMO, J1772) has a unique URL that directs users to the payment page with the connector pre-selected.
              </p>
            </div>
          </div>

          {chargers.length === 0 ? (
            <div className="text-center py-12 bg-slate-50 dark:bg-slate-800 rounded-lg">
              <QrCode className="w-12 h-12 text-slate-400 mx-auto mb-4" />
              <p className="text-slate-600 dark:text-slate-400 mb-2">No chargers found</p>
              <p className="text-sm text-slate-500">Add chargers in the Chargers page to generate QR codes</p>
            </div>
          ) : (
            <div className="space-y-6">
              {chargers.map((charger) => (
                <div key={charger.id} className="border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden">
                  {/* Charger Header */}
                  <div className="bg-slate-50 dark:bg-slate-800 px-4 py-3 border-b border-slate-200 dark:border-slate-700">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-bold text-lg">{charger.name}</h3>
                        <p className="text-sm text-slate-500">ID: {charger.charger_id} {charger.location && `• ${charger.location}`}</p>
                      </div>
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                        charger.status?.toLowerCase() === 'available' 
                          ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400'
                          : 'bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-300'
                      }`}>
                        {charger.status}
                      </span>
                    </div>
                  </div>

                  {/* Connector QR Codes */}
                  <div className="p-4">
                    <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-4">QR Codes & URLs per Connector:</p>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {CONNECTORS.map((connector) => {
                        const url = getQRCodeUrl(charger.charger_id, connector);
                        const copyKey = `${charger.id}-${connector}`;
                        
                        return (
                          <div 
                            key={connector}
                            className="p-4 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700"
                          >
                            {/* Connector Label */}
                            <div className="flex items-center justify-between mb-3">
                              <div className={`px-3 py-1 rounded-full text-xs font-bold ${
                                connector === 'CCS2' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' :
                                connector === 'CHADEMO' ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400' :
                                'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                              }`}>
                                {connector}
                              </div>
                            </div>
                            
                            {/* QR Code */}
                            <div className="bg-white p-3 rounded-lg mb-3 flex justify-center">
                              <QRCodeSVG
                                id={`qr-${charger.charger_id}-${connector}`}
                                value={url}
                                size={150}
                                level="M"
                                includeMargin={true}
                              />
                            </div>
                            
                            {/* URL Display */}
                            <div className="mb-3">
                              <p className="text-xs text-slate-500 mb-1">URL for EV Charger UI:</p>
                              <div className="bg-white dark:bg-slate-900 p-2 rounded border border-slate-200 dark:border-slate-700">
                                <p className="text-xs font-mono text-slate-600 dark:text-slate-400 break-all select-all">{url}</p>
                              </div>
                            </div>
                            
                            {/* Action Buttons */}
                            <div className="flex gap-2">
                              <button
                                onClick={() => downloadQRCode(charger.charger_id, connector)}
                                className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg text-sm font-medium transition-colors"
                                title="Download QR Code"
                                data-testid={`download-${charger.charger_id}-${connector}`}
                              >
                                <Download className="w-4 h-4" />
                                Download
                              </button>
                              
                              <button
                                onClick={() => copyToClipboard(url, copyKey)}
                                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                                  copiedUrl === copyKey
                                    ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                                    : 'bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-300'
                                }`}
                                title="Copy URL"
                                data-testid={`copy-${charger.charger_id}-${connector}`}
                              >
                                {copiedUrl === copyKey ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                              </button>
                              
                              <a
                                href={url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="px-3 py-2 bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-300 rounded-lg transition-colors"
                                title="Open in new tab"
                                data-testid={`open-${charger.charger_id}-${connector}`}
                              >
                                <ExternalLink className="w-4 h-4" />
                              </a>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* QR Code Usage Info */}
          <div className="mt-6 border-t border-slate-200 dark:border-slate-800 pt-6">
            <h3 className="font-medium mb-4">How to Use QR Codes</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-slate-50 dark:bg-slate-800 rounded-lg p-4">
                <h4 className="font-medium text-sm mb-2 flex items-center gap-2">
                  <Download className="w-4 h-4 text-orange-600" />
                  For Physical Display
                </h4>
                <ol className="list-decimal list-inside space-y-1 text-sm text-slate-600 dark:text-slate-400">
                  <li>Click "Download" to get the QR code PNG</li>
                  <li>Print and display on your charger for that connector</li>
                  <li>Users scan with phone to start charging</li>
                </ol>
              </div>
              <div className="bg-slate-50 dark:bg-slate-800 rounded-lg p-4">
                <h4 className="font-medium text-sm mb-2 flex items-center gap-2">
                  <ExternalLink className="w-4 h-4 text-blue-600" />
                  For Digital Display (EV Charger UI)
                </h4>
                <ol className="list-decimal list-inside space-y-1 text-sm text-slate-600 dark:text-slate-400">
                  <li>Copy the URL shown below each QR code</li>
                  <li>Configure your charger's UI to display this URL</li>
                  <li>Users can tap/click to open payment page</li>
                </ol>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* BOLD.CO Settings */}
      {activeTab === 'bold' && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-3 bg-green-50 dark:bg-green-950/30 rounded-lg">
              <CreditCard className="w-6 h-6 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>BOLD.CO Colombia</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">Configure BOLD.CO payment gateway for QR code payments</p>
            </div>
          </div>

          {/* Info Banner */}
          <div className="bg-blue-50 dark:bg-blue-950/30 rounded-lg p-4 mb-6 flex items-start gap-3">
            <Zap className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm text-blue-700 dark:text-blue-400 font-medium">Payment Methods Available</p>
              <p className="text-xs text-blue-600 dark:text-blue-500 mt-1">
                Credit/Debit Cards, PSE, Botón Bancolombia, Nequi
              </p>
            </div>
          </div>
          
          <div className="space-y-4 mb-6">
            <div>
              <label className="block text-sm font-medium mb-2">API Key (Llave de Identidad)</label>
              <div className="relative">
                <input
                  type={showApiKey.bold ? 'text' : 'password'}
                  value={boldSettings.api_key}
                  onChange={(e) => setBoldSettings({...boldSettings, api_key: e.target.value})}
                  className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm pr-10"
                  placeholder="Your BOLD.CO API Key"
                  data-testid="bold-api-key"
                />
                <button
                  type="button"
                  onClick={() => setShowApiKey({...showApiKey, bold: !showApiKey.bold})}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600"
                >
                  {showApiKey.bold ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Get your API key from <a href="https://bold.co" target="_blank" rel="noopener noreferrer" className="text-orange-600 hover:underline">bold.co</a> → Panel de comercios → Integraciones
              </p>
            </div>
          </div>
          
          <div className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-800 rounded-lg mb-6">
            <div>
              <p className="font-medium">Test Mode (Sandbox)</p>
              <p className="text-sm text-slate-500 dark:text-slate-400">Use sandbox environment for testing</p>
            </div>
            <button
              onClick={() => setBoldSettings({...boldSettings, test_mode: !boldSettings.test_mode})}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                boldSettings.test_mode ? 'bg-orange-600' : 'bg-slate-300 dark:bg-slate-600'
              }`}
              data-testid="bold-test-mode"
            >
              <span className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                boldSettings.test_mode ? 'translate-x-7' : 'translate-x-1'
              }`} />
            </button>
          </div>
          
          <button
            onClick={saveBoldSettings}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-md transition-colors font-medium disabled:opacity-50"
            data-testid="save-bold-btn"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save BOLD.CO Settings'}
          </button>

          {/* Webhook Configuration Info */}
          <div className="mt-6 border-t border-slate-200 dark:border-slate-800 pt-6">
            <h3 className="font-medium mb-3">Webhook Configuration</h3>
            <div className="bg-slate-50 dark:bg-slate-800 rounded-lg p-4">
              <p className="text-sm text-slate-600 dark:text-slate-400 mb-2">
                Configure the following webhook URL in your BOLD.CO merchant panel to receive payment notifications:
              </p>
              <div className="bg-white dark:bg-slate-900 p-2 rounded border border-slate-200 dark:border-slate-700">
                <code className="text-xs text-slate-700 dark:text-slate-300 break-all select-all">
                  {window.location.origin}/api/public/bold-webhook
                </code>
              </div>
            </div>
          </div>
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

      {/* FullColombia Integration Settings */}
      {activeTab === 'webhook' && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-3 bg-purple-50 dark:bg-purple-950/30 rounded-lg">
              <Webhook className="w-6 h-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>FullColombia Integration</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">Send transaction data to FullColombia invoicing system</p>
            </div>
          </div>
          
          <div className="flex items-center justify-between p-4 bg-purple-50 dark:bg-purple-950/30 rounded-lg mb-6">
            <div>
              <p className="font-medium">Enable FullColombia</p>
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
              <label className="block text-sm font-medium mb-2">FullColombia API URL</label>
              <input
                type="url"
                value={webhookSettings.webhook_url}
                onChange={(e) => setWebhookSettings({...webhookSettings, webhook_url: e.target.value})}
                className="w-full h-10 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                placeholder="https://api.fullcolombia.com/invoice"
                data-testid="webhook-url"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-2">API Key</label>
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
