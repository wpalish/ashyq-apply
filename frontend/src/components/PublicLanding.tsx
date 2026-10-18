import { useState } from 'react';
import { ArrowRight, MagnifyingGlass } from '@phosphor-icons/react';
import { savePublicSearchIntent } from '@/lib/publicSearchIntent';

export function PublicLanding() {
  const [subject, setSubject] = useState('Computer Science');
  const [country, setCountry] = useState('');
  const [budget, setBudget] = useState('');
  return (
    <div className="landing">
      <header className="landing__header">
        <a className="landing__brand" href="#/welcome" aria-label="Unimatch home"><img src="/brand/unimatch-orbit.svg" alt="" />unimatch</a>
        <nav aria-label="Public navigation"><a href="#how-it-works">How it works</a><a href="#why-unimatch">Why Unimatch</a><a href="#/legal">Privacy &amp; terms</a></nav>
        <a className="landing__sign-in" href="#/sign-in">Sign in</a>
      </header>
      <main>
        <section className="landing__hero" aria-labelledby="landing-title">
          <div className="landing__hero-copy"><h1 id="landing-title">Find where to study.<br />Know what comes next.</h1><p>Programmes, entry requirements, funding and your next steps — together in one clear path.</p>
            <div className="landing__actions"><a className="landing__cta" href="#/sign-in?create=1">Start your journey <ArrowRight size={18} /></a><a className="landing__secondary" href="#how-it-works">See how it works</a></div>
          </div><img src="/brand/unimatch-globe.webp" alt="A globe connects international study destinations" fetchPriority="high" />
        </section>
        <form className="landing__search" aria-label="Plan your university search" onSubmit={event => {
          event.preventDefault(); savePublicSearchIntent({ subject: subject.trim(), country, budget: budget === '' ? null : Number(budget) }); window.location.hash = '#/sign-in?create=1';
        }}>
          <label>What do you want to study?<input value={subject} maxLength={120} required onChange={event => setSubject(event.target.value)} /></label>
          <label>Where?<select value={country} onChange={event => setCountry(event.target.value)}><option value="">Explore worldwide</option>{['Canada','Germany','Netherlands','United Kingdom','United States','Japan','Australia'].map(value => <option key={value}>{value}</option>)}</select></label>
          <label>Annual family budget (USD)<input type="number" min={0} max={1000000} placeholder="Not decided yet" value={budget} onChange={event => setBudget(event.target.value)} /></label>
          <button className="btn btn--primary" type="submit"><MagnifyingGlass size={18} />Find programmes</button>
        </form>
        <div className="landing__topics"><span>Popular fields:</span>{['Computer Science','Business','Engineering','Medicine','Art & Design'].map(value => <button type="button" key={value} aria-pressed={subject === value} onClick={() => setSubject(value)}>{value}</button>)}</div>
        <section className="landing__steps" id="how-it-works" aria-labelledby="steps-title"><h2 id="steps-title">From a possibility to a plan.</h2><ol>
          <li><strong>01 · Build your profile</strong><span>Keep your original grades, goals and budget in one place.</span></li><li><strong>02 · We research</strong><span>Explore available official university and programme sources.</span></li><li><strong>03 · Compare with clarity</strong><span>See confirmed facts, unknowns and source limitations together.</span></li><li><strong>04 · Plan your next step</strong><span>Organise documents, applications and your own reminders.</span></li>
        </ol></section>
        <section className="landing__promise" id="why-unimatch"><h2>Evidence behind your choices.</h2><p>Unimatch shows what a source confirms, what remains unknown, and which questions are worth asking. A research match is not an admission probability. You stay in control of your decision.</p></section>
      </main>
      <footer className="landing__footer"><span>© {new Date().getFullYear()} Unimatch</span><a href="#/legal">Privacy &amp; terms · Drafts awaiting legal review</a></footer>
    </div>
  );
}
