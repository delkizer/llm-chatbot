/**
 * SPO Chatbot - Markdown Renderer
 *
 * 경량 마크다운 → HTML 변환 (XSS 방지)
 */

const ALLOWED_TAGS = new Set([
  'h1', 'h2', 'h3', 'h4', 'p', 'strong', 'em',
  'ul', 'ol', 'li', 'table', 'thead', 'tbody',
  'tr', 'th', 'td', 'pre', 'code', 'br',
]);

export class MarkdownRenderer {
  render(markdown: string): string {
    if (!markdown) return '';
    const html = this.parse(markdown);
    return this.sanitize(html);
  }

  private parse(md: string): string {
    let html = md;

    // Code blocks (```...```) — 먼저 처리하여 내부 마크다운 방지
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_m, _lang, code) => {
      return `<pre><code>${this.escapeHtml(code.trim())}</code></pre>`;
    });

    // Inline code (`...`)
    html = html.replace(/`([^`]+)`/g, (_m, code) => {
      return `<code>${this.escapeHtml(code)}</code>`;
    });

    // Headers
    html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

    // Bold & Italic
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Tables
    html = this.parseTables(html);

    // Lists
    html = this.parseLists(html);

    // Paragraphs (줄바꿈 처리)
    html = html.replace(/\n{2,}/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');

    // 최외곽 p 태그
    if (!html.startsWith('<')) {
      html = `<p>${html}</p>`;
    }

    return html;
  }

  private parseTables(html: string): string {
    const tableRegex = /(?:^\|.+\|$\n?)+/gm;

    return html.replace(tableRegex, (block) => {
      const rows = block.trim().split('\n').filter(r => r.trim());
      if (rows.length < 2) return block;

      // 구분선 행 확인
      const separatorIdx = rows.findIndex(r => /^\|[\s\-:|]+\|$/.test(r));
      if (separatorIdx < 0) return block;

      const headerRows = rows.slice(0, separatorIdx);
      const bodyRows = rows.slice(separatorIdx + 1);

      const parseRow = (row: string, tag: string): string => {
        const cells = row.split('|').slice(1, -1);
        const cellsHtml = cells.map(c => `<${tag}>${c.trim()}</${tag}>`).join('');
        return `<tr>${cellsHtml}</tr>`;
      };

      const thead = headerRows.map(r => parseRow(r, 'th')).join('');
      const tbody = bodyRows.map(r => parseRow(r, 'td')).join('');

      return `<table><thead>${thead}</thead><tbody>${tbody}</tbody></table>`;
    });
  }

  private parseLists(html: string): string {
    // Unordered lists
    html = html.replace(/((?:^- .+$\n?)+)/gm, (block) => {
      const items = block.trim().split('\n')
        .map(line => `<li>${line.replace(/^- /, '')}</li>`)
        .join('');
      return `<ul>${items}</ul>`;
    });

    // Ordered lists
    html = html.replace(/((?:^\d+\. .+$\n?)+)/gm, (block) => {
      const items = block.trim().split('\n')
        .map(line => `<li>${line.replace(/^\d+\. /, '')}</li>`)
        .join('');
      return `<ol>${items}</ol>`;
    });

    return html;
  }

  private sanitize(html: string): string {
    // 1. allowlist에 없는 태그 제거 (태그만 제거, 내부 텍스트는 보존)
    html = html.replace(/<\/?([a-zA-Z][a-zA-Z0-9]*)\b[^>]*>/gi, (match, tag) => {
      if (ALLOWED_TAGS.has(tag.toLowerCase())) {
        return match;
      }
      return '';
    });

    // 2. 허용된 태그의 위험 속성 제거 (on* 이벤트 핸들러)
    html = html.replace(/\son\w+\s*=\s*["'][^"']*["']/gi, '');
    // javascript: 프로토콜 제거
    html = html.replace(/javascript\s*:/gi, '');

    return html;
  }

  private escapeHtml(text: string): string {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
}
