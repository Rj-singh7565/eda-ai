'use client';

import React from 'react';
import { Citation } from '../lib/types';

interface CitationCardProps {
  citation: Citation;
  isSelected?: boolean;
  onSelect: () => void;
}

export default function CitationCard({ citation, isSelected, onSelect }: CitationCardProps) {
  const isExact = citation.match_type === 'Exact match';

  return (
    <div
      onClick={onSelect}
      className={`cite-card ${isSelected ? 'selected' : ''}`}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--ink)' }}>
            {citation.location}
          </div>
          <div style={{ fontSize: '0.73rem', color: 'var(--muted)', marginTop: '1px' }}>
            {citation.document_name}
          </div>
        </div>
        <span className={isExact ? 'badge-exact' : 'badge-text'}>
          {citation.match_type}
        </span>
      </div>

      {/* Text Snippet */}
      {citation.snippet && (
        <p style={{ fontSize: '0.8rem', color: 'var(--ink)', lineHeight: '1.5', background: 'var(--surface)', padding: '8px 10px', borderRadius: '4px', border: '1px solid var(--border)' }}>
          {citation.snippet}
        </p>
      )}

      {/* Mini Table Preview */}
      {citation.category === 'table' && citation.table_data && (
        <div style={{ overflowX: 'auto', border: '1px solid var(--border)', borderRadius: '4px', marginTop: '4px' }}>
          <table style={{ width: '100%', fontSize: '0.68rem', borderCollapse: 'collapse', fontFamily: 'var(--font-mono)' }}>
            <thead>
              <tr style={{ background: 'var(--surface)' }}>
                {citation.table_data.headers.map((h, i) => (
                  <th key={i} style={{ padding: '3px 6px', borderBottom: '1px solid var(--border)', textAlign: 'left' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {citation.table_data.rows.map((row, rIdx) => (
                <tr key={rIdx}>
                  {row.map((cell, cIdx) => (
                    <td key={cIdx} style={{ padding: '3px 6px', borderBottom: '1px solid var(--border)' }}>{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Mini Figure Preview */}
      {citation.category === 'figure' && (
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '4px', padding: '8px', display: 'flex', alignItems: 'flex-end', justifyContent: 'space-around', height: '54px' }}>
          <div style={{ width: '14px', height: '24px', background: 'var(--slate)', borderRadius: '2px' }} />
          <div style={{ width: '14px', height: '34px', background: 'var(--slate)', borderRadius: '2px' }} />
          <div style={{ width: '14px', height: '44px', background: 'var(--slate)', borderRadius: '2px' }} />
        </div>
      )}

      <div style={{ fontSize: '0.7rem', color: 'var(--muted)', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
        Score: {citation.score.toFixed(2)}
      </div>
    </div>
  );
}
