import React, { useState } from 'react';
import BotSettings from './BotSettings';
import PaymentSettings from './PaymentSettings';
import ReferralSettings from './ReferralSettings';
import AntifraudSettings from './AntifraudSettings';
import NotificationSettings from './NotificationSettings';
import SystemSettings from './SystemSettings';

const SettingsPage = () => {
  const [activeTab, setActiveTab] = useState('bot');

  const tabs = [
    { id: 'bot', label: '🤖 Бот', component: BotSettings },
    { id: 'payments', label: '💰 Платежи', component: PaymentSettings },
    { id: 'referral', label: '🤝 Рефералка', component: ReferralSettings },
    { id: 'antifraud', label: '🛡️ Антифрод', component: AntifraudSettings },
    { id: 'notifications', label: '🔔 Уведомления', component: NotificationSettings },
    { id: 'system', label: '⚙️ Система', component: SystemSettings },
  ];

  const ActiveComponent = tabs.find(t => t.id === activeTab)?.component || BotSettings;

  return (
    <div className="settings-page">
      <h1>⚙️ Настройки GUSTO VPN</h1>
      <div className="tabs">
        {tabs.map(tab => (
          <button
            key={tab.id}
            className={activeTab === tab.id ? 'active' : ''}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="tab-content">
        <ActiveComponent />
      </div>
    </div>
  );
};

export default SettingsPage;
