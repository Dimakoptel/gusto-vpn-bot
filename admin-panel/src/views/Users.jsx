import React from "react"

function Users() {
  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-6 text-[#FF6B35]">👥 Пользователи</h2>
      <div className="bg-[#1A1A2E] rounded-xl overflow-hidden border border-white/5">
        <table className="w-full text-sm">
          <thead className="bg-[#0F0F1A] text-gray-400">
            <tr>
              <th className="p-4 text-left">ID</th>
              <th className="p-4 text-left">Telegram</th>
              <th className="p-4 text-left">Подписка</th>
              <th className="p-4 text-left">Статус</th>
            </tr>
          </thead>
          <tbody>
            {[1, 2, 3].map((i) => (
              <tr key={i} className="border-t border-white/5">
                <td className="p-4">{1000 + i}</td>
                <td className="p-4">@user_{i}</td>
                <td className="p-4">GUSTO Pro</td>
                <td className="p-4"><span className="text-[#00E676]">● Активен</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default Users
