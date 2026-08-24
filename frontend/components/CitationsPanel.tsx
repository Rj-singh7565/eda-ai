'use client';

import React, { useState } from 'react';
import { Citation } from '../lib/types';
import CitationCard from './CitationCard';

interface CitationsPanelProps {
  selectedCitationId: string | null;
  onSelectCitation: (id: string) => void;
  citations?: Citation[];
  onClose?: () => void;
}

export default function CitationsPanel({
  selectedCitationId,
  onSelectCitation,
  citations,
  onClose
}: CitationsPanelProps) {
  const [filterTab, setFilterTab] = useState<'all' | 'table' | 'figure' | 'text'>('all');

  const activeCitations = citations || [];

  const filteredCitations = activeCitations.filter((c) => {
    if (filterTab === 'all') return true;
    return c.category === filterTab;
  });

  const tableCount = activeCitations.filter((c) => c.category === 'table').length;
  const figureCount = activeCitations.filter((c) => c.category === 'figure').length;
  const textCount = activeCitations.filter((c) => c.category === 'text').length;

  const handleExportCSV = () => {
    let csvContent = 'data:text/csv;charset=utf-8,Document,Location,Category,Match Type,Score,Snippet\n';
    activeCitations.forEach((c) => {
      csvContent += `"${c.document_name || 'Document'}","${c.location}","${c.category}","${c.match_type}",${c.score},"${c.snippet.replace(/"/g, '""')}"\n`;
    });
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', 'eda_citations_export.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <aside className="col-citations">
      {/* Header */}
      <div className="citations-header">
        <span>Citations ({activeCitations.length})</span>
        <button
          onClick={onClose}
          style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '1rem', color: 'var(--muted)' }}
          title="Close citations panel"
        >
          ✕
        </button>
      </div>

      {/* Filter Category Tabs */}
      <div className="citations-tabs">
        <button
          className={`cite-tab ${filterTab === 'all' ? 'active' : ''}`}
          onClick={() => setFilterTab('all')}
        >
          All {activeCitations.length}
        </button>
        <button
          className={`cite-tab ${filterTab === 'table' ? 'active' : ''}`}
          onClick={() => setFilterTab('table')}
        >
          Tables {tableCount}
        </button>
        <button
          className={`cite-tab ${filterTab === 'figure' ? 'active' : ''}`}
          onClick={() => setFilterTab('figure')}
        >
          Figures {figureCount}
        </button>
        <button
          className={`cite-tab ${filterTab === 'text' ? 'active' : ''}`}
          onClick={() => setFilterTab('text')}
        >
          Text {textCount}
        </button>
      </div>

      {/* Feed */}
      <div className="citations-feed">
        {filteredCitations.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '30px 10px', color: 'var(--muted)', fontSize: '0.82rem' }}>
            No citations available for this section. Ask a question to view matching document citations.
          </div>
        ) : (
          filteredCitations.map((c) => (
            <CitationCard
              key={c.id}
              citation={c}
              isSelected={selectedCitationId === c.id}
              onSelect={() => onSelectCitation(c.id)}
            />
          ))
        )}
      </div>

      {/* Bottom Export Action */}
      {activeCitations.length > 0 && (
        <div className="export-cite-bar">
          <button className="export-btn" onClick={handleExportCSV}>
            <span>↓ Export citations</span>
          </button>
        </div>
      )}
    </aside>
  );
}
