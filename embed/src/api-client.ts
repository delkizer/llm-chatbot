/**
 * SPO Chatbot - REST API Client
 */

import type { ChatRequest, ChatResponse, CreateSessionRequest, SessionInfo } from './types';

export class ApiClient {
  private baseUrl: string;
  private token: string;

  constructor(baseUrl: string, token: string) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.token = token;
  }

  setToken(token: string): void {
    this.token = token;
  }

  async createSession(request: CreateSessionRequest): Promise<SessionInfo> {
    const res = await this.request<SessionInfo>('/api/chat/session', {
      method: 'POST',
      body: JSON.stringify(request),
    });
    return res;
  }

  async chat(request: ChatRequest): Promise<ChatResponse> {
    const res = await this.request<ChatResponse>('/api/chat/', {
      method: 'POST',
      body: JSON.stringify(request),
    });
    return res;
  }

  async getSessionInfo(contextType: string): Promise<SessionInfo | null> {
    try {
      return await this.request<SessionInfo>(
        `/api/chat/session?context_type=${encodeURIComponent(contextType)}`
      );
    } catch {
      return null;
    }
  }

  async deleteSession(contextType: string): Promise<void> {
    await this.request(`/api/chat/session?context_type=${encodeURIComponent(contextType)}`, {
      method: 'DELETE',
    });
  }

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(url, {
      ...init,
      headers: { ...headers, ...init?.headers },
    });

    if (!response.ok) {
      const detail = await response.text().catch(() => '');
      throw new ApiError(response.status, detail);
    }

    return response.json();
  }
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, detail: string) {
    super(`API Error ${status}: ${detail}`);
    this.status = status;
  }
}
