'use client';

import React from 'react';
import { DocumentStatus } from '../lib/types';

interface ProcessingStatusProps {
  status: DocumentStatus;
  errorMessage?: string;
  chunkCount?: number;
  compact?: boolean;
}

export default function ProcessingStatus({ status, errorMessage, chunkCount, compact }: ProcessingStatusProps) {
  const stages: { key: DocumentStatus; label: string }[] = [
    { key: 'parsing', label: 'Parsing' },
    { key: 'chunking', label: 'Chunking' },
    { key: 'embedding', label: 'Embedding' },
    { key: 'indexing', label: 'Indexing' },
    { key: 'ready', label: 'Ready' }
  ];

  const getStageIndex = (st: DocumentStatus) => {
    switch (st) {
      case 'processing':
      case 'parsing':
      case 'normalizing':
        return 0;
      case 'chunking':
        return 1;
      case 'embedding':
        return 2;
      case 'indexing':
        return 3;
      case 'ready':
        return 4;
      default:
        return -1;
    }
  };

  const currentIndex = getStageIndex(status);

  if (status === 'ready') {
    return (
      <span
        className="meta-pill"
        style={{
          background: 'rgba(22, 163, 74, 0.12)',
          color: '#16a34a',
          borderColor: 'rgba(22, 163, 74, 0.3)',
          fontWeight: 600,
          fontSize: compact ? '0.68rem' : '0.75rem',
          display: 'inline-flex',
          alignItems: 'center',
          gap: '4px'
        }}
      >
        <span style={{ color: '#16a34a' }}>✓</span> Ready to use • Embedding complete
        {chunkCount && chunkCount > 0 ? ` (${chunkCount.toLocaleString()} chunks)` : ''}
      </span>
    );
  }

  if (status === 'failed') {
    return (
      <span
        className="meta-pill"
        style={{
          background: 'rgba(220, 38, 38, 0.12)',
          color: '#dc2626',
          borderColor: 'rgba(220, 38, 38, 0.3)',
          fontSize: compact ? '0.68rem' : '0.75rem'
        }}
        title={errorMessage}
      >
        ⚠️ Ingestion Failed
      </span>
    );
  }

  if (compact) {
    const currentLabel = stages[currentIndex]?.label || status;
    return (
      <span
        className="meta-pill"
        style={{
          background: 'rgba(99, 102, 241, 0.12)',
          color: '#6366f1',
          borderColor: 'rgba(99, 102, 241, 0.3)',
          fontSize: '0.68rem',
          display: 'inline-flex',
          alignItems: 'center',
          gap: '4px'
        }}
      >
        <span style={{ animation: 'spin 1.5s linear infinite', display: 'inline-block' }}>⏳</span> {currentLabel}...
      </span>
    );
  }

  return (
    <div className="pipeline-container" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
      {stages.map((stg, idx) => {
        const isCompleted = idx < currentIndex;
        const isActive = idx === currentIndex;

        return (
          <React.Fragment key={stg.key}>
            <span
              className={`pipeline-step ${isActive ? 'active' : isCompleted ? 'completed' : ''}`}
              style={{
                fontSize: '0.72rem',
                fontWeight: isActive ? 700 : isCompleted ? 600 : 400,
                color: isCompleted ? '#16a34a' : isActive ? '#6366f1' : 'var(--text-muted)'
              }}
            >
              {isCompleted ? '✓' : isActive ? '⏳' : '○'} {stg.label}
            </span>
            {idx < stages.length - 1 && (
              <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>→</span>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}
