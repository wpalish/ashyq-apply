/**
 * The last line before a white screen.
 *
 * A render error anywhere unmounted the whole tree and left the applicant
 * looking at nothing at all — with no way to tell whether their work had been
 * lost. It has not: everything is on the server, and the fallback says so.
 */

import { Component, type ErrorInfo, type ReactNode } from 'react';

type Props = { children: ReactNode; label?: string };
type State = { error: Error | null };

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Logged rather than swallowed: without this the stack is gone the moment
    // the fallback renders.
    console.error(`Rendering failed in ${this.props.label ?? 'the app'}`, error, info.componentStack);
  }

  render(): ReactNode {
    if (!this.state.error) return this.props.children;
    return (
      <div className="notice notice--risk" role="alert" data-testid="error-boundary">
        <div className="stack stack--tight">
          <strong>Something broke while rendering {this.props.label ?? 'this page'}.</strong>
          <p className="small">
            Your data is safe on the server — nothing you saved has been lost. Reloading usually
            clears it.
          </p>
          <p className="xs mono faint" style={{ overflowWrap: 'anywhere' }}>
            {this.state.error.message}
          </p>
          <div className="row">
            <button className="btn btn--primary" onClick={() => window.location.reload()}>
              Reload
            </button>
          </div>
        </div>
      </div>
    );
  }
}
