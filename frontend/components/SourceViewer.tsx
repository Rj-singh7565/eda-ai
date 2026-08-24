'use client';

import React, { useState } from 'react';
import EvidenceRuler from './EvidenceRuler';

interface SourceViewerProps {
  filename: string;
  activeCoordinate: string;
  onSelectCoordinate: (coord: string) => void;
  markdownContent?: string;
}

export default function SourceViewer({
  filename,
  activeCoordinate,
  onSelectCoordinate,
  markdownContent
}: SourceViewerProps) {
  const [activeSubTab, setActiveSubTab] = useState<'source' | 'preview' | 'metadata'>('source');
  const [zoomLevel, setZoomLevel] = useState(110);
  const [currentPage, setCurrentPage] = useState(12);

  const handleZoom = (delta: number) => {
    setZoomLevel((prev) => Math.max(50, Math.min(200, prev + delta)));
  };

  return (
    <main className="col-source">
      {/* Top Document Header Tab */}
      <div className="source-header-tabs">
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div className="tab-pill active">
            <span style={{ color: '#dc2626', fontSize: '0.8rem', fontWeight: 700 }}>PDF</span>
            <span>{filename || 'Annual Report 2023.pdf'}</span>
            <span style={{ fontSize: '0.8rem', marginLeft: '6px', color: 'var(--muted)' }}>✕</span>
          </div>
          <button style={{ background: 'transparent', border: 'none', fontSize: '1.1rem', color: 'var(--muted)', cursor: 'pointer', padding: '4px 8px' }}>
            +
          </button>
        </div>
      </div>

      {/* Secondary Action Bar */}
      <div className="source-subbar">
        <div className="subtab-group">
          <span
            className={`subtab-item ${activeSubTab === 'source' ? 'active' : ''}`}
            onClick={() => setActiveSubTab('source')}
          >
            Source
          </span>
          <span
            className={`subtab-item ${activeSubTab === 'preview' ? 'active' : ''}`}
            onClick={() => setActiveSubTab('preview')}
          >
            Preview
          </span>
          <span
            className={`subtab-item ${activeSubTab === 'metadata' ? 'active' : ''}`}
            onClick={() => setActiveSubTab('metadata')}
          >
            Metadata
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: '0.82rem', color: 'var(--muted)' }}>
          <span style={{ cursor: 'pointer' }} title="Download Document">📥 Download</span>
          <span style={{ cursor: 'pointer' }} title="Expand View">⛶ Expand</span>
          <span style={{ cursor: 'pointer' }} title="More options">•••</span>
        </div>
      </div>

      {/* Main Body: Evidence Ruler + Paper Document Surface */}
      <div className="source-body-layout">
        {/* Signature Evidence Ruler */}
        <EvidenceRuler
          activeCoordinate={activeCoordinate}
          onSelectCoordinate={onSelectCoordinate}
        />

        {/* Paper Surface Document Reader */}
        <div className="paper-surface" style={{ zoom: `${zoomLevel}%` }}>
          {markdownContent ? (
            activeSubTab === 'source' ? (
              <pre
                style={{
                  fontFamily: 'var(--font-mono, monospace)',
                  fontSize: '0.82rem',
                  lineHeight: '1.6',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  color: 'var(--ink)'
                }}
              >
                {markdownContent}
              </pre>
            ) : activeSubTab === 'metadata' ? (
              <div>
                <h2 style={{ fontSize: '1rem', marginBottom: '12px' }}>Document Metadata</h2>
                <div style={{ padding: '14px', background: 'var(--surface)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', fontSize: '0.85rem' }}>
                  <div style={{ marginBottom: '8px' }}><strong>Filename:</strong> {filename}</div>
                  <div style={{ marginBottom: '8px' }}><strong>Size:</strong> {markdownContent.length} bytes</div>
                  <div style={{ marginBottom: '8px' }}><strong>Format:</strong> {filename.split('.').pop()?.toUpperCase()}</div>
                  <div><strong>Lines:</strong> {markdownContent.split('\n').length} lines</div>
                </div>
              </div>
            ) : (
              <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.7', fontSize: '0.9rem' }}>
                {markdownContent}
              </div>
            )
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', minHeight: '300px', color: 'var(--muted)', textAlign: 'center' }}>
              <div style={{ fontSize: '2.5rem', marginBottom: '12px' }}>📄</div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--ink)', marginBottom: '6px' }}>No Document Viewable</h3>
              <p style={{ fontSize: '0.85rem', maxWidth: '360px' }}>
                Upload or select a document from the left library sidebar to inspect its extracted text, tables, and citations.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Bottom Pagination & Zoom Controls Bar */}
      <div className="source-pagination-bar">
        <span>Page {currentPage} of 120</span>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button onClick={() => handleZoom(-10)} style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '1rem' }}>−</button>
          <span>{zoomLevel}%</span>
          <button onClick={() => handleZoom(10)} style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '1rem' }}>+</button>
        </div>
      </div>
    </main>
  );
}
