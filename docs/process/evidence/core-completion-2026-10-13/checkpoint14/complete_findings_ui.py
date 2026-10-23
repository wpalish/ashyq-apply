from pathlib import Path
import json,hashlib
s=Path(__file__).resolve().parent;b=s.parents[1];repo=b/'work/unimatch-calendar-materials';out=s/'findings5-proposal';out.mkdir(exist_ok=False)
# Compose disjoint reviewed proposals. The exact current grant comes after inspection, not from stale hashes.
for directory in ['billing4e-proposal','dates5b-proposal']:
 for p in (s/directory).rglob('*'):
  if p.is_file():q=out/p.relative_to(s/directory);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes())
def get(p):return(out/p).read_text()
def put(p,t):q=out/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(t)
rows=[
('billing.accessUnknown','Access not confirmed','Доступ не подтверждён','Қолжетімділік расталмады'),
('billing.accessReadFailure','Could not confirm access for this case. Refresh to try again.','Не удалось подтвердить доступ для этого дела. Обновите сведения.','Бұл іс үшін қолжетімділікті растау мүмкін болмады. Мәліметтерді жаңартыңыз.'),
('billing.accessMismatch','The access response did not match this case.','Ответ о доступе не соответствует текущему делу.','Қолжетімділік жауабы қазіргі іске сәйкес емес.'),
('billing.personalUngated','Research access does not restrict your personal document tasks and application history.','Доступ к исследованию не ограничивает личные задачи по документам и историю заявок.','Зерттеуге қолжетімділік жеке құжат тапсырмалары мен өтініштер тарихын шектемейді.'),
('billing.refreshBeforeAction','Refresh access before using a subscription case or starting payment.','Обновите доступ перед использованием дела из подписки или началом оплаты.','Жазылымдағы істі пайдаланбас не төлемді бастамас бұрын қолжетімділікті жаңартыңыз.'),
('billing.refreshAccess','Refresh access','Обновить доступ','Қолжетімділікті жаңарту'),
('dates.earlier','Earlier calendar date','Предыдущая календарная дата','Өткен күнтізбелік күн'),
('dates.zoneUnknown','Time zone unknown','Часовой пояс неизвестен','Уақыт белдеуі белгісіз'),
('dates.closureUnknown','Closing time not confirmed','Время закрытия не подтверждено','Жабылу уақыты расталмаған'),
('dates.sourceDateHint','A calendar date does not establish the closing time.','Календарная дата не определяет время закрытия.','Күнтізбелік күн жабылу уақытын анықтамайды.'),
('dates.timelineHint','Calendar dates have no confirmed closing time here. An unknown time zone prevents a precise expiry comparison.','Для этих календарных дат время закрытия не подтверждено. Неизвестный часовой пояс не позволяет точно определить просроченность.','Бұл күнтізбелік күндер үшін жабылу уақыты расталмаған. Белгісіз уақыт белдеуі мерзімнің өткенін дәл анықтауға мүмкіндік бермейді.'),
('dates.closest','Closest recorded date:','Ближайшая записанная дата:','Ең жақын тіркелген күн:'),
('dates.noCurrent','No current admission date is confirmed here. Review the original programme requirements.','Текущая дата поступления здесь не подтверждена. Проверьте исходные требования программы.','Қазіргі қабылдау күні мұнда расталмаған. Бағдарламаның бастапқы талаптарын тексеріңіз.')]
p='frontend/src/lib/i18n.ts';t=(repo/p).read_text();markers=['const EN = {','const RU: Partial<Record<MessageKey, string>> = {','const KK: Partial<Record<MessageKey, string>> = {']
# Existing locale declarations differ in exact annotation; derive from their real source.
import re
for i,name in enumerate(['EN','RU','KK'],1):
 m=re.search(r'const '+name+r'[^\n]*\{',t);assert m,name
 pos=m.end();t=t[:pos]+'\n'+''.join('  '+json.dumps(row[0],ensure_ascii=False)+': '+json.dumps(row[i],ensure_ascii=False)+',\n' for row in rows)+t[pos:]
