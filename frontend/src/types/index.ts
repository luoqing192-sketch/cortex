export interface User {
  id: number;
  username: string;
  role: 'admin' | 'user';
}

export interface LoginResponse {
  token: string;
  user: User;
}

export interface Conversation {
  id: number;
  user_id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: number;
  conversation_id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
}

export interface LLMSettings {
  llm_base_url: string;
  llm_api_key: string;
  llm_model: string;
  llm_temperature: string;
  llm_max_tokens: string;
  llm_top_p: string;
  knowledge_retrieval_limit: string;
  knowledge_min_score: string;
  intent_prompt: string;
}

export interface Prompt {
  id: number;
  name: string;
  content: string;
  description: string;
  is_active: boolean;
  created_at: string;
}

export interface WikiFile {
  name: string;
  filename: string;
  size: number;
  updated_at: string;
}

export interface DocItem {
  id: number;
  filename: string;
  original_name: string;
  file_size: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  error_message?: string;
  uploaded_at: string;
  knowledge_base_id: number;
}

export interface QueueStatus {
  pending: number;
  active: number;
  maxConcurrent: number;
  estimatedWaitTime: number;
}

export interface Source {
  title: string;
  url: string;
}

export interface ChatStreamEvent {
  content?: string;
  error?: string;
  type?: 'queue' | 'notice' | 'tool_progress' | 'preview' | 'intent' | 'sources';
  message?: string;
  pending?: number;
  active?: number;
  tool?: string;
  status?: string;
  url?: string;
  intent?: string;
  sources?: Source[];
}
