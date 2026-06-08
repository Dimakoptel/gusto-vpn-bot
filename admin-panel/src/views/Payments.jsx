import React, { useState } from "react"

function Payments() {
  const [payments] = useState([
    { id: "PAY-2841", user: "@ivan_petrov", email: "ivan@example.com", amount: "299₽", provider: "CryptoBot", status: "completed", date: "2024-06-08 14:32" },
    { id: "PAY-2842", user: "@anna_sokolova", email: "anna@example.com", amount: "599₽", provider: "YooKassa", status: "completed", date: "2024-06-08 12:15" },
    { id: "PAY-2843", user: "@dmitry_k", email: "dmitry@example.com", amount: "199₽", provider: "FreeKassa", status: "pending", date: "2024-06-08 10:45" },
    { id: "PAY-2844", user: "@olga_m", email: "olga@example.com", amount: "299₽", provider: "Stripe", status: "completed", date: "2024-06-08 09:20" },
    { id: "PAY-2845", user: "@nikita_s", email: "nikita@example.com", amount: "99₽", provider: "CryptoBot", status: "failed", date: "2024-06-07 23:50" },
  ])

  const getStatusBadge = (status) => {
    const badges = {
      completed: { color: "bg-green-500/10 text-green-400", icon: "fas fa-check-circle", text: "Успешно" },
      pending: { color: "bg-yellow-500/10 text-yellow-400", icon: "fas fa-hourglass-end", text: "Ожидает" },
      failed: { color: "bg-red-500/10 text-red-400", icon: "fas fa-times-circle", text: "Ошибка" }
    }
    return badges[status]
  }

  const stats = [
    { label: "Всего платежей", value: payments.length, icon: "fas fa-credit-card", color: "blue" },
    { label: "Успешных", value: payments.filter(p => p.status === 'completed').length, icon: "fas fa-check-circle", color: "green" },
    { label: "На рассмотрении", value: payments.filter(p => p.status === 'pending').length, icon: "fas fa-hourglass-end", color: "yellow" },
    { label: "Ошибок", value: payments.filter(p => p.status === 'failed').length, icon: "fas fa-times-circle", color: "red" }
  ]

  const getColorClasses = (color) => {
    const colors = {
      blue: "bg-blue-500/10 text-blue-400",
      green: "bg-green-500/10 text-green-400",
      yellow: "bg-yellow-500/10 text-yellow-400",
      red: "bg-red-500/10 text-red-400"
    }
    return colors[color]
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Платежи</h1>
          <p className="text-sm text-slate-400 mt-1">Управление и мониторинг всех платежей</p>
        </div>
        <button className="btn-primary">
          <i className="fas fa-download mr-2"></i>Экспортировать
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {stats.map((stat) => (
          <div key={stat.label} className="stat-card">
            <div className="flex items-center justify-between mb-3">
              <span className="text-slate-400 text-sm">{stat.label}</span>
              <div className={`w-10 h-10 rounded-lg ${getColorClasses(stat.color)} flex items-center justify-center`}>
                <i className={stat.icon}></i>
              </div>
            </div>
            <p className="text-3xl font-bold">{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Filter Bar */}
      <div className="flex gap-3 mb-6">
        <input
          type="text"
          placeholder="Поиск по ID платежа или пользователю..."
          className="flex-1 input-field"
        />
        <select className="input-field w-40">
          <option>Все статусы</option>
          <option>Успешно</option>
          <option>Ожидает</option>
          <option>Ошибка</option>
        </select>
        <select className="input-field w-40">
          <option>Все провайдеры</option>
          <option>CryptoBot</option>
          <option>YooKassa</option>
          <option>FreeKassa</option>
          <option>Stripe</option>
        </select>
      </div>

      {/* Payments Table */}
      <div className="bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-700/50 border-b border-slate-700">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-semibold text-slate-300">ID платежа</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-slate-300">Пользователь</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-slate-300">Провайдер</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-slate-300">Сумма</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-slate-300">Статус</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-slate-300">Дата и время</th>
              <th className="px-6 py-3 text-right text-xs font-semibold text-slate-300">Действия</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/50">
            {payments.map((payment) => {
              const badge = getStatusBadge(payment.status)
              return (
                <tr key={payment.id} className="hover:bg-slate-700/20 transition">
                  <td className="px-6 py-4 text-sm font-mono text-blue-400">{payment.id}</td>
                  <td className="px-6 py-4 text-sm">
                    <div className="flex flex-col">
                      <span className="text-slate-200 font-medium">{payment.user}</span>
                      <span className="text-xs text-slate-500">{payment.email}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <span className="inline-flex items-center px-3 py-1 rounded-full bg-slate-700/50 text-slate-300 text-xs font-medium">
                      {payment.provider}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm font-semibold text-slate-200">{payment.amount}</td>
                  <td className="px-6 py-4 text-sm">
                    <span className={`inline-flex items-center gap-2 px-3 py-1 rounded-full ${badge.color} text-xs font-medium`}>
                      <i className={badge.icon}></i>
                      {badge.text}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-400">{payment.date}</td>
                  <td className="px-6 py-4 text-sm text-right">
                    <button className="text-blue-400 hover:text-blue-300 transition mr-3">
                      <i className="fas fa-eye"></i>
                    </button>
                    <button className="text-slate-400 hover:text-slate-300 transition">
                      <i className="fas fa-ellipsis-v"></i>
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between mt-6">
        <p className="text-sm text-slate-400">Показано 5 из {payments.length} платежей</p>
        <div className="flex gap-2">
          <button className="btn-secondary">
            <i className="fas fa-chevron-left mr-2"></i>Назад
          </button>
          <button className="btn-secondary">
            Далее<i className="fas fa-chevron-right ml-2"></i>
          </button>
        </div>
      </div>
    </div>
  )
}

export default Payments
