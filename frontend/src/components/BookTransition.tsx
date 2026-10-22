import { useEffect, useRef, type ReactNode } from 'react';

/** Animate the surface, never its identity, data, focus or persistence lifecycle. */
export function BookTransition({ children, motionKey, className = '' }: {
  children: ReactNode;
  motionKey: string;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = ref.current;
    const media = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    if (!element?.animate || media?.matches || document.documentElement.dataset.motionInput === 'keyboard') return;
    const animation = element.animate([
      { opacity: .65, transform: 'translateY(6px)' },
      { opacity: 1, transform: 'translateY(0)' },
    ], { duration: 220, easing: 'cubic-bezier(0.16, 1, 0.3, 1)' });
    const cancel = () => animation.cancel();
    // An accessibility preference or keyboard action wins even mid-transition.
    document.addEventListener('keydown', cancel, true);
    media?.addEventListener('change', cancel);
    return () => {
      cancel();
      document.removeEventListener('keydown', cancel, true);
      media?.removeEventListener('change', cancel);
    };
  }, [motionKey]);
  return <div className={`book-transition ${className}`} ref={ref}>{children}</div>;
}
