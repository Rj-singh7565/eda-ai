import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'AI-Based EDA Assistant — Enterprise Workspace',
  description: 'AI Document Intelligence Engine with RAG Retrieval and Page/Slide/Row Citations',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="theme-dark">{children}</body>
    </html>
  );
}
