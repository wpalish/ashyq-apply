/**
 * Privacy policy and terms of use.
 *
 * Drafts, and they say so at the top. The product holds an applicant's
 * education history, financial situation and citizenship, and its users are
 * mostly school leavers - which in most jurisdictions means some of them are
 * minors. Shipping without any statement at all was the worse option; shipping
 * a page that pretends to be reviewed would be worse still.
 *
 * Every factual claim below is true of the code today. When one stops being
 * true, this page is wrong and has to change with it.
 */

import { Notice, Panel } from '@/components/primitives';

const UPDATED = '4 September 2026';

export function LegalScreen() {
  return (
    <>
      <div className="screen__head">
        <p className="screen__eyebrow">About</p>
        <h1 className="screen__title">Privacy &amp; terms</h1>
        <p className="screen__lede">
          What ASHYQ Apply stores, what it never does, and what is still owed to you.
        </p>
      </div>

      <div className="stack stack--loose">
        <Notice kind="warn">
          <div data-testid="legal-draft">
            <strong>These are drafts, not reviewed by a lawyer.</strong> They describe honestly
            what the software does today, and they are not a substitute for legal advice or for a
            privacy notice reviewed against the law that applies to you. If you are running this
            service for real applicants, have both documents reviewed before you open
            registration — particularly the parts that concern applicants under 18.
          </div>
        </Notice>

        <Panel title="Privacy policy (draft)" hint={`Last updated ${UPDATED}`}>
          <div className="stack stack--tight small">
            <p>
              <strong>What is stored.</strong> The applicant profile you fill in (education,
              grades, test scores, citizenship, country of residence, budget and preferences), the
              research runs you start, their results and your decisions and notes on them, and the
              evidence behind every value: the address of each official page that was read, the
              excerpt taken from it and the date it was read.
            </p>
            <p>
              <strong>Accounts.</strong> When authentication is enabled, an account holds an email
              address, a display name and a password that is stored only as a scrypt hash. A
              session is an opaque random token; no applicant data is placed in a browser cookie.
              An append-only audit trail records who did what, and holds identifiers and actions
              only — never applicant data.
            </p>
            <p>
              <strong>The community is public, and it is the only part that is.</strong>{' '}
              Everything above stays inside your workspace. The community does not: if you create
              a community profile, your display name, the city, major and universities you say you
              are aiming at, the status you choose, your description of yourself, and every post
              and reply you write are visible to every other signed-in applicant, including people
              in other workspaces. That is the point of it — but it is a separate decision, and
              registering an account does not make it for you. Nothing from your applicant case,
              your research or your shortlist appears there. You can leave at any time, which
              deletes your community profile, your posts and your replies and keeps your account
              and your research.
            </p>
            <p>
              <strong>What leaves the service.</strong> Requests to universities&apos; own public
              pages, which never carry your data: the fetcher refuses to place applicant
              information in an outbound URL, honours robots.txt, reads nothing behind a login and
              bypasses no CAPTCHA. If password-reset email is configured, your address reaches the
              configured SMTP provider. There is no analytics, no advertising, no tracking pixel
              and no third-party script — the browser is told so by the content security policy.
            </p>
            <p>
              <strong>What you can do with it.</strong> Export the complete record for a case
              (profile, runs, results, claims, conflicts and the audit trail) as JSON, and delete
              a case or the whole account. Deleting an account deletes its organisation&apos;s
              cases and their runs with it.
            </p>
            <p>
              <strong>How long it is kept.</strong> Until you delete it. The operator of a given
              deployment sets its own backup retention; backups contain the same applicant data
              and must be treated the same way.
            </p>
            <p>
              <strong>Applicants under 18.</strong> The product is built for people applying to
              undergraduate study, so it will be used by minors. It does not currently ask for
              age, verify it, or ask for a parent&apos;s consent. That is a gap a legal review has
              to close, not a decision that this is acceptable.
            </p>
          </div>
        </Panel>

        <Panel title="Terms of use (draft)" hint={`Last updated ${UPDATED}`}>
          <div className="stack stack--tight small">
            <p>
              <strong>What this service is.</strong> It reads published admission and funding
              criteria and shows you how your profile sits against them, with a source and a date
              behind every value. It is a research assistant, not an adviser and not an agent.
            </p>
            <p>
              <strong>What it never does.</strong> It never predicts whether you will be admitted
              or funded, and no number on any screen is a probability of either. It never submits
              an application, signs anything, or pays anything on your behalf. It never fills a
              gap in the evidence with a guess: a value that could not be confirmed is shown as
              unknown, and two sources that disagree are both shown to you.
            </p>
            <p>
              <strong>What you have to check yourself.</strong> Official pages change, and grade
              conversions and currency conversions are approximations from a dated snapshot. Before
              you act on anything here — a deadline, a fee, an eligibility rule — confirm it
              against the university&apos;s own page. The service links every claim to its source
              so that check takes seconds.
            </p>
            <p>
              <strong>No warranty.</strong> The software is provided as-is under the MIT licence,
              without warranty of any kind. A missed deadline or a misread requirement remains
              yours to bear, which is why the sources are on every screen.
            </p>
            <p>
              <strong>Acceptable use.</strong> Do not use the service to harvest data about other
              people, to evade a site&apos;s stated crawling rules, or to submit applications
              automatically. Reading the community and its profiles is what they are there for;
              copying them out in bulk, or contacting people through anything you learn there
              without being asked, is not. The fetcher enforces the crawling rules; automatic
              submission it simply cannot do.
            </p>
            <p>
              <strong>What you write in the community.</strong> You keep what you write and stay
              responsible for it. Do not post another person&apos;s private information, impersonate
              anyone, or harass, and do not present a rumour about a university&apos;s requirements
              as a fact — the rest of the product exists precisely because published criteria and
              hearsay are not the same thing. The operator of a deployment may remove a post or an
              account. Be aware that there is no reporting button, no moderation queue and no
              automated filtering in this build: removal today means someone with database access
              doing it by hand.
            </p>
          </div>
        </Panel>
      </div>
    </>
  );
}
