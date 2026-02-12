/**
 * Next.js - spo-chatbot Sample
 *
 * SSR 우회가 핵심:
 * - Next.js는 서버 사이드에서 customElements API가 존재하지 않는다.
 * - dynamic import + ssr: false 로 ChatbotWrapper를 CSR 전용으로 로드한다.
 * - 이를 통해 hydration mismatch를 방지한다.
 */

import dynamic from 'next/dynamic'
import Head from 'next/head'

const ChatbotWrapper = dynamic(
  () => import('../components/ChatbotWrapper'),
  { ssr: false }
)

export default function Home() {
  return (
    <>
      <Head>
        <title>Next.js - spo-chatbot Sample</title>
        <meta charSet="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      </Head>
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
          Next.js - spo-chatbot Sample
        </h1>
        <ChatbotWrapper />
      </div>
    </>
  )
}
