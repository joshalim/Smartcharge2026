import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { AlertCircle, Globe } from 'lucide-react';

function Login() {
  const { t, i18n } = useTranslation();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const toggleLanguage = () => {
    const newLang = i18n.language === 'en' ? 'es' : 'en';
    i18n.changeLanguage(newLang);
    localStorage.setItem('language', newLang);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isLogin) {
        await login(email, password);
        navigate('/dashboard');
      } else {
        await register(email, password, name);
        await login(email, password);
        navigate('/dashboard');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex" style={{ fontFamily: 'IBM Plex Sans, sans-serif' }}>
      <div className="flex-1 flex items-center justify-center p-8 bg-white dark:bg-slate-900 relative">
        <button
          onClick={toggleLanguage}
          className="absolute top-4 right-4 flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-md transition-colors"
          data-testid="language-toggle-login"
        >
          <Globe className="w-4 h-4" />
          {i18n.language === 'en' ? 'ES' : 'EN'}
        </button>

        <div className="w-full max-w-md">
          <div className="mb-8 text-center">
            <img 
              src="https://customer-assets.emergentagent.com/job_evbill-manager/artifacts/snbut79m_smart-charge-high-resolution-logo%20mini%20sw.png" 
              alt="Smart Charge" 
              className="h-16 mb-6 mx-auto"
            />
            <p className="text-slate-500 dark:text-slate-400">
              {isLogin ? t('auth.signin') : t('auth.signup')}
            </p>
          </div>

          {error && (
            <div className="mb-6 p-4 bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800 rounded-lg flex items-start gap-3" data-testid="error-message">
              <AlertCircle className="w-5 h-5 text-rose-600 dark:text-rose-400 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-rose-600 dark:text-rose-400">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6" data-testid="login-form">
            {!isLogin && (
              <div>
                <label htmlFor="name" className="block text-sm font-medium mb-2">
                  {t('auth.name')}
                </label>
                <input
                  id="name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required={!isLogin}
                  className="flex h-10 w-full rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  placeholder="John Doe"
                  data-testid="name-input"
                />
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-sm font-medium mb-2">
                {t('auth.email')}
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="flex h-10 w-full rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                placeholder="you@example.com"
                data-testid="email-input"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium mb-2">
                {t('auth.password')}
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="flex h-10 w-full rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                placeholder="••••••••"
                data-testid="password-input"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full h-10 bg-orange-600 hover:bg-orange-700 text-white font-medium rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="submit-btn"
            >
              {loading ? t('common.pleaseWait') : isLogin ? t('auth.signInBtn') : t('auth.createAccount')}
            </button>
          </form>

          <div className="mt-6 text-center">
            <button
              onClick={() => {
                setIsLogin(!isLogin);
                setError('');
              }}
              className="text-sm text-orange-600 dark:text-orange-400 hover:underline"
              data-testid="toggle-auth-mode"
            >
              {isLogin ? t('auth.noAccount') : t('auth.hasAccount')}
            </button>
          </div>

          {isLogin && (
            <div className="mt-6 p-4 bg-slate-50 dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700">
              <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-2">Demo Credentials:</p>
              <div className="space-y-1">
                <p className="text-xs text-slate-600 dark:text-slate-300">
                  <span className="font-medium">Admin:</span> admin@evcharge.com / admin123
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      <div
        className="hidden lg:block flex-1 bg-cover bg-center relative"
        style={{ backgroundImage: `url('https://images.pexels.com/photos/27243718/pexels-photo-27243718.jpeg')` }}
      >
        <div className="absolute inset-0 bg-gradient-to-br from-orange-600/80 to-orange-800/80" />
        <div className="absolute inset-0 flex items-center justify-center p-12">
          <div className="text-white text-center">
            <h2 className="text-5xl font-black mb-4" style={{ fontFamily: 'Chivo, sans-serif' }}>
              Smart Charge
            </h2>
            <p className="text-xl text-white/90 leading-relaxed">
              {t('dashboard.subtitle')}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Login;