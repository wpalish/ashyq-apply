import { StrictMode, useState } from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { BookMotion } from './BookMotion';
import { BookTransition } from './BookTransition';
import { BookTabRail } from './BookTabRail';

const originalAnimate = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'animate');
afterEach(() => {
  vi.restoreAllMocks(); vi.unstubAllGlobals(); delete document.documentElement.dataset.motionInput;
  if (originalAnimate) Object.defineProperty(HTMLElement.prototype, 'animate', originalAnimate);
  else delete (HTMLElement.prototype as unknown as { animate?: unknown }).animate;
});

function mediaPreference(reduced = false) {
  const listeners = new Set<() => void>();
  vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: reduced,
    addEventListener: (_: string, callback: () => void) => listeners.add(callback),
    removeEventListener: (_: string, callback: () => void) => listeners.delete(callback),
  })));
  return listeners;
}

describe('motion does not own applicant state', () => {
  it('keeps edited values and input identity through pointer/keyboard and StrictMode cleanup', () => {
    mediaPreference();
    function Form() { const [text, setText] = useState(''); return <input aria-label="Draft" value={text} onChange={event => setText(event.target.value)}/>; }
    const view = render(<StrictMode><BookMotion><Form/></BookMotion></StrictMode>);
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'Unsent draft' } });
    fireEvent.keyDown(input, { key: 'Tab' });
    expect(document.documentElement.dataset.motionInput).toBe('keyboard');
    fireEvent.pointerDown(input);
    expect(document.documentElement.dataset.motionInput).toBe('pointer');
    expect(screen.getByRole('textbox')).toBe(input);
    expect(input).toHaveValue('Unsent draft');
    view.unmount();
    fireEvent.pointerDown(document);
    expect(document.documentElement.dataset.motionInput).toBeUndefined();
  });

  it('cancels a superseded transition without replacing the focused child or its draft', () => {
    mediaPreference();
    const cancels = [vi.fn(), vi.fn(), vi.fn()];
    const animate = vi.fn().mockReturnValueOnce({ cancel: cancels[0] }).mockReturnValueOnce({ cancel: cancels[1] }).mockReturnValueOnce({ cancel: cancels[2] });
    Object.defineProperty(HTMLElement.prototype, 'animate', { configurable: true, value: animate });
    const view = render(<BookTransition motionKey="overview"><input aria-label="Draft" defaultValue="Still here"/></BookTransition>);
    const input = screen.getByRole('textbox'); input.focus();
    view.rerender(<BookTransition motionKey="costs"><input aria-label="Draft" defaultValue="Still here"/></BookTransition>);
    view.rerender(<BookTransition motionKey="overview"><input aria-label="Draft" defaultValue="Still here"/></BookTransition>);
    expect(cancels[0]).toHaveBeenCalledOnce(); expect(cancels[1]).toHaveBeenCalledOnce();
    expect(screen.getByRole('textbox')).toBe(input);
    expect(input).toHaveFocus(); expect(input).toHaveValue('Still here');
    view.unmount(); expect(cancels[2]).toHaveBeenCalledOnce();
  });

  it('honours reduced motion and keyboard actions, including an in-flight preference change', () => {
    const listeners = mediaPreference(); const cancel = vi.fn(); const animate = vi.fn(() => ({ cancel }));
    Object.defineProperty(HTMLElement.prototype, 'animate', { configurable: true, value: animate });
    const view = render(<BookTransition motionKey="a">First</BookTransition>);
    act(() => listeners.forEach(callback => callback()));
    expect(cancel).toHaveBeenCalledOnce();
    fireEvent.keyDown(document, { key: 'Tab' }); expect(cancel).toHaveBeenCalledTimes(2);
    document.documentElement.dataset.motionInput = 'keyboard';
    view.rerender(<BookTransition motionKey="b">Keyboard</BookTransition>);
    expect(animate).toHaveBeenCalledOnce(); expect(listeners.size).toBe(0);
    delete document.documentElement.dataset.motionInput;
    mediaPreference(true);
    view.rerender(<BookTransition motionKey="c">Reduced motion</BookTransition>);
    expect(animate).toHaveBeenCalledOnce();
    view.unmount();
  });

  it('keeps native tab buttons focused and measures the selected underline after resizing', () => {
    const disconnect = vi.fn(); let resize: () => void = () => {};
    vi.stubGlobal('ResizeObserver', class { constructor(callback: () => void) { resize = callback; } observe() {} disconnect = disconnect; });
    vi.spyOn(HTMLElement.prototype, 'offsetLeft', 'get').mockImplementation(function (this: HTMLElement) { return this.textContent === 'Costs' ? 120 : 24; });
    vi.spyOn(HTMLElement.prototype, 'offsetWidth', 'get').mockReturnValue(80);
    const items = ['Overview', 'Costs'];
    function Tabs() { const [value, setValue] = useState('Overview'); return <BookTabRail items={items} value={value} onChange={setValue} label="Programme"/>; }
    const view = render(<Tabs/>); const costs = screen.getByRole('button', { name: 'Costs' });
    costs.focus(); fireEvent.click(costs);
    expect(costs).toHaveFocus(); expect(costs).toHaveAttribute('aria-current', 'page');
    expect(view.container.querySelector('[aria-hidden="true"]')).toHaveStyle({ transform: 'translateX(120px) scaleX(80)' });
    act(() => resize()); expect(screen.getAllByRole('button')).toHaveLength(2);
    view.unmount(); expect(disconnect).toHaveBeenCalled();
  });
});
