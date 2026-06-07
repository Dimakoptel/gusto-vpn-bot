import React from "react"
import { BrowserRouter as Router, Routes, Route } from "react-router-dom"
import Dashboard from "./views/Dashboard"
import Users from "./views/Users"
import Servers from "./views/Servers"
import Payments from "./views/Payments"

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-[#0F0F1A] text-white">
        <nav className="bg-[#1A1A2E] p-4 border-b border-[#FF6B35]/20">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-[#FF6B35] rounded-lg flex items-center justify-center font-bold">G</div>
            <h1 className="text-xl font-bold text-[#FF6B35]">GUSTO Admin</h1>
          </div>
        </nav>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/users" element={<Users />} />
          <Route path="/servers" element={<Servers />} />
          <Route path="/payments" element={<Payments />} />
        </Routes>
      </div>
    </Router>
  )
}

export default App
