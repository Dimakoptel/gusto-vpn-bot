import React, { useState, useEffect } from 'react';
import api from '../services/api';

const NotificationSettings = () => {
  const [settings, setSettings] = useState({
    notify_expiry_3days: true,
    notify_expiry_1day: true,
    notify_expiry_today: true,
    notify_low_traffic_gb: 5,
    notify_channel_id: '',
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
      await api.patch('/api/settings/notifications', settings);
      setMessage('✅ Настройки уведомлений сохранены!');
      setTimeout(() => setMessage(''), 3000);
    } catch (e) {
      setMessage('❌ Ошибка сохранения');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="settings-section">
      <h2>🔔 Уведомления</h2>
      {message && <div className="alert">{message}</div>}

      <h3>⏰ Уведомления об истечении подписки</h3>

      <label className="toggle">
        <input
          type="checkbox"
          checked={settings.notify_expiry_3days}
          onChange={e => setSettings({...settings, notify_expiry_3days: e.target.checked})}
        />
        За 3 дня до истечения
      </label>

      <label className="toggle">
        <input
          type="checkbox"
          checked={settings.notify_expiry_1day}
          onChange={e => setSettings({...settings, notify_expiry_1day: e.target.checked})}
        />
        За 1 день до истечения
      </label>

      <label className="toggle">
        <input
          type="checkbox"
          checked={settings.notify_expiry_today}
          onChange={e => setSettings({...settings, notify_expiry_today: e.target.checked})}
        />
        В день истечения
      </label>

      <h3>📊 Уведомления о трафике</h3>

      <div className="form-group">
        <label>Порог уведомления (GB):</label>
        <input
          type="number"
          min="0.1"
          max="1000"
          step="0.1"
          value={settings.notify_low_traffic_gb}
          onChange={e => setSettings({...settings, notify_low_traffic_gb: parseFloat(e.target.value)})}
        />
        <small>Уведомить когда осталось менее X GB трафика</small>
      </div>

      <h3>📢 Канал уведомлений</h3>

      <div className="form-group">
        <label>ID канала/группы (для массовых уведомлений):</label>
        <input
          type="text"
          value={settings.notify_channel_id || ''}
          onChange={e => setSettings({...settings, notify_channel_id: e.target.value})}
          placeholder="-1001234567890"
        />
        <small>Укажите ID канала для публикации новостей и акций</small>
      </div>

      <button onClick={handleSave} disabled={loading} className="btn-primary">
        {loading ? 'Сохранение...' : '💾 Сохранить'}
      </button>
    </div>
  );
};

export default NotificationSettings;
