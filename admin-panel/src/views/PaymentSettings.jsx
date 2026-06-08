import React, { useState, useEffect } from 'react'
import api from '../services/api'

const PaymentSettings = () => {
  const [settings, setSettings] = useState({
    cryptobot_token: '',
    cryptobot_enabled: false,
    yookassa_shop_id: '',
    yookassa_secret_key: '',
    yookassa_enabled: false,
    yookassa_fiscal_enabled: false,
    freekassa_id: '',
    freekassa_secret: '',
    freekassa_api_key: '',
    freekassa_enabled: false,
  })
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [testResult, setTestResult] = useState(null)

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
      await api.patch('/api/settings/payments', settings)
      setMessage({ type: 'success', text: 'Настройки платежей сохранены!' })
      setTimeout(() => setMessage(''), 3000)
    } catch (e) {
      setMessage({ type: 'error', text: 'Ошибка при сохранении' })
    } finally {
      setLoading(false)
    }
  }

  const testProvider = async (provider) => {
    setTestResult({ provider, status: 'testing' })
    try {
      const resp = await api.post(`/api/settings/payments/${provider}/test`)
      setTestResult({ provider, status: 'done', result: resp.data })
      setTimeout(() => setTestResult(null), 3000)
    } catch (e) {
      setTestResult({ provider, status: 'error', error: e.message })
      setTimeout(() => setTestResult(null), 3000)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">Настройки платежей</h1>

      {message && (
        <div className={`mb-6 p-4 rounded-lg ${message.type === 'success' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
          <i className={`fas ${message.type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'} mr-2`}></i>
          {message.text}
        </div>
      )}

      <div className="space-y-6">
        {/* CryptoBot Provider */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">
              <i className="fas fa-coins text-yellow-400 mr-2"></i>CryptoBot
            </h3>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.cryptobot_enabled}
                onChange={e => setSettings({...settings, cryptobot_enabled: e.target.checked})}
                className="w-5 h-5 rounded border-slate-600 text-blue-600 cursor-pointer"
              />
              <span className="text-sm text-slate-400">Активно</span>
            </label>
          </div>
          {settings.cryptobot_enabled && (
            <>
              <div className="mb-4">
                <label className="block text-sm font-semibold text-slate-300 mb-2">API Token</label>
                <input
                  type="password"
                  value={settings.cryptobot_token || ''}
                  onChange={e => setSettings({...settings, cryptobot_token: e.target.value})}
                  placeholder="CryptoBot API Token"
                  className="input-field"
                />
              </div>
              <button onClick={() => testProvider('cryptobot')} className="btn-secondary text-sm">
                <i className="fas fa-plug mr-2"></i>Проверить подключение
              </button>
            </>
          )}
        </div>

        {/* YooKassa Provider */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">
              <i className="fas fa-credit-card text-red-400 mr-2"></i>ЮKassa
            </h3>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.yookassa_enabled}
                onChange={e => setSettings({...settings, yookassa_enabled: e.target.checked})}
                className="w-5 h-5 rounded border-slate-600 text-blue-600 cursor-pointer"
              />
              <span className="text-sm text-slate-400">Активно</span>
            </label>
          </div>
          {settings.yookassa_enabled && (
            <>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-semibold text-slate-300 mb-2">Shop ID</label>
                  <input
                    type="text"
                    value={settings.yookassa_shop_id || ''}
                    onChange={e => setSettings({...settings, yookassa_shop_id: e.target.value})}
                    placeholder="123456"
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-slate-300 mb-2">Secret Key</label>
                  <input
                    type="password"
                    value={settings.yookassa_secret_key || ''}
                    onChange={e => setSettings({...settings, yookassa_secret_key: e.target.value})}
                    placeholder="test_... или live_..."
                    className="input-field"
                  />
                </div>
              </div>
              <label className="flex items-center gap-3 cursor-pointer mb-4">
                <input
                  type="checkbox"
                  checked={settings.yookassa_fiscal_enabled}
                  onChange={e => setSettings({...settings, yookassa_fiscal_enabled: e.target.checked})}
                  className="w-5 h-5 rounded border-slate-600 text-blue-600 cursor-pointer"
                />
                <span className="text-slate-300 text-sm">Фискализация (54-ФЗ)</span>
              </label>
              <button onClick={() => testProvider('yookassa')} className="btn-secondary text-sm">
                <i className="fas fa-plug mr-2"></i>Проверить подключение
              </button>
            </>
          )}
        </div>

        {/* FreeKassa Provider */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">
              <i className="fas fa-money-bill text-green-400 mr-2"></i>FreeKassa
            </h3>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.freekassa_enabled}
                onChange={e => setSettings({...settings, freekassa_enabled: e.target.checked})}
                className="w-5 h-5 rounded border-slate-600 text-blue-600 cursor-pointer"
              />
              <span className="text-sm text-slate-400">Активно</span>
            </label>
          </div>
          {settings.freekassa_enabled && (
            <>
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-semibold text-slate-300 mb-2">ID магазина</label>
                  <input
                    type="text"
                    value={settings.freekassa_id || ''}
                    onChange={e => setSettings({...settings, freekassa_id: e.target.value})}
                    placeholder="12345"
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-slate-300 mb-2">Секретный ключ</label>
                  <input
                    type="password"
                    value={settings.freekassa_secret || ''}
                    onChange={e => setSettings({...settings, freekassa_secret: e.target.value})}
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-slate-300 mb-2">API Key</label>
                  <input
                    type="password"
                    value={settings.freekassa_api_key || ''}
                    onChange={e => setSettings({...settings, freekassa_api_key: e.target.value})}
                    className="input-field"
                  />
                </div>
              </div>
              <button onClick={() => testProvider('freekassa')} className="btn-secondary text-sm">
                <i className="fas fa-plug mr-2"></i>Проверить подключение
              </button>
            </>
          )}
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
              <i className="fas fa-save mr-2"></i>Сохранить все настройки
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

export default PaymentSettings
