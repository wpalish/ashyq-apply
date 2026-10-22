import { useLayoutEffect, useRef, useState } from 'react';

/** Real buttons retain native keyboard activation; the moving line is decorative. */
export function BookTabRail<T extends string>({ items, value, onChange, label }: {
  items: readonly T[];
  value: T;
  onChange: (value: T) => void;
  label: string;
}) {
  const rail = useRef<HTMLElement>(null);
  const indicator = useRef<HTMLSpanElement>(null);
  const [ready, setReady] = useState(false);
  useLayoutEffect(() => {
    const nav = rail.current;
    const line = indicator.current;
    if (!nav || !line) return;
    const measure = () => {
      const active = nav.querySelector<HTMLButtonElement>('[aria-current="page"]');
      if (!active) return;
      line.style.transform = `translateX(${active.offsetLeft}px) scaleX(${active.offsetWidth})`;
      setReady(true);
    };
    measure();
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(measure);
    observer?.observe(nav);
    // Font loading and wrap changes can resize the buttons without resizing nav.
    nav.querySelectorAll('button').forEach(button => observer?.observe(button));
    return () => observer?.disconnect();
  }, [value, items]);
  return <nav className="book-programme__tabs book-tab-rail" aria-label={label} ref={rail} data-ready={ready}>
    {items.map(item => <button key={item} type="button" aria-current={value === item ? 'page' : undefined} onClick={() => onChange(item)}>{item}</button>)}
    <span className="book-tab-rail__indicator" aria-hidden="true" ref={indicator}/>
  </nav>;
}
