import React, { useState, useEffect } from "react"

function Dashboard() {
  const [stats, setStats] = useState({
    totalUsers: "1,284",
    activeSubscriptions: "892",
    revenue: "45,230",
    serversOnline: "3/4",
    recentPayments: [
      { user: "User #1024", provider: "CryptoBot", amount: "+299", time: "2 мин назад", status: "success" },
      { user: "User #891", provider: "YooKassa", amount: "+599", time: "15 мин назад", status: "success" },
      { user: "User #1102", provider: "FreeKassa", amount: "199", time: "Ожидает", status: "pending" }
    ],
    serverLoad: [
      { name: "NL-01 Амстердам", load: 78 },
      { name: "DE-01 Франкфурт", load: 45 },
      { name: "JP-01 Токио", load: 62 },
      { name: "US-01 Нью-Йорк", load: 89 }
    ]
  })

  const statCards = [
    {
      icon: "fas fa-users",
      label: "Всего пользователей",
      value: stats.totalUsers,
      change: "+12%",
      color: "blue"
    },
    {
      icon: "fas fa-user-check",
      label: "Активные подписки",
      value: stats.activeSubscriptions,
      change: "+5%",
      color: "green"
    },
    {
      icon: "fas fa-ruble-sign",
      label: "Выручка (руб.)",
      value: stats.revenue,
      change: "+23%",
      color: "purple"
    },
    {
      icon: "fas fa-server",
      label: "Серверы онлайн",
      value: stats.serversOnline,
      change: "4 сервера",
      color: "orange"
    }
  ]

  const getColorClasses = (color) => {
    const colors = {
      blue: "bg-blue-500/10 text-blue-400",
      green: "bg-green-500/10 text-green-400",
      purple: "bg-purple-500/10 text-purple-400",
      orange: "bg-orange-500/10 text-orange-400"
    }
    return colors[color]
  }

  const getBgColorClasses = (color) => {
    const colors = {
      blue: "bg-blue-500/10 text-blue-400",
      green: "bg-green-500/10 text-green-400",
      purple: "bg-purple-500/10 text-purple-400",
      orange: "bg-orange-500/10 text-orange-400"
    }
    return colors[color]
  }

  return (
    <div>
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {statCards.map((card) => (
          <div key={card.label} className="stat-card">
            <div className="flex items-center justify-between mb-4">
              <div className={`w-12 h-12 rounded-lg ${getColorClasses(card.color)} flex items-center justify-center`}>
                <i className={`${card.icon} text-xl`}></i>
              </div>
              <span className="text-xs text-green-400 bg-green-500/10 px-2 py-1 rounded-full">
                {card.change}
              </span>
            </div>
            <p className="text-3xl font-bold">{card.value}</p>
            <p className="text-sm text-slate-400 mt-1">{card.label}</p>
          </div>
        ))}
      </div>

      {/* Charts & Data */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Payments */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Последние платежи</h3>
          <div className="space-y-3">
            {stats.recentPayments.map((payment, idx) => (
              <div key={idx} className="flex items-center justify-between p-3 rounded-lg bg-slate-700/30">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                    payment.status === 'success' ? 'bg-green-500/10' : 'bg-yellow-500/10'
                  }`}>
                    <i className={`fas ${payment.status === 'success' ? 'fa-check text-green-400' : 'fa-clock text-yellow-400'}`}></i>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-white">{payment.user}</p>
                    <p className="text-xs text-slate-400">{payment.provider} - {payment.time}</p>
                  </div>
                </div>
                <span className={`text-sm font-semibold ${payment.status === 'success' ? 'text-green-400' : 'text-yellow-400'}`}>
                  {payment.amount}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Server Load */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Нагрузка серверов</h3>
          <div className="space-y-4">
            {stats.serverLoad.map((server, idx) => (
              <div key={idx}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-slate-300">{server.name}</span>
                  <span className="text-slate-400">{server.load}%</span>
                </div>
                <div className="w-full bg-slate-700 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all ${
                      server.load > 80 ? 'bg-red-500' : server.load > 60 ? 'bg-yellow-500' : 'bg-blue-500'
                    }`}
                    style={{ width: `${server.load}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Additional Info */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        {/* System Status */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Статус системы</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-300">API</span>
              <span className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-500"></div>
                <span className="text-xs text-green-400">Работает</span>
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-300">База данных</span>
              <span className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-500"></div>
                <span className="text-xs text-green-400">Работает</span>
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-300">Cache</span>
              <span className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-500"></div>
                <span className="text-xs text-green-400">Работает</span>
              </span>
            </div>
          </div>
        </div>

        {/* Top Countries */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Топ страны</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-300">🇷🇺 Россия</span>
              <span className="text-sm font-semibold text-blue-400">345 пользователей</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-300">🇺🇸 США</span>
              <span className="text-sm font-semibold text-blue-400">234 пользователя</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-300">🇩🇪 Германия</span>
              <span className="text-sm font-semibold text-blue-400">189 пользователей</span>
            </div>
          </div>
        </div>

        {/* Recent Users */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Новые пользователи</h3>
          <div className="space-y-3">
            <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-700/30 transition cursor-pointer">
              <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-xs font-bold text-white">И</div>
              <div className="min-w-0">
                <p className="text-sm font-medium text-white truncate">@ivan_petrov</p>
                <p className="text-xs text-slate-400">5 мин назад</p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-700/30 transition cursor-pointer">
              <div className="w-8 h-8 rounded-full bg-purple-500 flex items-center justify-center text-xs font-bold text-white">А</div>
              <div className="min-w-0">
                <p className="text-sm font-medium text-white truncate">@anna_sokolova</p>
                <p className="text-xs text-slate-400">12 мин назад</p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-700/30 transition cursor-pointer">
              <div className="w-8 h-8 rounded-full bg-green-500 flex items-center justify-center text-xs font-bold text-white">Д</div>
              <div className="min-w-0">
                <p className="text-sm font-medium text-white truncate">@dmitry_k</p>
                <p className="text-xs text-slate-400">25 мин назад</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
