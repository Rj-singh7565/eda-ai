'use client';

import React, { useState } from 'react';

interface DocumentViewerProps {
  isOpen: boolean;
  filename: string;
  markdownContent: string;
  onClose: () => void;
}

export default function DocumentViewer({ isOpen, filename, markdownContent, onClose }: DocumentViewerProps) {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(markdownContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
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
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.65)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: 200,
        animation: 'fadeIn 0.2s ease-out'
      }}
    >
      <div
        style={{
          width: '80%',
          maxWidth: '1000px',
          height: '82%',
          backgroundColor: 'var(--bg-sidebar)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-lg)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          boxShadow: 'var(--shadow-lg)'
        }}
      >
        <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-glass)' }}>
          <div>
            <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.1rem', fontWeight: 700 }}>Canonical Markdown — {filename}</h3>
            <span style={{ fontSize: '0.73rem', color: 'var(--text-muted)' }}>Normalized YAML Frontmatter + Structured Text</span>
          </div>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <button onClick={handleCopy} className="btn-primary" style={{ padding: '6px 14px', fontSize: '0.8rem', borderRadius: '8px' }}>
              {copied ? '✅ Copied' : '📋 Copy'}
            </button>
            <button onClick={handleDownload} className="btn-primary" style={{ padding: '6px 14px', fontSize: '0.8rem', borderRadius: '8px' }}>
              ⬇️ Download .md
            </button>
            <button
              onClick={onClose}
              style={{
                background: 'rgba(255, 255, 255, 0.06)',
                border: '1px solid var(--border-color)',
                color: 'var(--text-primary)',
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                fontSize: '1.2rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              &times;
            </button>
          </div>
        </div>
        <div style={{ flex: 1, padding: '24px', overflowY: 'auto', backgroundColor: 'var(--bg-app)' }}>
          <pre style={{ fontFamily: 'var(--font-mono)', fontSize: '0.88rem', lineHeight: '1.65', whiteSpace: 'pre-wrap', color: 'var(--text-primary)' }}>
            {markdownContent}
          </pre>
        </div>
      </div>
    </div>
  );
}
