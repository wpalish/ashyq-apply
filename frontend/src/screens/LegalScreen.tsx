/**
 * Privacy policy and terms of use.
 *
 * Draft notice bound to the audited software behavior. The operator's legal
 * details, actual hosting, recipients and minors procedure remain unresolved.
 * Recheck the notice when processing behavior or deployment facts change.
 */

import { Notice, Panel } from '@/components/primitives';

const UPDATED = '9 October 2026';
const VERSION = '2026-10-09.draft1';

export function LegalScreen() {
  return (
    <>
      <div className="screen__head">
        <p className="screen__eyebrow">LEGAL / PRIVACY</p>
        <h1 className="screen__title">Privacy with <span className="find-yellow">clarity.</span></h1>
        <p className="screen__lede">
          Understand where your data goes, who can see it, and how to export or delete it.
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

        <Panel title="Your data at a glance" hint={`Notice version ${VERSION}`}>
          <div className="stack stack--tight small" data-testid="privacy-summary">
            <p>Your applicant case belongs to a workspace. Members of that workspace can access its cases; workspace privacy is not a promise that only one person can see them.</p>
            <p>Joining the community is a separate choice. A saved programme or collected checklist does not send an application to a university.</p>
            <p>Use Export to download or delete a saved case, and Account to close your account. These are different actions. Closing an account does not erase a workspace that still has other members.</p>
            <p data-testid="privacy-operator-gap">The legal operator, privacy contact, actual database and backup locations, recipients and retention schedule must be confirmed for this deployment before this draft can be published as its final notice.</p>
            <p data-testid="privacy-consent-gap">Registration does not currently record an accepted notice version or a legal representative’s authorization. A policy page alone is not evidence of consent.</p>
          </div>
        </Panel>

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
              session is an opaque random token; no applicant profile is placed in the session cookie. The browser also stores local drafts, case pointers, theme preferences and document ticks; those are not encrypted storage.
              An append-only audit trail records identifiers, actions and operation details, which can include error text or payment metadata. It is not a guarantee that every stored error is free of personal data. Logs require access, minimization and retention controls; identifiers are not anonymous data.
            </p>
            <p>
              <strong>The community is public, and it is the only part that is.</strong>{' '}
              The applicant case is shared inside its workspace rather than public. The community is different: if you create
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
              <strong>A picture, if you add one.</strong> It is stored here rather than anywhere
              else, and served only to signed-in applicants. Before it is stored, the metadata is
              stripped — a photograph taken on a phone records where it was taken, and that is not
              something to publish alongside a school leaver&apos;s name. Nothing is inferred from
              the image: it is not scanned, matched against anything, or used to identify you.
            </p>
            <p>
              <strong>Private messages.</strong> Conversations are stored so both people can read
              them, and are visible to nobody else through ordinary conversation endpoints — with one exception, which exists so that
              harassment can be dealt with: either person in a conversation can report a message,
              and reporting it shows that message to a moderator. Who may write to you first is
              your setting, and it starts narrow. Messages are not end-to-end encrypted: authorized operators with database access can technically access stored content. Leaving the community is not the same as deleting the account or a conversation.
            </p>
            <p>
              <strong>What leaves the service.</strong> University-page reads and configured search-provider queries use privacy-validated programme, degree, intake and public audience context, which may derive from your preferences. The normal query contract excludes the full profile, identity, contact details, grades and budget; it is not a promise that every query is anonymous. The fetcher honours robots.txt, reads nothing behind a login and bypasses no CAPTCHA. If password-reset email is enabled, your email address and reset message reach the configured mail provider. If you choose a payment, the payment provider receives the information required for that transaction; a masked phone in our database does not mean the provider received only a masked phone. Hosting and network operators can process connection metadata. Their actual identities, countries and retention terms must be disclosed by this deployment. No advertising or analytics SDK is present in the reviewed application source; that is not a verification of every deployed infrastructure log.
            </p>
            <p>
              <strong>What you can do with it.</strong> Export the case record the API makes available as JSON, and delete a case or your account. The case export is not an export of every account, payment, community or operational record. Account deletion erases workspaces where you are the only member; a shared workspace and its cases remain for its other members. A deletion error must not be reported as success. Security audit records, operational job records, recipients’ copies and backups require their own retention and deletion review; deleting a live case is not proof that every copy everywhere disappeared.
            </p>
            <p>
              <strong>How long it is kept.</strong> The current application has deletion controls but no universal automatic expiry for every data class. The operator must publish a purpose-based retention schedule for profiles, account records, payments, audit/job records and backups, and demonstrate that it is applied. Backup settings and a planned deletion procedure are not evidence that a backup was actually erased. Exports you download remain on your device until you remove them.
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
              <strong>Service limits and your rights.</strong> Published pages, estimates and extraction can be incomplete or wrong. Check a material deadline, fee or condition before acting. The MIT licence applies to the source code; it does not remove any mandatory consumer or personal-data rights you have when using an operated service. Paid-service terms, refund rules and the responsible operator must be supplied before a purchase; this draft does not invent them.
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
              account. There is a reporting button on posts, answers, messages and profiles, and a
              queue that a moderator named by this deployment works from. There is no automated
              filtering and no alert when a report arrives, so how soon anything happens depends
              on a person opening the queue. If you need something to stop now rather than soon,
              blocking is the tool that works without waiting for anybody.
            </p>
          </div>
        </Panel>
        <Panel title="Community guidelines (draft)">
          <div className="stack stack--tight small">
            <p>Share your own experience and treat other students respectfully. Do not post another person&apos;s private information, impersonate anyone, harass others, or present a rumour about university requirements as official fact.</p>
            <p>Posts, replies, messages and profiles can be reported. Moderators review reports manually; urgent unwanted contact can be blocked immediately.</p>
            <p>Community experiences are personal opinions, not official university information. Confirm admissions, cost and scholarship facts against the linked official sources in your research results.</p>
          </div>
        </Panel>
        <Panel title="Data processing (draft)">
          <div className="stack stack--tight small">
            <p>Your applicant case and research evidence are accessible within your workspace; this is organization-level access. Public community information is created separately and only when you choose to join.</p>
            <p>Research reads public university sources using a bounded, privacy-validated target that may derive from degree, field and intake preferences, without a full applicant profile, identity, grades or budget in the normal query contract. The case record available from the API can be exported; case and account deletion have the separate scope explained above.</p>
            <p data-testid="privacy-ai-boundary">The transcript endpoint parses PDFs locally into suggestions. Configuration also supports an optional TypeSafe decision capability using programme information and public link state; an active product call path was not established by this source audit. A research privacy setting does not prove profile-aware AI processing, consent or a no-training contract. Before adding one, disclose its input fields, recipients, retention and training terms and obtain any required authorization.</p>
            <p>These statements describe reviewed source behavior. They still require legal review and deployment evidence, especially localization, international transfers and minors. No certification, penetration-test result or legal compliance is claimed.</p>
          </div>
        </Panel>
      </div>
    </>
  );
}
