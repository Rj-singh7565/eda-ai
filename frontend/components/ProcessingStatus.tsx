'use client';

import React from 'react';

interface ProcessingStatusProps {
  status: string;
  errorMessage?: string;
}

export default function ProcessingStatus({ status, errorMessage }: ProcessingStatusProps) {
  let badgeClass = 'status-processing';
  let label = 'Processing';

  switch (status) {
    case 'ready':
      badgeClass = 'status-ready';
      label = 'Ready';
      break;
    case 'failed':
      badgeClass = 'status-failed';
      label = 'Failed';
      break;
    case 'parsing':
      label = 'Parsing...';
      break;
    case 'normalizing':
      label = 'Normalizing...';
      break;
    case 'chunking':
      label = 'Chunking...';
      break;
    case 'embedding':
      label = 'Embedding...';
      break;
    case 'indexing':
      label = 'Indexing...';
      break;
    default:
      label = status;
  }

  return (
    <div style={{ display: 'inline-flex', flexDirection: 'column', gap: '4px' }}>
      <span className={`status-badge ${badgeClass}`}>{label}</span>
      {errorMessage && (
        <span style={{ fontSize: '0.75rem', color: '#ef4444' }}>{errorMessage}</span>
      )}
    </div>
  );
}
