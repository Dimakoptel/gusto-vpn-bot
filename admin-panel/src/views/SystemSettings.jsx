import React, { useState, useEffect } from 'react';
import api from '../services/api';

const SystemSettings = () => {
  const [settings, setSettings] = useState({
    app_name: 'GUSTO VPN',
    app_logo_url: '',
    maintenance_mode: false,
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
      await api.patch('/api/settings/system', settings);
      setMessage('✅ Системные настройки сохранены!');
      setTimeout(() => setMessage(''), 3000);
    } catch (e) {
      setMessage('❌ Ошибка сохранения');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="settings-section">
      <h2>⚙️ Системные настройки</h2>
      {message && <div className="alert">{message}</div>}

      <div className="form-group">
        <label>Название приложения:</label>
        <input
          type="text"
          value={settings.app_name || ''}
          onChange={e => setSettings({...settings, app_name: e.target.value})}
          placeholder="GUSTO VPN"
        />
      </div>

      <div className="form-group">
        <label>URL логотипа:</label>
        <input
          type="text"
          value={settings.app_logo_url || ''}
          onChange={e => setSettings({...settings, app_logo_url: e.target.value})}
          placeholder="https://example.com/logo.png"
        />
      </div>

      <div className="maintenance-toggle">
        <label className="toggle">
          <input
            type="checkbox"
            checked={settings.maintenance_mode}
            onChange={e => setSettings({...settings, maintenance_mode: e.target.checked})}
          />
          🔧 Режим технических работ
        </label>
        <small className="warning">
          ⚠️ При включении бот будет показывать "Технические работы" всем пользователям (кроме админов)
        </small>
      </div>

      <button onClick={handleSave} disabled={loading} className="btn-primary">
        {loading ? 'Сохранение...' : '💾 Сохранить'}
      </button>
    </div>
  );
};

export default SystemSettings;
