import React, { useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useTranslation } from 'react-i18next';
import { LayoutDashboard, Zap, Upload, Users, LogOut, Menu, X, DollarSign, Globe, Activity, Battery, BarChart3, Settings, UsersRound, Receipt } from 'lucide-react';

function Layout() {
  const { user, logout } = useAuth();
  const { t, i18n } = useTranslation();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const navigation = [
    { name: t('nav.dashboard'), href: '/dashboard', icon: LayoutDashboard, roles: ['admin', 'user', 'viewer'] },
    { name: t('nav.transactions'), href: '/transactions', icon: Zap, roles: ['admin', 'user', 'viewer'] },
    { name: t('nav.import'), href: '/import', icon: Upload, roles: ['admin', 'user'] },
    { name: t('nav.chargers'), href: '/chargers', icon: Battery, roles: ['admin'] },
    { name: t('nav.pricing'), href: '/pricing', icon: DollarSign, roles: ['admin'] },
    { name: t('nav.pricingGroups'), href: '/pricing-groups', icon: UsersRound, roles: ['admin'] },
    { name: t('nav.expenses'), href: '/expenses', icon: Receipt, roles: ['admin', 'user'] },
    { name: t('nav.reports'), href: '/reports', icon: BarChart3, roles: ['admin', 'user'] },
    { name: 'OCPP', href: '/ocpp', icon: Activity, roles: ['admin', 'user'] },
    { name: t('nav.users'), href: '/users', icon: Users, roles: ['admin'] },
    { name: t('nav.settings'), href: '/settings', icon: Settings, roles: ['admin'] },
  ];

  const filteredNav = navigation.filter(item => item.roles.includes(user?.role));

  const toggleLanguage = () => {
    const newLang = i18n.language === 'en' ? 'es' : 'en';
    i18n.changeLanguage(newLang);
    localStorage.setItem('language', newLang);
  };

  return (
    <div className="min-h-screen bg-white dark:bg-slate-950">
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-slate-900/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
          data-testid="sidebar-backdrop"
        />
      )}

      <aside
        className={`fixed top-0 left-0 z-50 h-screen w-64 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 transform transition-transform duration-200 ease-in-out lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
        data-testid="sidebar"
      >
        <div className="flex flex-col h-full">
          <div className="flex items-center justify-between h-16 px-6 border-b border-slate-200 dark:border-slate-800">
            <img 
              src="https://customer-assets.emergentagent.com/job_evbill-manager/artifacts/snbut79m_smart-charge-high-resolution-logo%20mini%20sw.png" 
              alt="Smart Charge" 
              className="h-10"
            />
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden p-2 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800"
              data-testid="close-sidebar-btn"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <nav className="flex-1 px-3 py-4 space-y-1">
            {filteredNav.map((item) => {
              const isActive = location.pathname === item.href;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-orange-50 dark:bg-orange-950/30 text-orange-600 dark:text-orange-400 border-l-4 border-l-orange-600 dark:border-l-orange-400'
                      : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                  onClick={() => setSidebarOpen(false)}
                  data-testid={`nav-${item.name.toLowerCase()}`}
                >
                  <item.icon className="w-5 h-5" />
                  {item.name}
                </Link>
              );
            })}
          </nav>

          <div className="p-4 border-t border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-full bg-orange-100 dark:bg-orange-900 flex items-center justify-center text-orange-600 dark:text-orange-400 font-semibold">
                {user?.name?.charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">{user?.name}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400 capitalize">{user?.role}</p>
              </div>
            </div>
            <button
              onClick={logout}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-md transition-colors mb-2"
              data-testid="logout-btn"
            >
              <LogOut className="w-4 h-4" />
              {t('nav.logout')}
            </button>
            <button
              onClick={toggleLanguage}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-md transition-colors"
              data-testid="language-toggle"
            >
              <Globe className="w-4 h-4" />
              {i18n.language === 'en' ? 'Español' : 'English'}
            </button>
          </div>
        </div>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-30 h-16 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800">
          <div className="flex items-center justify-between h-full px-4 sm:px-6 lg:px-8">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800"
              data-testid="open-sidebar-btn"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="flex-1" />
          </div>
        </header>

        <main className="p-4 sm:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default Layout;