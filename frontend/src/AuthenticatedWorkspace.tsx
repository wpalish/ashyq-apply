import App from './App';
import { StoreProvider } from '@/lib/store';
/** The private application is loaded only after AuthGate confirms its owner. */
export default function AuthenticatedWorkspace() {
  return <StoreProvider><App /></StoreProvider>;
}
