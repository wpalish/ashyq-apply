"""Offline build of reviewed official-source programme facts; no seed admission scores."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DATE='2026-10-19'
def source(url,title):return {'url':url,'title':title,'checkedAt':DATE,'method':'editorial_official_page_read'}
def fact(text,url,title,scope):return {'text':text,'source':source(url,title),'scope':scope}
OBA='https://www.ox.ac.uk/admissions/undergraduate/courses/course-listing/computer-science'
OMS='https://www.ox.ac.uk/admissions/graduate/courses/msc-advanced-computer-science'
MBA='https://www.eecs.mit.edu/academics/undergraduate-programs/curriculum/6-3-computer-science-and-engineering/'
MAD='https://mitadmissions.org/apply/firstyear/deadlines-requirements/'
MFEE='https://registrar.mit.edu/registration-academics/tuition-fees/undergraduate'
MAID='https://sfs.mit.edu/undergraduate-students/types-of-aid/mit-scholarships-grants/'
MENG='https://www.eecs.mit.edu/academics/graduate-programs/degree-programs/'
P=[]
def programme(id,uni,title,level,url,cycle,scope,**kwargs):
 row={'id':id,'universityId':uni,'title':title,'level':level,'url':url,'cycle':cycle,'scope':scope,'checkedAt':DATE,'access':'external_applicants','requirements':[],'costs':[],'funding':[],'deadlines':[],'documents':[],'unknowns':[],**kwargs};row['version']=hashlib.sha256(json.dumps(row,sort_keys=True,ensure_ascii=False).encode()).hexdigest();P.append(row);return row
scope='2027 entry; qualification and fee category must be checked individually'
programme('oxford-computer-science-ba','qs2027-004','Computer Science — BA','bachelor',OBA,'2027 entry',scope,
 requirements=[fact('A-level: A*AA; IB:39 with766 atHL, including7 inHL Mathematics. Other qualifications need an accepted equivalent. TMUA is required; Further Mathematics is expected when offered by the school.',OBA,'Oxford Computer Science',scope)],
 costs=[{'amount':66580,'currency':'GBP','period':'academic_year','population':'Overseas','academicYear':'2027–28','source':source(OBA,'Oxford Computer Science fees'),'excludes':'Living costs; later years may increase.'},{'amount':10050,'currency':'GBP','period':'academic_year','population':'Home','academicYear':'2027–28','source':source(OBA,'Oxford Computer Science fees'),'excludes':'Living costs; fee status must be established.'}],
 funding=[fact('Overseas applicants are directed to the university scholarship search. Home bursaries have income/residence conditions. An award for this applicant is not confirmed.',OBA,'Oxford Computer Science funding',scope)],
 deadlines=[{'label':'UCAS application','date':'2026-10-15','time':'18:00','timezone':'Europe/London','cycle':'2027 entry','source':source(OBA,'Oxford Computer Science application'),'scope':'All course applicants; apply in the year before entry.'}],
 documents=[fact('UCAS application and academic reference; check qualification evidence and course admissions-test steps.',OBA,'Oxford course application',scope)],
 unknowns=['Individual equivalence of the applicant’s qualification','Named overseas scholarship and award eligibility','No availability for a later entry year is inferred from this expired deadline.'])
scope='2027–28 full-time MSc; academic equivalence and language exemptions remain individual'
programme('oxford-advanced-computer-science-msc','qs2027-004','MSc in Advanced Computer Science','master',OMS,'2027–28',scope,
 requirements=[fact('First-class honours degree in computer science or mathematics, or equivalent. US bachelor’s benchmark:3.7/4.0. Mathematical and programming preparation required. No GRE/GMAT requested. IELTS Academic7.5 overall,7.0 each component; exemptions and accepted test rules apply.',OMS,'Oxford MSc entry requirements',scope)],
 costs=[{'amount':46350,'currency':'GBP','period':'academic_year','population':'Overseas','academicYear':'2027–28','source':source(OMS,'Oxford MSc annual course fees'),'excludes':'Living costs and additional personal costs.'},{'amount':20100,'currency':'GBP','period':'academic_year','population':'Home','academicYear':'2027–28','source':source(OMS,'Oxford MSc annual course fees'),'excludes':'Living costs.'}],
 funding=[fact('January-deadline applicants with a course offer are considered for Oxford scholarships; many are automatic, others require separate applications. Course funding and individual award eligibility are not guaranteed.',OMS,'Oxford MSc funding','2027–28; course funding route, not an individual award decision')],
 deadlines=[{'label':'Final application and principal scholarship consideration','date':'2027-01-06','time':'12:00','timezone':'Europe/London','cycle':'2027–28','source':source(OMS,'Oxford MSc application deadline'),'scope':'Full-time MSc; additional scholarship deadlines may differ.'}],
 documents=[fact('Зарегистрировать трёх рекомендателей; предпочтительны академические рекомендации. Оценка может начаться с двух, третью могут запросить позже.',OMS,'Oxford MSc referees',scope),fact('Официальные университетские транскрипты с оценками; для документов не на английском нужен заверенный перевод.',OMS,'Oxford MSc transcripts',scope),fact('Подготовить обязательное CV с академическими достижениями и релевантным опытом.',OMS,'Oxford MSc CV',scope),fact('Подготовить statement of purpose на английском, максимум 1000 слов: опыт, образование, научные интересы и мотивация.',OMS,'Oxford MSc statement of purpose',scope)],
 unknowns=['Named scholarship award amount and individual eligibility','Final qualification equivalence and any offer conditions'])
scope='MIT first-year admission, followed by major selection; not direct admission toCourse6-3'
programme('mit-computer-science-engineering-sb','qs2027-001','Computer Science and Engineering — SB (Course6-3)','bachelor',MBA,'First-year cycle; tuition snapshot2026–27',scope,
 requirements=[fact('First-year application, school transcript/report and two teacher recommendations. SAT orACT required; English testing is recommended for certain non-native speakers.',MAD,'MIT first-year requirements',scope)],
 costs=[{'amount':33360,'currency':'USD','period':'term','population':'Full regular undergraduate tuition','academicYear':'2026–27','source':source(MFEE,'MIT Registrar undergraduate tuition'),'excludes':'Housing, food, fees and other attendance costs. Not a2027–28 price.'}],
 funding=[fact('MIT Scholarship is need-based grant aid. Applicants who apply for aid and complete the CSS Profile are considered. The amount depends on assessed financial need.',MAID,'MIT Scholarships and grants','Undergraduate institutional aid; applicant eligibility and award not assessed')],
 deadlines=[{'label':'Early Action','date':None,'time':None,'timezone':None,'cycle':'Year not explicit on the cited page','source':source(MAD,'MIT first-year deadlines'),'scope':'Published recurring date: November1; exact year/timezone must be confirmed.'},{'label':'Regular Action','date':None,'time':None,'timezone':None,'cycle':'Year not explicit on the cited page','source':source(MAD,'MIT first-year deadlines'),'scope':'Published recurring date: January4; not converted to a guessed calendar year.'}],
 documents=[fact('Secondary School Report and transcript',MAD,'MIT first-year documents',scope),fact('Two teacher recommendations',MAD,'MIT first-year documents',scope)],
 unknowns=['Exact upcoming entry-year deadline instant','2027–28 tuition','Individual aid amount'])
programme('mit-eecs-meng','qs2027-001','Electrical Engineering and Computer Science — MEng','master',MENG,'Current programme access rule','Restricted to MIT EECS undergraduates',access='internal_only',
 requirements=[fact('MEng is restricted to MIT EECS undergraduates. The department’s SM is part of doctoral/LGO routes; this is not an externally accessible terminal CS master’s application.',MENG,'MIT EECS degree programmes','Department-specific restriction; other MIT master’s departments differ')],
 unknowns=['No external terminal-MEng application route is offered by this record','Current programme-specific tuition/funding/deadlines not collected'])
extra=ROOT/'scripts/programmes/reviewed_programme_additions.json'
if extra.exists():
 for row in json.loads(extra.read_text()):
  row['version']=hashlib.sha256(json.dumps(row,sort_keys=True,ensure_ascii=False).encode()).hexdigest();P.append(row)
names={row['id']:row['name'] for row in json.loads((ROOT/'frontend/src/data/universityDirectory.json').read_text())}
for row in P:
 row['universityName']=names[row['universityId']];row.pop('version',None);row['version']=hashlib.sha256(json.dumps(row,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
OUT=ROOT/'frontend/src/data/officialProgrammes.json';old=json.loads(OUT.read_text()) if OUT.exists() else {};current_versions={row['version'] for row in P};history={row['version']:row for row in [*old.get('history',[]),*old.get('programmes',[])] if row['version'] not in current_versions}
OUT.write_text(json.dumps({'schemaVersion':'official-programme-library-v1','builtAt':DATE,'programmes':P,'history':list(history.values()),'institutions':{id:names[id] for id in {p['universityId'] for p in P}}},ensure_ascii=False,indent=2)+'\n')
print('Reviewed programmes',len(P),'institutions',len({p['universityId'] for p in P}))
