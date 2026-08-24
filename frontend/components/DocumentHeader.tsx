'use client';

import React from 'react';
import { Document, WorkspaceViewMode } from '../lib/types';
import ProcessingStatus from './ProcessingStatus';

interface DocumentHeaderProps {
  activeDoc: Document | null;
  onOpenMarkdown: () => void;
  viewMode: WorkspaceViewMode;
  onViewModeChange: (mode: WorkspaceViewMode) => void;
}

export default function DocumentHeader({
  activeDoc,
  onOpenMarkdown,
  viewMode,
  onViewModeChange
}: DocumentHeaderProps) {
  if (!activeDoc) {
    return (
      <header className="workspace-header">
        <div className="active-doc-info">
          <h1>Select a Document</h1>
          <div className="active-doc-meta">
            <span className="meta-pill" style={{ color: 'var(--text-muted)' }}>
              No Active Workspace Selection
            </span>
          </div>
        </div>
      </header>
    );
  }

  const formattedSize = activeDoc.file_size
    ? `${(activeDoc.file_size / 1024).toFixed(1)} KB`
    : 'Unknown size';

  return (
    <header className="workspace-header">
      <div className="active-doc-info">
        <h1>{activeDoc.filename}</h1>
        <div className="active-doc-meta">
          <span className="meta-pill">
            📄 {activeDoc.page_count || 0} Pages
          </span>
          <span className="meta-pill">
            🧩 {activeDoc.chunk_count || 0} Vectors
          </span>
          <span className="meta-pill">
            💾 {formattedSize}
          </span>
          <ProcessingStatus status={activeDoc.status} errorMessage={activeDoc.error_message} />
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        {/* View Mode Tabs */}
        <div className="view-mode-tabs">
          <button
            className={`view-mode-btn ${viewMode === 'chat' ? 'active' : ''}`}
            onClick={() => onViewModeChange('chat')}
            title="AI Analytical Chat Workspace"
          >
            <span>💬</span> AI Q&A
          </button>
          <button
            className={`view-mode-btn ${viewMode === 'reader' ? 'active' : ''}`}
            onClick={() => onViewModeChange('reader')}
            title="Inline Document Reader"
          >
            <span>📖</span> Reader View
          </button>
          <button
            className={`view-mode-btn ${viewMode === 'split' ? 'active' : ''}`}
            onClick={() => onViewModeChange('split')}
            title="Side-by-side Split View"
          >
            <span>📑</span> Split View
          </button>
        </div>

        {/* View Markdown Action Button */}
        <button
          onClick={onOpenMarkdown}
          className="btn-primary"
          style={{ fontSize: '0.8rem', padding: '6px 12px' }}
        >
          <span>👁️</span> Markdown Modal
        </button>
      </div>
    </header>
  );
}
