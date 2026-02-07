import React, { useState, useEffect } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { Zap, Battery, CreditCard, Car, Mail, Phone, CheckCircle, AlertCircle, Loader2, ExternalLink } from 'lucide-react';
import { formatCOP } from '../utils/currency';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Preset amounts in COP
const PRESET_AMOUNTS = [5000, 10000, 20000, 50000, 100000];

function QRCharge() {
  const { chargerId } = useParams();
  const [searchParams] = useSearchParams();
  const connectorParam = searchParams.get('connector');
  
  const [charger, setCharger] = useState(null);
  const [pricing, setPricing] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Form state
  const [selectedConnector, setSelectedConnector] = useState(connectorParam || '');
  const [amount, setAmount] = useState(20000);
  const [customAmount, setCustomAmount] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [placa, setPlaca] = useState('');
  
  // Session state
  const [session, setSession] = useState(null);
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    fetchChargerInfo();
    fetchPricing();
  }, [chargerId]);

  const fetchChargerInfo = async () => {
    try {
      const response = await fetch(`${API}/public/charger/${chargerId}`);
      if (!response.ok) {
        throw new Error('Charger not found');
      }
      const data = await response.json();
      setCharger(data);
      
      // Set default connector if available
      if (data.connectors && data.connectors.length > 0 && !selectedConnector) {
        setSelectedConnector(data.connectors[0].type || data.connectors[0]);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchPricing = async () => {
    try {
      const response = await fetch(`${API}/public/pricing`);
      const data = await response.json();
      setPricing(data.pricing || {});
    } catch (err) {
      console.error('Failed to fetch pricing:', err);
    }
  };

  const getPrice = (connectorType) => {
    const upper = (connectorType || '').toUpperCase();
    return pricing[upper] || pricing['CCS'] || 2000;
  };

  const calculateEstimatedKwh = () => {
    const pricePerKwh = getPrice(selectedConnector);
    const selectedAmount = customAmount ? parseFloat(customAmount) : amount;
    return (selectedAmount / pricePerKwh).toFixed(2);
  };

  const handleStartCharge = async () => {
    const selectedAmount = customAmount ? parseFloat(customAmount) : amount;
    
    if (!selectedConnector) {
      alert('Please select a connector type');
      return;
    }
    
    if (!selectedAmount || selectedAmount < 1000) {
      alert('Minimum amount is $1,000 COP');
      return;
    }
    
    setProcessing(true);
    
    try {
      const response = await fetch(`${API}/public/start-charge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          charger_id: chargerId,
          connector_type: selectedConnector,
          amount: selectedAmount,
          email: email || null,
          phone: phone || null,
          placa: placa || null
        })
      });
      
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Failed to start charge');
      }
      
      const data = await response.json();
      setSession(data);
      
      // If PayU payment URL is provided, redirect to PayU
      if (data.payment_url) {
        window.location.href = data.payment_url;
      }
      
    } catch (err) {
      alert(err.message);
      setProcessing(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-50 to-white dark:from-slate-900 dark:to-slate-800 flex items-center justify-center" data-testid="qr-charge-loading">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-50 to-white dark:from-slate-900 dark:to-slate-800 flex items-center justify-center p-4" data-testid="qr-charge-error">
        <div className="bg-white dark:bg-slate-900 rounded-2xl p-8 shadow-xl max-w-md w-full text-center">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">Charger Not Found</h1>
          <p className="text-slate-600 dark:text-slate-400">{error}</p>
        </div>
      </div>
    );
  }

  if (session && !session.payment_url) {
    // Show session created but no PayU configured
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-50 to-white dark:from-slate-900 dark:to-slate-800 flex items-center justify-center p-4" data-testid="qr-charge-session">
        <div className="bg-white dark:bg-slate-900 rounded-2xl p-8 shadow-xl max-w-md w-full text-center">
          <CheckCircle className="w-16 h-16 text-emerald-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">Session Created!</h1>
          <p className="text-slate-600 dark:text-slate-400 mb-6">Your charging session has been initiated.</p>
          
          <div className="bg-slate-50 dark:bg-slate-800 rounded-xl p-4 mb-6 text-left">
            <div className="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <span className="text-slate-500">Session ID</span>
              <span className="font-mono font-bold">{session.session_id}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <span className="text-slate-500">Amount</span>
              <span className="font-bold text-orange-600">{formatCOP(session.amount)}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <span className="text-slate-500">Connector</span>
              <span className="font-medium">{session.connector_type}</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-slate-500">Status</span>
              <span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded-full text-xs font-medium">
                Pending Payment
              </span>
            </div>
          </div>
          
          <div className="bg-orange-50 dark:bg-orange-900/20 rounded-xl p-4 mb-4">
            <p className="text-sm text-orange-700 dark:text-orange-400">
              <AlertCircle className="w-4 h-4 inline mr-1" />
              PayU payment is not configured. Please contact the station administrator.
            </p>
          </div>
          
          <button
            onClick={() => window.location.reload()}
            className="w-full py-3 bg-orange-600 hover:bg-orange-700 text-white rounded-xl font-medium transition-colors"
            data-testid="start-new-session-btn"
          >
            Start New Session
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 to-white dark:from-slate-900 dark:to-slate-800 p-4" data-testid="qr-charge-page">
      <div className="max-w-md mx-auto">
        {/* Header */}
        <div className="text-center mb-6 pt-4">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-orange-100 dark:bg-orange-900/30 rounded-full mb-4">
            <Zap className="w-8 h-8 text-orange-600" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">SmartCharge</h1>
          <p className="text-slate-500 dark:text-slate-400">Quick & Easy EV Charging</p>
        </div>

        {/* Charger Info */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-lg mb-4" data-testid="charger-info-card">
          <div className="flex items-center gap-4 mb-4">
            <div className="w-12 h-12 bg-emerald-100 dark:bg-emerald-900/30 rounded-xl flex items-center justify-center">
              <Battery className="w-6 h-6 text-emerald-600" />
            </div>
            <div>
              <h2 className="font-bold text-lg text-slate-900 dark:text-white" data-testid="charger-name">{charger?.name}</h2>
              <p className="text-sm text-slate-500">{charger?.location || chargerId}</p>
            </div>
            <div className="ml-auto">
              <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                charger?.status === 'available' || charger?.status === 'Available'
                  ? 'bg-emerald-100 text-emerald-800'
                  : 'bg-red-100 text-red-800'
              }`} data-testid="charger-status">
                {charger?.status}
              </span>
            </div>
          </div>

          {/* Connector Selection */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
              Connector Type
            </label>
            <div className="grid grid-cols-3 gap-2" data-testid="connector-selection">
              {['CCS', 'CHADEMO', 'J1772'].map((type) => (
                <button
                  key={type}
                  onClick={() => setSelectedConnector(type)}
                  className={`py-3 px-4 rounded-xl border-2 text-sm font-medium transition-all ${
                    selectedConnector === type
                      ? 'border-orange-500 bg-orange-50 dark:bg-orange-900/20 text-orange-700 dark:text-orange-400'
                      : 'border-slate-200 dark:border-slate-700 hover:border-slate-300'
                  }`}
                  data-testid={`connector-${type.toLowerCase()}`}
                >
                  {type}
                </button>
              ))}
            </div>
            {selectedConnector && (
              <p className="text-xs text-slate-500 mt-2">
                Price: {formatCOP(getPrice(selectedConnector))}/kWh
              </p>
            )}
          </div>
        </div>

        {/* Amount Selection */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-lg mb-4" data-testid="amount-selection-card">
          <div className="flex items-center gap-2 mb-4">
            <CreditCard className="w-5 h-5 text-orange-600" />
            <h3 className="font-bold text-slate-900 dark:text-white">Select Amount</h3>
          </div>
          
          <div className="grid grid-cols-3 gap-2 mb-4" data-testid="preset-amounts">
            {PRESET_AMOUNTS.map((preset) => (
              <button
                key={preset}
                onClick={() => { setAmount(preset); setCustomAmount(''); }}
                className={`py-3 rounded-xl text-sm font-medium transition-all ${
                  amount === preset && !customAmount
                    ? 'bg-orange-600 text-white'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200'
                }`}
                data-testid={`amount-${preset}`}
              >
                {formatCOP(preset)}
              </button>
            ))}
          </div>
          
          <div>
            <label className="block text-sm text-slate-500 mb-1">Or enter custom amount</label>
            <input
              type="number"
              value={customAmount}
              onChange={(e) => setCustomAmount(e.target.value)}
              placeholder="Enter amount in COP"
              className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 dark:bg-slate-800"
              data-testid="custom-amount-input"
            />
          </div>
          
          {selectedConnector && (
            <div className="mt-4 p-4 bg-orange-50 dark:bg-orange-900/20 rounded-xl">
              <div className="flex justify-between items-center">
                <span className="text-slate-600 dark:text-slate-400">Estimated Energy</span>
                <span className="text-2xl font-bold text-orange-600" data-testid="estimated-kwh">{calculateEstimatedKwh()} kWh</span>
              </div>
            </div>
          )}
        </div>

        {/* Contact Info (Optional) */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-lg mb-4" data-testid="contact-info-card">
          <h3 className="font-bold text-slate-900 dark:text-white mb-4">Contact Info (Optional)</h3>
          
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <Mail className="w-5 h-5 text-slate-400" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Email for receipt"
                className="flex-1 px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 dark:bg-slate-800"
                data-testid="email-input"
              />
            </div>
            <div className="flex items-center gap-3">
              <Phone className="w-5 h-5 text-slate-400" />
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="Phone number"
                className="flex-1 px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 dark:bg-slate-800"
                data-testid="phone-input"
              />
            </div>
            <div className="flex items-center gap-3">
              <Car className="w-5 h-5 text-slate-400" />
              <input
                type="text"
                value={placa}
                onChange={(e) => setPlaca(e.target.value)}
                placeholder="Vehicle plate (PLACA)"
                className="flex-1 px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 dark:bg-slate-800"
                data-testid="placa-input"
              />
            </div>
          </div>
        </div>

        {/* PayU Info Banner */}
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl p-4 mb-4 flex items-start gap-3">
          <ExternalLink className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-sm text-blue-700 dark:text-blue-400 font-medium">Secure Payment via PayU</p>
            <p className="text-xs text-blue-600 dark:text-blue-500">You will be redirected to PayU to complete payment securely.</p>
          </div>
        </div>

        {/* Start Button */}
        <button
          onClick={handleStartCharge}
          disabled={processing || !selectedConnector}
          className="w-full py-4 bg-orange-600 hover:bg-orange-700 disabled:bg-slate-400 text-white rounded-2xl font-bold text-lg transition-colors flex items-center justify-center gap-2 shadow-lg"
          data-testid="start-charge-btn"
        >
          {processing ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Processing...
            </>
          ) : (
            <>
              <Zap className="w-5 h-5" />
              Start Charging - {formatCOP(customAmount ? parseFloat(customAmount) : amount)}
            </>
          )}
        </button>

        <p className="text-center text-xs text-slate-500 mt-4">
          By starting, you agree to our terms of service
        </p>
      </div>
    </div>
  );
}

export default QRCharge;
