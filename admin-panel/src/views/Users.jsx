import React, { useState } from "react"

function Users() {
  const [users] = useState([
    { id: 1024, username: "@ivan_petrov", email: "ivan@example.com", subscription: "GUSTO Pro", status: "active", joinDate: "2024-06-01", payment: "299₽" },
    { id: 1025, username: "@anna_sokolova", email: "anna@example.com", subscription: "GUSTO Plus", status: "active", joinDate: "2024-06-02", payment: "199₽" },
    { id: 1026, username: "@dmitry_k", email: "dmitry@example.com", subscription: "GUSTO Basic", status: "inactive", joinDate: "2024-05-15", payment: "99₽" },
    { id: 1027, username: "@olga_m", email: "olga@example.com", subscription: "GUSTO Pro", status: "active", joinDate: "2024-06-05", payment: "299₽" },
    { id: 1028, username: "@nikita_s", email: "nikita@example.com", subscription: "Trial", status: "trial", joinDate: "2024-06-07", payment: "Бесплатно" },
  ])

  const getStatusBadge = (status) => {
    const badges = {
      active: { color: "bg-green-500/10 text-green-400", icon: "fas fa-check-circle", text: "Активен" },
      inactive: { color: "bg-red-500/10 text-red-400", icon: "fas fa-times-circle", text: "Неактивен" },
      trial: { color: "bg-blue-500/10 text-blue-400", icon: "fas fa-hourglass-end", text: "Trial" }
    }
    return badges[status]
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Пользователи</h1>
          <p className="text-sm text-slate-400 mt-1">Всего: {users.length} пользователей</p>
        </div>
        <button className="btn-primary">
          <i className="fas fa-plus mr-2"></i>Добавить пользователя
        </button>
      </div>

      {/* Filter Bar */}
      <div className="flex gap-3 mb-6">
        <input
          type="text"
          placeholder="Поиск по имени..."
          className="flex-1 input-field"
        />
        <select className="input-field w-32">
          <option>Все</option>
          <option>Активные</option>
          <option>Неактивные</option>
        </select>
      </div>

      {/* Users Table */}
      <div className="bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-700/50 border-b border-slate-700">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-semibold text-slate-300">ID</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-slate-300">Пользователь</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-slate-300">Email</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-slate-300">Подписка</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-slate-300">Статус</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-slate-300">Дата присоединения</th>
              <th className="px-6 py-3 text-right text-xs font-semibold text-slate-300">Действия</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/50">
            {users.map((user) => {
              const badge = getStatusBadge(user.status)
              return (
                <tr key={user.id} className="hover:bg-slate-700/20 transition">
                  <td className="px-6 py-4 text-sm text-slate-300">#{user.id}</td>
                  <td className="px-6 py-4 text-sm">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-xs font-bold text-white">
                        {user.username.charAt(1).toUpperCase()}
                      </div>
                      <span className="text-slate-200">{user.username}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-400">{user.email}</td>
                  <td className="px-6 py-4 text-sm text-slate-300">{user.subscription}</td>
                  <td className="px-6 py-4 text-sm">
                    <span className={`inline-flex items-center gap-2 px-3 py-1 rounded-full ${badge.color} text-xs font-medium`}>
                      <i className={badge.icon}></i>
                      {badge.text}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-400">{user.joinDate}</td>
                  <td className="px-6 py-4 text-sm text-right">
                    <button className="text-blue-400 hover:text-blue-300 transition mr-3">
                      <i className="fas fa-edit"></i>
                    </button>
                    <button className="text-red-400 hover:text-red-300 transition">
                      <i className="fas fa-trash"></i>
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
        <p className="text-sm text-slate-400">Показано 5 из {users.length} записей</p>
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

export default Users
