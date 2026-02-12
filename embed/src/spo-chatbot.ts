/**
 * SPO Chatbot - Web Component Entry Point
 *
 * <spo-chatbot> Custom Element 정의
 */

import type { SpoChatbotConfig, Message, ChartData, ChatRequest, CreateSessionRequest } from './types';
import { ApiClient, ApiError } from './api-client';
import { SSEClient } from './sse-client';
import { ChatUI } from './chat-ui';
import baseCSS from './styles/base.css?inline';
import defaultTheme from './themes/default.css?inline';
import bwfTheme from './themes/bwf.css?inline';
import bxlTheme from './themes/bxl.css?inline';

const THEMES: Record<string, string> = {
  default: defaultTheme,
  bwf: bwfTheme,
  bxl: bxlTheme,
};

class SpoChatbot extends HTMLElement {
  static observedAttributes = [
    'api-url', 'token', 'theme', 'context-type', 'lang',
    'match-id', 'player-id', 'tournament-id',
    'game-id', 'team-id',
    'pitcher-id', 'batter-id',
  ];

  private config: SpoChatbotConfig = {
    apiUrl: '',
    token: '',
    theme: 'default',
    contextType: 'badminton',
    contextParams: {},
    lang: 'ko',
  };

  private api!: ApiClient;
  private sse: SSEClient = new SSEClient();
  private ui!: ChatUI;
  private sessionId: string | null = null;
  private messages: Message[] = [];
  private messageCounter = 0;
  private error: string | null = null;
  private lastFailedMessage: string | null = null;

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  connectedCallback(): void {
    // 속성에서 config 초기화
    this.config.apiUrl = this.getAttribute('api-url') || '';
    this.config.token = this.getAttribute('token') || '';
    this.config.theme = this.getAttribute('theme') || 'default';
    this.config.contextType = this.getAttribute('context-type') || 'badminton';
    this.config.lang = this.getAttribute('lang') || 'ko';
    this.config.contextParams = this.collectContextParams();

    if (!this.config.apiUrl) {
      console.error('[spo-chatbot] api-url attribute is required');
      return;
    }

    this.api = new ApiClient(this.config.apiUrl, this.config.token);

    // Shadow DOM 렌더링
    this.renderShadow();

    // 세션 생성
    this.initSession();
  }

  disconnectedCallback(): void {
    this.sse.abort();
    this.ui?.destroy();
  }

  attributeChangedCallback(name: string, oldValue: string | null, newValue: string | null): void {
    if (oldValue === newValue) return;

    switch (name) {
      case 'api-url':
        this.config.apiUrl = newValue || '';
        if (this.api) {
          this.api = new ApiClient(this.config.apiUrl, this.config.token);
        }
        break;
      case 'token':
        this.config.token = newValue || '';
        this.api?.setToken(this.config.token);
        // SSEClient는 stream() 호출 시 토큰을 매번 전달받으므로 별도 setToken 불필요
        // 이전에 401 에러였다면 에러 상태 초기화 + 입력 활성화
        if (newValue && this.error?.includes('인증')) {
          this.error = null;
          this.ui?.setInputDisabled(false);
        }
        break;
      case 'theme':
        this.config.theme = newValue || 'default';
        this.applyTheme(this.config.theme);
        break;
      case 'context-type':
        this.config.contextType = newValue || 'badminton';
        break;
      case 'lang':
        this.config.lang = newValue || 'ko';
        break;
      default:
        // Context 속성 변경
        this.config.contextParams = this.collectContextParams();
        break;
    }
  }

  // ─────────────────────────────────────────────
  // Init
  // ─────────────────────────────────────────────

  private renderShadow(): void {
    const shadow = this.shadowRoot!;

    // Base CSS
    const baseStyle = document.createElement('style');
    baseStyle.textContent = baseCSS;
    shadow.appendChild(baseStyle);

    // Theme CSS
    const themeStyle = document.createElement('style');
    themeStyle.classList.add('theme-style');
    themeStyle.textContent = THEMES[this.config.theme] || THEMES['default'];
    shadow.appendChild(themeStyle);

    // UI
    this.ui = new ChatUI(shadow, {
      onSend: (message) => this.handleSend(message),
      onReset: () => this.handleReset(),
    });
    this.ui.render();
  }

  private async initSession(): Promise<void> {
    try {
      const request: CreateSessionRequest = {
        context_type: this.config.contextType,
        context: this.config.contextParams,
      };
      const session = await this.api.createSession(request);
      this.sessionId = session.session_id;
    } catch (err) {
      this.handleApiError(err);
    }
  }

  private applyTheme(theme: string): void {
    const shadow = this.shadowRoot!;
    const old = shadow.querySelector('.theme-style');
    if (old) {
      (old as HTMLStyleElement).textContent = THEMES[theme] || THEMES['default'];
    }
  }

