import React from "react"

function Dashboard() {
  const stats = [
    { label: "Пользователи", value: "1,247", color: "#FF6B35" },
    { label: "Активные подписки", value: "892", color: "#00E676" },
    { label: "Серверы онлайн", value: "5/6", color: "#00D9FF" },
    { label: "Выручка (30д)", value: "89,400₽", color: "#FFC107" },
  ]

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-6 text-[#FF6B35]">🚀 GUSTO Dashboard</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((s) => (
          <div key={s.label} className="bg-[#1A1A2E] rounded-xl p-6 border border-white/5">
            <p className="text-sm text-gray-400 mb-1">{s.label}</p>
            <p className="text-2xl font-bold" style={{ color: s.color }}>{s.value}</p>
          </div>
        ))}
      </div>
      <div className="mt-8 bg-[#1A1A2E] rounded-xl p-6 border border-white/5">
        <h3 className="text-lg font-semibold mb-4">Последние действия</h3>
        <div className="space-y-3">
          {[
            "🟢 Новый пользователь @ivan_p",
            "💰 Платеж 299₽ от @anna_s",
            "⚠️ Высокая нагрузка на GUSTO-DE-1",
          ].map((item, i) => (
            <div key={i} className="p-3 bg-[#0F0F1A] rounded-lg text-sm">{item}</div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default Dashboard
