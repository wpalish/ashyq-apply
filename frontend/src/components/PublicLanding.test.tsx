import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PublicLanding } from './PublicLanding';
import { ProductTour } from './ProductTour';
import { readPublicSearchIntent } from '@/lib/publicSearchIntent';

const language = vi.hoisted(() => ({ value: 'ru' }));
vi.mock('@/lib/useTranslation', () => ({ useTranslation: () => ({ locale: language.value, setLocale: (value: string) => { language.value = value; }, t: (value: string) => value }) }));
beforeEach(() => { language.value = 'ru'; sessionStorage.clear(); window.location.hash = '#/welcome'; });

describe('editorial landing keeps the real start path', () => {
  it('takes the primary action straight to the editable search and retains exact preferences for registration', () => {
    render(<PublicLanding/>);
    fireEvent.click(screen.getByRole('button', { name: 'Найти программы' }));
    const subject = screen.getByRole('textbox', { name: 'Что изучать?' });
    expect(subject).toHaveFocus();
    fireEvent.change(subject, { target: { value: '  Environmental Science  ' } });
    fireEvent.change(screen.getByRole('combobox', { name: 'Куда?' }), { target: { value: 'Germany' } });
    fireEvent.change(screen.getByRole('spinbutton'), { target: { value: '18000' } });
    fireEvent.submit(screen.getByRole('form', { name: 'Plan your university search' }));
    expect(readPublicSearchIntent()).toEqual({ subject: 'Environmental Science', country: 'Germany', budget: 18000 });
    expect(window.location.hash).toBe('#/sign-in?create=1');
  });

  it('preserves an edited search while exploring the product, changing language and clearing an optional budget', () => {
    const view = render(<PublicLanding/>);
    const subject = screen.getByRole('textbox', { name: 'Что изучать?' });
    fireEvent.change(subject, { target: { value: 'Architecture' } });
    fireEvent.click(screen.getByRole('button', { name: 'Источники' }));
    fireEvent.click(screen.getByRole('button', { name: 'Твой план' }));
    expect(subject).toHaveValue('Architecture');
    language.value = 'en'; view.rerender(<PublicLanding/>);
    expect(screen.getByRole('textbox', { name: 'What do you want to study?' })).toBe(subject);
    fireEvent.change(screen.getByRole('spinbutton'), { target: { value: '' } });
    fireEvent.submit(screen.getByRole('form'));
    expect(readPublicSearchIntent()).toEqual({ subject: 'Architecture', country: '', budget: null });
  });

  it('uses only public anchors accepted by the existing auth route and labels the illustration honestly', () => {
    render(<PublicLanding/>);
    expect(screen.getByRole('link', { name: 'Почему источники' })).toHaveAttribute('href', '#why-unimatch');
    expect(document.getElementById('why-unimatch')).toBeTruthy();
    expect(document.getElementById('how-it-works')).toBeTruthy();
    expect(screen.getByText(/Это знакомство с продуктом, а не результат подбора/)).toBeVisible();
    expect(screen.getByText(/Решение принимает университет/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Engineering' }));
    expect(screen.getByRole('textbox', { name: 'Что изучать?' })).toHaveValue('Engineering');
  });

  it('keeps a single current tour surface and focused controls during fast reversals', () => {
    render(<ProductTour/>);
    const evidence = screen.getByRole('button', { name: 'Источники' });
    evidence.focus(); fireEvent.click(evidence);
    expect(evidence).toHaveFocus(); expect(evidence).toHaveAttribute('aria-pressed', 'true');
    fireEvent.click(screen.getByRole('button', { name: 'Твой план' }));
    fireEvent.click(evidence);
    expect(screen.getAllByRole('button', { pressed: true })).toHaveLength(1);
    expect(screen.getByRole('heading', { name: 'За каждым решением — основание.' })).toBeVisible();
    expect(document.querySelectorAll('#product-tour-detail')).toHaveLength(1);
    expect(window.location.hash).toBe('#/welcome');
  });
});
