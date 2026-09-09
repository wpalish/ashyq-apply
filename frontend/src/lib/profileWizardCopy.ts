import type { Locale } from './i18n';

export const profileWizardCopy: Record<Locale, { steps: string[]; navigation: string; all: string; wizard: string; back: string; next: string; step: string; hint: string }> = {
  ru: { steps: ['Заявка', 'Оценки', 'Английский', 'Тесты', 'Активности', 'Достижения'], navigation: 'Разделы профиля', all: 'Показать все поля', wizard: 'Вернуться к шагам', back: 'Назад', next: 'Далее', step: 'Шаг', hint: 'Заполняйте в своём темпе. Между разделами можно переходить свободно; переход не означает, что данные уже проверены.' },
  kk: { steps: ['Өтінім', 'Бағалар', 'Ағылшын тілі', 'Тесттер', 'Белсенділік', 'Жетістіктер'], navigation: 'Профиль бөлімдері', all: 'Барлық өрістерді көрсету', wizard: 'Қадамдарға оралу', back: 'Артқа', next: 'Келесі', step: 'Қадам', hint: 'Өз қарқыныңызбен толтырыңыз. Бөлімдер арасында еркін өтуге болады; бұл деректер тексерілді дегенді білдірмейді.' },
  en: { steps: ['Application', 'Grades', 'English', 'Tests', 'Activities', 'Achievements'], navigation: 'Profile sections', all: 'Show all fields', wizard: 'Return to steps', back: 'Back', next: 'Continue', step: 'Step', hint: 'Work at your own pace. Move freely between sections; visiting a section does not mean its data has been verified.' },
};
