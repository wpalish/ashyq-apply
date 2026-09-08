import { useEffect, useState, type ReactNode } from 'react';

type Theme = 'light' | 'dark';
type Tone = 'success' | 'info' | 'warning' | 'danger' | 'neutral' | 'demo' | 'deadline';

const THEME_KEY = 'ashyq.design-system.theme';

const palette = [
  ['Ashyq Ink', '#111827', 'Текст · тёмные поверхности'],
  ['Paper', '#F7F3EA', 'Основной фон'],
  ['Academic Blue', '#526DA6', 'CTA · SAT · навигация'],
  ['Library Burgundy', '#8E3F4C', 'Документы · application'],
  ['Scholar Teal', '#437A78', 'IELTS · подтверждено'],
  ['Parchment Gold', '#C5A66B', 'Премиальный акцент'],
  ['Deadline Coral', '#E47A6A', 'Дедлайны · срочность'],
] as const;

const statuses: { group: string; items: [string, string, Tone][] }[] = [
  {
    group: 'Eligibility',
    items: [
      ['✓', 'Требование выполнено', 'success'],
      ['○', 'Ожидает проверки', 'warning'],
      ['!', 'Есть несоответствие', 'danger'],
      ['?', 'Не опубликовано', 'neutral'],
    ],
  },
  {
    group: 'Portfolio bucket',
    items: [
      ['◆', 'Хорошо подходит', 'success'],
      ['◇', 'Реалистичный вариант', 'info'],
      ['△', 'Амбициозный вариант', 'warning'],
      ['!', 'Выше бюджета', 'danger'],
    ],
  },
  {
    group: 'Freshness & mode',
    items: [
      ['●', 'Обновлено 2 дня назад', 'success'],
      ['◐', 'Данные устаревают', 'warning'],
      ['!', 'Нужна повторная проверка', 'deadline'],
      ['D', 'Демо-данные', 'demo'],
    ],
  },
];

function Section({
  number,
  title,
  kicker,
  id,
  children,
}: {
  number: string;
  title: string;
  kicker: string;
  id: string;
  children: ReactNode;
}) {
  return (
    <section className="ds-section" id={id} aria-labelledby={`${id}-title`}>
      <header className="ds-section__head">
        <span className="ds-section__number">{number}</span>
        <div>
          <p className="ds-section__kicker">{kicker}</p>
          <h2 id={`${id}-title`}>{title}</h2>
        </div>
      </header>
      {children}
    </section>
  );
}

function Status({ icon, children, tone }: { icon: string; children: ReactNode; tone: Tone }) {
  return (
    <span className={`ds-status ds-status--${tone}`}>
      <span className="ds-status__icon" aria-hidden="true">{icon}</span>
      {children}
    </span>
  );
}

function OpenPageMark() {
  return (
    <span className="ds-open-page" aria-hidden="true">
      <span />
      <span />
    </span>
  );
}

