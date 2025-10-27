import type { Metadata } from 'next'
import '../styles/globals.css'
import { LanguageProvider } from '../contexts/LanguageContext'

export const metadata: Metadata = {
  title: 'مساعد الهيئة الذكي | AI-Powered ICP Assistant',
  description: 'مساعد ذكي مدعوم بالذكاء الاصطناعي لتحليل المستندات | AI-powered document analysis and content generation for ICP',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50">
        <LanguageProvider>
          {children}
        </LanguageProvider>
      </body>
    </html>
  )
}