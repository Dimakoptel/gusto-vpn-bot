import React, { useState, useEffect } from 'react';
import { Shield, ToggleLeft, ToggleRight, Globe, Clock, Ban } from 'lucide-react';

export default function AntifraudSettings({ settings, onSave, saving }) {
  const [form, setForm] = useState({
    antifraud_enabled: true,
    antifraud_max_ips: 3,
    antifraud_max_countries: 2,
    antifraud_ban_hours: 24,
  });

  useEffect(() => {
    if (settings) {
      setForm({
        antifraud_enabled: settings.antifraud_enabled || true,
        antifraud_max_ips: settings.antifraud_max_ips || 3,
        antifraud_max_countries: settings.antifraud_max_countries || 2,
        antifraud_ban_hours: settings.antifraud_ban_hours || 24,
      });
    }
  }, [settings]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm({ ...form, [name]: type === 'checkbox' ? checked : parseInt(value) });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave({
      antifraud_enabled: form.antifraud_enabled,
      antifraud_max_ips: form.antifraud_max_ips,
      antifraud_max_countries: form.antifraud_max_countries,
      antifraud_ban_hours: form.antifraud_ban_hours,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="flex items-center gap-2 mb-4">
        <Shield className="w-5 h-5 text-blue-600" />
        <h2 className="text-lg font-semibold">Антифрод система</h2>
      </div>

      <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
        <div>
          <h3 className="font-medium text-gray-900">Включить антифрод</h3>
          <p className="text-sm text-gray-500">Автоматическое обнаружение sharing конфигов</p>
        </div>
        <button
          type="button"
          onClick={() => setForm({ ...form, antifraud_enabled: !form.antifraud_enabled })}
          className="flex items-center gap-2"
        >
          {form.antifraud_enabled ? (
            <ToggleRight className="w-8 h-8 text-blue-600" />
          ) : (
            <ToggleLeft className="w-8 h-8 text-gray-400" />
          )}
        </button>
      </div>

      {form.antifraud_enabled && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
              <Globe className="w-4 h-4" />
              Макс. IP-адресов
            </label>
            <input
              type="number"
              name="antifraud_max_ips"
              value={form.antifraud_max_ips}
              onChange={handleChange}
              min="1"
              max="20"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-500">Макс. одновременных IP</p>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
              <Globe className="w-4 h-4" />
              Макс. стран
            </label>
            <input
              type="number"
              name="antifraud_max_countries"
              value={form.antifraud_max_countries}
              onChange={handleChange}
              min="1"
              max="10"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-500">Макс. разных стран за 24ч</p>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
              <Clock className="w-4 h-4" />
              Время бана
            </label>
            <div className="relative">
              <input
                type="number"
                name="antifraud_ban_hours"
                value={form.antifraud_ban_hours}
                onChange={handleChange}
                min="1"
                max="720"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 pr-12"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">ч</span>
            </div>
            <p className="text-xs text-gray-500">На сколько часов банить</p>
          </div>
        </div>
      )}

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
