import React, { useState, useEffect } from 'react';
import { 
  Settings, Bot, CreditCard, Users, Shield, Bell, 
  Globe, Save, Loader, CheckCircle, AlertTriangle 
} from 'lucide-react';
import BotSettings from './BotSettings';
import PaymentSettings from './PaymentSettings';
import ReferralSettings from './ReferralSettings';
import AntifraudSettings from './AntifraudSettings';
import NotificationSettings from './NotificationSettings';
import SystemSettings from './SystemSettings';
import api from '../services/api';

const TABS = [
  { id: 'bot', label: 'Бот', icon: Bot, component: BotSettings },
  { id: 'payments', label: 'Платежи', icon: CreditCard, component: PaymentSettings },
  { id: 'referral', label: 'Рефералка', icon: Users, component: ReferralSettings },
  { id: 'antifraud', label: 'Антифрод', icon: Shield, component: AntifraudSettings },
  { id: 'notifications', label: 'Уведомления', icon: Bell, component: NotificationSettings },
  { id: 'system', label: 'Система', icon: Globe, component: SystemSettings },
];

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('bot');
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const res = await api.get('/settings/');
      setSettings(res.data);
    } catch (err) {
      setMessage({ type: 'error', text: 'Ошибка загрузки настроек' });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (sectionData) => {
    setSaving(true);
    setMessage(null);
    try {
      const res = await api.put('/settings/', { [activeTab]: sectionData });
      setSettings(res.data);
      setMessage({ type: 'success', text: 'Настройки сохранены!' });
      setTimeout(() => setMessage(null), 3000);
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Ошибка сохранения' });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  const ActiveComponent = TABS.find(t => t.id === activeTab)?.component;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Settings className="w-6 h-6" />
          Настройки системы
        </h1>
        {message && (
          <div className={`flex items-center gap-2 px-4 py-2 rounded-lg ${
            message.type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
          }`}>
            {message.type === 'success' ? <CheckCircle className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
            {message.text}
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8">
          {TABS.map(tab => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-1 py-4 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Active Tab Content */}
      <div className="bg-white rounded-lg shadow p-6">
        {ActiveComponent && (
          <ActiveComponent 
            settings={settings} 
            onSave={handleSave} 
            saving={saving}
          />
        )}
      </div>
    </div>
  );
}
