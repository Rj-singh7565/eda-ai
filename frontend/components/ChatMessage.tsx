'use client';

import React from 'react';
import { ChatMessage as ChatMessageType, Citation } from '../lib/types';

interface ChatMessageProps {
  message: ChatMessageType;
  onCitationClick: (citation: Citation) => void;
}

export default function ChatMessage({ message, onCitationClick }: ChatMessageProps) {
  const isUser = message.sender === 'user';

  return (
    <div className={`chat-bubble ${isUser ? 'user' : 'assistant'}`}>
      <div style={{ whiteSpace: 'pre-wrap' }}>{message.text}</div>

      {!isUser && message.citations && message.citations.length > 0 && (
        <div style={{ marginTop: '10px', paddingTop: '8px', borderTop: '1px solid var(--border-color)' }}>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
            Sources:
          </span>
          <div>
            {message.citations.map((cit, idx) => (
              <button
                key={idx}
                className="citation-chip"
                onClick={() => onCitationClick(cit)}
                title={`Similarity Score: ${(cit.score * 100).toFixed(1)}%`}
              >
                📍 [{cit.pages.join(', ')}]
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
