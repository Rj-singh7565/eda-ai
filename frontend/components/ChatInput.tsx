'use client';

import React, { useState } from 'react';

interface ChatInputProps {
  disabled: boolean;
  onSend: (question: string) => void;
}

export default function ChatInput({ disabled, onSend }: ChatInputProps) {
  const [text, setText] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || disabled) return;
    onSend(text.trim());
    setText('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="chat-input-container">
      <form onSubmit={handleSubmit} className="chat-form">
        <textarea
          className="question-input"
          placeholder={disabled ? 'Select or upload a ready document to start asking questions...' : 'Ask an analytical question about the active document...'}
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
        />
        <button type="submit" className="btn-primary" disabled={disabled || !text.trim()}>
          Send
        </button>
      </form>
      <div style={{ marginTop: '6px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
        Ask custom questions • Press <kbd>Enter ↵</kbd> to send • <kbd>Shift + Enter</kbd> for newline
      </div>
    </div>
  );
}
