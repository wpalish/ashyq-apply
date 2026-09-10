import { fireEvent, render, screen } from '@testing-library/react';
import { DesignSystem } from './DesignSystem';

describe('DesignSystem', () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.setAttribute('data-theme', 'light');
  });

  it('renders the brand foundations and all three trust registers', () => {
    render(<DesignSystem />);

    expect(screen.getByRole('heading', { name: 'Открытая глава. Понятный маршрут.' })).toBeInTheDocument();
    expect(screen.getByText('Факт')).toBeInTheDocument();
    expect(screen.getByText('Оценка')).toBeInTheDocument();
    expect(screen.getByText('Мнение ИИ')).toBeInTheDocument();
    expect(screen.getByText(/Не вероятность поступления/)).toBeInTheDocument();
    expect(screen.getByText(/Ресми университет беттерінде/)).toBeInTheDocument();
  });

  it('switches between the equal light and dark themes', () => {
    render(<DesignSystem />);

    const toggle = screen.getByRole('button', { name: 'Включить тёмную тему' });
    fireEvent.click(toggle);

    expect(document.documentElement).toHaveAttribute('data-theme', 'dark');
    expect(screen.getByRole('button', { name: 'Включить светлую тему' })).toHaveAttribute('aria-pressed', 'true');
  });

  it('keeps unknown data explicit and actionable', () => {
    render(<DesignSystem />);

    expect(screen.getAllByText('Не опубликовано').length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: 'Спросить вуз' })).toBeEnabled();
    expect(screen.getAllByText('Демо-данные').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Живые данные').length).toBeGreaterThan(0);
  });
});
