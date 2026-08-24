'use client';

import React, { useState } from 'react';

interface ChatInputProps {
  disabled?: boolean;
  onSend: (text: string) => void;
}

export default function ChatInput({ disabled, onSend }: ChatInputProps) {
  const [input, setInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || disabled) return;
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
      <form onSubmit={handleSubmit} className="composer-input-wrapper">
        <textarea
          className="composer-textarea"
          placeholder="Ask a question about your documents..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={2}
        />
        <div className="composer-toolbar">
          <span style={{ fontSize: '1rem', color: 'var(--muted)', cursor: 'pointer' }} title="Attach file">
            📎
          </span>
          <button
            type="submit"
            disabled={!input.trim() || disabled}
            className="send-action-btn"
            title="Send Message"
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
