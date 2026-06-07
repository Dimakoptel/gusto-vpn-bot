import React, { useState, useEffect } from 'react';
import api from '../services/api';

const BotSettings = () => {
  const [settings, setSettings] = useState({
    bot_token: '',
    admin_ids: [],
    support_username: '',
    welcome_message: '',
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
      await api.patch('/api/settings/bot', settings);
      setMessage('✅ Настройки сохранены!');
      setTimeout(() => setMessage(''), 3000);
    } catch (e) {
      setMessage('❌ Ошибка сохранения');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="settings-section">
      <h2>🤖 Настройки бота</h2>
      {message && <div className="alert">{message}</div>}

      <div className="form-group">
        <label>Токен бота (BotFather):</label>
        <input
          type="password"
          value={settings.bot_token || ''}
          onChange={e => setSettings({...settings, bot_token: e.target.value})}
          placeholder="Введите токен..."
        />
      </div>

      <div className="form-group">
        <label>ID администраторов (через запятую):</label>
        <input
          type="text"
          value={settings.admin_ids?.join(', ') || ''}
          onChange={e => setSettings({...settings, admin_ids: e.target.value.split(',').map(s => parseInt(s.trim())).filter(Boolean)})}
          placeholder="123456789, 987654321"
        />
      </div>

      <div className="form-group">
        <label>Username поддержки (без @):</label>
        <input
          type="text"
          value={settings.support_username || ''}
          onChange={e => setSettings({...settings, support_username: e.target.value})}
          placeholder="gusto_support"
        />
      </div>

      <div className="form-group">
        <label>Welcome message:</label>
        <textarea
          value={settings.welcome_message || ''}
          onChange={e => setSettings({...settings, welcome_message: e.target.value})}
          rows={4}
          placeholder="Добро пожаловать в GUSTO VPN!"
        />
      </div>

      <button onClick={handleSave} disabled={loading} className="btn-primary">
        {loading ? 'Сохранение...' : '💾 Сохранить'}
      </button>
    </div>
  );
};

export default BotSettings;
