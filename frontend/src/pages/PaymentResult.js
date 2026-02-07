import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { CheckCircle, XCircle, Clock, AlertCircle, Zap, ArrowLeft, RefreshCw } from 'lucide-react';
import { formatCOP } from '../utils/currency';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function PaymentResult() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // PayU callback parameters
  const referenceCode = searchParams.get('referenceCode') || searchParams.get('reference_code');
  const transactionState = searchParams.get('transactionState') || searchParams.get('lapTransactionState');
  const polResponseCode = searchParams.get('polResponseCode');
  const sessionId = searchParams.get('session_id');

  useEffect(() => {
    if (referenceCode || sessionId) {
      fetchSessionStatus();
    } else {
      setLoading(false);
      setError('No session reference found');
    }
  }, [referenceCode, sessionId]);

  const fetchSessionStatus = async () => {
    try {
      const ref = referenceCode || sessionId;
      const response = await fetch(`${API}/public/session/${ref}`);
      if (!response.ok) {
        throw new Error('Session not found');
      }
      const data = await response.json();
      setSession(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getStatusInfo = () => {
    const state = transactionState || session?.payment_status;
    
    // PayU transaction states: 4=APPROVED, 5=EXPIRED, 6=DECLINED, 7=PENDING
    if (state === '4' || state === 'APPROVED' || state === 'PAID') {
      return {
        icon: CheckCircle,
        color: 'text-emerald-500',
        bgColor: 'bg-emerald-100 dark:bg-emerald-900/30',
        title: 'Payment Successful!',
        subtitle: 'Your charging session has been activated.',
        status: 'APPROVED'
      };
    } else if (state === '6' || state === 'DECLINED' || state === 'REJECTED') {
      return {
        icon: XCircle,
        color: 'text-red-500',
        bgColor: 'bg-red-100 dark:bg-red-900/30',
        title: 'Payment Declined',
        subtitle: 'Your payment could not be processed.',
        status: 'DECLINED'
      };
    } else if (state === '5' || state === 'EXPIRED') {
      return {
        icon: AlertCircle,
        color: 'text-orange-500',
        bgColor: 'bg-orange-100 dark:bg-orange-900/30',
        title: 'Payment Expired',
        subtitle: 'The payment session has expired.',
        status: 'EXPIRED'
      };
    } else {
      return {
        icon: Clock,
        color: 'text-yellow-500',
        bgColor: 'bg-yellow-100 dark:bg-yellow-900/30',
        title: 'Payment Pending',
        subtitle: 'Your payment is being processed.',
        status: 'PENDING'
      };
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-50 to-white dark:from-slate-900 dark:to-slate-800 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-12 h-12 text-orange-600 animate-spin mx-auto mb-4" />
          <p className="text-slate-600 dark:text-slate-400">Verifying payment...</p>
        </div>
      </div>
    );
  }

  if (error && !session) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-50 to-white dark:from-slate-900 dark:to-slate-800 flex items-center justify-center p-4">
        <div className="bg-white dark:bg-slate-900 rounded-2xl p-8 shadow-xl max-w-md w-full text-center">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">Session Not Found</h1>
          <p className="text-slate-600 dark:text-slate-400 mb-6">{error}</p>
          <button
            onClick={() => navigate('/')}
            className="px-6 py-3 bg-orange-600 hover:bg-orange-700 text-white rounded-xl font-medium transition-colors"
          >
            Go Home
          </button>
        </div>
      </div>
    );
  }

  const statusInfo = getStatusInfo();
  const StatusIcon = statusInfo.icon;

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 to-white dark:from-slate-900 dark:to-slate-800 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-slate-900 rounded-2xl p-8 shadow-xl max-w-md w-full">
        {/* Status Icon */}
        <div className="text-center mb-6">
          <div className={`inline-flex items-center justify-center w-20 h-20 ${statusInfo.bgColor} rounded-full mb-4`}>
            <StatusIcon className={`w-10 h-10 ${statusInfo.color}`} />
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{statusInfo.title}</h1>
          <p className="text-slate-600 dark:text-slate-400">{statusInfo.subtitle}</p>
        </div>

        {/* Session Details */}
        {session && (
          <div className="bg-slate-50 dark:bg-slate-800 rounded-xl p-4 mb-6">
            <div className="space-y-3">
              <div className="flex justify-between items-center py-2 border-b border-slate-200 dark:border-slate-700">
                <span className="text-slate-500 text-sm">Session ID</span>
                <span className="font-mono font-bold text-sm">{session.session_id}</span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-slate-200 dark:border-slate-700">
                <span className="text-slate-500 text-sm">Charger</span>
                <span className="font-medium">{session.charger_id}</span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-slate-200 dark:border-slate-700">
                <span className="text-slate-500 text-sm">Connector</span>
                <span className="font-medium">{session.connector_type}</span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-slate-200 dark:border-slate-700">
                <span className="text-slate-500 text-sm">Amount</span>
                <span className="font-bold text-orange-600">{formatCOP(session.amount)}</span>
              </div>
              <div className="flex justify-between items-center py-2">
                <span className="text-slate-500 text-sm">Status</span>
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                  statusInfo.status === 'APPROVED' ? 'bg-emerald-100 text-emerald-800' :
                  statusInfo.status === 'DECLINED' ? 'bg-red-100 text-red-800' :
                  statusInfo.status === 'EXPIRED' ? 'bg-orange-100 text-orange-800' :
                  'bg-yellow-100 text-yellow-800'
                }`}>
                  {statusInfo.status}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="space-y-3">
          {statusInfo.status === 'APPROVED' && (
            <div className="bg-emerald-50 dark:bg-emerald-900/20 rounded-xl p-4 text-center">
              <Zap className="w-8 h-8 text-emerald-600 mx-auto mb-2" />
              <p className="text-emerald-700 dark:text-emerald-400 font-medium">
                Charging is now active!
              </p>
              <p className="text-sm text-emerald-600 dark:text-emerald-500">
                Please connect your vehicle to the charger.
              </p>
            </div>
          )}

          {statusInfo.status === 'DECLINED' && session?.charger_id && (
            <button
              onClick={() => navigate(`/charge/${session.charger_id}`)}
              className="w-full py-3 bg-orange-600 hover:bg-orange-700 text-white rounded-xl font-medium transition-colors flex items-center justify-center gap-2"
            >
              <RefreshCw className="w-5 h-5" />
              Try Again
            </button>
          )}

          {statusInfo.status === 'PENDING' && (
            <button
              onClick={fetchSessionStatus}
              className="w-full py-3 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-xl font-medium transition-colors flex items-center justify-center gap-2"
            >
              <RefreshCw className="w-5 h-5" />
              Refresh Status
            </button>
          )}

          <button
            onClick={() => navigate('/')}
            className="w-full py-3 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-xl font-medium transition-colors flex items-center justify-center gap-2"
          >
            <ArrowLeft className="w-5 h-5" />
            Back to Home
          </button>
        </div>

        {/* Reference Code */}
        {referenceCode && (
          <p className="text-center text-xs text-slate-400 mt-4">
            Reference: {referenceCode}
          </p>
        )}
      </div>
    </div>
  );
}

export default PaymentResult;
