export interface Document {
  doc_id: string;
  filename: string;
  file_size: number;
  file_type: string;
  page_count?: number;
  chunk_count?: number;
  status: 'processing' | 'parsing' | 'normalizing' | 'chunking' | 'embedding' | 'indexing' | 'ready' | 'failed';
  error_message?: string;
  markdown_path?: string;
  created_at?: string;
}

export interface Citation {
  pages: string[];
  score: number;
  text_snippet: string;
  full_text: string;
  is_table?: boolean;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  citations?: Citation[];
  timestamp?: string;
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
