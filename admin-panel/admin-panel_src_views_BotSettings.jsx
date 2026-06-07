import React, { useState, useEffect } from 'react';
import { Eye, EyeOff, Bot, MessageSquare, UserCog } from 'lucide-react';

export default function BotSettings({ settings, onSave, saving }) {
  const [form, setForm] = useState({
    bot_token: '',
    admin_ids: '',
    support_username: '',
    welcome_message: '',
  });
  const [showToken, setShowToken] = useState(false);

  useEffect(() => {
    if (settings) {
      setForm({
        bot_token: settings.bot_token || '',
        admin_ids: (settings.admin_ids || []).join(', '),
        support_username: settings.support_username || '',
        welcome_message: settings.welcome_message || '',
      });
    }
  }, [settings]);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave({
      bot_token: form.bot_token,
      admin_ids: form.admin_ids.split(',').map(id => parseInt(id.trim())).filter(Boolean),
      support_username: form.support_username,
      welcome_message: form.welcome_message,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="flex items-center gap-2 mb-4">
        <Bot className="w-5 h-5 text-blue-600" />
        <h2 className="text-lg font-semibold">Настройки Telegram бота</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Bot Token */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
            <Bot className="w-4 h-4" />
            Bot Token
          </label>
          <div className="relative">
            <input
              type={showToken ? 'text' : 'password'}
              name="bot_token"
              value={form.bot_token}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 pr-10"
              placeholder="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
            />
            <button
              type="button"
              onClick={() => setShowToken(!showToken)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              {showToken ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          <p className="text-xs text-gray-500">Получите у @BotFather</p>
        </div>

        {/* Admin IDs */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
            <UserCog className="w-4 h-4" />
            ID администраторов
          </label>
          <input
            type="text"
            name="admin_ids"
            value={form.admin_ids}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="123456789, 987654321"
          />
          <p className="text-xs text-gray-500">Telegram ID через запятую</p>
        </div>

        {/* Support Username */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700">Поддержка (username)</label>
          <input
            type="text"
            name="support_username"
            value={form.support_username}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="@support_username"
          />
        </div>
      </div>

      {/* Welcome Message */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
          <MessageSquare className="w-4 h-4" />
          Приветственное сообщение
        </label>
        <textarea
          name="welcome_message"
          value={form.welcome_message}
          onChange={handleChange}
          rows={4}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          placeholder="Добро пожаловать! ..."
        />
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
