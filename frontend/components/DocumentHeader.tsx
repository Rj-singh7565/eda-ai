'use client';

import React from 'react';
import { Document } from '../lib/types';
import ProcessingStatus from './ProcessingStatus';

interface DocumentHeaderProps {
  activeDoc: Document | null;
  onOpenMarkdown: () => void;
}

export default function DocumentHeader({ activeDoc, onOpenMarkdown }: DocumentHeaderProps) {
  if (!activeDoc) {
    return (
      <header className="workspace-header">
        <div className="active-doc-info">
          <h1>Select a Document</h1>
          <div className="active-doc-meta">
            <span className="status-badge status-idle">No Document Selected</span>
          </div>
        </div>
      </header>
    );
  }

  return (
    <header className="workspace-header">
      <div className="active-doc-info">
        <h1>{activeDoc.filename}</h1>
        <div className="active-doc-meta">
          <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
            {activeDoc.page_count || 0} pages / sections
          </span>
          <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
            {activeDoc.chunk_count || 0} chunks
          </span>
          <ProcessingStatus status={activeDoc.status} errorMessage={activeDoc.error_message} />
        </div>
      </div>
      <div>
        <button
          onClick={onOpenMarkdown}
          className="btn-primary"
          style={{ fontSize: '0.85rem', padding: '6px 14px', borderRadius: '8px' }}
        >
          📄 View Markdown
        </button>
      </div>
    </header>
  );
}
