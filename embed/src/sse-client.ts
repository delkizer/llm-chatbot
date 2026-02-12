/**
 * SPO Chatbot - SSE Streaming Client
 *
 * fetch + ReadableStream 기반 SSE 파서
 */

import type { ChartData, SSEHandlers } from './types';

export class SSEClient {
  private abortController: AbortController | null = null;

  async stream(
    url: string,
    body: object,
    token: string,
    handlers: SSEHandlers
  ): Promise<void> {
    this.abort();
    this.abortController = new AbortController();

    const maxRetries = 3;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        // abort된 상태면 재시도하지 않음
        if (this.abortController.signal.aborted) {
          return;
        }

        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify(body),
          signal: this.abortController.signal,
        });

        if (!response.ok) {
          const detail = await response.text().catch(() => '');
          handlers.onError(`HTTP ${response.status}: ${detail}`);
          return;
        }

        if (!response.body) {
          handlers.onError('No response body');
          return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          let currentEvent = 'message';
          for (const line of lines) {
            if (line.startsWith('event: ')) {
              currentEvent = line.slice(7).trim();
            } else if (line.startsWith('data: ')) {
              const data = line.slice(6);
              this.handleEvent(currentEvent, data, handlers);
              currentEvent = 'message';
            }
          }
        }

        // 스트림 정상 완료 시 종료
        return;
      } catch (err: unknown) {
        // AbortError는 재시도하지 않음
        if (err instanceof DOMException && err.name === 'AbortError') {
          return;
        }

        // 마지막 시도였으면 에러 전파
        if (attempt === maxRetries) {
          handlers.onError('네트워크 연결을 확인해주세요.');
          return;
        }

        // 지수 백오프 대기 (1s, 2s, 4s)
        const delay = Math.pow(2, attempt) * 1000;
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }

    this.abortController = null;
  }

  abort(): void {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }

  private handleEvent(event: string, data: string, handlers: SSEHandlers): void {
    switch (event) {
      case 'message':
        handlers.onMessage(data);
        break;
      case 'chart':
        try {
          const chart: ChartData = JSON.parse(data);
          handlers.onChart(chart);
        } catch {
          // JSON 파싱 실패 시 무시
        }
        break;
      case 'done':
        handlers.onDone();
        break;
      case 'error':
        handlers.onError(data);
        break;
    }
  }
}
