import React from "react"
import { BrowserRouter as Router, Routes, Route } from "react-router-dom"
import Layout from "./components/Layout"
import Dashboard from "./views/Dashboard"
import Users from "./views/Users"
import Servers from "./views/Servers"
import Payments from "./views/Payments"
import BotSettings from "./views/BotSettings"
import ReferralSettings from "./views/ReferralSettings"
import AntifraudSettings from "./views/AntifraudSettings"
import NotificationSettings from "./views/NotificationSettings"
import SystemSettings from "./views/SystemSettings"

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/users" element={<Users />} />
          <Route path="/servers" element={<Servers />} />
          <Route path="/payments" element={<Payments />} />
          <Route path="/bot" element={<BotSettings />} />
          <Route path="/referral" element={<ReferralSettings />} />
          <Route path="/antifraud" element={<AntifraudSettings />} />
          <Route path="/notifications" element={<NotificationSettings />} />
          <Route path="/system" element={<SystemSettings />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App
