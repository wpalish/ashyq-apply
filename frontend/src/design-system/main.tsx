import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import '@fontsource/onest/400.css';
import '@fontsource/onest/500.css';
import '@fontsource/onest/600.css';
import '@fontsource/onest/700.css';
import '@fontsource/prata/400.css';
import '@fontsource/ibm-plex-mono/400.css';
import '@fontsource/ibm-plex-mono/500.css';
import '@/styles/global.css';
import './design-system.css';
import { DesignSystem } from './DesignSystem';

createRoot(document.getElementById('design-system-root')!).render(
  <StrictMode>
    <DesignSystem />
  </StrictMode>,
);
