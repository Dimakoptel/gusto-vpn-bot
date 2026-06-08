import React, { useState, useEffect } from 'react'
import api from '../services/api'

const SystemSettings = () => {
  const [settings, setSettings] = useState({
    app_name: 'Gusto VPN',
    app_logo_url: '',
    maintenance_mode: false,
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
      await api.patch('/api/settings/system', settings)
      setMessage({ type: 'success', text: 'Системные настройки сохранены!' })
      setTimeout(() => setMessage(''), 3000)
    } catch (e) {
      setMessage({ type: 'error', text: 'Ошибка при сохранении' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">Системные настройки</h1>

      {message && (
        <div className={`mb-6 p-4 rounded-lg ${message.type === 'success' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
          <i className={`fas ${message.type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'} mr-2`}></i>
          {message.text}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* App Name */}\n        <div className=\"bg-slate-800/50 border border-slate-700 rounded-xl p-6\">\n          <label className=\"block text-sm font-semibold text-slate-300 mb-3\">\n            <i className=\"fas fa-cube text-blue-400 mr-2\"></i>Название приложения\n          </label>\n          <input\n            type=\"text\"\n            value={settings.app_name || ''}\n            onChange={e => setSettings({...settings, app_name: e.target.value})}\n            placeholder=\"Gusto VPN\"\n            className=\"input-field\"\n          />\n        </div>\n\n        {/* Logo URL */}\n        <div className=\"bg-slate-800/50 border border-slate-700 rounded-xl p-6\">\n          <label className=\"block text-sm font-semibold text-slate-300 mb-3\">\n            <i className=\"fas fa-image text-purple-400 mr-2\"></i>URL логотипа\n          </label>\n          <input\n            type=\"text\"\n            value={settings.app_logo_url || ''}\n            onChange={e => setSettings({...settings, app_logo_url: e.target.value})}\n            placeholder=\"https://example.com/logo.png\"\n            className=\"input-field\"\n          />\n        </div>\n\n        {/* Maintenance Mode */}\n        <div className=\"bg-slate-800/50 border border-slate-700 rounded-xl p-6 lg:col-span-2\">\n          <label className=\"flex items-center gap-3 cursor-pointer mb-3\">\n            <input\n              type=\"checkbox\"\n              checked={settings.maintenance_mode}\n              onChange={e => setSettings({...settings, maintenance_mode: e.target.checked})}\n              className=\"w-5 h-5 rounded border-slate-600 text-yellow-600 cursor-pointer\"\n            />\n            <span className=\"text-slate-300 font-medium\">\n              <i className=\"fas fa-tools text-yellow-400 mr-2\"></i>Режим технических работ\n            </span>\n          </label>\n          <div className=\"bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3\">\n            <p className=\"text-xs text-yellow-400\">\n              <i className=\"fas fa-info-circle mr-2\"></i>\nПри включении бот будет показывать \"Технические работы\" всем пользователям (кроме администраторов)\n            </p>\n          </div>\n        </div>\n      </div>\n\n      {/* Save Button */}\n      <div className=\"flex gap-3 mt-6\">\n        <button onClick={handleSave} disabled={loading} className=\"btn-primary\">\n          {loading ? (\n            <>\n              <i className=\"fas fa-spinner fa-spin mr-2\"></i>Сохранение...\n            </>\n          ) : (\n            <>\n              <i className=\"fas fa-save mr-2\"></i>Сохранить настройки\n            </>\n          )}\n        </button>\n        <button className=\"btn-secondary\">\n          <i className=\"fas fa-redo mr-2\"></i>Отменить\n        </button>\n      </div>\n    </div>\n  )\n}\n\nexport default SystemSettings
