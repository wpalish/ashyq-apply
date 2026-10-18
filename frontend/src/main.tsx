import { lazy, StrictMode, Suspense } from 'react';
import { createRoot } from 'react-dom/client';
const AuthenticatedWorkspace = lazy(() => import('./AuthenticatedWorkspace'));
import { AuthGate } from '@/AuthGate';
import { ErrorBoundary } from '@/components/ErrorBoundary';
// Self-hosted. The production CSP is style-src 'self', so the Google Fonts
// stylesheet was blocked in the very environment it was meant to serve, and in
// development it leaked every visitor to a third party.
import '@fontsource/inter/400.css';
import '@fontsource/inter/500.css';
import '@fontsource/inter/600.css';
import '@fontsource/inter/700.css';
import '@fontsource/jetbrains-mono/400.css';
import '@fontsource/jetbrains-mono/500.css';
import './styles/global.css';
import './styles/components.css';
import './styles/unimatch.css';
import './styles/book.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <AuthGate>
        <Suspense fallback={<main className="auth-shell" role="status">Opening your workspace…</main>}>
          <AuthenticatedWorkspace />
        </Suspense>
      </AuthGate>
    </ErrorBoundary>
  </StrictMode>,
);
