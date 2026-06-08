import React, { useState, useEffect } from 'react'
import api from '../services/api'

const BotSettings = () => {
  const [settings, setSettings] = useState({
    bot_token: '',
    admin_ids: [],
    support_username: '',
    welcome_message: 'Добро пожаловать в Gusto VPN!',
  })
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [adminInput, setAdminInput] = useState('')

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
      await api.patch('/api/settings/bot', settings)
      setMessage({ type: 'success', text: 'Настройки бота сохранены!' })
      setTimeout(() => setMessage(''), 3000)
    } catch (e) {
      setMessage({ type: 'error', text: 'Ошибка при сохранении' })
    } finally {
      setLoading(false)
    }
  }

  const addAdmin = () => {
    if (adminInput && !settings.admin_ids.includes(adminInput)) {
      setSettings({
        ...settings,
        admin_ids: [...settings.admin_ids, adminInput]
      })
      setAdminInput('')
    }
  }

  const removeAdmin = (id) => {
    setSettings({
      ...settings,
      admin_ids: settings.admin_ids.filter(a => a !== id)
    })
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">Настройки бота</h1>

      {message && (
        <div className={`mb-6 p-4 rounded-lg ${message.type === 'success' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
          <i className={`fas ${message.type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'} mr-2`}></i>
          {message.text}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Bot Token */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 lg:col-span-2">
          <label className="block text-sm font-semibold text-slate-300 mb-3">
            <i className="fas fa-key mr-2"></i>Токен бота (от BotFather)
          </label>
          <input
            type="password"
            value={settings.bot_token || ''}
            onChange={e => setSettings({...settings, bot_token: e.target.value})}
            placeholder="123456:ABCdefGHIjklmnoPQRstuvWXyz"
            className="input-field"
          />
          <p className="text-xs text-slate-500 mt-2">Храните в безопасности. Этот токен дает полный доступ к боту.</p>
        </div>

        {/* Support Username */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <label className="block text-sm font-semibold text-slate-300 mb-3">
            <i className="fas fa-headset mr-2"></i>Username поддержки
          </label>
          <input
            type="text"
            value={settings.support_username || ''}
            onChange={e => setSettings({...settings, support_username: e.target.value})}
            placeholder="@gusto_support"
            className="input-field"
          />
        </div>

        {/* Admin IDs */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <label className="block text-sm font-semibold text-slate-300 mb-3">
            <i className="fas fa-shield-alt mr-2"></i>IDs администраторов
          </label>
          <div className="flex gap-2 mb-3">
            <input
              type="text"
              value={adminInput}
              onChange={e => setAdminInput(e.target.value)}
              placeholder="Введите ID администратора"
              className="flex-1 input-field"
            />
            <button onClick={addAdmin} className="btn-primary px-4">
              <i className="fas fa-plus"></i>
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {settings.admin_ids?.map(id => (
              <div key={id} className="bg-blue-500/10 text-blue-400 px-3 py-1 rounded-full flex items-center gap-2 text-sm">
                <span>{id}</span>
                <button onClick={() => removeAdmin(id)} className="hover:text-blue-300">
                  <i className="fas fa-times"></i>
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Welcome Message */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 lg:col-span-2">
          <label className="block text-sm font-semibold text-slate-300 mb-3">
            <i className="fas fa-comment mr-2"></i>Приветственное сообщение
          </label>
          <textarea
            value={settings.welcome_message || ''}
            onChange={e => setSettings({...settings, welcome_message: e.target.value})}
            rows="4"
            className="input-field resize-none"
            placeholder="Введите текст приветственного сообщения"
          ></textarea>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex gap-3 mt-6">
        <button onClick={handleSave} disabled={loading} className="btn-primary">
          {loading ? (
            <>
              <i className="fas fa-spinner fa-spin mr-2"></i>Сохранение...
            </>
          ) : (
            <>
              <i className="fas fa-save mr-2"></i>Сохранить настройки
            </>
          )}
        </button>
        <button className="btn-secondary">
          <i className="fas fa-redo mr-2"></i>Отменить
        </button>
      </div>
    </div>
  )
}

export default BotSettings
