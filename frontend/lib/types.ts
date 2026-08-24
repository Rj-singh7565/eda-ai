export type DocumentStatus =
  | 'processing'
  | 'parsing'
  | 'normalizing'
  | 'chunking'
  | 'embedding'
  | 'indexing'
  | 'ready'
  | 'failed';

export interface Document {
  doc_id: string;
  filename: string;
  file_size: number;
  file_type: string;
  page_count?: number;
  chunk_count?: number;
  status: DocumentStatus;
  error_message?: string;
  markdown_path?: string;
  created_at?: string;
  updated_at?: string;
}

export type CitationCategory = 'text' | 'table' | 'figure';

export interface Citation {
  id: string;
  doc_id?: string;
  document_name: string;
  category: CitationCategory;
  location: string; // e.g. "Page 12", "Table 3.1", "Figure 3.1", "Slide 14"
  title?: string;
  snippet: string;
  match_type: 'Exact match' | 'Text match';
  score: number; // 0.0 - 1.0
  pages?: string[];
  table_data?: { headers: string[]; rows: string[][] };
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  citations?: Citation[];
  streaming?: boolean;
}

export interface SkippedFile {
  filename: string;
  reason: string;
}

export interface UploadResponse {
  batch: boolean;
  doc_id?: string;
  filename?: string;
  file_type?: string;
  status: string;
  documents: Document[];
  skipped: SkippedFile[];
  message: string;
}

export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'offline';
  version: string;
  embedding_model: string;
  llm_model: string;
  pinecone_index: string;
  database: string;
  storage: string;
}

export type WorkspaceViewMode = 'chat' | 'reader' | 'split';
