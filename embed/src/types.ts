/**
 * SPO Chatbot Embed - Type Definitions
 */

// ─────────────────────────────────────────────
// Chat Types
// ─────────────────────────────────────────────

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  charts?: ChartData[];
  timestamp: number;
}

export interface ChartData {
  type: 'bar' | 'line' | 'pie';
  title: string;
  data: {
    labels: string[];
    datasets: ChartDataset[];
  };
}

export interface ChartDataset {
  label: string;
  data: number[];
}

// ─────────────────────────────────────────────
// API Types
// ─────────────────────────────────────────────

export interface ChatRequest {
  message: string;
  context_type: string;
  skill_name?: string;
  context?: Record<string, string>;
  temperature?: number;
  max_tokens?: number;
}

export interface ChatResponse {
  text: string;
  charts?: ChartData[];
  session_id: string;
  model: string;
  response_time_ms: number;
  tokens: {
    prompt: number;
    completion: number;
    total: number;
  };
  skill_name: string;
  message_count: number;
}

export interface CreateSessionRequest {
  context_type: string;
  skill_name?: string;
  context?: Record<string, string>;
}

export interface SessionInfo {
  session_id: string;
  user_id: string;
  context_type: string;
  skill_name: string;
  message_count: number;
  context: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

// ─────────────────────────────────────────────
// SSE Types
// ─────────────────────────────────────────────

export interface SSEHandlers {
  onMessage: (chunk: string) => void;
  onChart: (chart: ChartData) => void;
  onDone: () => void;
  onError: (error: string) => void;
}

// ─────────────────────────────────────────────
// Config Types
// ─────────────────────────────────────────────

export interface SpoChatbotConfig {
  apiUrl: string;
  token: string;
  theme: string;
  contextType: string;
  contextParams: Record<string, string>;
  lang: string;
}
