'use client';

import React, { useState } from 'react';
import { Sparkles, Send, Paperclip } from 'lucide-react';

interface CommandBarProps {
  activeDocName: string;
  onSend: (promptText: string) => void;
  onExportPDF?: () => void;
  disabled?: boolean;
}

export default function CommandBar({
  activeDocName,
  onSend,
  onExportPDF,
  disabled = false
}: CommandBarProps) {
  const [inputText, setInputText] = useState('');

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputText.trim() || disabled) return;
    onSend(inputText.trim());
    setInputText('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div
      className="analysis-command-bar-wrapper"
      style={{
        backgroundColor: '#ffffff',
        borderTop: '1px solid #e2e8f0',
        padding: '16px 28px',
        width: '100%',
        zIndex: 20,
        boxShadow: '0 -2px 10px rgba(0, 0, 0, 0.02)'
      }}
    >
      {/* ── Command Input Box ──────────────────────────────────────── */}
      <form
        onSubmit={handleSubmit}
        className="command-input-form-card"
        style={{
          display: 'flex',
          alignItems: 'center',
          backgroundColor: '#f8fafc',
          border: '1px solid #e2e8f0',
          borderRadius: '12px',
          padding: '6px 8px 6px 16px',
          gap: '12px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.04)',
          transition: 'border-color 0.15s ease, box-shadow 0.15s ease'
        }}
      >
        {/* Left Sparkles Icon */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#2563eb' }}>
          <Sparkles size={18} />
        </div>

        {/* Text Input */}
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask any analytical question..."
          disabled={disabled}
          className="command-prompt-input"
          style={{
            flex: 1,
            backgroundColor: 'transparent',
            border: 'none',
            outline: 'none',
            fontSize: '0.88rem',
            color: '#0f172a',
            fontFamily: 'var(--font-body, sans-serif)',
            padding: '6px 0'
          }}
        />

        {/* Attachment Paperclip Icon Button */}
        <button
          type="button"
          title="Attach document or dataset"
          style={{
            background: 'transparent',
            border: 'none',
            color: '#94a3b8',
            cursor: 'pointer',
            padding: '6px',
            borderRadius: '6px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'color 0.15s ease'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.color = '#475569';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.color = '#94a3b8';
          }}
        >
          <Paperclip size={18} />
        </button>

        {/* Run Query Button */}
        <button
          type="submit"
          disabled={!inputText.trim() || disabled}
          className="command-send-btn"
          style={{
            backgroundColor: !inputText.trim() || disabled ? '#94a3b8' : '#2563eb',
            color: '#ffffff',
            border: 'none',
            borderRadius: '8px',
            padding: '8px 18px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '0.84rem',
            fontWeight: 600,
            cursor: !inputText.trim() || disabled ? 'not-allowed' : 'pointer',
            transition: 'all 0.15s ease',
            boxShadow: !inputText.trim() || disabled ? 'none' : '0 2px 6px rgba(37, 99, 235, 0.3)'
          }}
          onMouseEnter={(e) => {
            if (inputText.trim() && !disabled) {
              e.currentTarget.style.backgroundColor = '#1d4ed8';
            }
          }}
          onMouseLeave={(e) => {
            if (inputText.trim() && !disabled) {
              e.currentTarget.style.backgroundColor = '#2563eb';
            }
          }}
        >
          <span>Run Query</span>
          <Send size={14} />
        </button>
      </form>
    </div>
  );
}
