import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: 'Task Manager',
  description: 'Multi-tenant SaaS task platform',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="bg-gray-900 text-gray-100 antialiased">
        {children}
      </body>
    </html>
  );
}
