import type { ReactNode } from 'react';
import Script from 'next/script';

import { TelegramInit } from './TelegramInit';

export const metadata = {
  title: 'Каталог',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ru">
      <body>
        <Script src="https://telegram.org/js/telegram-web-app.js" strategy="beforeInteractive" />
        <TelegramInit />
        {children}
      </body>
    </html>
  );
}
