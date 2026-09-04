import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import { StoreProvider } from '@/lib/store';
import { AuthGate } from '@/AuthGate';
import { ErrorBoundary } from '@/components/ErrorBoundary';
// Self-hosted. The production CSP is style-src 'self', so the Google Fonts
// stylesheet was blocked in the very environment it was meant to serve, and in
// development it leaked every visitor to a third party.
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
