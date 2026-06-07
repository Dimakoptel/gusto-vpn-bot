import React, { useState, useEffect } from 'react';
import { Users, Percent, DollarSign, ToggleLeft, ToggleRight } from 'lucide-react';

export default function ReferralSettings({ settings, onSave, saving }) {
  const [form, setForm] = useState({
    referral_enabled: false,
    referral_level1_percent: 30,
    referral_level2_percent: 15,
    referral_level3_percent: 5,
    referral_min_payout: 500,
  });

  useEffect(() => {
    if (settings) {
      setForm({
        referral_enabled: settings.referral_enabled || false,
        referral_level1_percent: settings.referral_level1_percent || 30,
        referral_level2_percent: settings.referral_level2_percent || 15,
        referral_level3_percent: settings.referral_level3_percent || 5,
        referral_min_payout: settings.referral_min_payout || 500,
      });
    }
  }, [settings]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm({ ...form, [name]: type === 'checkbox' ? checked : parseFloat(value) });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave({
      referral_enabled: form.referral_enabled,
      referral_level1_percent: form.referral_level1_percent,
      referral_level2_percent: form.referral_level2_percent,
      referral_level3_percent: form.referral_level3_percent,
      referral_min_payout: form.referral_min_payout,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="flex items-center gap-2 mb-4">
        <Users className="w-5 h-5 text-blue-600" />
        <h2 className="text-lg font-semibold">Реферальная система</h2>
      </div>

      <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
        <div>
          <h3 className="font-medium text-gray-900">Включить реферальную систему</h3>
          <p className="text-sm text-gray-500">Пользователи смогут приглашать друзей и получать бонусы</p>
        </div>
        <button
          type="button"
          onClick={() => setForm({ ...form, referral_enabled: !form.referral_enabled })}
          className="flex items-center gap-2"
        >
          {form.referral_enabled ? (
            <ToggleRight className="w-8 h-8 text-blue-600" />
          ) : (
            <ToggleLeft className="w-8 h-8 text-gray-400" />
          )}
        </button>
      </div>

      {form.referral_enabled && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
                <Percent className="w-4 h-4" />
                Уровень 1 (прямой реферал)
              </label>
              <div className="relative">
                <input
                  type="number"
                  name="referral_level1_percent"
                  value={form.referral_level1_percent}
                  onChange={handleChange}
                  min="0"
                  max="100"
                  step="0.1"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 pr-8"
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">%</span>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
                <Percent className="w-4 h-4" />
                Уровень 2
              </label>
              <div className="relative">
                <input
                  type="number"
                  name="referral_level2_percent"
                  value={form.referral_level2_percent}
                  onChange={handleChange}
                  min="0"
                  max="100"
                  step="0.1"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 pr-8"
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">%</span>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
                <Percent className="w-4 h-4" />
                Уровень 3
              </label>
              <div className="relative">
                <input
                  type="number"
                  name="referral_level3_percent"
                  value={form.referral_level3_percent}
                  onChange={handleChange}
                  min="0"
                  max="100"
                  step="0.1"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 pr-8"
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">%</span>
              </div>
            </div>
          </div>

          <div className="space-y-2 max-w-xs">
            <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
              <DollarSign className="w-4 h-4" />
              Минимальная сумма для вывода
            </label>
            <div className="relative">
              <input
                type="number"
                name="referral_min_payout"
                value={form.referral_min_payout}
                onChange={handleChange}
                min="0"
                step="10"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 pr-12"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">₽</span>
            </div>
          </div>

          <div className="p-4 bg-blue-50 rounded-lg">
            <h4 className="text-sm font-medium text-blue-900 mb-2">Превью расчета</h4>
            <p className="text-sm text-blue-700">
              При оплате подписки за 1000 ₽:
              <br />• Уровень 1 получит {((1000 * form.referral_level1_percent) / 100).toFixed(0)} ₽
              <br />• Уровень 2 получит {((1000 * form.referral_level2_percent) / 100).toFixed(0)} ₽
              <br />• Уровень 3 получит {((1000 * form.referral_level3_percent) / 100).toFixed(0)} ₽
            </p>
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
