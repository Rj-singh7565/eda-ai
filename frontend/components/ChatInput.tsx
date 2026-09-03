'use client';

import React, { useState } from 'react';

interface ChatInputProps {
  disabled?: boolean;
  isDocReady?: boolean;
  docStatus?: string;
  onSend: (text: string) => void;
}

export default function ChatInput({ disabled, isDocReady = true, docStatus, onSend }: ChatInputProps) {
  const [input, setInput] = useState('');

  const isDisabled = disabled || !isDocReady;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isDisabled) return;
    onSend(input.trim());
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="chat-composer-box">
      {!isDocReady && (
        <div
          style={{
            background: 'rgba(99, 102, 241, 0.1)',
            border: '1px solid rgba(99, 102, 241, 0.3)',
            borderRadius: 'var(--radius-xs, 8px)',
            padding: '8px 12px',
            marginBottom: '8px',
            fontSize: '0.78rem',
            color: '#6366f1',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontWeight: 600
          }}
        >
          <span style={{ fontSize: '0.9rem' }}>🔒</span>
          <span>
            Document status is <strong>&quot;{docStatus || 'processing'}&quot;</strong>. Q&amp;A submission is locked until vector embedding and indexing complete.
          </span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="composer-input-wrapper">
        <textarea
          className="composer-textarea"
          placeholder={
            !isDocReady
              ? "⏳ Q&A locked — waiting for document embedding & vector DB storage to complete..."
              : "Ask a question about your documents..."
          }
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isDisabled}
          rows={2}
          style={{ opacity: isDisabled ? 0.6 : 1, cursor: isDisabled ? 'not-allowed' : 'text' }}
        />
        <div className="composer-toolbar">
          <span style={{ fontSize: '1rem', color: 'var(--muted)', cursor: 'pointer' }} title="Attach file">
            📎
          </span>
          <button
            type="submit"
            disabled={!input.trim() || isDisabled}
            className="send-action-btn"
            title={!isDocReady ? "Q&A locked until embedding completes" : "Send Message"}
            style={{ opacity: (!input.trim() || isDisabled) ? 0.5 : 1, cursor: isDisabled ? 'not-allowed' : 'pointer' }}
          >
            &rarr;
          </button>
        </div>
      </form>

      <div style={{ fontSize: '0.7rem', color: 'var(--muted)', textAlign: 'center', marginTop: '8px' }}>
        AI responses can make mistakes. Verify important information.
      </div>
    </div>
  );
}
