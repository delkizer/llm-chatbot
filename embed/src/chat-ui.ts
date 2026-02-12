/**
 * SPO Chatbot - Chat UI Components
 *
 * Shadow DOM 내부 UI 렌더링을 담당합니다.
 * - ChatHeader: 헤더 (테마명 + 초기화 버튼)
 * - MessageList: 메시지 목록 (스크롤, 스트리밍 append)
 * - InputArea: 입력 영역 (textarea + 전송 버튼)
 */

import type { Message, ChartData } from './types';
import { MarkdownRenderer } from './markdown-renderer';
import { ChartRenderer } from './chart-renderer';

export interface ChatUICallbacks {
  onSend: (message: string) => void;
  onReset: () => void;
}

export class ChatUI {
  private root: ShadowRoot;
  private callbacks: ChatUICallbacks;
  private markdown: MarkdownRenderer;
  private chartRenderer: ChartRenderer;

  private messagesEl!: HTMLElement;
  private textarea!: HTMLTextAreaElement;
  private sendBtn!: HTMLButtonElement;
  private loadingEl!: HTMLElement;

  constructor(root: ShadowRoot, callbacks: ChatUICallbacks) {
    this.root = root;
    this.callbacks = callbacks;
    this.markdown = new MarkdownRenderer();
    this.chartRenderer = new ChartRenderer();
  }

  render(): void {
    const container = document.createElement('div');
    container.className = 'spo-chatbot';

    // Header
    container.appendChild(this.createHeader());

    // Messages
    this.messagesEl = document.createElement('div');
    this.messagesEl.className = 'spo-messages';

    // Empty state
    const empty = document.createElement('div');
    empty.className = 'spo-empty';
    empty.textContent = '무엇이든 물어보세요';
    this.messagesEl.appendChild(empty);

    container.appendChild(this.messagesEl);

    // Loading indicator
    this.loadingEl = document.createElement('div');
    this.loadingEl.className = 'spo-message spo-message--assistant';
    this.loadingEl.style.display = 'none';
    this.loadingEl.innerHTML = `
      <div class="spo-loading">
        <div class="spo-loading-dot"></div>
        <div class="spo-loading-dot"></div>
        <div class="spo-loading-dot"></div>
      </div>
    `;

    // Input
    container.appendChild(this.createInputArea());

    this.root.appendChild(container);
  }

  addMessage(message: Message): void {
    this.removeEmpty();

    const el = document.createElement('div');
    el.className = `spo-message spo-message--${message.role}`;
    el.dataset.messageId = message.id;

    if (message.role === 'user') {
      el.textContent = message.content;
    } else {
      el.innerHTML = this.markdown.render(message.content);

      if (message.charts) {
        for (const chart of message.charts) {
          this.chartRenderer.render(el, chart);
        }
      }
    }

    this.messagesEl.appendChild(el);
    this.scrollToBottom();
  }

  appendToLastAssistant(chunk: string): void {
    const all = this.messagesEl.querySelectorAll('.spo-message--assistant[data-raw]');
    const last = all.length > 0 ? all[all.length - 1] : null;
    if (last) {
      const current = last.getAttribute('data-raw') || '';
      const updated = current + chunk;
      last.setAttribute('data-raw', updated);
      last.innerHTML = this.markdown.render(updated);
      this.scrollToBottom();
    }
  }

  addChartToLastAssistant(chart: ChartData): void {
    const all = this.messagesEl.querySelectorAll('.spo-message--assistant[data-raw]');
    const last = all.length > 0 ? all[all.length - 1] as HTMLElement : null;
    if (last) {
      this.chartRenderer.render(last, chart);
      this.scrollToBottom();
    }
  }

  startStreaming(): void {
    this.removeEmpty();

    // 빈 assistant 메시지 생성
    const el = document.createElement('div');
    el.className = 'spo-message spo-message--assistant';
    el.setAttribute('data-raw', '');
    this.messagesEl.appendChild(el);

    // 로딩 표시
    this.messagesEl.appendChild(this.loadingEl);
    this.loadingEl.style.display = '';

    this.setInputDisabled(true);
    this.scrollToBottom();
  }

