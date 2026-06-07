import React, { useState, useEffect } from 'react';
import api from '../services/api';

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
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [testResult, setTestResult] = useState(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const resp = await api.get('/api/settings/');
      setSettings(resp.data);
    } catch (e) {
      console.error('Failed to load settings:', e);
    }
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      await api.patch('/api/settings/payments', settings);
      setMessage('✅ Настройки платежей сохранены!');
      setTimeout(() => setMessage(''), 3000);
    } catch (e) {
      setMessage('❌ Ошибка сохранения');
    } finally {
      setLoading(false);
    }
  };

  const testProvider = async (provider) => {
    setTestResult({ provider, status: 'testing' });
    try {
      const resp = await api.post(`/api/settings/payments/${provider}/test`);
      setTestResult({ provider, status: 'done', result: resp.data });
    } catch (e) {
      setTestResult({ provider, status: 'error', error: e.message });
    }
  };

  return (
    <div className="settings-section">
      <h2>💰 Настройки платежей</h2>
      {message && <div className="alert">{message}</div>}

      {/* CryptoBot */}
      <div className="provider-section">
        <h3>💎 CryptoBot</h3>
        <label className="toggle">
          <input
            type="checkbox"
            checked={settings.cryptobot_enabled}
            onChange={e => setSettings({...settings, cryptobot_enabled: e.target.checked})}
          />
          Включить CryptoBot
        </label>
        <div className="form-group">
          <label>API Token:</label>
          <input
            type="password"
            value={settings.cryptobot_token || ''}
            onChange={e => setSettings({...settings, cryptobot_token: e.target.value})}
            placeholder="CryptoBot API Token"
          />
        </div>
        <button onClick={() => testProvider('cryptobot')} className="btn-secondary">
          🔌 Проверить подключение
        </button>
        {testResult?.provider === 'cryptobot' && (
          <div className={`test-result ${testResult.status}`}>
            {testResult.status === 'testing' ? '⏳ Тестирование...' :
             testResult.status === 'done' ? `✅ ${testResult.result?.message || 'OK'}` :
             `❌ ${testResult.error}`}
          </div>
        )}
      </div>

      {/* YooKassa */}
      <div className="provider-section">
        <h3>💳 ЮKassa</h3>
        <label className="toggle">
          <input
            type="checkbox"
            checked={settings.yookassa_enabled}
            onChange={e => setSettings({...settings, yookassa_enabled: e.target.checked})}
          />
          Включить ЮKassa
        </label>
        <div className="form-group">
          <label>Shop ID:</label>
          <input
            type="text"
            value={settings.yookassa_shop_id || ''}
            onChange={e => setSettings({...settings, yookassa_shop_id: e.target.value})}
            placeholder="123456"
          />
        </div>
        <div className="form-group">
          <label>Secret Key:</label>
          <input
            type="password"
            value={settings.yookassa_secret_key || ''}
            onChange={e => setSettings({...settings, yookassa_secret_key: e.target.value})}
            placeholder="test_... или live_..."
          />
        </div>
        <label className="toggle">
          <input
            type="checkbox"
            checked={settings.yookassa_fiscal_enabled}
            onChange={e => setSettings({...settings, yookassa_fiscal_enabled: e.target.checked})}
          />
          Фискализация (54-ФЗ)
        </label>
        <button onClick={() => testProvider('yookassa')} className="btn-secondary">
          🔌 Проверить подключение
        </button>
      </div>

      {/* FreeKassa */}
      <div className="provider-section">
        <h3>💵 FreeKassa</h3>
        <label className="toggle">
          <input
            type="checkbox"
            checked={settings.freekassa_enabled}
            onChange={e => setSettings({...settings, freekassa_enabled: e.target.checked})}
          />
          Включить FreeKassa
        </label>
        <div className="form-group">
          <label>ID магазина:</label>
          <input
            type="text"
            value={settings.freekassa_id || ''}
            onChange={e => setSettings({...settings, freekassa_id: e.target.value})}
            placeholder="12345"
          />
        </div>
        <div className="form-group">
          <label>Секретный ключ:</label>
          <input
            type="password"
            value={settings.freekassa_secret || ''}
            onChange={e => setSettings({...settings, freekassa_secret: e.target.value})}
          />
        </div>
        <div className="form-group">
          <label>API Key:</label>
          <input
            type="password"
            value={settings.freekassa_api_key || ''}
            onChange={e => setSettings({...settings, freekassa_api_key: e.target.value})}
          />
        </div>
        <button onClick={() => testProvider('freekassa')} className="btn-secondary">
          🔌 Проверить подключение
        </button>
      </div>

      <button onClick={handleSave} disabled={loading} className="btn-primary">
        {loading ? 'Сохранение...' : '💾 Сохранить все'}
      </button>
    </div>
  );
};

export default PaymentSettings;
