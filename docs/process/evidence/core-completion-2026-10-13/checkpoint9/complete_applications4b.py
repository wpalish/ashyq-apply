from pathlib import Path
import json
root=Path(__file__).resolve().parent;repo=root.parents[1]/'work/unimatch-calendar-materials';out=root/'applications4b-proposal'
p=out/'frontend/src/screens/ApplicationsPanel.tsx';t=p.read_text().replace("'documents.savePersonal'","'documents.save'").replace("'documents.noHistory'","'applications.noHistory'");p.write_text(t)
p=out/'frontend/src/types/admissionsActions.ts';t=p.read_text();t=t.replace("      || JSON.stringify(apps[0].details) !== JSON.stringify(request.details)) return false;", "      || !samePersonalDetails(apps[0].details, request.details)) return false;")
marker='function sameManualTarget('
helper='''function samePersonalDetails(actual: unknown, expected: ActionPersonalDetailsV1): boolean {
  if (!object(actual) || actual.notes !== expected.notes) return false;
  if (actual.due === null || expected.due === null) return actual.due === null && expected.due === null;
  return object(actual.due) && actual.due.origin === expected.due.origin && actual.due.local_date === expected.due.local_date
    && actual.due.timezone === expected.due.timezone && actual.due.official_deadline === expected.due.official_deadline;
}
'''
t=t.replace(marker,helper+marker,1);p.write_text(t)
p='frontend/src/screens/ApprovedScreen.tsx';t=(repo/p).read_text().replace("import { Chip,", "import { ApplicationsPanel } from './ApplicationsPanel';\nimport { Chip,",1).replace('const { results, run, collectDocuments, decide } = useStore();','const { results, run, savedProfile, collectDocuments, decide } = useStore();').replace('if (results.length === 0) return (\n    <Panel',"if (results.length === 0) return (\n    <>\n    {savedProfile && <ApplicationsPanel />}\n    <Panel",1).replace('    </Panel>\n  );','    </Panel>\n    </>\n  );',1).replace('<div className="stack stack--loose">','<div className="stack stack--loose">\n        {savedProfile && <ApplicationsPanel />}',1);q=out/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(t)
keys={
 'title':['Your saved applications','Ваши сохранённые заявки','Сақталған өтінімдеріңіз'],
 'hint':['Applications work without research or an exam course. Plans and declarations are your personal records.','Заявки работают без исследования и экзаменационного курса. Планирование и заявления о подаче — ваши личные записи.','Өтінімдер зерттеу мен емтихан курсынсыз жұмыс істейді. Жоспарлар мен жіберу туралы мәлімдемелер — жеке жазбаларыңыз.'],
 'empty':['No saved applications yet. You can add one manually.','Сохранённых заявок пока нет. Добавьте заявку вручную.','Сақталған өтінімдер жоқ. Өтінімді қолмен қосуға болады.'],
 'add':['Add an application','Добавить заявку','Өтінім қосу'],
 'planning':['Planning','Планирую','Жоспарлап жатырмын'],
 'preparing':['Preparing','Готовлю','Дайындап жатырмын'],
 'submitted':['Submission · declared by you','Подача · по вашему заявлению','Жіберілді · өз мәлімдемеңіз'],
 'withdrawn':['Withdrawal · declared by you','Отзыв · по вашему заявлению','Кері қайтарылды · өз мәлімдемеңіз'],
 'unknown':['Unknown','Неизвестно','Белгісіз'],
 'context':['Your entered context','Указанный вами контекст','Сіз енгізген мәнмәтін'],
 'label':['Application name','Название заявки','Өтінім атауы'],
 'target':['Programme reference','Связь с программой','Бағдарламамен байланыс'],
 'manual':['Enter manually · requirements unverified','Вручную · требования не проверены','Қолмен енгізу · талаптар тексерілмеген'],
 'university':['University, as entered by you','Университет, как вы его указали','Өзіңіз енгізген университет'],
 'programme':['Programme, if known','Программа, если известна','Бағдарлама, белгілі болса'],
 'purpose':['Application purpose','Цель заявки','Өтінім мақсаты'],
 'admission':['Admission','Поступление','Оқуға түсу'],
 'scholarship':['Scholarship','Стипендия','Стипендия'],
 'award':['Scholarship name, if known','Название стипендии, если известно','Стипендия атауы, белгілі болса'],
 'intake':['Intake, if known','Набор, если известен','Қабылдау кезеңі, белгілі болса'],
 'route':['Application route, if known','Способ подачи, если известен','Өтінім беру тәсілі, белгілі болса'],
 'programmeLink':['Programme information · destination unverified','Страница программы · адрес не проверен','Бағдарлама туралы ақпарат · мекенжай тексерілмеген'],
 'requirementsUnknown':['Current official requirements are not confirmed here. Your saved application remains available.','Текущие официальные требования здесь не подтверждены. Сохранённая заявка остаётся доступной.','Мұнда қазіргі ресми талаптар расталмаған. Сақталған өтініміңіз қолжетімді.'],
 'declareSubmission':['Record my submission statement','Записать моё заявление о подаче','Жіберу туралы мәлімдемемді сақтау'],
 'declareWithdrawal':['Record my withdrawal statement','Записать моё заявление об отзыве','Кері қайтару туралы мәлімдемемді сақтау'],
 'declarationHint':['This records what you say happened. It does not send an application, verify university receipt or create an offer.','Это запись события с ваших слов. Она не отправляет заявку, не подтверждает её получение университетом и не создаёт оффер.','Бұл сіз хабарлаған оқиғаны жазады. Өтінімді жібермейді, университеттің алғанын растамайды және қабылдау ұсынысын жасамайды.'],
 'eventTime':['Your event time, if known','Время вашего события, если известно','Оқиға уақыты, белгілі болса'],
 'channel':['Submission channel, as entered by you','Канал подачи, как вы его указали','Өзіңіз енгізген жіберу арнасы'],
 'reference':['Your receipt or reference, if available','Ваш номер или подтверждение, если есть','Растама немесе нөміріңіз, бар болса'],
 'confirm':['I reviewed these personal details and confirm this is my own record.','Я проверил(а) эти сведения и подтверждаю, что это моя личная запись.','Бұл мәліметтерді тексердім және жеке жазбам екенін растаймын.'],
 'replacement':['Corrected personal statement','Исправленное личное заявление','Түзетілген жеке мәлімдеме'],
 'serverEvent':['Recorded by the server','Записано сервером','Серверде жазылды'],
 'correct':['Correct this declaration','Исправить это заявление','Бұл мәлімдемені түзету'],
 'moreHistory':['Next history page','Следующая страница истории','Тарихтың келесі беті'],
 'noHistory':['No events for this application on this history page.','На этой странице истории нет событий по заявке.','Бұл тарих бетінде өтінімге қатысты оқиғалар жоқ.'],
}
p='frontend/src/lib/i18n.ts';t=(repo/p).read_text()
for name,i in [('EN',0),('RU',1),('KK',2)]:
 marker='const '+name+(' = {' if name=='EN' else ': Partial<Record<MessageKey, string>> = {')
 block='\n'+''.join('  '+json.dumps('applications.'+k)+': '+json.dumps(v[i],ensure_ascii=False)+',\n' for k,v in keys.items())
 assert marker in t;t=t.replace(marker,marker+block,1)
q=out/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(t)
print('Application form and three dictionaries completed as external proposals only.')
