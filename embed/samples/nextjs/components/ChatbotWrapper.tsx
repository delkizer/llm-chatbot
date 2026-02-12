/**
 * ChatbotWrapper - CSR 전용 컴포넌트
 *
 * Next.js SSR 환경에서 customElements API가 존재하지 않으므로,
 * 이 컴포넌트는 반드시 dynamic import + ssr: false 로 로드해야 한다.
 *
 * embed.js 로드 방법:
 *   cd embed/samples/nextjs
 *   mkdir -p public
 *   ln -sf ../../../dist/embed.js public/embed.js
 */

'use client'

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

export default function ChatbotWrapper() {
  const chatbotRef = useRef<HTMLElement>(null)
  const [token, setToken] = useState('dev-test-token')
  const [theme, setTheme] = useState('bwf')
  const [matchId, setMatchId] = useState('test-match-001')
  const [loaded, setLoaded] = useState(false)

  // 클라이언트에서만 embed.js 동적 로드
  useEffect(() => {
    const script = document.createElement('script')
    script.src = '/embed.js' // public/ 폴더에 배치 (심볼릭 링크)
    script.onload = () => setLoaded(true)
    document.head.appendChild(script)

    return () => {
      document.head.removeChild(script)
    }
  }, [])

  // 동적 속성 변경: token
  useEffect(() => {
    if (chatbotRef.current) {
      chatbotRef.current.setAttribute('token', token)
    }
  }, [token])

  // 동적 속성 변경: theme
  useEffect(() => {
    if (chatbotRef.current) {
      chatbotRef.current.setAttribute('theme', theme)
    }
  }, [theme])

  // 동적 속성 변경: match-id
  useEffect(() => {
    if (chatbotRef.current) {
      chatbotRef.current.setAttribute('match-id', matchId)
    }
  }, [matchId])

  if (!loaded) {
    return <div>Loading chatbot...</div>
  }

  return (
    <>
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
    </>
  )
}
