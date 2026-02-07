import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Transactions from './pages/Transactions';
import Import from './pages/Import';
import Users from './pages/Users';
import Pricing from './pages/Pricing';
import PricingGroups from './pages/PricingGroups';
import OCPP from './pages/OCPP';
import Chargers from './pages/Chargers';
import Reports from './pages/Reports';
import Settings from './pages/Settings';
import Layout from './components/Layout';
import QRCharge from './pages/QRCharge';
import PaymentResult from './pages/PaymentResult';
import './App.css';

function ProtectedRoute({ children, allowedRoles }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" data-testid="loading-spinner">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

function AppRoutes() {
  const { user } = useAuth();

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/dashboard" replace /> : <Login />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="transactions" element={<Transactions />} />
        <Route
          path="import"
          element={
            <ProtectedRoute allowedRoles={['admin', 'user']}>
              <Import />
            </ProtectedRoute>
          }
        />
        <Route
          path="pricing"
          element={
            <ProtectedRoute allowedRoles={['admin']}>
              <Pricing />
            </ProtectedRoute>
          }
        />
        <Route
          path="ocpp"
          element={
            <ProtectedRoute allowedRoles={['admin', 'user']}>
              <OCPP />
            </ProtectedRoute>
          }
        />
        <Route
          path="users"
          element={
            <ProtectedRoute allowedRoles={['admin']}>
              <Users />
            </ProtectedRoute>
          }
        />
        <Route
          path="chargers"
          element={
            <ProtectedRoute allowedRoles={['admin']}>
              <Chargers />
            </ProtectedRoute>
          }
        />
        <Route
          path="reports"
          element={
            <ProtectedRoute allowedRoles={['admin', 'user']}>
              <Reports />
            </ProtectedRoute>
          }
        />
        <Route
          path="settings"
          element={
            <ProtectedRoute allowedRoles={['admin']}>
              <Settings />
            </ProtectedRoute>
          }
        />
        <Route
          path="pricing-groups"
          element={
            <ProtectedRoute allowedRoles={['admin']}>
              <PricingGroups />
            </ProtectedRoute>
          }
        />
      </Route>
      {/* Public QR Charge routes - no auth required */}
      <Route path="/charge/:chargerId" element={<QRCharge />} />
      <Route path="/payment/result" element={<PaymentResult />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;