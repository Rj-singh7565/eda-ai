'use client';

import React from 'react';
import { Document } from '../lib/types';
import UploadZone from './UploadZone';

interface DocumentSidebarProps {
  documents: Document[];
  activeDocId: string | null;
  onSelectDoc: (docId: string) => void;
  onDeleteDoc: (docId: string) => void;
  onUpload: (file: File) => void;
  isUploading: boolean;
}

export default function DocumentSidebar({
  documents,
  activeDocId,
  onSelectDoc,
  onDeleteDoc,
  onUpload,
  isUploading
}: DocumentSidebarProps) {
  return (
    <aside className="sidebar">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>EDA Assistant</h2>
          <span style={{ fontSize: '0.72rem', color: 'var(--accent-primary)', background: 'var(--accent-glow)', padding: '2px 6px', borderRadius: '4px' }}>
            v2.0 MVP
          </span>
        </div>
      </div>

      <UploadZone onUpload={onUpload} isUploading={isUploading} />

      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
          <span>Documents</span>
          <span>{documents.length}</span>
        </div>

        <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {documents.map((doc) => {
            const isActive = doc.doc_id === activeDocId;
            return (
              <li
                key={doc.doc_id}
                onClick={() => onSelectDoc(doc.doc_id)}
                style={{
                  padding: '10px 12px',
                  borderRadius: '8px',
                  backgroundColor: isActive ? 'var(--bg-card-hover)' : 'var(--bg-card)',
                  border: isActive ? '1px solid var(--border-focus)' : '1px solid var(--border-color)',
                  cursor: 'pointer',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
              >
                <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: 500, color: 'var(--text-primary)' }}>
                    {doc.filename}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    {doc.status === 'ready' ? '● Ready' : `● ${doc.status}`}
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteDoc(doc.doc_id);
                  }}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                    fontSize: '1rem',
                    padding: '2px 6px'
                  }}
                  title="Delete Document"
                >
                  &times;
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </aside>
  );
}
