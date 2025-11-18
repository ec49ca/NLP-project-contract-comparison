import React from 'react';
import './globals.css';
import type { Metadata } from 'next';
import { ThemeProvider } from './components/theme-provider';

export const metadata: Metadata = {
  title: 'Samvid Agent Hub',
  description: 'A modern, intelligent web interface for discovering and executing agents from MCP servers',
  icons: {
    icon: '/favicon.ico',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body className="min-h-screen bg-background">
        <ThemeProvider defaultTheme="system">
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
