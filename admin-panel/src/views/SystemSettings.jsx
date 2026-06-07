import React, { useState, useEffect } from 'react';
import { Globe, Type, Image, Wrench, AlertTriangle, ToggleLeft, ToggleRight } from 'lucide-react';

export default function SystemSettings({ settings, onSave, saving }) {
  const [form, setForm] = useState({
    app_name: 'GUSTO VPN',
    app_logo_url: '',
    maintenance_mode: false,
  });

  useEffect(() => {
    if (settings) {
      setForm({
        app_name: settings.app_name || 'GUSTO VPN',
        app_logo_url: settings.app_logo_url || '',
        maintenance_mode: settings.maintenance_mode || false,
      });
    }
  }, [settings]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm({ ...form, [name]: type === 'checkbox' ? checked : value });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave({
      app_name: form.app_name,
      app_logo_url: form.app_logo_url,
      maintenance_mode: form.maintenance_mode,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="flex items-center gap-2 mb-4">
        <Globe className="w-5 h-5 text-blue-600" />
        <h2 className="text-lg font-semibold">Системные настройки</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
            <Type className="w-4 h-4" />
            Название приложения
          </label>
          <input
            type="text"
            name="app_name"
            value={form.app_name}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            placeholder="GUSTO VPN"
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
            <Image className="w-4 h-4" />
            URL логотипа
          </label>
          <input
            type="url"
            name="app_logo_url"
            value={form.app_logo_url}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            placeholder="https://example.com/logo.png"
          />
        </div>
      </div>

      <div className={`border rounded-lg p-4 ${form.maintenance_mode ? 'border-yellow-200 bg-yellow-50' : 'border-gray-200'}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Wrench className={`w-5 h-5 ${form.maintenance_mode ? 'text-yellow-600' : 'text-gray-500'}`} />
            <div>
              <h3 className="font-medium text-gray-900">Режим обслуживания</h3>
              <p className="text-sm text-gray-500">
                {form.maintenance_mode 
                  ? 'Бот и API недоступны для пользователей' 
                  : 'Все системы работают нормально'}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setForm({ ...form, maintenance_mode: !form.maintenance_mode })}
            className="flex items-center gap-2"
          >
            {form.maintenance_mode ? (
              <ToggleRight className="w-8 h-8 text-yellow-600" />
            ) : (
              <ToggleLeft className="w-8 h-8 text-gray-400" />
            )}
          </button>
        </div>

        {form.maintenance_mode && (
          <div className="mt-3 flex items-center gap-2 text-yellow-700 text-sm">
            <AlertTriangle className="w-4 h-4" />
            Внимание: пользователи увидят сообщение "Технические работы"
          </div>
        )}
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