  private collectContextParams(): Record<string, string> {
    const params: Record<string, string> = {};
    const contextAttrs = [
      'match-id', 'player-id', 'tournament-id',
      'game-id', 'team-id',
      'pitcher-id', 'batter-id',
    ];

    for (const attr of contextAttrs) {
      const value = this.getAttribute(attr);
      if (value) {
        // kebab-case → snake_case
        const key = attr.replace(/-/g, '_');
        params[key] = value;
      }
    }

    return params;
  }

  // ─────────────────────────────────────────────
  // Handlers
  // ─────────────────────────────────────────────

  private buildChatRequest(message: string): ChatRequest {
    const request: ChatRequest = {
      message,
      context_type: this.config.contextType,
    };

    // contextParams가 비어있으면 context 키를 포함하지 않음
    if (Object.keys(this.config.contextParams).length > 0) {
      request.context = this.config.contextParams;
    }

    return request;
  }

  private async handleSend(text: string): Promise<void> {
    // 에러 상태 초기화
    this.error = null;
    this.lastFailedMessage = null;

    // 사용자 메시지 추가
    const userMsg: Message = {
      id: `msg-${++this.messageCounter}`,
      role: 'user',
      content: text,
      timestamp: Date.now(),
    };
    this.messages.push(userMsg);
    this.ui.addMessage(userMsg);

    // 스트리밍 시작
    this.ui.startStreaming();

    const request = this.buildChatRequest(text);

    const url = `${this.config.apiUrl.replace(/\/$/, '')}/api/chat/stream`;

    await this.sse.stream(url, request, this.config.token, {
      onMessage: (chunk) => {
        this.ui.appendToLastAssistant(chunk);
      },
      onChart: (chart: ChartData) => {
        this.ui.addChartToLastAssistant(chart);
      },
      onDone: () => {
        this.ui.endStreaming();
        this.lastFailedMessage = null;

        // assistant 메시지 기록 — data-raw 속성이 있는 assistant 메시지만 선택 (loadingEl 제외)
        const all = this.shadowRoot!.querySelectorAll('.spo-message--assistant[data-raw]');
        const lastEl = all.length > 0 ? all[all.length - 1] : null;
        const raw = lastEl?.getAttribute('data-raw') || '';
        const assistantMsg: Message = {
          id: `msg-${++this.messageCounter}`,
          role: 'assistant',
          content: raw,
          timestamp: Date.now(),
        };
        this.messages.push(assistantMsg);
      },
      onError: (error) => {
        this.ui.endStreaming();
        this.lastFailedMessage = text;
        this.handleStreamError(error);
      },
    });
  }

  private handleRetry(): void {
    if (this.lastFailedMessage) {
      this.error = null;
      const message = this.lastFailedMessage;
      this.lastFailedMessage = null;
      this.handleSend(message);
    }
  }

  private async handleReset(): Promise<void> {
    try {
      await this.api.deleteSession(this.config.contextType);
    } catch {
      // 세션 삭제 실패해도 UI는 초기화
    }

    this.messages = [];
    this.sessionId = null;
    this.ui.clearMessages();

    // 새 세션 생성
    await this.initSession();
  }

  // ─────────────────────────────────────────────
  // Error Handling
  // ─────────────────────────────────────────────

  private handleApiError(err: unknown): void {
    if (err instanceof ApiError) {
      switch (err.status) {
        case 401:
          this.error = '인증이 만료되었습니다. 다시 로그인해주세요.';
          this.ui.showError(this.error);
          this.ui.setInputDisabled(true);
          break;
        case 403:
          this.error = '접근 권한이 부족합니다.';
          this.ui.showError(this.error);
          this.ui.setInputDisabled(true);
          break;
        case 410:
          // 세션 만료 — 자동 재생성
          this.initSession();
          break;
        default:
          this.error = '서버 오류입니다. 잠시 후 다시 시도해주세요.';
          this.ui.showError(this.error, () => this.handleRetry());
      }
    } else {
      this.error = '네트워크 연결을 확인해주세요.';
      this.ui.showError(this.error, () => this.handleRetry());
    }
  }

  private handleStreamError(error: string): void {
    if (error.includes('401')) {
      this.error = '인증이 만료되었습니다. 다시 로그인해주세요.';
      this.ui.showError(this.error);
      this.ui.setInputDisabled(true);
    } else if (error.includes('410')) {
      this.error = '세션이 만료되었습니다. 초기화 버튼을 눌러주세요.';
      this.ui.showError(this.error);
    } else {
      this.error = '응답 중 오류가 발생했습니다.';
      this.ui.showError(this.error, () => this.handleRetry());
    }
  }
}

// Custom Element 등록
customElements.define('spo-chatbot', SpoChatbot);
