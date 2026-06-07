import React, { useState, useEffect } from 'react';
import { Bell, ToggleLeft, ToggleRight, MessageSquare, AlertTriangle, Clock } from 'lucide-react';

export default function NotificationSettings({ settings, onSave, saving }) {
  const [form, setForm] = useState({
    notify_expiry_3days: true,
    notify_expiry_1day: true,
    notify_expiry_today: true,
    notify_low_traffic_gb: 5,
    notify_channel_id: '',
  });

  useEffect(() => {
    if (settings) {
      setForm({
        notify_expiry_3days: settings.notify_expiry_3days ?? true,
        notify_expiry_1day: settings.notify_expiry_1day ?? true,
        notify_expiry_today: settings.notify_expiry_today ?? true,
        notify_low_traffic_gb: settings.notify_low_traffic_gb || 5,
        notify_channel_id: settings.notify_channel_id || '',
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
      notify_expiry_3days: form.notify_expiry_3days,
      notify_expiry_1day: form.notify_expiry_1day,
      notify_expiry_today: form.notify_expiry_today,
      notify_low_traffic_gb: parseFloat(form.notify_low_traffic_gb),
      notify_channel_id: form.notify_channel_id,
    });
  };

  const notifications = [
    { key: 'notify_expiry_3days', label: 'За 3 дня до истечения', icon: Clock, desc: 'Уведомить пользователя за 3 дня' },
    { key: 'notify_expiry_1day', label: 'За 1 день до истечения', icon: AlertTriangle, desc: 'Уведомить пользователя за 1 день' },
    { key: 'notify_expiry_today', label: 'В день истечения', icon: Bell, desc: 'Финальное уведомление' },
  ];

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="flex items-center gap-2 mb-4">
        <Bell className="w-5 h-5 text-blue-600" />
        <h2 className="text-lg font-semibold">Уведомления</h2>
      </div>

      <div className="space-y-4">
        <h3 className="text-sm font-medium text-gray-900">Уведомления об истечении подписки</h3>
        {notifications.map(({ key, label, icon: Icon, desc }) => (
          <div key={key} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-3">
              <Icon className="w-5 h-5 text-gray-500" />
              <div>
                <p className="font-medium text-gray-900">{label}</p>
                <p className="text-sm text-gray-500">{desc}</p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => handleToggle(key)}
              className="flex items-center gap-2"
            >
              {form[key] ? (
                <ToggleRight className="w-8 h-8 text-blue-600" />
              ) : (
                <ToggleLeft className="w-8 h-8 text-gray-400" />
              )}
            </button>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            Порог низкого трафика (GB)
          </label>
          <input
            type="number"
            name="notify_low_traffic_gb"
            value={form.notify_low_traffic_gb}
            onChange={handleChange}
            min="0.1"
            max="1000"
            step="0.1"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-xs text-gray-500">Уведомить когда осталось меньше этого значения</p>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
            <MessageSquare className="w-4 h-4" />
            ID канала для уведомлений
          </label>
          <input
            type="text"
            name="notify_channel_id"
            value={form.notify_channel_id}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            placeholder="-1001234567890"
          />
          <p className="text-xs text-gray-500">Telegram ID канала (опционально)</p>
        </div>
      </div>

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
            'Сохранить'
          )}
        </button>
      </div>
    </form>
  );
}
