'use client';

import React from 'react';
import {
  LayoutDashboard,
  Database,
  Sparkles,
  Clock,
  HardDrive,
  Settings,
  LogOut,
  ChevronDown,
  Home
} from 'lucide-react';
import { Document, NavTab } from '../lib/types';

interface NavSidebarProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  activeDoc: Document | null;
  onPreviewDoc?: (doc: Document) => void;
}

export default function NavSidebar({
  activeTab,
  onTabChange,
  activeDoc,
  onPreviewDoc
}: NavSidebarProps) {
  const isCompact = activeTab === 'analysis';

  const workspaceNav = [
    { id: 'overview' as NavTab, label: 'Overview', icon: LayoutDashboard },
    { id: 'datasets' as NavTab, label: 'Datasets', icon: Database },
    { id: 'analysis' as NavTab, label: 'Analysis', icon: Sparkles },
    { id: 'history' as NavTab, label: 'History', icon: Clock },
  ];

  const systemNav = [
    { id: 'storage' as NavTab, label: 'Storage', icon: HardDrive },
    { id: 'settings' as NavTab, label: 'Settings', icon: Settings },
  ];

  // ── COMPACT ICON-ONLY RAIL (FOR ANALYSIS PAGE) ──────────────────────
  if (isCompact) {
    return (
      <aside
        className="app-sidebar-nav compact-analysis-sidebar"
        style={{
          width: '64px',
          minWidth: '64px',
          maxWidth: '64px',
          height: '100%',
          backgroundColor: '#ffffff',
          borderRight: '1px solid #e2e8f0',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 8px',
          zIndex: 20
        }}
      >
        {/* Top: Brand Logo */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px', width: '100%' }}>
          <div
            style={{
              width: '38px',
              height: '38px',
              backgroundColor: '#2563eb',
              color: '#ffffff',
              borderRadius: '10px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 700,
              fontSize: '1rem',
              boxShadow: '0 2px 6px rgba(37, 99, 235, 0.3)',
              cursor: 'pointer'
            }}
            onClick={() => onTabChange('overview')}
            title="EDA Assistant"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="20" x2="18" y2="10"></line>
              <line x1="12" y1="20" x2="12" y2="4"></line>
              <line x1="6" y1="20" x2="6" y2="14"></line>
            </svg>
          </div>

          {/* Navigation Icons List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '100%', alignItems: 'center' }}>
            {workspaceNav.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onTabChange(item.id)}
                  title={item.label}
                  style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '10px',
                    border: 'none',
                    background: isActive ? '#eff6ff' : 'transparent',
                    color: isActive ? '#2563eb' : '#64748b',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                    boxShadow: isActive ? '0 1px 3px rgba(37, 99, 235, 0.1)' : 'none'
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.backgroundColor = '#f1f5f9';
                      e.currentTarget.style.color = '#0f172a';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.backgroundColor = 'transparent';
                      e.currentTarget.style.color = '#64748b';
                    }
                  }}
                >
                  <Icon size={20} />
                </button>
              );
            })}

            {/* Separator */}
            <div style={{ width: '28px', height: '1px', backgroundColor: '#e2e8f0', margin: '4px 0' }} />

            {systemNav.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onTabChange(item.id)}
                  title={item.label}
                  style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '10px',
                    border: 'none',
                    background: isActive ? '#eff6ff' : 'transparent',
                    color: isActive ? '#2563eb' : '#64748b',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.backgroundColor = '#f1f5f9';
                      e.currentTarget.style.color = '#0f172a';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.backgroundColor = 'transparent';
                      e.currentTarget.style.color = '#64748b';
                    }
                  }}
                >
                  <Icon size={20} />
                </button>
              );
            })}
          </div>
        </div>

        {/* Bottom: Exit / Logout Icon */}
        <div>
          <button
            onClick={() => onTabChange('overview')}
            title="Overview / Home"
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              border: 'none',
              background: 'transparent',
              color: '#94a3b8',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = '#f1f5f9';
              e.currentTarget.style.color = '#0f172a';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
              e.currentTarget.style.color = '#94a3b8';
            }}
          >
            <LogOut size={19} />
          </button>
        </div>
      </aside>
    );
  }

  // ── STANDARD FULL SIDEBAR (FOR OTHER TABS) ──────────────────────────
  return (
    <aside className="app-sidebar-nav">
      {/* Brand Header */}
      <div className="sidebar-brand-container">
        <div className="sidebar-brand-icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="20" x2="18" y2="10"></line>
            <line x1="12" y1="20" x2="12" y2="4"></line>
            <line x1="6" y1="20" x2="6" y2="14"></line>
          </svg>
        </div>
        <div>
          <div className="sidebar-brand-title">AI-Based EDA</div>
          <div className="sidebar-brand-subtitle">Assistant</div>
        </div>
      </div>

      {/* Navigation Sections */}
      <div className="sidebar-scrollable-content">
        {/* Workspace Section */}
        <div className="sidebar-nav-section">
          <div className="sidebar-section-header">WORKSPACE</div>
          <div className="sidebar-nav-items">
            {workspaceNav.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onTabChange(item.id)}
                  className={`sidebar-nav-btn ${isActive ? 'active' : ''}`}
                >
                  <Icon size={18} className="sidebar-nav-icon" />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* System Section */}
        <div className="sidebar-nav-section" style={{ marginTop: '16px' }}>
          <div className="sidebar-section-header">SYSTEM</div>
          <div className="sidebar-nav-items">
            {systemNav.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onTabChange(item.id)}
                  className={`sidebar-nav-btn ${isActive ? 'active' : ''}`}
                >
                  <Icon size={18} className="sidebar-nav-icon" />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Bottom Sticky Area: Active Dataset Card & User Profile */}
      <div className="sidebar-footer-area">
        {activeDoc && (
          <div className="sidebar-active-dataset-card">
            <div className="active-card-header">
              <span className="active-dot-label">ACTIVE DATASET</span>
              <span className="active-status-dot"></span>
            </div>
            <div className="active-card-filename" title={activeDoc.filename}>
              {activeDoc.filename}
            </div>
            <div className="active-card-meta">
              {activeDoc.file_type.toUpperCase()} • {activeDoc.chunk_count ? `${activeDoc.chunk_count} chunks` : activeDoc.page_count ? `${activeDoc.page_count} pages` : 'Ready'}
            </div>
            <div className="active-card-actions">
              <button
                className="active-card-preview-btn"
                onClick={() => onPreviewDoc && onPreviewDoc(activeDoc)}
              >
                View Preview
              </button>
              <ChevronDown size={14} className="active-card-chevron" />
            </div>
          </div>
        )}

        <div className="sidebar-user-profile">
          <div className="user-avatar-badge">RS</div>
          <div className="user-profile-info">
            <div className="user-profile-name">Raj Singh</div>
            <div className="user-profile-mode">
              <span className="user-mode-dot"></span> Local Mode
            </div>
          </div>
          <ChevronDown size={16} className="user-dropdown-icon" />
        </div>
      </div>
    </aside>
  );
}
