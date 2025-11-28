import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Wisdom Agent',
  description: 'An AI companion for growing in wisdom through Something Deeperism philosophy',
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
    <html lang="en" className="h-full">
      <body className="h-full bg-pattern">
        {children}
      </body>
    </html>
  );
}
