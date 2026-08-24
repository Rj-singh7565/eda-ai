'use client';

import React from 'react';

interface NavSidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

export default function NavSidebar({ activeTab, onTabChange }: NavSidebarProps) {
  return (
    <aside className="col-nav">
      {/* Brand Header */}
      <div className="nav-brand-group">
        <div className="brand-badge-logo">EA</div>
        <div>
          <div className="brand-name">EDA Assistant</div>
          <div className="brand-subtext">Exploratory Data Analysis</div>
        </div>
      </div>

      {/* Global Document Search Box */}
      <div className="nav-search-box">
        <span>🔍 Search documents...</span>
        <span className="shortcut-badge">⌘K</span>
      </div>

      {/* Primary Navigation Menu */}
      <div className="nav-menu-list">
        {[
          { id: 'home', label: 'Home', icon: '🏠' },
          { id: 'documents', label: 'Documents', icon: '📄' },
          { id: 'chats', label: 'Chats', icon: '💬' },
          { id: 'uploads', label: 'Uploads', icon: '📤' },
          { id: 'settings', label: 'Settings', icon: '⚙️' }
        ].map((item) => {
          const isActive = activeTab === item.id;
          return (
            <div
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`nav-link-item ${isActive ? 'active' : ''}`}
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </div>
          );
        })}
      </div>

      {/* Help Link & User Profile Bottom Card */}
      <div style={{ marginTop: 'auto' }}>
        <div style={{ fontSize: '0.82rem', color: 'rgba(255, 255, 255, 0.6)', padding: '8px 12px', cursor: 'pointer', marginBottom: '12px' }}>
          ❓ Help
        </div>

        <div className="user-profile-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div className="user-avatar-circle">RS</div>
            <div>
              <div style={{ fontSize: '0.84rem', fontWeight: 600, color: '#FFFFFF' }}>Raj Singh</div>
              <div style={{ fontSize: '0.7rem', color: 'rgba(255, 255, 255, 0.5)' }}>Analyst</div>
            </div>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'rgba(255, 255, 255, 0.5)' }}>❯</span>
        </div>
      </div>
    </aside>
  );
}
