import React, { useState, useEffect } from 'react';
import api from '../services/api';

const AntifraudSettings = () => {
  const [settings, setSettings] = useState({
    antifraud_enabled: true,
    antifraud_max_ips: 3,
    antifraud_max_countries: 2,
    antifraud_ban_hours: 24,
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

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
      await api.patch('/api/settings/antifraud', settings);
      setMessage('✅ Настройки антифрода сохранены!');
      setTimeout(() => setMessage(''), 3000);
    } catch (e) {
      setMessage('❌ Ошибка сохранения');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="settings-section">
      <h2>🛡️ Антифрод система</h2>
      {message && <div className="alert">{message}</div>}

      <label className="toggle">
        <input
          type="checkbox"
          checked={settings.antifraud_enabled}
          onChange={e => setSettings({...settings, antifraud_enabled: e.target.checked})}
        />
        Включить антифрод
      </label>

      <div className="form-group">
        <label>Макс. уникальных IP (за 24ч):</label>
        <input
          type="number"
          min="1"
          max="20"
          value={settings.antifraud_max_ips}
          onChange={e => setSettings({...settings, antifraud_max_ips: parseInt(e.target.value)})}
        />
        <small>При превышении — подписка ограничивается</small>
      </div>

      <div className="form-group">
        <label>Макс. стран:</label>
        <input
          type="number"
          min="1"
          max="10"
          value={settings.antifraud_max_countries}
          onChange={e => setSettings({...settings, antifraud_max_countries: parseInt(e.target.value)})}
        />
        <small>При превышении — подписка ограничивается</small>
      </div>

      <div className="form-group">
        <label>Время бана (часов):</label>
        <input
          type="number"
          min="1"
          max="720"
          value={settings.antifraud_ban_hours}
          onChange={e => setSettings({...settings, antifraud_ban_hours: parseInt(e.target.value)})}
        />
        <small>На сколько часов ограничить подписку при нарушении</small>
      </div>

      <div className="info-box">
        <h4>📋 Как работает антифрод:</h4>
        <ul>
          <li>Мониторит уникальные IP-адреса каждого клиента</li>
          <li>Отслеживает геолокацию подключений</li>
          <li>При превышении лимитов — временно ограничивает скорость</li>
          <li>Уведомляет администраторов о подозрительной активности</li>
        </ul>
      </div>

      <button onClick={handleSave} disabled={loading} className="btn-primary">
        {loading ? 'Сохранение...' : '💾 Сохранить'}
      </button>
    </div>
  );
};

export default AntifraudSettings;
