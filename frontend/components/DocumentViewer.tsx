'use client';

import React from 'react';

interface DocumentViewerProps {
  isOpen: boolean;
  filename: string;
  markdownContent: string;
  onClose: () => void;
}

export default function DocumentViewer({ isOpen, filename, markdownContent, onClose }: DocumentViewerProps) {
  if (!isOpen) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(markdownContent);
    alert('Markdown content copied to clipboard!');
  };

  const handleDownload = () => {
    const blob = new Blob([markdownContent], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${filename}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        backgroundColor: 'rgba(0,0,0,0.6)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: 200
      }}
    >
      <div
        style={{
          width: '75%',
          height: '80%',
          backgroundColor: 'var(--bg-sidebar)',
          border: '1px solid var(--border-color)',
          borderRadius: '12px',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}
      >
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3>Document Markdown — {filename}</h3>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button onClick={handleCopy} className="btn-primary" style={{ padding: '4px 12px', fontSize: '0.8rem' }}>📋 Copy</button>
            <button onClick={handleDownload} className="btn-primary" style={{ padding: '4px 12px', fontSize: '0.8rem' }}>⬇️ Download .md</button>
            <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-primary)', fontSize: '1.2rem', cursor: 'pointer' }}>&times;</button>
          </div>
        </div>
        <div style={{ flex: 1, padding: '20px', overflowY: 'auto', backgroundColor: 'var(--bg-app)' }}>
          <pre style={{ fontFamily: 'var(--font-mono)', fontSize: '0.88rem', whiteSpace: 'pre-wrap', color: 'var(--text-primary)' }}>
            {markdownContent}
          </pre>
        </div>
      </div>
    </div>
  );
}
