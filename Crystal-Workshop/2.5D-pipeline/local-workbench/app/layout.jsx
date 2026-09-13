/**
 * File: local-workbench/app/layout.jsx
 * Purpose:
 *  - Define metadata and the local-only 2.5D workbench document shell.
 */

import './globals.css';

export const metadata = {
  title: 'ACM 2.5D Workbench',
  description: 'Local Leið A to 2.5D generation to Leið B crystal review workflow.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="is" className="dark">
      <body>{children}</body>
    </html>
  );
}
