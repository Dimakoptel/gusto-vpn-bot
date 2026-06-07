import React, { useState, useEffect } from 'react';
import { CreditCard, ToggleLeft, ToggleRight, Eye, EyeOff, TestTube, CheckCircle, XCircle } from 'lucide-react';
import api from '../services/api';

const PROVIDERS = [
  { id: 'cryptobot', name: 'CryptoBot', color: 'blue', icon: '💎' },
  { id: 'yookassa', name: 'YooKassa', color: 'green', icon: '💳' },
  { id: 'freekassa', name: 'FreeKassa', color: 'orange', icon: '💰' },
];

export default function PaymentSettings({ settings, onSave, saving }) {
  const [form, setForm] = useState({
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
  });
  const [showSecrets, setShowSecrets] = useState({});
  const [testResults, setTestResults] = useState({});
  const [testing, setTesting] = useState({});

  useEffect(() => {
    if (settings) {
      setForm({
        cryptobot_token: settings.cryptobot_token || '',
        cryptobot_enabled: settings.cryptobot_enabled || false,
        yookassa_shop_id: settings.yookassa_shop_id || '',
        yookassa_secret_key: settings.yookassa_secret_key || '',
        yookassa_enabled: settings.yookassa_enabled || false,
        yookassa_fiscal_enabled: settings.yookassa_fiscal_enabled || false,
        freekassa_id: settings.freekassa_id || '',
        freekassa_secret: settings.freekassa_secret || '',
        freekassa_api_key: settings.freekassa_api_key || '',
        freekassa_enabled: settings.freekassa_enabled || false,
      });
    }
  }, [settings]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm({ ...form, [name]: type === 'checkbox' ? checked : value });
  };

  const handleToggle = (field) => {
    setForm({ ...form, [field]: !form[field] });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave({
      cryptobot_token: form.cryptobot_token,
      cryptobot_enabled: form.cryptobot_enabled,
      yookassa_shop_id: form.yookassa_shop_id,
      yookassa_secret_key: form.yookassa_secret_key,
      yookassa_enabled: form.yookassa_enabled,
      yookassa_fiscal_enabled: form.yookassa_fiscal_enabled,
      freekassa_id: form.freekassa_id,
      freekassa_secret: form.freekassa_secret,
      freekassa_api_key: form.freekassa_api_key,
      freekassa_enabled: form.freekassa_enabled,
    });
  };

  const testProvider = async (provider) => {
    setTesting({ ...testing, [provider]: true });
    setTestResults({ ...testResults, [provider]: null });
    try {
      const res = await api.get(`/settings/payments/${provider}/test`);
      setTestResults({ ...testResults, [provider]: res.data });
    } catch (err) {
      setTestResults({ ...testResults, [provider]: { status: 'error', message: err.message } });
    } finally {
      setTesting({ ...testing, [provider]: false });
    }
  };

  const toggleShowSecret = (field) => {
    setShowSecrets({ ...showSecrets, [field]: !showSecrets[field] });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      <div className="flex items-center gap-2 mb-4">
        <CreditCard className="w-5 h-5 text-blue-600" />
        <h2 className="text-lg font-semibold">Настройки платежных систем</h2>
      </div>

      {PROVIDERS.map(provider => {
        const isEnabled = form[`${provider.id}_enabled`];
        const result = testResults[provider.id];

        return (
          <div key={provider.id} className={`border rounded-lg p-6 ${isEnabled ? 'border-' + provider.color + '-200 bg-' + provider.color + '-50' : 'border-gray-200'}`}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <span className="text-2xl">{provider.icon}</span>
                <div>
                  <h3 className="font-semibold text-gray-900">{provider.name}</h3>
                  <p className="text-sm text-gray-500">
                    {isEnabled ? 'Активен' : 'Отключен'}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => handleToggle(`${provider.id}_enabled`)}
                className="flex items-center gap-2"
              >
                {isEnabled ? (
                  <ToggleRight className={`w-8 h-8 text-${provider.color}-600`} />
                ) : (
                  <ToggleLeft className="w-8 h-8 text-gray-400" />
                )}
              </button>
            </div>

            {isEnabled && (
              <div className="space-y-4 mt-4">
                {provider.id === 'cryptobot' && (
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-700">API Token</label>
                    <div className="relative">
                      <input
                        type={showSecrets.cryptobot_token ? 'text' : 'password'}
                        name="cryptobot_token"
                        value={form.cryptobot_token}
                        onChange={handleChange}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 pr-10"
                        placeholder="CryptoBot API Token"
                      />
                      <button
                        type="button"
                        onClick={() => toggleShowSecret('cryptobot_token')}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"
                      >
                        {showSecrets.cryptobot_token ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                )}

                {provider.id === 'yookassa' && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-gray-700">Shop ID</label>
                      <input
                        type="text"
                        name="yookassa_shop_id"
                        value={form.yookassa_shop_id}
                        onChange={handleChange}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        placeholder="123456"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-gray-700">Secret Key</label>
                      <div className="relative">
                        <input
                          type={showSecrets.yookassa_secret ? 'text' : 'password'}
                          name="yookassa_secret_key"
                          value={form.yookassa_secret_key}
                          onChange={handleChange}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 pr-10"
                          placeholder="live_..."
                        />
                        <button
                          type="button"
                          onClick={() => toggleShowSecret('yookassa_secret')}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"
                        >
                          {showSecrets.yookassa_secret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 md:col-span-2">
                      <input
                        type="checkbox"
                        name="yookassa_fiscal_enabled"
                        checked={form.yookassa_fiscal_enabled}
                        onChange={handleChange}
                        className="w-4 h-4 text-blue-600 rounded"
                      />
                      <label className="text-sm text-gray-700">Фискальный чек (54-ФЗ)</label>
                    </div>
                  </div>
                )}

                {provider.id === 'freekassa' && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-gray-700">ID Магазина</label>
                      <input
                        type="text"
                        name="freekassa_id"
                        value={form.freekassa_id}
                        onChange={handleChange}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        placeholder="12345"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-gray-700">Secret Key</label>
                      <div className="relative">
                        <input
                          type={showSecrets.freekassa_secret ? 'text' : 'password'}
                          name="freekassa_secret"
                          value={form.freekassa_secret}
                          onChange={handleChange}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 pr-10"
                          placeholder="secret_word"
                        />
                        <button
                          type="button"
                          onClick={() => toggleShowSecret('freekassa_secret')}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"
                        >
                          {showSecrets.freekassa_secret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-gray-700">API Key</label>
                      <div className="relative">
                        <input
                          type={showSecrets.freekassa_api ? 'text' : 'password'}
                          name="freekassa_api_key"
                          value={form.freekassa_api_key}
                          onChange={handleChange}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 pr-10"
                          placeholder="api_key"
                        />
                        <button
                          type="button"
                          onClick={() => toggleShowSecret('freekassa_api')}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"
                        >
                          {showSecrets.freekassa_api ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* Test Button */}
                <div className="flex items-center gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => testProvider(provider.id)}
                    disabled={testing[provider.id]}
                    className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50"
                  >
                    <TestTube className="w-4 h-4" />
                    {testing[provider.id] ? 'Проверка...' : 'Проверить подключение'}
                  </button>

                  {result && (
                    <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm ${
                      result.status === 'ok' ? 'bg-green-100 text-green-800' : 
                      result.status === 'disabled' ? 'bg-gray-100 text-gray-600' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {result.status === 'ok' ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                      {result.message}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        );
      })}

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={saving}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {saving ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Сохранение...
            </>
          ) : (
            'Сохранить платежи'
          )}
        </button>
      </div>
    </form>
  );
}
