/**
 * React - spo-chatbot Sample
 *
 * React의 Web Component 제약:
 * - JSX는 Custom Element에 props를 HTML attribute(문자열)로만 전달한다.
 * - 동적 속성 변경은 useRef + useEffect에서 setAttribute로 직접 처리한다.
 *
 * embed.js 로드:
 *   개발 시: ln -sf ../../../dist/embed.js public/embed.js
 *   index.html의 <script src="/embed.js"> 로 로드
 */

import { useRef, useEffect, useState } from 'react'

declare global {
  namespace JSX {
    interface IntrinsicElements {
      'spo-chatbot': React.DetailedHTMLProps<
        React.HTMLAttributes<HTMLElement> & {
          'api-url'?: string
          token?: string
          theme?: string
          'context-type'?: string
          'match-id'?: string
        },
        HTMLElement
      >
    }
  }
}

function App() {
  const chatbotRef = useRef<HTMLElement>(null)
  const [token, setToken] = useState('dev-test-token')
  const [theme, setTheme] = useState('bwf')
  const [matchId, setMatchId] = useState('test-match-001')

  // React의 JSX는 Custom Element attribute를 문자열로만 전달하므로
  // 동적 속성 변경은 useEffect에서 직접 setAttribute로 처리한다
  useEffect(() => {
    if (chatbotRef.current) {
      chatbotRef.current.setAttribute('token', token)
    }
  }, [token])

  useEffect(() => {
    if (chatbotRef.current) {
      chatbotRef.current.setAttribute('theme', theme)
    }
  }, [theme])

  useEffect(() => {
    if (chatbotRef.current) {
      chatbotRef.current.setAttribute('match-id', matchId)
    }
  }, [matchId])

  return (
    <div style={{
      fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      background: '#f5f5f5',
      color: '#333',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      padding: '24px',
      minHeight: '100vh'
    }}>
      <h1 style={{ fontSize: '1.4rem', marginBottom: '16px' }}>
        React - spo-chatbot Sample
      </h1>

      <div style={{
        display: 'flex',
        gap: '16px',
        flexWrap: 'wrap',
        alignItems: 'center',
        marginBottom: '20px',
        padding: '16px',
        background: '#fff',
        borderRadius: '8px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
      }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.9rem', fontWeight: 500 }}>
          Token:
          <input
            value={token}
            onChange={e => setToken(e.target.value)}
            placeholder="JWT token"
            style={{ padding: '6px 10px', border: '1px solid #d1d5db', borderRadius: '4px', fontSize: '0.9rem', width: '180px' }}
          />
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.9rem', fontWeight: 500 }}>
          Theme:
          <select
            value={theme}
            onChange={e => setTheme(e.target.value)}
            style={{ padding: '6px 10px', border: '1px solid #d1d5db', borderRadius: '4px', fontSize: '0.9rem' }}
          >
            <option value="default">Default</option>
            <option value="bwf">BWF</option>
            <option value="bxl">BXL</option>
          </select>
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.9rem', fontWeight: 500 }}>
          Match ID:
          <input
            value={matchId}
            onChange={e => setMatchId(e.target.value)}
            placeholder="match ID"
            style={{ padding: '6px 10px', border: '1px solid #d1d5db', borderRadius: '4px', fontSize: '0.9rem', width: '180px' }}
          />
        </label>
      </div>

      <div style={{ width: '400px', height: '600px' }}>
        <spo-chatbot
          ref={chatbotRef}
          api-url="http://localhost:4502"
          token={token}
          theme={theme}
          context-type="badminton"
          match-id={matchId}
          style={{ display: 'block', width: '100%', height: '100%' }}
        />
      </div>
    </div>
  )
}

export default App
