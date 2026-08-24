'use client';

import React from 'react';
import { ChatMessage as ChatMessageType, Citation } from '../lib/types';

interface ChatMessageProps {
  message: ChatMessageType;
  onCitationClick: (citation: Citation) => void;
}

export default function ChatMessage({ message, onCitationClick }: ChatMessageProps) {
  const isUser = message.sender === 'user';
  const isStreaming = message.streaming && !message.text;

  // Sanitize internal metadata labels like [Sheet 'Data' (Rows 1-39) Table]
  const cleanRawText = (text: string) => {
    if (!text) return '';
    let cleaned = text.replace(/\[(Sheet|Page|Slide|Section|Row|Rows)[^\]]*Table\]/gi, '').trim();
    cleaned = cleaned.replace(/\[(Sheet|Section)[^\]]*\]\n?/gi, '').trim();
    return cleaned;
  };

  const textToRender = cleanRawText(message.text);

  // Helper to render Markdown table blocks as HTML JSX tables
  const renderFormattedContent = (content: string) => {
    if (!content) return null;

    const tablePattern = /(\|[^\n]+\|\n\|[-:\s|]+\|\n(?:\|[^\n]+\|\n?)+)/g;
    const parts = content.split(tablePattern);

    return parts.map((part, pIdx) => {
      if (part.trim().startsWith('|') && part.includes('\n|')) {
        const lines = part.trim().split('\n').filter((l) => l.trim().startsWith('|'));
        if (lines.length >= 2) {
          const headers = lines[0].split('|').slice(1, -1).map((h) => h.trim());
          const rows = lines.slice(2).map((r) => r.split('|').slice(1, -1).map((c) => c.trim()));

          return (
            <div key={pIdx} className="table-responsive-wrapper" style={{ overflowX: 'auto', margin: '12px 0', borderRadius: '8px', border: '1px solid var(--border)' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.86rem', textAlign: 'left' }}>
                <thead>
                  <tr style={{ background: 'var(--paper-soft, rgba(255, 255, 255, 0.05))', borderBottom: '2px solid var(--border)' }}>
                    {headers.map((h, hIdx) => (
                      <th key={hIdx} style={{ padding: '8px 12px', fontWeight: 600, color: 'var(--slate)' }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, rIdx) => (
                    <tr key={rIdx} style={{ borderBottom: rIdx === rows.length - 1 ? 'none' : '1px solid var(--border)' }}>
                      {row.map((cell, cIdx) => (
                        <td key={cIdx} style={{ padding: '8px 12px' }}>
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }
      }

      return (
        <div key={pIdx} style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
          {part}
        </div>
      );
    });
  };

  return (
    <div className={`chat-bubble ${isUser ? 'user' : 'assistant'}`}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', fontSize: '0.78rem', color: isUser ? 'rgba(255, 255, 255, 0.8)' : 'var(--muted)', fontWeight: 600 }}>
        <span>{isUser ? '👤 You' : '⚡ EDA Assistant'}</span>
      </div>

      <div>
        {renderFormattedContent(textToRender)}
        {isStreaming && (
          <span className="streaming-dot" title="Generating token stream..." />
        )}
      </div>
    </div>
  );
}
