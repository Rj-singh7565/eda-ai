'use client';

import React from 'react';
import { DocumentStatus } from '../lib/types';

interface ProcessingStatusProps {
  status: DocumentStatus;
  errorMessage?: string;
}

export default function ProcessingStatus({ status, errorMessage }: ProcessingStatusProps) {
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
      <span className="meta-pill" style={{ background: 'var(--status-ready-bg)', color: 'var(--status-ready)', borderColor: 'rgba(22, 163, 74, 0.2)' }}>
        ● Ready & Indexed
      </span>
    );
  }

  if (status === 'failed') {
    return (
      <span className="meta-pill" style={{ background: 'var(--status-failed-bg)', color: 'var(--status-failed)', borderColor: 'rgba(220, 38, 38, 0.2)' }} title={errorMessage}>
        ⚠️ Ingestion Failed
      </span>
    );
  }

  return (
    <div className="pipeline-container">
      {stages.map((stg, idx) => {
        const isCompleted = idx < currentIndex;
        const isActive = idx === currentIndex;

        return (
          <React.Fragment key={stg.key}>
            <span className={`pipeline-step ${isActive ? 'active' : isCompleted ? 'completed' : ''}`}>
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
