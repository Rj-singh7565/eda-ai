'use client';

import React from 'react';
import { SystemHealth } from '../lib/types';

interface GlobalHeaderProps {
  searchQuery: string;
  onSearchChange: (q: string) => void;
  health: SystemHealth | null;
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
}

export default function GlobalHeader({
  searchQuery,
  onSearchChange,
  health,
  theme,
  onToggleTheme
}: GlobalHeaderProps) {
  const isHealthy = health?.status === 'healthy';

  return (
    <header className="global-header">
      {/* Brand Title */}
      <div className="header-brand">
        <div className="header-brand-logo">⚡</div>
        <span>EDA Assistant</span>
        <span
          style={{
            fontSize: '0.68rem',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
            padding: '2px 8px',
            borderRadius: '12px',
            background: 'var(--bg-app)',
            border: '1px solid var(--border-color)',
            color: 'var(--text-secondary)'
          }}
        >
          v2.0 Enterprise
        </span>
      </div>

      {/* Global Document Search Bar */}
      <div className="header-center">
        <div className="header-search">
          <span className="header-search-icon">🔍</span>
          <input
            type="text"
            placeholder="Search documents by name or file format..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
          />
        </div>
      </div>

      {/* System Health & Theme Toggle & Profile */}
      <div className="header-actions">
        {/* Health Badge */}
        <div className="health-badge">
          <span
            className="health-dot"
            style={{ background: isHealthy ? 'var(--status-ready)' : 'var(--status-processing)' }}
          />
          <span>{isHealthy ? 'System Ready' : health?.status || 'Connecting...'}</span>
        </div>

        {/* Theme Toggle Button */}
        <button className="theme-toggle-btn" onClick={onToggleTheme} title="Toggle Dark / Light Theme">
          <span>{theme === 'light' ? '🌙 Dark' : '☀️ Light'}</span>
        </button>

        {/* User Profile Avatar */}
        <div className="user-profile-badge" title="User Profile">
          EA
        </div>
      </div>
    </header>
  );
}
