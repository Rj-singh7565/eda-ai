'use client';

import React, { useEffect } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('[Dashboard Error Boundary Caught]:', error);
  }, [error]);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        width: '100vw',
        backgroundColor: '#0f172a',
        color: '#f8fafc',
        padding: '24px',
        textAlign: 'center',
        boxSizing: 'border-box',
      }}
    >
      <div
        style={{
          width: '56px',
          height: '56px',
          borderRadius: '16px',
          backgroundColor: '#450a0a',
          color: '#ef4444',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: '20px',
          border: '1px solid #7f1d1d',
        }}
      >
        <AlertTriangle size={28} />
      </div>

      <h2
        style={{
          fontSize: '1.5rem',
          fontWeight: 700,
          margin: '0 0 8px 0',
          fontFamily: 'var(--font-heading, sans-serif)',
        }}
      >
        Workspace Error Detected
      </h2>

      <p
        style={{
          maxWidth: '520px',
          color: '#94a3b8',
          fontSize: '0.9rem',
          lineHeight: '1.6',
          marginBottom: '24px',
        }}
      >
        {error?.message || 'An unexpected rendering error occurred. The server-first architecture isolated the issue.'}
      </p>

      <button
        onClick={() => reset()}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '10px 20px',
          backgroundColor: '#2563eb',
          color: '#ffffff',
          border: 'none',
          borderRadius: '8px',
          fontSize: '0.88rem',
          fontWeight: 600,
          cursor: 'pointer',
          boxShadow: '0 2px 8px rgba(37, 99, 235, 0.4)',
        }}
      >
        <RefreshCw size={16} />
        <span>Reload Workspace</span>
      </button>
    </div>
  );
}
