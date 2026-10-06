/**
 * The public landing (palette E, Unimatch): the scroll story first - the
 * question, the routes from home, a pass opened line by line, the three
 * answers - then how it works and what it will not do, in plain words.
 */

import { LandingStory } from '@/components/LandingStory';

const STEPS = [
  { n: '1', title: 'Your profile', text: 'What you study, your results and where you would go. Nothing is guessed for you.' },
  { n: '2', title: 'We read the pages', text: 'Official programme, fee and grant pages — each fact keeps its source and the date it was read.' },
  { n: '3', title: 'Decide one at a time', text: 'Every programme as a pass: what is left to pay, and three separate answers.' },
  { n: '4', title: 'Your plan', text: 'The deadlines on what you keep, and the documents each one asks for.' },
];

export function PublicLanding() {
  return (
    <div className="landing">
      <header className="landing__header">
        <a className="landing__brand" href="#/welcome" aria-label="Unimatch home">
          <span className="logo-tile" aria-hidden="true" /> unimatch
        </a>
        <nav aria-label="Public navigation">
          <a href="#how-it-works">How it works</a>
          <a href="#why-unimatch">Why Unimatch</a>
          <a href="#/legal">Privacy &amp; terms</a>
        </nav>
        <a className="landing__sign-in" href="#/sign-in">Sign in</a>
      </header>

      <main>
        <LandingStory />

        <section className="landing__steps" id="how-it-works" aria-labelledby="steps-title">
          <p className="landing__kicker">How it works</p>
          <h2 id="steps-title">Four steps, each one yours</h2>
          <ol>
            {STEPS.map((s) => (
              <li key={s.n}>
                <span className="landing__n" aria-hidden="true">{s.n}</span>
                <strong>{s.title}</strong>
                <span>{s.text}</span>
              </li>
            ))}
          </ol>
        </section>

        <section className="landing__promise" id="why-unimatch" aria-labelledby="promise-title">
          <div>
            <p className="landing__kicker">Why Unimatch</p>
            <h2 id="promise-title">What a page says, what it does not — and no guesses</h2>
          </div>
          <div className="landing__promise-text">
            <p>
              Every price, requirement and deadline comes with the page it was read from and the date.
              What a page does not publish stays unknown — it is never filled in for you.
            </p>
            <p>
              Requirements, your profile and money stay three separate answers. None of them predicts
              an admission decision: that is the university&apos;s.
            </p>
            <a className="landing__cta" href="#/sign-in?create=1">Start with your profile <span aria-hidden="true">→</span></a>
          </div>
        </section>
      </main>

      <footer className="landing__footer">
        <span>© {new Date().getFullYear()} Unimatch</span>
        <a href="#/legal">Privacy &amp; terms · Drafts awaiting legal review</a>
      </footer>
    </div>
  );
}
