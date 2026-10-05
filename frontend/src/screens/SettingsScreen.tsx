import { AccountMenu } from '@/components/AccountMenu';
import { api } from '@/api/client';
import { Panel } from '@/components/primitives';
import { LOCALES, type Locale } from '@/lib/i18n';

type Theme = 'system' | 'light' | 'dark';
type Destination = 'profile' | 'me' | 'export' | 'legal' | 'billing';

export function SettingsScreen({ theme, setTheme, locale, setLocale, onNavigate, onSignedOut }: {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  locale: Locale;
  setLocale: (locale: Locale) => void;
  onNavigate: (destination: Destination) => void;
  onSignedOut: () => void;
}) {
  return (
    <div className="stack stack--loose">
      <div className="screen__head">
        <p className="screen__eyebrow">ACCOUNT & PREFERENCES</p>
        <h1 className="screen__title">Make Unimatch feel like <span className="find-yellow">you.</span></h1>
        <p className="screen__lede">Manage your account, workspace and the information you choose to share.</p>
      </div>
      <div className="settings-grid">
        <Panel title="Your information" hint="Your applicant case and public community profile are separate.">
          <div className="settings-links">
            <button type="button" onClick={() => onNavigate('profile')}>Applicant profile <span>Education, scores and goals</span></button>
            <button type="button" onClick={() => onNavigate('me')}>Community profile & privacy <span>Public profile, visibility and messages</span></button>
            <button type="button" onClick={() => onNavigate('export')}>Data & exports <span>Download or delete an applicant case</span></button>
          </div>
        </Panel>
        <Panel title="Appearance & language" hint="Partial translations fall back to English.">
          <div className="grid-2">
            <label className="field"><span className="field__label">Appearance</span><select value={theme} onChange={(event) => setTheme(event.target.value as Theme)}><option value="system">System</option><option value="light">Light</option><option value="dark">Dark</option></select></label>
            <label className="field"><span className="field__label">Language</span><select value={locale} onChange={(event) => setLocale(event.target.value as Locale)}>{LOCALES.map((option) => <option key={option.id} value={option.id}>{option.label}</option>)}</select></label>
          </div>
        </Panel>
        <Panel title="Account & workspace" hint="Change your password, switch workspace or delete your account.">
          <AccountMenu initiallyOpen onSignedOut={onSignedOut} />
        </Panel>
        <Panel title="Billing & legal">
          <div className="settings-links">
            <button type="button" onClick={() => onNavigate('billing')}>Billing & access <span>Case unlocks and subscription quota</span></button>
            <button type="button" onClick={() => onNavigate('legal')}>Privacy & terms <span>Public draft documents</span></button>
          </div>
        </Panel>
        <Panel title="Notifications">
          <p className="small muted">Notification delivery and reminder preferences are planned. This deployment does not send deadline or research alerts, so there is no switch to enable yet.</p>
        </Panel>
      </div>
      <button className="btn btn--ghost" type="button" onClick={async () => { await api.logout(); onSignedOut(); }}>Sign out</button>
    </div>
  );
}
