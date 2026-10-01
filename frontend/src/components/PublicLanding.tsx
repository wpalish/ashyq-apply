export function PublicLanding() {
  return (
    <div className="landing">
      <header className="landing__header">
        <a className="landing__brand" href="#/welcome" aria-label="Unimatch home">
          <img src="/brand/unimatch-mark.png" alt="" /> Unimatch
        </a>
        <nav aria-label="Public navigation">
          <a href="#how-it-works">How it works</a>
          <a href="#why-unimatch">Why Unimatch</a>
          <a href="#/legal">Privacy &amp; terms</a>
        </nav>
        <a className="landing__sign-in" href="#/sign-in">Sign in</a>
      </header>

      <main>
        <section className="landing__hero" aria-labelledby="landing-title">
          <div className="landing__hero-copy">
            <span className="home-eyebrow">SAME STUDENTS. BIGGER HORIZONS.</span>
            <h1 id="landing-title">Find a university<br />that fits <em>you.</em></h1>
            <p>Personalized recommendations. Real data. Global opportunities. Your path, made clearer.</p>
            <div className="landing__actions">
              <a className="landing__cta" href="#/sign-in?create=1">Start your journey <span aria-hidden="true">→</span></a>
              <a className="landing__secondary" href="#how-it-works">See how it works</a>
            </div>
          </div>
          <img src="/brand/unimatch-journey.png" alt="A small Unimatch robot looks toward a university across a mountain lake" />
        </section>

        <section className="landing__steps" id="how-it-works" aria-labelledby="steps-title">
          <span className="home-eyebrow">A CLEARER PATH</span>
          <h2 id="steps-title">Four simple steps. One brighter future.</h2>
          <ol>
            <li><strong>01 · Build your profile</strong><span>Share your goals and academic background.</span></li>
            <li><strong>02 · We research</strong><span>We check available university and programme sources.</span></li>
            <li><strong>03 · Compare with clarity</strong><span>See matches, unknowns and evidence together.</span></li>
            <li><strong>04 · Plan your next step</strong><span>Keep decisions and document requirements organized.</span></li>
          </ol>
        </section>

        <section className="landing__promise" id="why-unimatch">
          <div>
            <span className="home-eyebrow">MORE THAN A SEARCH</span>
            <h2>Real information.<br /><em>Brighter choices.</em></h2>
          </div>
          <p>Unimatch shows what a source confirms, what remains unknown, and which questions are worth asking. You make the decision with a clearer view.</p>
        </section>
      </main>

      <footer className="landing__footer">
        <span>© {new Date().getFullYear()} Unimatch</span>
        <a href="#/legal">Privacy &amp; terms · Drafts awaiting legal review</a>
      </footer>
    </div>
  );
}
