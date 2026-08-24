'use client';

import React, { useState } from 'react';

interface DocumentWorkspaceReaderProps {
  filename: string;
  markdownContent: string;
  isLoading: boolean;
  onOpenModal: () => void;
}

export default function DocumentWorkspaceReader({
  filename,
  markdownContent,
  isLoading,
  onOpenModal
}: DocumentWorkspaceReaderProps) {
  const [searchFilter, setSearchFilter] = useState('');

  if (isLoading) {
    return (
      <div className="doc-reader-pane" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
          Loading document representation...
        </div>
      </div>
    );
  }

  if (!markdownContent) {
    return (
      <div className="doc-reader-pane" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
          <p style={{ marginBottom: '8px' }}>📄 No Markdown representation available for this document yet.</p>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            The document may still be undergoing parsing or normalization.
          </p>
        </div>
      </div>
    );
  }

  // Helper to split YAML header from body if present
  let yamlHeader = '';
  let bodyContent = markdownContent;

  if (markdownContent.startsWith('---')) {
    const parts = markdownContent.split('---');
    if (parts.length >= 3) {
      yamlHeader = parts[1].trim();
      bodyContent = parts.slice(2).join('---').trim();
    }
  }

  return (
    <div className="doc-reader-pane">
      {/* Reader Toolbar */}
      <div className="doc-reader-header">
        <div>
          <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.05rem', fontWeight: 700 }}>
            {filename}
          </h2>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
            Normalized Editorial Document View
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <input
            type="text"
            placeholder="Search text in document..."
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            style={{
              padding: '5px 10px',
              borderRadius: 'var(--radius-xs)',
              border: '1px solid var(--border-color)',
              background: 'var(--bg-app)',
              color: 'var(--text-primary)',
              fontSize: '0.8rem',
              outline: 'none'
            }}
          />
          <button className="btn-primary" onClick={onOpenModal} style={{ fontSize: '0.78rem', padding: '6px 12px' }}>
            <span>🔍</span> Expand Fullscreen
          </button>
        </div>
      </div>

      {/* YAML Metadata Display */}
      {yamlHeader && (
        <div className="yaml-metadata-box">
          <div style={{ fontWeight: 700, marginBottom: '4px', textTransform: 'uppercase', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
            Metadata Overview (YAML)
          </div>
          <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{yamlHeader}</pre>
        </div>
      )}

      {/* Document Body View */}
      <div className="doc-reader-content">
        {bodyContent.split('\n\n').map((block, idx) => {
          const trimmed = block.trim();
          if (!trimmed) return null;

          if (trimmed.startsWith('# ')) {
            return <h1 key={idx}>{trimmed.replace(/^#\s+/, '')}</h1>;
          }
          if (trimmed.startsWith('## ')) {
            return <h2 key={idx}>{trimmed.replace(/^##\s+/, '')}</h2>;
          }
          if (trimmed.startsWith('### ')) {
            return <h3 key={idx}>{trimmed.replace(/^###\s+/, '')}</h3>;
          }

          // Table render simple detection
          if (trimmed.includes('|')) {
            const rows = trimmed.split('\n').filter((r) => r.trim().startsWith('|'));
            if (rows.length > 0) {
              const headers = rows[0]
                .split('|')
                .filter((c) => c.trim() !== '')
                .map((c) => c.trim());
              const bodyRows = rows.slice(2);

              return (
                <div key={idx} style={{ overflowX: 'auto', margin: '14px 0' }}>
                  <table>
                    <thead>
                      <tr>
                        {headers.map((h, i) => (
                          <th key={i}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {bodyRows.map((row, rIdx) => {
                        const cols = row
                          .split('|')
                          .filter((c) => c.trim() !== '')
                          .map((c) => c.trim());
                        return (
                          <tr key={rIdx}>
                            {cols.map((col, cIdx) => (
                              <td key={cIdx}>{col}</td>
                            ))}
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              );
            }
          }

          return <p key={idx} style={{ marginBottom: '12px' }}>{trimmed}</p>;
        })}
      </div>
    </div>
  );
}
