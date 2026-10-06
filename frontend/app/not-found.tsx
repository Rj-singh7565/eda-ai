import React from 'react';
import Link from 'next/link';
import { Home } from 'lucide-react';

export default function NotFound() {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        width: '100vw',
        backgroundColor: '#f8fafc',
        color: '#0f172a',
        padding: '24px',
        textAlign: 'center',
      }}
    >
      <h1
        style={{
          fontSize: '4rem',
          fontWeight: 800,
          color: '#2563eb',
          margin: '0 0 12px 0',
          fontFamily: 'var(--font-heading, sans-serif)',
        }}
      >
        404
      </h1>
      <h2 style={{ fontSize: '1.4rem', fontWeight: 600, margin: '0 0 12px 0' }}>
        Dataset or Workspace Resource Not Found
      </h2>
      <p style={{ color: '#64748b', maxWidth: '440px', lineHeight: '1.6', marginBottom: '24px' }}>
        The requested document, analysis session, or route does not exist in the EDA Assistant workspace.
      </p>
      <Link
        href="/"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
          padding: '10px 20px',
          backgroundColor: '#2563eb',
          color: '#ffffff',
          borderRadius: '8px',
          textDecoration: 'none',
          fontSize: '0.88rem',
          fontWeight: 600,
        }}
      >
        <Home size={16} />
        <span>Return to Dashboard</span>
      </Link>
    </div>
  );
}
