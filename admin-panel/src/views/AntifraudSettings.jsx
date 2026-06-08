import React, { useState, useEffect } from 'react'
import api from '../services/api'

const AntifraudSettings = () => {
  const [settings, setSettings] = useState({
    antifraud_enabled: true,
    antifraud_max_ips: 3,
    antifraud_max_countries: 2,
    antifraud_ban_hours: 24,
  })
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      const resp = await api.get('/api/settings/')
      setSettings(resp.data)
    } catch (e) {
      console.error('Failed to load settings:', e)
    }
  }

  const handleSave = async () => {
    setLoading(true)
    try {
      await api.patch('/api/settings/antifraud', settings)
      setMessage({ type: 'success', text: 'Настройки антифрода сохранены!' })
      setTimeout(() => setMessage(''), 3000)
    } catch (e) {
      setMessage({ type: 'error', text: 'Ошибка при сохранении' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">Антифрод система</h1>

      {message && (
        <div className={`mb-6 p-4 rounded-lg ${message.type === 'success' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
          <i className={`fas ${message.type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'} mr-2`}></i>
          {message.text}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Enable Antifraud */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 lg:col-span-2">
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.antifraud_enabled}
              onChange={e => setSettings({...settings, antifraud_enabled: e.target.checked})}
              className="w-5 h-5 rounded border-slate-600 text-blue-600 cursor-pointer"
            />
            <span className="text-slate-300 font-medium">Включить антифрод систему</span>
          </label>
        </div>

        {/* Max IPs */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <label className="block text-sm font-semibold text-slate-300 mb-3">
            <i className="fas fa-globe text-blue-400 mr-2"></i>Макс. уникальных IP за 24ч
          </label>
          <input
            type="number"
            min="1"
            max="20"
            value={settings.antifraud_max_ips}
            onChange={e => setSettings({...settings, antifraud_max_ips: parseInt(e.target.value)})}
            className="input-field"
          />
          <p className="text-xs text-slate-500 mt-2">При превышении - подписка ограничивается</p>
        </div>

        {/* Max Countries */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <label className="block text-sm font-semibold text-slate-300 mb-3">
            <i className="fas fa-map text-green-400 mr-2"></i>Максимум стран
          </label>
          <input
            type="number"
            min="1"
            max="10"
            value={settings.antifraud_max_countries}
            onChange={e => setSettings({...settings, antifraud_max_countries: parseInt(e.target.value)})}
            className="input-field"
          />
          <p className="text-xs text-slate-500 mt-2">При превышении - подписка ограничивается</p>
        </div>

        {/* Ban Duration */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <label className="block text-sm font-semibold text-slate-300 mb-3">
            <i className="fas fa-ban text-red-400 mr-2"></i>Время ограничения (часов)
          </label>
          <input
            type="number"
            min="1"
            max="720"
            value={settings.antifraud_ban_hours}
            onChange={e => setSettings({...settings, antifraud_ban_hours: parseInt(e.target.value)})}
            className="input-field"
          />
          <p className="text-xs text-slate-500 mt-2">На сколько часов ограничить подписку</p>
        </div>

        {/* Info Box */}
        <div className="bg-gradient-to-br from-blue-500/10 to-blue-600/10 border border-blue-500/20 rounded-xl p-6 lg:col-span-2">
          <h3 className="text-lg font-semibold text-blue-300 mb-3">
            <i className="fas fa-info-circle mr-2"></i>Как работает антифрод
          </h3>
          <ul className="space-y-2 text-slate-300 text-sm">
            <li><i className="fas fa-check text-green-400 mr-2"></i>Мониторит уникальные IP-адреса каждого клиента</li>\n            <li><i className="fas fa-check text-green-400 mr-2"></i>Отслеживает геолокацию подключений</li>\n            <li><i className="fas fa-check text-green-400 mr-2"></i>При превышении лимитов - ограничивает скорость</li>\n            <li><i className="fas fa-check text-green-400 mr-2"></i>Уведомляет администраторов о подозрительной активности</li>\n          </ul>\n        </div>\n      </div>\n\n      {/* Save Button */}\n      <div className="flex gap-3 mt-6">\n        <button onClick={handleSave} disabled={loading} className="btn-primary">\n          {loading ? (\n            <>\n              <i className="fas fa-spinner fa-spin mr-2"></i>Сохранение...\n            </>\n          ) : (\n            <>\n              <i className="fas fa-save mr-2"></i>Сохранить настройки\n            </>\n          )}\n        </button>\n        <button className="btn-secondary">\n          <i className="fas fa-redo mr-2"></i>Отменить\n        </button>\n      </div>\n    </div>\n  )\n}

export default AntifraudSettings
