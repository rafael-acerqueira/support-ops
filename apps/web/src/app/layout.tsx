import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'SupportOps',
  description: 'Customer support operations platform for B2B SaaS teams',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
