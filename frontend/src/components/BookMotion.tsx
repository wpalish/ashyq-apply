import { useEffect, type ReactNode } from 'react';
import { LazyMotion, MotionConfig } from 'motion/react';
const features = () => import('./bookMotionFeatures').then(module => module.default);
/** Stable wrapper: no route/case keys or exits that can retire forms or stores. */
export function BookMotion({ children }: { children: ReactNode }) {
  useEffect(() => {
    // A presentation-only gate, outside React state: typing never rerenders or
    // remounts an applicant form. Keyboard navigation stays immediate.
    const root = document.documentElement;
    const previous = root.dataset.motionInput;
    root.dataset.motionInput = 'pointer';
    const pointer = () => { root.dataset.motionInput = 'pointer'; };
    const keyboard = (event: KeyboardEvent) => {
      if (!event.metaKey && !event.ctrlKey && !event.altKey) root.dataset.motionInput = 'keyboard';
    };
    document.addEventListener('pointerdown', pointer, true);
    document.addEventListener('keydown', keyboard, true);
    return () => {
      document.removeEventListener('pointerdown', pointer, true);
      document.removeEventListener('keydown', keyboard, true);
      if (previous === undefined) delete root.dataset.motionInput;
      else root.dataset.motionInput = previous;
    };
  }, []);
  return <MotionConfig reducedMotion="user" transition={{ duration: .18, ease: [.16, 1, .3, 1] }}><LazyMotion features={features} strict>{children}</LazyMotion></MotionConfig>;
}