put(p,t)
p='frontend/src/screens/BillingScreen.tsx';t=get(p)
for literal,key in [('Access not confirmed','billing.accessUnknown'),('Could not confirm access for this case. Refresh to try again.','billing.accessReadFailure'),('The access response did not match this case.','billing.accessMismatch'),('Research access does not restrict your personal document tasks and application history.','billing.personalUngated'),('Refresh access before using a subscription case or starting payment.','billing.refreshBeforeAction')]:t=t.replace("'"+literal+"'", "t('"+key+"')")
t=t.replace('>Refresh access</button>', ">{t('billing.refreshAccess')}</button>")
# Translation t identity changes with locale, so callback reads the current stable catalogue function directly.
t=t.replace("import { useTranslation }", "import { t as translate } from '@/lib/i18n';\nimport { useTranslation }",1)
t=t.replace("t('billing.accessReadFailure')", "translate('billing.accessReadFailure')").replace("t('billing.accessMismatch')", "translate('billing.accessMismatch')")
put(p,t)
p='frontend/src/screens/ApprovedScreen.tsx';t=get(p).replace('`Closest recorded date: ${nextDeadline.university}`',"`${t('dates.closest')} ${nextDeadline.university}`").replace("'No current admission date is confirmed here. Review the original programme requirements.'", "t('dates.noCurrent')")
t=t.replace('A calendar date does not establish the closing time. {nextDeadline.admission_deadline_timezone ?? \'Time zone unknown.\'}',"{t('dates.sourceDateHint')} {nextDeadline.admission_deadline_timezone ?? t('dates.zoneUnknown')}");put(p,t)
p='frontend/src/screens/DocumentsScreen.tsx';t=get(p).replace('>Earlier calendar date</Chip>', ">{t('dates.earlier')}</Chip>").replace('Calendar dates have no confirmed closing time here. An unknown time zone prevents a precise expiry comparison.', "{t('dates.timelineHint')}");put(p,t)
p='frontend/src/screens/ShortlistScreen.tsx';t=get(p).replace("import { useStore }", "import { useTranslation } from '@/lib/useTranslation';\nimport { useStore }",1);t=t.replace("export function ShortlistScreen({ onStart, onProgress }: { onStart?: () => void; onProgress?: () => void }) {", "export function ShortlistScreen({ onStart, onProgress }: { onStart?: () => void; onProgress?: () => void }) {\n  const { t } = useTranslation();",1).replace('>Earlier calendar date</Chip>', ">{t('dates.earlier')}</Chip>").replace('>Time zone unknown</div>', ">{t('dates.zoneUnknown')}</div>");put(p,t)
p='frontend/src/components/ResultDetail.tsx';t=get(p).replace("import { useState }", "import { useTranslation } from '@/lib/useTranslation';\nimport { useState }",1).replace('function Requirements({ result }: { result: ProgramResult }) {', 'function Requirements({ result }: { result: ProgramResult }) {\n  const { t } = useTranslation();',1).replace('>Earlier calendar date</Chip>', ">{t('dates.earlier')}</Chip>").replace("Closing time not confirmed{!result.admission_deadline_timezone ? ' · time zone unknown' : ''}.", "{t('dates.closureUnknown')}{!result.admission_deadline_timezone ? ` · ${t('dates.zoneUnknown')}` : ''}.");put(p,t)
paths={};h=lambda raw:hashlib.sha256(raw).hexdigest()
for p in out.rglob('*'):
 if p.is_file():rel=str(p.relative_to(out));f=repo/rel;pre=h(f.read_bytes()) if f.exists() else None;paths[rel]={'preimage':pre,'postimage':h(p.read_bytes())};q=s/'findings5-preimages'/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(f.read_bytes()) if f.exists() else None
(s/'FINDINGS_5_PREPARATION.json').write_text(json.dumps({'status':'EXTERNAL_PROPOSAL_ROOT_REVIEW_PENDING_NOT_GRANTED','paths':paths,'scope':'LocalDate/Instant display and known-zone date comparison; current Billing read/payment/quota case generation fencing; explicit unknown access on failures; exact EN/RU/KK keys. No backend/API/provider/payment protocol changes. Native FE gates and backend640 byte carry required.'},indent=2)+'\n')
print(len(paths),'external finding proposal paths with three locales, not applied.')
