import React, { useState } from "react"

function Servers() {
  const [servers] = useState([
    { id: "NL-01", name: "Амстердам", location: "🇳🇱 Нидерланды", status: "online", load: 45, users: 234, ip: "185.10.XX.XX", uptime: "99.95%" },
    { id: "DE-01", name: "Франкфурт", location: "🇩🇪 Германия", status: "online", load: 78, users: 456, ip: "185.20.XX.XX", uptime: "99.88%" },
    { id: "JP-01", name: "Токио", location: "🇯🇵 Япония", status: "online", load: 62, users: 345, ip: "185.30.XX.XX", uptime: "99.92%" },
    { id: "US-01", name: "Нью-Йорк", location: "🇺🇸 США", status: "warning", load: 89, users: 567, ip: "185.40.XX.XX", uptime: "99.85%" },
    { id: "SG-01", name: "Сингапур", location: "🇸🇬 Сингапур", status: "online", load: 34, users: 189, ip: "185.50.XX.XX", uptime: "99.99%" },
  ])

  const getStatusClass = (status) => {
    return status === "online" ? "text-green-400" : "text-yellow-400"
  }

  const getStatusBg = (status) => {
    return status === "online" ? "bg-green-500/10" : "bg-yellow-500/10"
  }

  const getLoadColor = (load) => {
    if (load > 80) return "bg-red-500"
    if (load > 60) return "bg-yellow-500"
    return "bg-blue-500"
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Серверы</h1>
          <p className="text-sm text-slate-400 mt-1">Всего: {servers.length} серверов</p>
        </div>
        <button className="btn-primary">
          <i className="fas fa-plus mr-2"></i>Добавить сервер
        </button>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="stat-card">
          <div className="flex items-center justify-between mb-2">
            <span className="text-slate-400 text-sm">Серверов онлайн</span>
            <i className="fas fa-server text-blue-400 text-xl"></i>
          </div>
          <p className="text-3xl font-bold">{servers.filter(s => s.status === 'online').length}/{servers.length}</p>
        </div>
        <div className="stat-card">
          <div className="flex items-center justify-between mb-2">
            <span className="text-slate-400 text-sm">Средняя нагрузка</span>
            <i className="fas fa-chart-line text-purple-400 text-xl"></i>
          </div>
          <p className="text-3xl font-bold">{Math.round(servers.reduce((a, b) => a + b.load, 0) / servers.length)}%</p>
        </div>
        <div className="stat-card">
          <div className="flex items-center justify-between mb-2">
            <span className="text-slate-400 text-sm">Всего пользователей</span>
            <i className="fas fa-users text-green-400 text-xl"></i>
          </div>
          <p className="text-3xl font-bold">{servers.reduce((a, b) => a + b.users, 0)}</p>
        </div>
      </div>

      {/* Servers Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {servers.map((server) => (
          <div key={server.id} className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 hover:border-slate-600 transition">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center">
                    <i className="fas fa-server text-blue-400"></i>
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">{server.id} - {server.name}</h3>
                    <p className="text-xs text-slate-400">{server.location}</p>
                  </div>
                </div>
              </div>
              <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusBg(server.status)} ${getStatusClass(server.status)} flex items-center gap-1`}>
                <span className="w-2 h-2 rounded-full bg-current"></span>
                {server.status === "online" ? "Онлайн" : "Внимание"}
              </span>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 gap-4 mb-4 pb-4 border-b border-slate-700/50">
              <div>
                <p className="text-xs text-slate-400 mb-1">IP адрес</p>
                <p className="text-sm font-mono text-slate-300">{server.ip}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400 mb-1">Uptime</p>
                <p className="text-sm text-green-400 font-medium">{server.uptime}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400 mb-1">Пользователей</p>
                <p className="text-sm font-semibold text-slate-300">{server.users}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400 mb-1">Пинг</p>
                <p className="text-sm text-slate-300">~24ms</p>
              </div>
            </div>

            {/* Load Bar */}
            <div className="mb-4">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm text-slate-300">Нагрузка</span>
                <span className={`text-sm font-semibold ${
                  server.load > 80 ? 'text-red-400' : server.load > 60 ? 'text-yellow-400' : 'text-green-400'
                }`}>{server.load}%</span>
              </div>
              <div className="w-full bg-slate-700/50 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all ${getLoadColor(server.load)}`}
                  style={{ width: `${server.load}%` }}
                ></div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-2">
              <button className="flex-1 btn-secondary text-sm">
                <i className="fas fa-edit mr-2"></i>Редактировать
              </button>
              <button className="flex-1 btn-secondary text-sm">
                <i className="fas fa-redo mr-2"></i>Перезагрузить
              </button>
              <button className="btn-secondary text-sm px-3">
                <i className="fas fa-ellipsis-v"></i>
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default Servers
