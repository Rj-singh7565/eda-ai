'use client';

import React from 'react';
import { Settings, Cpu, HardDrive, ShieldCheck, Key, Sliders, CheckCircle2 } from 'lucide-react';
import { SystemHealth } from '../../lib/types';

interface SettingsViewProps {
  health: SystemHealth | null;
}

export default function SettingsView({ health }: SettingsViewProps) {
  return (
    <div className="settings-view-container">
      <div className="dashboard-panel">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">System & Pipeline Configuration</h2>
            <span className="panel-subtitle">EDA Assistant engine parameters and active model settings</span>
          </div>
        </div>

        <div className="settings-cards-grid">
          {/* Section 1: Embedding Model */}
          <div className="settings-item-card">
            <div className="settings-card-header">
              <div className="settings-icon-circle blue">
                <Cpu size={18} />
              </div>
              <div>
                <div className="settings-card-title">Embedding Model</div>
                <div className="settings-card-desc">Local dense vector transformation</div>
              </div>
            </div>
            <div className="settings-field-row">
              <label>Model Identifier</label>
              <input type="text" readOnly value={health?.embedding_model || 'BAAI/bge-small-en-v1.5'} />
            </div>
            <div className="settings-field-row">
              <label>Embedding Dimension</label>
              <input type="text" readOnly value="384 dimensions" />
            </div>
          </div>

          {/* Section 2: LLM Inference */}
          <div className="settings-item-card">
            <div className="settings-card-header">
              <div className="settings-icon-circle orange">
                <Sliders size={18} />
              </div>
              <div>
                <div className="settings-card-title">Inference Engine (LLM)</div>
                <div className="settings-card-desc">High-speed streaming generative engine</div>
              </div>
            </div>
            <div className="settings-field-row">
              <label>Active LLM Model</label>
              <input type="text" readOnly value={health?.llm_model || 'openai/gpt-oss-120b'} />
            </div>
            <div className="settings-field-row">
              <label>Memory Turns</label>
              <input type="text" readOnly value="4 turns per session" />
            </div>
          </div>

          {/* Section 3: Vector & Relational Storage */}
          <div className="settings-item-card">
            <div className="settings-card-header">
              <div className="settings-icon-circle purple">
                <HardDrive size={18} />
              </div>
              <div>
                <div className="settings-card-title">Vector Database & Persistence</div>
                <div className="settings-card-desc">Isolated namespace retrieval</div>
              </div>
            </div>
            <div className="settings-field-row">
              <label>Pinecone Index</label>
              <input type="text" readOnly value={health?.pinecone_index || 'eda-assistant'} />
            </div>
            <div className="settings-field-row">
              <label>Database Type</label>
              <input type="text" readOnly value={health?.database ? health.database.toUpperCase() : 'SQLITE'} />
            </div>
          </div>

          {/* Section 4: Chunking & Retrieval */}
          <div className="settings-item-card">
            <div className="settings-card-header">
              <div className="settings-icon-circle teal">
                <ShieldCheck size={18} />
              </div>
              <div>
                <div className="settings-card-title">RAG Retrieval Hyperparameters</div>
                <div className="settings-card-desc">Chunk size and similarity thresholds</div>
              </div>
            </div>
            <div className="settings-field-row">
              <label>Chunk Size / Overlap</label>
              <input type="text" readOnly value="600 characters / 100 overlap" />
            </div>
            <div className="settings-field-row">
              <label>Top-K / Similarity Threshold</label>
              <input type="text" readOnly value="Top 5 chunks / 0.35 threshold" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
