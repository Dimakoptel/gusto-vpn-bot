import React, { useState, useEffect } from 'react'
import api from '../services/api'

const ReferralSettings = () => {
  const [settings, setSettings] = useState({
    referral_enabled: true,
    referral_level1_percent: 30,
    referral_level2_percent: 15,
    referral_level3_percent: 5,
    referral_min_payout: 500,
  })
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [previewAmount, setPreviewAmount] = useState(1000)

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
      await api.patch('/api/settings/referral', settings)
      setMessage({ type: 'success', text: 'Настройки рефералки сохранены!' })
      setTimeout(() => setMessage(''), 3000)
    } catch (e) {
      setMessage({ type: 'error', text: 'Ошибка при сохранении' })
    } finally {
      setLoading(false)
    }
  }

  const calculatePreview = () => {
    const l1 = previewAmount * (settings.referral_level1_percent / 100)
    const l2 = previewAmount * (settings.referral_level2_percent / 100)
    const l3 = previewAmount * (settings.referral_level3_percent / 100)
    return { l1, l2, l3, total: l1 + l2 + l3 }
  }

  const preview = calculatePreview()

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">Реферальная система</h1>

      {message && (
        <div className={`mb-6 p-4 rounded-lg ${message.type === 'success' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
          <i className={`fas ${message.type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'} mr-2`}></i>
          {message.text}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Enable Referral */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 lg:col-span-2">
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.referral_enabled}
              onChange={e => setSettings({...settings, referral_enabled: e.target.checked})}
              className="w-5 h-5 rounded border-slate-600 text-blue-600 cursor-pointer"
            />
            <span className="text-slate-300 font-medium">Включить реферальную систему</span>
          </label>
        </div>

        {/* Level 1 */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <label className="block text-sm font-semibold text-slate-300 mb-3">
            <i className="fas fa-trophy text-yellow-400 mr-2"></i>1 уровень (%)
          </label>
          <input
            type="number"
            min="0"
            max="100"
            value={settings.referral_level1_percent}
            onChange={e => setSettings({...settings, referral_level1_percent: parseFloat(e.target.value)})}
            className="input-field"
          />
          <p className="text-xs text-slate-500 mt-2">Процент для прямых рефералов</p>
        </div>

        {/* Level 2 */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <label className="block text-sm font-semibold text-slate-300 mb-3">
            <i className="fas fa-medal text-gray-400 mr-2"></i>2 уровень (%)
          </label>
          <input
            type="number"
            min="0"
            max="100"
            value={settings.referral_level2_percent}
            onChange={e => setSettings({...settings, referral_level2_percent: parseFloat(e.target.value)})}
            className="input-field"
          />
          <p className="text-xs text-slate-500 mt-2">Процент для рефералов уровня 2</p>
        </div>

        {/* Level 3 */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <label className="block text-sm font-semibold text-slate-300 mb-3">
            <i className="fas fa-gem text-blue-400 mr-2"></i>3 уровень (%)
          </label>
          <input
            type="number"
            min="0"
            max="100"
            value={settings.referral_level3_percent}
            onChange={e => setSettings({...settings, referral_level3_percent: parseFloat(e.target.value)})}
            className="input-field"
          />
          <p className="text-xs text-slate-500 mt-2">Процент для рефералов уровня 3</p>
        </div>

        {/* Min Payout */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <label className="block text-sm font-semibold text-slate-300 mb-3">
            <i className="fas fa-wallet text-green-400 mr-2"></i>Минимум для вывода (₽)
          </label>
          <input
            type="number"
            min="0"
            value={settings.referral_min_payout}
            onChange={e => setSettings({...settings, referral_min_payout: parseFloat(e.target.value)})}
            className="input-field"
          />
        </div>

        {/* Preview */}
        <div className="bg-gradient-to-br from-slate-800/50 to-slate-700/30 border border-slate-700 rounded-xl p-6 lg:col-span-2">
          <h3 className="text-lg font-semibold text-white mb-4">Расчет реферальных начислений</h3>
          <div className="mb-4">
            <label className="block text-sm font-semibold text-slate-300 mb-2">Сумма платежа (₽):</label>
            <input
              type="number"
              value={previewAmount}
              onChange={e => setPreviewAmount(parseFloat(e.target.value) || 0)}
              className="input-field"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-700/50 rounded-lg p-3">
              <p className="text-xs text-slate-400">1 уровень</p>
              <p className="text-lg font-bold text-yellow-400">{preview.l1.toFixed(2)}₽</p>
            </div>
            <div className="bg-slate-700/50 rounded-lg p-3">
              <p className="text-xs text-slate-400">2 уровень</p>
              <p className="text-lg font-bold text-gray-300">{preview.l2.toFixed(2)}₽</p>
            </div>
            <div className="bg-slate-700/50 rounded-lg p-3">
              <p className="text-xs text-slate-400">3 уровень</p>
              <p className="text-lg font-bold text-blue-300">{preview.l3.toFixed(2)}₽</p>
            </div>
            <div className="bg-blue-500/10 rounded-lg p-3">
              <p className="text-xs text-blue-400">Всего</p>
              <p className="text-lg font-bold text-blue-400">{preview.total.toFixed(2)}₽</p>
            </div>
          </div>
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

export default ReferralSettings
