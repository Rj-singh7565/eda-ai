'use client';

import React from 'react';
import { Citation } from '../lib/types';

interface CitationCardProps {
  citation: Citation | null;
  onClose: () => void;
}

export default function CitationCard({ citation, onClose }: CitationCardProps) {
  if (!citation) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        right: 0,
        width: '380px',
        height: '100vh',
        backgroundColor: 'var(--bg-sidebar)',
        borderLeft: '1px solid var(--border-color)',
        padding: '24px',
        zIndex: 100,
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        boxShadow: 'var(--shadow-lg)'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ fontSize: '1.05rem', fontWeight: 600 }}>Source Excerpt</h3>
        <button
          onClick={onClose}
          style={{ background: 'none', border: 'none', color: 'var(--text-primary)', fontSize: '1.2rem', cursor: 'pointer' }}
        >
          &times;
        </button>
      </div>

      <div style={{ display: 'flex', gap: '12px', fontSize: '0.8rem' }}>
        <span className="status-badge status-ready">{citation.pages.join(', ')}</span>
        <span style={{ color: 'var(--text-secondary)' }}>
          Score: {(citation.score * 100).toFixed(1)}%
        </span>
      </div>

      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          backgroundColor: 'var(--bg-app)',
          padding: '14px',
          borderRadius: '8px',
          fontFamily: 'var(--font-mono)',
          fontSize: '0.85rem',
          whiteSpace: 'pre-wrap',
          color: 'var(--text-primary)'
        }}
      >
        {citation.full_text || citation.text_snippet}
      </div>
    </div>
  );
}
