import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import { StoreProvider } from '@/lib/store';
import { AuthGate } from '@/AuthGate';
import { ErrorBoundary } from '@/components/ErrorBoundary';
// Self-hosted. The production CSP is style-src 'self', so the Google Fonts
// stylesheet was blocked in the very environment it was meant to serve, and in
// development it leaked every visitor to a third party.
// Onest for text and numbers, Montserrat for headings: both cover every
// Kazakh letter (Ә Ғ Қ Ң Ө Ұ Ү Һ) and the tenge sign; the faces they replace did not.
import '@fontsource/onest/400.css';
import '@fontsource/onest/500.css';
import '@fontsource/onest/600.css';
import '@fontsource/onest/700.css';
import '@fontsource/montserrat/700.css';
import '@fontsource/montserrat/800.css';
// Inter (and Fraunces) are Unimatch's faces; the port to palette E moves text to Inter.
import '@fontsource/inter/400.css';
import '@fontsource/inter/500.css';
import '@fontsource/inter/600.css';
import '@fontsource/inter/700.css';
import '@fontsource/fraunces/400.css';
import '@fontsource/fraunces/600.css';
import '@fontsource/fraunces/700.css';
import '@fontsource/jetbrains-mono/400.css';
import '@fontsource/jetbrains-mono/500.css';
import './styles/global.css';
import './styles/components.css';
import './styles/unimatch.css';
import './styles/pass.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <AuthGate>
        <StoreProvider>
          <App />
        </StoreProvider>
      </AuthGate>
    </ErrorBoundary>
  </StrictMode>,
);
