import React, { useState, useEffect } from 'react'
import api from '../services/api'

const NotificationSettings = () => {
  const [settings, setSettings] = useState({
    notify_expiry_3days: true,
    notify_expiry_1day: true,
    notify_expiry_today: true,
    notify_low_traffic_gb: 5,
    notify_channel_id: '',
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
      await api.patch('/api/settings/notifications', settings)
      setMessage({ type: 'success', text: 'Настройки уведомлений сохранены!' })
      setTimeout(() => setMessage(''), 3000)
    } catch (e) {
      setMessage({ type: 'error', text: 'Ошибка при сохранении' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">Уведомления</h1>

      {message && (
        <div className={`mb-6 p-4 rounded-lg ${message.type === 'success' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
          <i className={`fas ${message.type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'} mr-2`}></i>
          {message.text}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Expiry Notifications */}\n        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 lg:col-span-2\">\n          <h3 className=\"text-lg font-semibold text-white mb-4\">\n            <i className=\"fas fa-hourglass-end mr-2 text-yellow-400\"></i>Уведомления об истечении подписки\n          </h3>\n          <div className=\"space-y-3\">\n            <label className=\"flex items-center gap-3 cursor-pointer\">\n              <input\n                type=\"checkbox\"\n                checked={settings.notify_expiry_3days}\n                onChange={e => setSettings({...settings, notify_expiry_3days: e.target.checked})}\n                className=\"w-5 h-5 rounded border-slate-600 text-blue-600 cursor-pointer\"\n              />\n              <span className=\"text-slate-300\">Отправить уведомление за 3 дня до истечения</span>\n            </label>\n            <label className=\"flex items-center gap-3 cursor-pointer\">\n              <input\n                type=\"checkbox\"\n                checked={settings.notify_expiry_1day}\n                onChange={e => setSettings({...settings, notify_expiry_1day: e.target.checked})}\n                className=\"w-5 h-5 rounded border-slate-600 text-blue-600 cursor-pointer\"\n              />\n              <span className=\"text-slate-300\">Отправить уведомление за 1 день до истечения</span>\n            </label>\n            <label className=\"flex items-center gap-3 cursor-pointer\">\n              <input\n                type=\"checkbox\"\n                checked={settings.notify_expiry_today}\n                onChange={e => setSettings({...settings, notify_expiry_today: e.target.checked})}\n                className=\"w-5 h-5 rounded border-slate-600 text-blue-600 cursor-pointer\"\n              />\n              <span className=\"text-slate-300\">Отправить уведомление в день истечения</span>\n            </label>\n          </div>\n        </div>\n\n        {/* Traffic Notifications */}\n        <div className=\"bg-slate-800/50 border border-slate-700 rounded-xl p-6\">\n          <label className=\"block text-sm font-semibold text-slate-300 mb-3\">\n            <i className=\"fas fa-tachometer-alt text-purple-400 mr-2\"></i>Порог оповещения о трафике (GB)\n          </label>\n          <input\n            type=\"number\"\n            min=\"0.1\"\n            max=\"1000\"\n            step=\"0.1\"\n            value={settings.notify_low_traffic_gb}\n            onChange={e => setSettings({...settings, notify_low_traffic_gb: parseFloat(e.target.value)})}\n            className=\"input-field\"\n          />\n          <p className=\"text-xs text-slate-500 mt-2\">Уведомлять когда осталось менее X GB трафика</p>\n        </div>\n\n        {/* Channel ID */}\n        <div className=\"bg-slate-800/50 border border-slate-700 rounded-xl p-6\">\n          <label className=\"block text-sm font-semibold text-slate-300 mb-3\">\n            <i className=\"fas fa-comments mr-2 text-blue-400\"></i>ID канала для массовых уведомлений\n          </label>\n          <input\n            type=\"text\"\n            value={settings.notify_channel_id || ''}\n            onChange={e => setSettings({...settings, notify_channel_id: e.target.value})}\n            placeholder=\"-1001234567890\"\n            className=\"input-field\"\n          />\n          <p className=\"text-xs text-slate-500 mt-2\">Для публикации новостей, акций и объявлений</p>\n        </div>\n      </div>\n\n      {/* Save Button */}\n      <div className=\"flex gap-3 mt-6\">\n        <button onClick={handleSave} disabled={loading} className=\"btn-primary\">\n          {loading ? (\n            <>\n              <i className=\"fas fa-spinner fa-spin mr-2\"></i>Сохранение...\n            </>\n          ) : (\n            <>\n              <i className=\"fas fa-save mr-2\"></i>Сохранить настройки\n            </>\n          )}\n        </button>\n        <button className=\"btn-secondary\">\n          <i className=\"fas fa-redo mr-2\"></i>Отменить\n        </button>\n      </div>\n    </div>\n  )\n}

export default NotificationSettings
