import React, { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

const Layout = ({ children }) => {
  const location = useLocation()
  const navigate = useNavigate()
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

  const menuItems = [
    { icon: 'fas fa-chart-line', label: 'Dashboard', path: '/' },
    { icon: 'fas fa-users', label: 'Пользователи', path: '/users' },
    { icon: 'fas fa-server', label: 'Серверы', path: '/servers' },
    { icon: 'fas fa-tags', label: 'Планы', path: '/plans' },
    { icon: 'fas fa-credit-card', label: 'Платежи', path: '/payments' },
  ]

  const settingsItems = [
    { icon: 'fab fa-telegram', label: 'Бот', path: '/bot' },
    { icon: 'fas fa-share-nodes', label: 'Реферальная программа', path: '/referral' },
    { icon: 'fas fa-shield-halved', label: 'Антифрод', path: '/antifraud' },
    { icon: 'fas fa-bell', label: 'Уведомления', path: '/notifications' },
    { icon: 'fas fa-cog', label: 'Система', path: '/system' },
  ]

  const getPageTitle = () => {
    const item = [...menuItems, ...settingsItems].find(i => i.path === location.pathname)
    return item?.label || 'Dashboard'
  }

  const isActive = (path) => location.pathname === path

  return (
    <div className="flex h-screen overflow-hidden bg-slate-900">
      {/* Sidebar */}
      <aside className={`w-64 bg-slate-800/50 border-r border-slate-700 flex flex-col fixed lg:relative h-full z-50 lg:z-auto transition-all duration-300 ${
        isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
      }`}>
        {/* Logo */}
        <div className="p-6 border-b border-slate-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center">
              <i className="fas fa-shield-alt text-white text-lg"></i>
            </div>
            <div>
              <h1 className="font-bold text-lg">Gusto VPN</h1>
              <p className="text-xs text-slate-400">Admin Panel</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {menuItems.map(item => (
            <button
              key={item.path}
              onClick={() => {
                navigate(item.path)
                setIsMobileMenuOpen(false)
              }}
              className={`tab-btn ${isActive(item.path) ? 'active' : ''}`}
            >
              <i className={`${item.icon} w-5`}></i>
              {item.label}
            </button>
          ))}

          <div className="pt-4 mt-4 border-t border-slate-700">
            <p className="px-4 text-xs font-semibold text-slate-500 uppercase mb-2">Настройки</p>
            {settingsItems.map(item => (
              <button
                key={item.path}
                onClick={() => {
                  navigate(item.path)
                  setIsMobileMenuOpen(false)
                }}
                className={`tab-btn ${isActive(item.path) ? 'active' : ''}`}
              >
                <i className={`${item.icon} w-5`}></i>
                {item.label}
              </button>
            ))}
          </div>
        </nav>

        {/* User Profile */}
        <div className="p-4 border-t border-slate-700">
          <div className="flex items-center gap-3 p-3 rounded-lg bg-slate-700/30">
            <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-xs font-bold">А</div>
            <div>
              <p className="text-sm font-medium">Администратор</p>
              <p className="text-xs text-slate-400">admin@gusto.vpn</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto w-full">
        {/* Top Bar */}
        <header className="glass sticky top-0 z-10 border-b border-slate-700 px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="lg:hidden w-9 h-9 rounded-lg bg-slate-700/50 hover:bg-slate-700 flex items-center justify-center transition"
            >
              <i className="fas fa-bars text-slate-400"></i>
            </button>
            <h2 className="text-xl font-semibold">{getPageTitle()}</h2>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-green-500/10 text-green-400 text-sm">
              <div className="w-2 h-2 rounded-full bg-green-500 status-dot"></div>
              Система работает
            </div>
            <button className="w-9 h-9 rounded-lg bg-slate-700/50 hover:bg-slate-700 flex items-center justify-center transition">
              <i className="fas fa-bell text-slate-400"></i>
            </button>
          </div>
        </header>

        {/* Close Mobile Menu Overlay */}
        {isMobileMenuOpen && (
          <div
            className="fixed inset-0 bg-black/50 lg:hidden z-40"
            onClick={() => setIsMobileMenuOpen(false)}
          ></div>
        )}

        {/* Page Content */}
        <div className="p-8">
          {children}
        </div>
      </main>
    </div>
  )
}

export default Layout
