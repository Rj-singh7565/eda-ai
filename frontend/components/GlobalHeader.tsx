'use client';

import React, { useState } from 'react';
import { Download, Bell, ChevronDown, FileText, Activity } from 'lucide-react';
import { Document, NavTab } from '../lib/types';

interface GlobalHeaderProps {
  activeTab: NavTab;
  activeDoc: Document | null;
  documents: Document[];
  onSelectDoc: (docId: string) => void;
  onExportReport?: () => void;
}

export default function GlobalHeader({
  activeTab,
  activeDoc,
  documents,
  onSelectDoc,
  onExportReport
}: GlobalHeaderProps) {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isNotificationOpen, setIsNotificationOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(3);

  const isAnalysisTab = activeTab === 'analysis';

  const getTitle = () => {
    switch (activeTab) {
      case 'overview':
        return 'Overview';
      case 'datasets':
        return 'Datasets Management';
      case 'analysis':
        return 'AI Analysis & Intelligence';
      case 'history':
        return 'Analysis History';
      case 'storage':
        return 'Storage & Persistence';
      case 'settings':
        return 'System Settings';
      default:
        return 'Dashboard';
    }
  };

  // ── COMPACT HEADER FOR ANALYSIS PAGE ──────────────────────────────────
  if (isAnalysisTab) {
    return (
      <header
        className="dashboard-global-header compact-analysis-header"
        style={{
          height: '60px',
          minHeight: '60px',
          padding: '0 24px',
          backgroundColor: '#ffffff',
          borderBottom: '1px solid #e2e8f0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          zIndex: 30
        }}
      >
        {/* Left: Clean Page Title */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <h1
            style={{
              fontFamily: 'var(--font-heading, sans-serif)',
              fontSize: '1.25rem',
              fontWeight: 700,
              color: '#0f172a',
              margin: 0,
              letterSpacing: '-0.02em'
            }}
          >
            AI Analysis & Intelligence
          </h1>
        </div>

        {/* Right: Controls Group */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Active Dataset Dropdown Selector */}
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              title="Select Active Dataset"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '6px 14px',
                backgroundColor: '#f8fafc',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                fontSize: '0.82rem',
                fontWeight: 600,
                color: '#1e293b',
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = '#f1f5f9';
                e.currentTarget.style.borderColor = '#cbd5e1';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = '#f8fafc';
                e.currentTarget.style.borderColor = '#e2e8f0';
              }}
            >
              <FileText size={15} style={{ color: '#2563eb' }} />
              <span style={{ maxWidth: '180px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {activeDoc ? activeDoc.filename : 'No dataset selected'}
              </span>
              <ChevronDown size={14} style={{ color: '#64748b' }} />
            </button>

            {isDropdownOpen && (
              <div
                style={{
                  position: 'absolute',
                  top: 'calc(100% + 6px)',
                  right: 0,
                  width: '280px',
                  backgroundColor: '#ffffff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '10px',
                  boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1)',
                  padding: '8px',
                  zIndex: 100,
                  maxHeight: '260px',
                  overflowY: 'auto'
                }}
              >
                <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', padding: '6px 8px' }}>
                  Switch Active Dataset
                </div>
                {documents.length === 0 ? (
                  <div style={{ padding: '8px', fontSize: '0.8rem', color: '#94a3b8', textAlign: 'center' }}>
                    No datasets available
                  </div>
                ) : (
                  documents.map((doc) => (
                    <div
                      key={doc.doc_id}
                      onClick={() => {
                        onSelectDoc(doc.doc_id);
                        setIsDropdownOpen(false);
                      }}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '8px 10px',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        fontSize: '0.82rem',
                        color: activeDoc?.doc_id === doc.doc_id ? '#2563eb' : '#0f172a',
                        backgroundColor: activeDoc?.doc_id === doc.doc_id ? '#eff6ff' : 'transparent',
                        fontWeight: activeDoc?.doc_id === doc.doc_id ? 600 : 400
                      }}
                      onMouseEnter={(e) => {
                        if (activeDoc?.doc_id !== doc.doc_id) e.currentTarget.style.backgroundColor = '#f1f5f9';
                      }}
                      onMouseLeave={(e) => {
                        if (activeDoc?.doc_id !== doc.doc_id) e.currentTarget.style.backgroundColor = 'transparent';
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', maxWidth: '200px' }}>
                        <FileText size={14} style={{ color: '#2563eb', flexShrink: 0 }} />
                        <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{doc.filename}</span>
                      </div>
                      <span style={{ width: '7px', height: '7px', borderRadius: '50%', backgroundColor: '#10b981' }}></span>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          {/* Engine Ready Badge */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: '#f0fdf4',
              border: '1px solid #bbf7d0',
              borderRadius: '9999px',
              padding: '5px 12px',
              fontSize: '0.78rem',
              color: '#166534',
              fontWeight: 600
            }}
          >
            <Activity size={14} style={{ color: '#10b981' }} className="health-pulse-icon" />
            <span>Engine: <strong>Ready</strong></span>
          </div>

          {/* Export / Download Icon Button */}
          <button
            onClick={onExportReport}
            title="Export Report"
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              border: '1px solid #e2e8f0',
              backgroundColor: '#ffffff',
              color: '#475569',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = '#f8fafc';
              e.currentTarget.style.color = '#0f172a';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = '#ffffff';
              e.currentTarget.style.color = '#475569';
            }}
          >
            <Download size={16} />
          </button>

          {/* Notification Bell Button */}
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => setIsNotificationOpen(!isNotificationOpen)}
              title="Notifications"
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '8px',
                border: '1px solid #e2e8f0',
                backgroundColor: '#ffffff',
                color: '#475569',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                position: 'relative',
                transition: 'all 0.15s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = '#f8fafc';
                e.currentTarget.style.color = '#0f172a';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = '#ffffff';
                e.currentTarget.style.color = '#475569';
              }}
            >
              <Bell size={16} />
              {unreadCount > 0 && (
                <span
                  style={{
                    position: 'absolute',
                    top: '-3px',
                    right: '-3px',
                    backgroundColor: '#2563eb',
                    color: '#ffffff',
                    fontSize: '0.65rem',
                    fontWeight: 700,
                    width: '15px',
                    height: '15px',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  {unreadCount}
                </span>
              )}
            </button>

            {isNotificationOpen && (
              <div
                style={{
                  position: 'absolute',
                  top: 'calc(100% + 6px)',
                  right: 0,
                  width: '300px',
                  backgroundColor: '#ffffff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '10px',
                  boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1)',
                  padding: '10px',
                  zIndex: 100
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '8px', borderBottom: '1px solid #f1f5f9', marginBottom: '8px' }}>
                  <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#0f172a' }}>Notifications</span>
                  {unreadCount > 0 && (
                    <button
                      onClick={() => setUnreadCount(0)}
                      style={{ background: 'transparent', border: 'none', color: '#2563eb', fontSize: '0.72rem', fontWeight: 600, cursor: 'pointer' }}
                    >
                      Mark all read
                    </button>
                  )}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div style={{ padding: '6px', borderRadius: '6px', backgroundColor: '#f8fafc' }}>
                    <div style={{ fontWeight: 600, fontSize: '0.8rem', color: '#0f172a' }}>System Ready</div>
                    <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Vector storage and DataFrame engine active</div>
                  </div>
                  <div style={{ padding: '6px', borderRadius: '6px', backgroundColor: '#f8fafc' }}>
                    <div style={{ fontWeight: 600, fontSize: '0.8rem', color: '#0f172a' }}>Large Dataset Pipeline</div>
                    <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Streaming and structured queries enabled</div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* User Avatar Circle */}
          <div
            style={{
              width: '34px',
              height: '34px',
              borderRadius: '50%',
              backgroundColor: '#2563eb',
              color: '#ffffff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 700,
              fontSize: '0.82rem',
              cursor: 'pointer',
              boxShadow: '0 2px 4px rgba(37, 99, 235, 0.2)'
            }}
            title="Raj Singh"
          >
            RS
          </div>
        </div>
      </header>
    );
  }

  // ── STANDARD FULL HEADER (FOR OTHER TABS) ─────────────────────────────
  return (
    <header className="dashboard-global-header">
      {/* Left: Greeting and Context */}
      <div className="header-greeting-group">
        <h1 className="header-page-title">{getTitle()}</h1>
        <p className="header-page-subtitle">Welcome back, Raj Singh</p>
      </div>

      {/* Right Controls */}
      <div className="header-controls-group">
        {/* Active Dataset Dropdown Selector */}
        <div className="dataset-switcher-wrapper">
          <div className="dataset-switcher-label">Active Dataset</div>
          <button
            className="dataset-switcher-btn"
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            title="Switch Active Dataset"
          >
            <FileText size={16} className="dataset-switcher-file-icon" />
            <span className="dataset-switcher-name">
              {activeDoc ? activeDoc.filename : 'Select a Dataset'}
            </span>
            {activeDoc && (
              <span className={`dataset-status-pill ${activeDoc.status}`}>
                {activeDoc.status === 'ready' ? 'Ready' : activeDoc.status}
              </span>
            )}
            <ChevronDown size={15} className="dataset-switcher-chevron" />
          </button>

          {isDropdownOpen && (
            <div className="dataset-dropdown-menu">
              <div className="dropdown-menu-title">Switch Active Dataset</div>
              {documents.length === 0 ? (
                <div className="dropdown-empty">No datasets available</div>
              ) : (
                documents.map((doc) => (
                  <div
                    key={doc.doc_id}
                    className={`dropdown-item ${activeDoc?.doc_id === doc.doc_id ? 'selected' : ''}`}
                    onClick={() => {
                      onSelectDoc(doc.doc_id);
                      setIsDropdownOpen(false);
                    }}
                  >
                    <div className="dropdown-item-left">
                      <FileText size={15} />
                      <span className="dropdown-item-name">{doc.filename}</span>
                    </div>
                    <span className={`dataset-status-pill ${doc.status}`}>
                      {doc.status}
                    </span>
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        {/* Export Report Button */}
        <button
          className="header-export-btn"
          onClick={onExportReport}
          title="Export Analysis Report"
        >
          <Download size={16} />
          <span>Export Report</span>
        </button>

        {/* Notification Bell Badge */}
        <div className="header-notification-wrapper" title="Notifications">
          <button
            className="header-bell-btn"
            onClick={() => setIsNotificationOpen(!isNotificationOpen)}
          >
            <Bell size={18} />
            {unreadCount > 0 && (
              <span className="notification-badge-count">{unreadCount}</span>
            )}
          </button>

          {isNotificationOpen && (
            <div className="dataset-dropdown-menu" style={{ width: '320px', right: 0 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 10px' }}>
                <span className="dropdown-menu-title" style={{ padding: 0 }}>Notifications</span>
                {unreadCount > 0 && (
                  <button
                    onClick={() => setUnreadCount(0)}
                    style={{ background: 'transparent', border: 'none', color: '#2563eb', fontSize: '0.72rem', fontWeight: 600, cursor: 'pointer' }}
                  >
                    Mark all read
                  </button>
                )}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <div className="dropdown-item" style={{ flexDirection: 'column', alignItems: 'flex-start' }}>
                  <div style={{ fontWeight: 600, fontSize: '0.82rem', color: '#0f172a' }}>System Ready</div>
                  <div style={{ fontSize: '0.74rem', color: '#64748b' }}>PostgreSQL & Pinecone vector storage active</div>
                </div>
                <div className="dropdown-item" style={{ flexDirection: 'column', alignItems: 'flex-start' }}>
                  <div style={{ fontWeight: 600, fontSize: '0.82rem', color: '#0f172a' }}>Large Dataset Pipeline</div>
                  <div style={{ fontSize: '0.74rem', color: '#64748b' }}>Fast streaming & 100k+ row indexing enabled</div>
                </div>
                <div className="dropdown-item" style={{ flexDirection: 'column', alignItems: 'flex-start' }}>
                  <div style={{ fontWeight: 600, fontSize: '0.82rem', color: '#0f172a' }}>Local Mode Active</div>
                  <div style={{ fontSize: '0.74rem', color: '#64748b' }}>Running on port 8000 (FastAPI backend)</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
