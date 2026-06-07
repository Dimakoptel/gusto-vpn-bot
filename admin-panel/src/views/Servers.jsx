import React from "react"

function Servers() {
  const servers = [
    { name: "GUSTO-NL-1", location: "Амстердам", status: "online", load: 45 },
    { name: "GUSTO-DE-1", location: "Франкфурт", status: "warning", load: 87 },
    { name: "GUSTO-SG-1", location: "Сингапур", status: "online", load: 32 },
  ]

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-6 text-[#FF6B35]">🌐 Серверы</h2>
      <div className="grid gap-4">
        {servers.map((s) => (
          <div key={s.name} className="bg-[#1A1A2E] rounded-xl p-6 border border-white/5">
            <div className="flex justify-between items-center">
              <div>
                <h3 className="font-semibold">{s.name}</h3>
                <p className="text-sm text-gray-400">{s.location}</p>
              </div>
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${s.status === "online" ? "bg-[#00E676]" : "bg-[#FFC107]"}`}></span>
                <span className="text-sm">{s.status}</span>
              </div>
            </div>
            <div className="mt-4">
              <div className="w-full bg-[#0F0F1A] rounded-full h-2">
                <div className="bg-gradient-to-r from-[#FF6B35] to-[#00D9FF] h-2 rounded-full" style={{ width: `${s.load}%` }}></div>
              </div>
              <p className="text-xs text-gray-400 mt-1">CPU: {s.load}%</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default Servers
