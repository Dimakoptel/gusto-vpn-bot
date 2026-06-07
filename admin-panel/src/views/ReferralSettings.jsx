import React, { useState, useEffect } from 'react';
import api from '../services/api';

const ReferralSettings = () => {
  const [settings, setSettings] = useState({
    referral_enabled: true,
    referral_level1_percent: 30,
    referral_level2_percent: 15,
    referral_level3_percent: 5,
    referral_min_payout: 500,
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [previewAmount, setPreviewAmount] = useState(1000);

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
      await api.patch('/api/settings/referral', settings);
      setMessage('✅ Настройки рефералки сохранены!');
      setTimeout(() => setMessage(''), 3000);
    } catch (e) {
      setMessage('❌ Ошибка сохранения');
    } finally {
      setLoading(false);
    }
  };

  const calculatePreview = () => {
    const l1 = previewAmount * (settings.referral_level1_percent / 100);
    const l2 = previewAmount * (settings.referral_level2_percent / 100);
    const l3 = previewAmount * (settings.referral_level3_percent / 100);
    return { l1, l2, l3, total: l1 + l2 + l3 };
  };

  const preview = calculatePreview();

  return (
    <div className="settings-section">
      <h2>🤝 Реферальная система</h2>
      {message && <div className="alert">{message}</div>}

      <label className="toggle">
        <input
          type="checkbox"
          checked={settings.referral_enabled}
          onChange={e => setSettings({...settings, referral_enabled: e.target.checked})}
        />
        Включить реферальную систему
      </label>

      <div className="form-group">
        <label>🥇 1 уровень (%):</label>
        <input
          type="number"
          min="0"
          max="100"
          value={settings.referral_level1_percent}
          onChange={e => setSettings({...settings, referral_level1_percent: parseFloat(e.target.value)})}
        />
      </div>

      <div className="form-group">
        <label>🥈 2 уровень (%):</label>
        <input
          type="number"
          min="0"
          max="100"
          value={settings.referral_level2_percent}
          onChange={e => setSettings({...settings, referral_level2_percent: parseFloat(e.target.value)})}
        />
      </div>

      <div className="form-group">
        <label>🥉 3 уровень (%):</label>
        <input
          type="number"
          min="0"
          max="100"
          value={settings.referral_level3_percent}
          onChange={e => setSettings({...settings, referral_level3_percent: parseFloat(e.target.value)})}
        />
      </div>

      <div className="form-group">
        <label>Минимум для вывода (₽):</label>
        <input
          type="number"
          min="0"
          value={settings.referral_min_payout}
          onChange={e => setSettings({...settings, referral_min_payout: parseFloat(e.target.value)})}
        />
      </div>

      <div className="preview-section">
        <h3>📊 Live-превью расчета</h3>
        <div className="form-group">
          <label>Сумма платежа (₽):</label>
          <input
            type="number"
            value={previewAmount}
            onChange={e => setPreviewAmount(parseFloat(e.target.value) || 0)}
          />
        </div>
        <div className="preview-results">
          <p>🥇 1 уровень: <strong>{preview.l1.toFixed(2)}₽</strong></p>
          <p>🥈 2 уровень: <strong>{preview.l2.toFixed(2)}₽</strong></p>
          <p>🥉 3 уровень: <strong>{preview.l3.toFixed(2)}₽</strong></p>
          <p className="total">💰 Всего: <strong>{preview.total.toFixed(2)}₽</strong></p>
        </div>
      </div>

      <button onClick={handleSave} disabled={loading} className="btn-primary">
        {loading ? 'Сохранение...' : '💾 Сохранить'}
      </button>
    </div>
  );
};

export default ReferralSettings;