  endStreaming(): void {
    this.loadingEl.style.display = 'none';
    this.setInputDisabled(false);
    this.textarea.focus();
  }

  showError(message: string, retryCallback?: () => void): void {
    const el = document.createElement('div');
    el.className = 'spo-error';
    el.textContent = message;

    // 재시도 버튼 (retryCallback이 있는 경우만 표시 — 401/403은 전달하지 않음)
    if (retryCallback) {
      const retryBtn = document.createElement('button');
      retryBtn.className = 'spo-retry-btn';
      retryBtn.textContent = '다시 시도';
      this.applyRetryBtnStyle(retryBtn);
      retryBtn.addEventListener('click', () => {
        el.remove();
        retryCallback();
      });
      el.appendChild(retryBtn);
    }

    this.messagesEl.appendChild(el);
    this.scrollToBottom();
  }

  clearMessages(): void {
    this.messagesEl.innerHTML = '';
    this.chartRenderer.destroyAll();

    const empty = document.createElement('div');
    empty.className = 'spo-empty';
    empty.textContent = '무엇이든 물어보세요';
    this.messagesEl.appendChild(empty);
  }

  setInputDisabled(disabled: boolean): void {
    this.textarea.disabled = disabled;
    this.sendBtn.disabled = disabled;
  }

  scrollToBottom(): void {
    requestAnimationFrame(() => {
      this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
    });
  }

  destroy(): void {
    this.chartRenderer.destroyAll();
  }

  // ─────────────────────────────────────────────
  // Private
  // ─────────────────────────────────────────────

  private createHeader(): HTMLElement {
    const header = document.createElement('div');
    header.className = 'spo-header';

    const title = document.createElement('span');
    title.className = 'spo-header-title';
    title.textContent = 'SPO Chatbot';
    header.appendChild(title);

    const resetBtn = document.createElement('button');
    resetBtn.className = 'spo-header-btn';
    resetBtn.textContent = '초기화';
    resetBtn.addEventListener('click', () => {
      if (confirm('대화를 초기화하시겠습니까?')) {
        this.callbacks.onReset();
      }
    });
    header.appendChild(resetBtn);

    return header;
  }

  private createInputArea(): HTMLElement {
    const area = document.createElement('div');
    area.className = 'spo-input-area';

    this.textarea = document.createElement('textarea');
    this.textarea.placeholder = '메시지를 입력하세요...';
    this.textarea.rows = 1;
    this.textarea.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.handleSend();
      }
    });
    this.textarea.addEventListener('input', () => {
      // 자동 높이 조정
      this.textarea.style.height = 'auto';
      this.textarea.style.height = Math.min(this.textarea.scrollHeight, 120) + 'px';
    });
    area.appendChild(this.textarea);

    this.sendBtn = document.createElement('button');
    this.sendBtn.className = 'spo-send-btn';
    this.sendBtn.textContent = '전송';
    this.sendBtn.addEventListener('click', () => this.handleSend());
    area.appendChild(this.sendBtn);

    return area;
  }

  private handleSend(): void {
    const text = this.textarea.value.trim();
    if (!text) return;

    this.textarea.value = '';
    this.textarea.style.height = 'auto';
    this.callbacks.onSend(text);
  }

  private applyRetryBtnStyle(btn: HTMLButtonElement): void {
    btn.style.display = 'block';
    btn.style.marginTop = '8px';
    btn.style.marginLeft = 'auto';
    btn.style.padding = '6px 16px';
    btn.style.border = '1px solid var(--spo-border, #e5e7eb)';
    btn.style.borderRadius = '4px';
    btn.style.background = 'var(--spo-bg, #ffffff)';
    btn.style.color = 'var(--spo-text, #1f2937)';
    btn.style.cursor = 'pointer';
    btn.style.fontSize = 'var(--spo-font-size, 14px)';

    btn.addEventListener('mouseenter', () => {
      btn.style.background = 'var(--spo-border, #e5e7eb)';
    });
    btn.addEventListener('mouseleave', () => {
      btn.style.background = 'var(--spo-bg, #ffffff)';
    });
  }

  private removeEmpty(): void {
    const empty = this.messagesEl.querySelector('.spo-empty');
    if (empty) empty.remove();
  }
}