export function DesignSystem() {
  const [theme, setTheme] = useState<Theme>(() => {
    try {
      return window.localStorage.getItem(THEME_KEY) === 'dark' ? 'dark' : 'light';
    } catch {
      return 'light';
    }
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    try {
      window.localStorage.setItem(THEME_KEY, theme);
    } catch {
      // Theme selection remains usable when storage is unavailable.
    }
  }, [theme]);

  return (
    <div className="ds-page">
      <a className="ds-skip" href="#foundations">К содержанию</a>
      <header className="ds-topbar">
        <a className="ds-wordmark" href="#top" aria-label="ashyq apply, начало страницы">
          <OpenPageMark />
          <span>ashyq</span>
          <small>apply</small>
        </a>
        <nav className="ds-nav" aria-label="Разделы дизайн-системы">
          <a href="#foundations">Основа</a>
          <a href="#trust">Доверие</a>
          <a href="#components">Компоненты</a>
          <a href="#patterns">Паттерны</a>
        </nav>
        <button
          className="ds-theme"
          type="button"
          aria-label={`Включить ${theme === 'light' ? 'тёмную' : 'светлую'} тему`}
          aria-pressed={theme === 'dark'}
          onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
        >
          <span aria-hidden="true">{theme === 'light' ? '☾' : '☀'}</span>
          {theme === 'light' ? 'Тёмная' : 'Светлая'}
        </button>
      </header>

      <main id="top">
        <section className="ds-hero" aria-labelledby="hero-title">
          <div className="ds-hero__copy">
            <p className="ds-eyebrow">Design system · v1.0 · mobile first</p>
            <h1 id="hero-title">Открытая глава.<br />Понятный маршрут.</h1>
            <p className="ds-hero__lede">
              Тёплая, редакторская и доказательная система для поступления без хаоса.
              Каждый факт имеет источник, каждое неизвестное — понятное действие.
            </p>
            <div className="ds-hero__actions">
              <a className="ds-button ds-button--primary" href="#components">Смотреть компоненты <span aria-hidden="true">→</span></a>
              <a className="ds-button ds-button--secondary" href="#trust">Как устроено доверие</a>
            </div>
          </div>
          <div className="ds-chapter" aria-label="Маршрут пользователя">
            <div className="ds-chapter__mark"><OpenPageMark /></div>
            <p className="ds-chapter__title">Следующий шаг всегда перед глазами</p>
            <ol className="ds-route">
              <li><span>01</span> Профиль</li>
              <li><span>02</span> Приоритеты</li>
              <li><span>03</span> Shortlist</li>
              <li><span>04</span> Application</li>
            </ol>
          </div>
        </section>

        <div className="ds-content">
          <Section number="01" title="Foundations" kicker="Спокойный editorial, точный digital" id="foundations">
            <div className="ds-grid ds-grid--palette">
              {palette.map(([name, hex, use]) => (
                <article className="ds-swatch" key={name}>
                  <div className={`ds-swatch__color ds-swatch__color--${name.toLowerCase().replaceAll(' ', '-')}`} />
                  <div className="ds-swatch__meta">
                    <strong>{name}</strong>
                    <code>{hex}</code>
                    <span>{use}</span>
                  </div>
                </article>
              ))}
            </div>

            <div className="ds-grid ds-grid--foundations">
              <article className="ds-specimen ds-type">
                <p className="ds-card-label">Typography</p>
                <p className="ds-type__display">Твой путь открыт</p>
                <p className="ds-type__brand">Manrope — бренд и действия</p>
                <p className="ds-type__body">Inter сохраняет ясность в длинных объяснениях, формах и инструкциях.</p>
                <p className="ds-type__mono">₸ 1 850 000 · 15 ЯНВ 2027</p>
                <dl className="ds-token-list">
                  <div><dt>Display</dt><dd>Fraunces 48/55</dd></div>
                  <div><dt>Action</dt><dd>Manrope 16/24</dd></div>
                  <div><dt>Body</dt><dd>Inter 16/26</dd></div>
                  <div><dt>Evidence</dt><dd>IBM Plex Mono 14/20</dd></div>
                </dl>
              </article>

              <article className="ds-specimen">
                <p className="ds-card-label">4 pt rhythm</p>
                <div className="ds-space-scale" aria-label="Шкала отступов 4, 8, 12, 16, 24, 32, 48 пикселей">
                  {[1, 2, 3, 4, 6, 7, 8].map((step) => <span key={step} className={`ds-space ds-space--${step}`}>{step === 7 ? 32 : step === 8 ? 48 : step * 4}</span>)}
                </div>
                <p className="ds-card-label ds-card-label--spaced">Radius</p>
                <div className="ds-radius-scale">
                  <span className="ds-radius ds-radius--sm">4</span>
                  <span className="ds-radius ds-radius--md">8</span>
                  <span className="ds-radius ds-radius--lg">12</span>
                  <span className="ds-radius ds-radius--page">24</span>
                </div>
                <p className="ds-footnote">4 / 8 / 12 — продукт. 24 — только крупная «страница» или фото.</p>
              </article>

              <article className="ds-specimen ds-image-style">
                <p className="ds-card-label">Photography</p>
                <figure className="ds-photo-frame">
                  <img src="/design-system/hero-reference.png" alt="Рюкзак, учебные материалы и вид на европейский город у моря" />
                  <figcaption>REFERENCE MOOD · NOT PRODUCT EVIDENCE</figcaption>
                </figure>
                <p>Люди в процессе, реальные города и учебные моменты. Мягкий дневной свет, воздух, редакторский кадр.</p>
                <p className="ds-footnote">Без стоковых улыбок, AI-учеников, 3D, неона и декоративных градиентов.</p>
              </article>
            </div>
          </Section>

          <Section number="02" title="Три регистра доверия" kicker="Факт, оценка и мнение никогда не смешиваются" id="trust">
            <div className="ds-grid ds-grid--trust">
              <article className="ds-trust-card ds-trust-card--fact">
                <div className="ds-origin"><span aria-hidden="true">▣</span> Факт</div>
                <p className="ds-evidence-value">€ 15 800 / год</p>
                <h3>Стоимость обучения</h3>
                <a href="#sources">Официальная страница ↗</a>
                <Status icon="●" tone="success">Проверено 2 дня назад</Status>
              </article>
              <article className="ds-trust-card ds-trust-card--assessment">
                <div className="ds-origin"><span aria-hidden="true">◇</span> Оценка</div>
                <h3>Реалистичный вариант</h3>
                <p>Соответствует вашим приоритетам по подтверждённым данным.</p>
                <div className="ds-axis-list">
                  <span><i /> Академические требования</span>
                  <span><i /> Бюджет семьи</span>
                  <span><i /> Предпочтения</span>
                </div>
              </article>
              <article className="ds-trust-card ds-trust-card--opinion">
                <div className="ds-origin"><span aria-hidden="true">✦</span> Мнение ИИ</div>
                <blockquote>«Сравните дедлайн с датой IELTS: результат может прийти позже.»</blockquote>
                <p className="ds-footnote">Совет помогает проверить решение, но не выдаётся за факт университета.</p>
              </article>
            </div>
            <div className="ds-disclaimer" role="note">
              <span aria-hidden="true">i</span>
              <strong>Единый дисклеймер</strong>
              <p>Соответствие вашим приоритетам по подтверждённым данным. Не вероятность поступления.</p>
            </div>
          </Section>

          <Section number="03" title="Components" kicker="44 px touch target · видимый focus · состояния словами" id="components">
            <div className="ds-grid ds-grid--components">
              <article className="ds-specimen">
                <p className="ds-card-label">Buttons</p>
                <div className="ds-component-row">
                  <button className="ds-button ds-button--primary" type="button">Добавить в shortlist <span aria-hidden="true">→</span></button>
                  <button className="ds-button ds-button--secondary" type="button">Сравнить</button>
                  <button className="ds-button ds-button--ghost" type="button">Отложить</button>
                  <button className="ds-button ds-button--danger" type="button">Удалить</button>
                  <button className="ds-button ds-button--secondary" type="button" disabled>Недоступно</button>
                </div>
              </article>

              <article className="ds-specimen">
                <p className="ds-card-label">Form controls</p>
                <div className="ds-form-grid">
                  <label className="ds-field">
                    <span>Бюджет семьи в год</span>
                    <span className="ds-input-wrap"><input defaultValue="6 000" inputMode="decimal" /><b>USD</b></span>
                    <small>Можно изменить позже</small>
                  </label>
                  <label className="ds-field">
                    <span>Страна</span>
                    <select defaultValue="nl"><option value="nl">Нидерланды</option><option value="ca">Канада</option></select>
                    <small>Можно выбрать несколько</small>
                  </label>
                </div>
              </article>

              <article className="ds-specimen ds-specimen--wide">
                <p className="ds-card-label">Semantic status roles</p>
                <div className="ds-status-groups">
                  {statuses.map(({ group, items }) => (
                    <div key={group}>
                      <h3>{group}</h3>
                      <div className="ds-component-row">
                        {items.map(([icon, label, tone]) => <Status key={label} icon={icon} tone={tone}>{label}</Status>)}
                      </div>
                    </div>
                  ))}
                </div>
              </article>

              <article className="ds-specimen">
                <p className="ds-card-label">Unknown value</p>
                <div className="ds-unknown">
                  <span className="ds-unknown__icon" aria-hidden="true">?</span>
                  <div><strong>Не опубликовано</strong><p>Не найдено на официальных страницах университета.</p></div>
                  <button className="ds-button ds-button--secondary" type="button">Спросить вуз</button>
                </div>
              </article>

              <article className="ds-specimen" id="sources">
                <p className="ds-card-label">Evidence & mode</p>
                <div className="ds-evidence-stack">
                  <a className="ds-evidence-link" href="#sources"><span aria-hidden="true">▣</span><span>admissions.example.edu</span><span aria-hidden="true">↗</span></a>
                  <Status icon="●" tone="success">Живые данные</Status>
                  <Status icon="D" tone="demo">Демо-данные</Status>
                  <Status icon="◐" tone="warning">Проверено 86 дней назад</Status>
                </div>
              </article>
            </div>
          </Section>

          <Section number="04" title="Responsive product patterns" kicker="Таблица на ноутбуке, карточки на телефоне" id="patterns">
            <article className="ds-product-card">
              <div className="ds-programme-head">
                <div>
                  <p className="ds-card-label">Bachelor · Computer Science</p>
                  <h3>University of Groningen</h3>
                  <p>Нидерланды · старт в сентябре 2027</p>
                </div>
                <Status icon="◇" tone="info">Реалистичный вариант</Status>
              </div>
              <div className="ds-table-wrap">
                <table>
                  <caption>Ключевые данные программы</caption>
                  <thead><tr><th>Стоимость</th><th>Финансирование</th><th>Дедлайн</th><th>Следующий шаг</th></tr></thead>
                  <tbody><tr>
                    <td><strong className="ds-num">€ 15 800</strong><a href="#sources">Источник ↗</a></td>
                    <td><Status icon="○" tone="warning">Частичное</Status></td>
                    <td><strong className="ds-num">15 ЯНВ 2027</strong><Status icon="●" tone="success">Свежие данные</Status></td>
                    <td><button className="ds-button ds-button--primary" type="button">Проверить требования</button></td>
                  </tr></tbody>
                </table>
              </div>
              <dl className="ds-card-list">
                <div><dt>Стоимость</dt><dd><strong className="ds-num">€ 15 800</strong><a href="#sources">Источник ↗</a></dd></div>
                <div><dt>Финансирование</dt><dd><Status icon="○" tone="warning">Частичное</Status></dd></div>
                <div><dt>Дедлайн</dt><dd><strong className="ds-num">15 ЯНВ 2027</strong><Status icon="●" tone="success">Свежие данные</Status></dd></div>
                <div><dt>Следующий шаг</dt><dd><button className="ds-button ds-button--primary" type="button">Проверить требования</button></dd></div>
              </dl>
            </article>

            <div className="ds-grid ds-grid--states">
              <article className="ds-state"><span aria-hidden="true">○</span><h3>Пока пусто</h3><p>Добавьте результаты IELTS, чтобы точнее проверить требования.</p><button className="ds-button ds-button--secondary" type="button">Добавить результат</button></article>
              <article className="ds-state"><span className="ds-loader" aria-hidden="true" /><h3>Проверяем источники</h3><p>Уже найдено 12 официальных страниц. Можно уйти с экрана.</p><Status icon="●" tone="info">Исследование идёт</Status></article>
              <article className="ds-state ds-state--success"><span aria-hidden="true">✓</span><h3>Профиль сохранён</h3><p>Следующий шаг — выбрать приоритеты и бюджет.</p><button className="ds-button ds-button--primary" type="button">Продолжить</button></article>
              <article className="ds-state ds-state--error"><span aria-hidden="true">!</span><h3>Источник недоступен</h3><p>Мы сохранили прежние данные и пометили дату проверки.</p><button className="ds-button ds-button--secondary" type="button">Повторить</button></article>
            </div>

            <aside className="ds-locale-test" aria-label="Проверка длинной казахской строки">
              <span className="ds-card-label">KK +30% stress test</span>
              <p>Ресми университет беттерінде жарияланбаған мәліметтерді нақтылау үшін университетке сұрақ жіберіңіз.</p>
            </aside>
          </Section>
        </div>
      </main>

      <footer className="ds-footer">
        <div><OpenPageMark /><strong>ashyq apply</strong></div>
        <p>Открой свой путь. Спокойно, честно, с источником рядом.</p>
        <span className="ds-card-label">RU · KK · EN / AA</span>
      </footer>
    </div>
  );
}
