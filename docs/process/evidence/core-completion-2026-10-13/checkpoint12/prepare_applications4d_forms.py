from pathlib import Path
import json
r=Path(__file__).resolve().parent; pre=r/'applications4d-preimages';out=r/'applications4d-proposal'
def get(p):return(pre/p).read_text()
def put(p,t):q=out/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(t)
p='frontend/src/screens/PersonalDocumentsPanel.tsx';t=get(p)
t=t.replace('ActionRequestV1,','ActionRequest,').replace("'new' | 'details' | 'report'", "'new' | 'details' | 'report' | 'remove'")
t=t.replace('applicationId: string; notes:', 'applicationId: string; dependencies: string[]; notes:')
t=t.replace("applicationId: task?.application_id ?? '', notes:", "applicationId: task?.application_id ?? '', dependencies: [...(task?.personal.depends_on_task_ids ?? [])], notes:")
t=t.replace("(draft.mode === 'report' && !draft.confirmed)","(draft.mode !== 'new' && !draft.confirmed)")
t=t.replace('let body: ActionRequestV1;', 'let body: ActionRequest;').replace('depends_on_task_ids: []','depends_on_task_ids: captured.dependencies')
t=t.replace("else if (captured.mode === 'details' && captured.taskId) body = { ...base, kind: 'set_personal_details',\n        target: { kind: 'document_task', id: captured.taskId }, details };", """else if (captured.mode === 'details' && captured.taskId) body = { ...base, schema_version: 'admissions-actions-v2', kind: 'set_personal_details', operation: 'document_metadata',
        target: { kind: 'document_task', id: captured.taskId }, application_id: captured.applicationId || null,
        personal: { label: captured.label, responsible_actor: captured.responsible, details, depends_on_task_ids: captured.dependencies }, confirmed_personal_metadata: true };
      else if (captured.mode === 'remove' && captured.taskId) body = { ...base, schema_version: 'admissions-actions-v2', kind: 'remove_personal_action',
        target: { kind: 'document_task', id: captured.taskId }, confirmed_personal_removal: true };""")
t=t.replace("if (outcome.accepted) setDraft(old => old === pending ? null : old);", """if (outcome.accepted) {
        setDraft(old => old === pending ? null : old);
        if (captured.mode === 'remove' && captured.taskId && await actions.loadHistory() && liveKey.current === captured.caseKey)
          setHistoryTask({ key: captured.caseKey, id: captured.taskId });
      }""",1)
t=t.replace("onClick={() => open('details', task)}>{t('documents.editDetails')}","onClick={() => open('details', task)}>{t('documents.editMetadata')}")
t=t.replace("onClick={() => open('report', task)}>{t('documents.updateReport')}</button>","onClick={() => open('report', task)}>{t('documents.updateReport')}</button>\n            <button type=\"button\" className=\"btn btn--ghost\" disabled={!canEdit} onClick={() => open('remove', task)}>{t('actions.removePersonal')}</button>")
t=t.replace("{draft.mode === 'new' && <>","{(draft.mode === 'new' || draft.mode === 'details') && <>",1)
t=t.replace("        </>}\n        {draft.mode !== 'report' ? <>","""          <fieldset className="stack"><legend>{t('documents.dependencies')}</legend>
            {tasks.filter(task => task.id !== draft.taskId).map(task => <label className="row" key={task.id}><input type="checkbox" checked={draft.dependencies.includes(task.id)} onChange={event => change({ dependencies: event.target.checked ? [...draft.dependencies, task.id] : draft.dependencies.filter(id => id !== task.id) })} />{task.personal.label}</label>)}
            {draft.dependencies.filter(id => !tasks.some(task => task.id === id)).map(id => <label className="row" key={id}><input type="checkbox" checked onChange={() => change({ dependencies: draft.dependencies.filter(item => item !== id) })} />{t('documents.missingDependency')}</label>)}
          </fieldset>
        </>}
        {draft.mode === 'remove' ? <Notice kind="warn">{t('actions.removalHint')}</Notice> : draft.mode !== 'report' ? <>""",1)
t=t.replace('          <label className="row"><input type="checkbox" checked={draft.confirmed} onChange={event => change({ confirmed: event.target.checked })} />{t(\'documents.confirmReport\')}</label>\n','',1)
t=t.replace("        <label className=\"stack stack--tight\">{t('documents.timezone')}","        {draft.mode !== 'remove' && <><label className=\"stack stack--tight\">{t('documents.timezone')}",1)
t=t.replace("<p className=\"small muted\">{t('documents.dateHint')}</p>","""<p className="small muted">{t('documents.dateHint')}</p></>}
        {draft.mode !== 'new' && <label className="row"><input type="checkbox" checked={draft.confirmed} onChange={event => change({ confirmed: event.target.checked })} />{t(draft.mode === 'report' ? 'documents.confirmReport' : draft.mode === 'remove' ? 'actions.confirmRemoval' : 'documents.confirmMetadata')}</label>}""",1)
t=t.replace("{' · '}{'personal' in event.request ? event.request.personal.label : t('documents.personalChange')}","""{' · '}{event.applied_delta.removed_document_task ? `${t('actions.removedPersonal')}: ${event.applied_delta.removed_document_task.personal.label}` : 'personal' in event.request ? event.request.personal.label : t('documents.personalChange')}""",1)
put(p,t)
p='frontend/src/screens/ApplicationsPanel.tsx';t=get(p)
t=t.replace("'new' | 'details' | 'submission'", "'new' | 'details' | 'context' | 'remove' | 'submission'",1)
t=t.replace('appId: string | null; label:','appId: string | null; awardId: string | null; label:',1)
t=t.replace("mode, appId: app?.id ?? null,", "mode, appId: app?.id ?? null, awardId: target?.award_id ?? null,",1)
t=t.replace("award: '', purpose:","award: target && 'award' in target && target.award.state === 'applicant_entered' ? target.award.value : '', purpose:",1)
t=t.replace("zone: mode === 'details' ?", "zone: mode === 'details' || mode === 'context' ?",1)
t=t.replace("if (captured.mode === 'new') {", "if (captured.mode === 'new' || captured.mode === 'context') {",1)
t=t.replace("if (!selectedResults.some(result => result.id === captured.resultId)) throw new Error('Target changed');", """const retained = applications.find(app => app.id === captured.appId)?.target;
          if (!selectedResults.some(result => result.id === captured.resultId) && !(captured.mode === 'context' && retained?.result_id === captured.resultId)) throw new Error('Target changed');""",1)
t=t.replace("target: { result_id: captured.resultId, purpose: 'admission', award_id: null,", "target: { result_id: captured.resultId, purpose: captured.purpose, award_id: captured.awardId,",1)
t=t.replace("      } else if (captured.mode === 'details'", """        if (captured.mode === 'context' && captured.appId) body = { ...base, schema_version: 'admissions-actions-v2', kind: 'set_personal_details',
          operation: 'application_context', target: { kind: 'application', id: captured.appId }, application_target: body.target,
          label: captured.label, details, confirmed_personal_context: true };
      } else if (captured.mode === 'remove' && captured.appId) body = { ...base, schema_version: 'admissions-actions-v2', kind: 'remove_personal_action',
        target: { kind: 'application', id: captured.appId }, confirmed_personal_removal: true };
      else if (captured.mode === 'details'""",1)
t=t.replace("if (outcome.accepted) setDraft(old => old === pending ? null : old);", """if (outcome.accepted) {
        setDraft(old => old === pending ? null : old);
        if (captured.mode === 'remove' && captured.appId && await actions.loadHistory() && liveKey.current === captured.caseKey)
          setHistoryFor({ key: captured.caseKey, id: captured.appId });
      }""",1)
t=t.replace("const declarationForm = draft !== null && draft.mode !== 'new' && draft.mode !== 'details';", """const declarationForm = draft?.mode === 'submission' || draft?.mode === 'withdrawal' || draft?.mode === 'correction';
  const declaredContext = draft?.mode === 'context' && applications.some(app => app.id === draft.appId && (app.status === 'submitted_declared' || app.status === 'withdrawn_declared'));
  const removalHasLinks = draft?.mode === 'remove' && tasks.some(task => task.application_id === draft.appId);""")
t=t.replace("onClick={() => open('details', app)}>{t('documents.editDetails')}</button>","""onClick={() => open('details', app)}>{t('documents.editDetails')}</button>
              <button type="button" className="btn" disabled={!canEdit} onClick={() => open('context', app)}>{t('applications.editContext')}</button>
              <button type="button" className="btn" disabled={!canEdit} onClick={() => open('remove', app)}>{t('actions.removePersonal')}</button>""",1)
t=t.replace("{draft.mode === 'new' && <>","{(draft.mode === 'new' || draft.mode === 'context') && <>",1)
t=t.replace("          <label className=\"stack stack--tight\">{t('applications.target')}","""          {draft.mode === 'context' && <Notice kind="warn">{t('applications.contextReviewHint')}</Notice>}
          <fieldset className="stack" disabled={declaredContext} style={{ border: 0, margin: 0, padding: 0, minWidth: 0 }}>
          {declaredContext && <p className="small">{t('applications.declaredContextLocked')}</p>}
          <label className="stack stack--tight">{t('applications.target')}""",1)
t=t.replace("resultId: event.target.value, purpose: 'admission', award: ''", "resultId: event.target.value, purpose: 'admission', award: '', awardId: null",1)
t=t.replace("<option value=\"\">{t('applications.manual')}</option>{selectedResults.map", """<option value="">{t('applications.manual')}</option>
            {draft.resultId && !selectedResults.some(result => result.id === draft.resultId) && <option value={draft.resultId}>{t('applications.retainedReference')}</option>}{selectedResults.map""",1)
t=t.replace("{t('applications.route')}<input maxLength={200} value={draft.route} onChange={event => change({ route: event.target.value })} /></label>\n        </>}","{t('applications.route')}<input maxLength={200} value={draft.route} onChange={event => change({ route: event.target.value })} /></label>\n          </fieldset>\n        </>}",1)
t=t.replace("{declarationForm ? <>","{draft.mode === 'remove' ? <><Notice kind=\"warn\">{t('actions.removalHint')}</Notice>{removalHasLinks && <Notice kind=\"warn\">{t('applications.removalHasLinks')}</Notice>}</> : declarationForm ? <>",1)
t=t.replace("        <label className=\"stack stack--tight\">{t('documents.timezone')}","        {draft.mode !== 'remove' && <><label className=\"stack stack--tight\">{t('documents.timezone')}",1)
t=t.replace("value={draft.notes} onChange={event => change({ notes: event.target.value })} /></label>\n        {draft.mode !== 'details'", "value={draft.notes} onChange={event => change({ notes: event.target.value })} /></label></>}\n        {draft.mode !== 'details'",1)
t=t.replace("{t('applications.confirm')}</label>","{t(draft.mode === 'remove' ? 'actions.confirmRemoval' : 'applications.confirm')}</label>",1)
t=t.replace("disabled={!canEdit || draft.attempted || (draft.mode !== 'details' && !draft.confirmed)}", "disabled={!canEdit || draft.attempted || removalHasLinks || (draft.mode !== 'details' && !draft.confirmed)}",1)
t=t.replace("<p>{t(statusKeys[event.applied_delta.applications[0]?.status ?? 'planning'])}</p>","""{event.applied_delta.removed_application ? <p>{t('actions.removedPersonal')}: {event.applied_delta.removed_application.label}</p>
          : <p>{t(statusKeys[event.applied_delta.applications[0]?.status ?? 'planning'])}</p>}""",1)
put(p,t)
keys=[
('documents.editMetadata','Edit document details','Изменить сведения документа','Құжат мәліметтерін өзгерту'),
('documents.confirmMetadata','I confirm these personal details; previous reports and requirement references remain in history.','Подтверждаю личные сведения; прежние отметки и ссылки на требования сохраняются в истории.','Жеке мәліметтерді растаймын; бұрынғы белгілер мен талап сілтемелері тарихта сақталады.'),
('documents.dependencies','Tasks to prepare first','Что подготовить сначала','Алдымен дайындайтын тапсырмалар'),
('documents.missingDependency','Earlier task is unavailable · uncheck to remove this dependency','Прежняя задача недоступна · снимите отметку, чтобы убрать зависимость','Бұрынғы тапсырма қолжетімсіз · тәуелділікті жою үшін белгіні алып тастаңыз'),
('actions.removePersonal','Remove personal record','Удалить личную запись','Жеке жазбаны жою'),
('actions.removedPersonal','Personal record removed','Личная запись удалена','Жеке жазба жойылды'),
('actions.confirmRemoval','I confirm removal of this personal record.','Подтверждаю удаление этой личной записи.','Осы жеке жазбаны жоюды растаймын.'),
('actions.removalHint','This removes your active personal record. Its history remains. It does not withdraw an application at a university or delete an uploaded file.','Будет удалена ваша активная личная запись; история сохранится. Это не отзыв заявки в университете и не удаление загруженного файла.','Белсенді жеке жазбаңыз жойылады, тарихы сақталады. Бұл университеттегі өтінішті қайтарып алу немесе жүктелген файлды жою емес.'),
('applications.editContext','Edit application context','Изменить сведения заявки','Өтініш мәліметтерін өзгерту'),
('applications.contextReviewHint','Review programme, intake and route. Changing context keeps earlier document reports and marks them for review.','Проверьте программу, набор и способ подачи. При изменении прежние отметки документов сохранятся и потребуют пересмотра.','Бағдарламаны, қабылдауды және өтініш жолын тексеріңіз. Өзгерту бұрынғы құжат белгілерін сақтап, қайта қарауды талап етеді.'),
('applications.declaredContextLocked','A recorded submission or withdrawal belongs to this context. Correct the declaration before changing that context.','Записанная подача или отзыв относятся к этим сведениям. Сначала исправьте своё заявление, чтобы изменить их.','Тіркелген жіберу не қайтарып алу осы мәліметтерге қатысты. Өзгертпес бұрын мәлімдемеңізді түзетіңіз.'),
('applications.retainedReference','Saved programme reference · current selection unavailable','Сохранённая ссылка на программу · текущий выбор недоступен','Сақталған бағдарлама сілтемесі · қазіргі таңдау қолжетімсіз'),
('applications.removalHasLinks','First unlink or remove the linked tasks in Documents. Their reports will not be deleted automatically.','Сначала отвяжите или удалите связанные задачи в Документах. Их отметки не будут удалены автоматически.','Алдымен Құжаттарда байланысты тапсырмаларды ажыратыңыз не жойыңыз. Олардың белгілері автоматты жойылмайды.')]
p='frontend/src/lib/i18n.ts';t=get(p)
# Insert each locale alongside its existing corresponding declaration key.
for i in range(1,4):
 marker='  "applications.confirm": '+json.dumps(['I reviewed these personal details and confirm this is my own record.','Я проверил(а) эти сведения и подтверждаю, что это моя личная запись.','Бұл мәліметтерді тексердім және жеке жазбам екенін растаймын.'][i-1],ensure_ascii=False)+','
 assert marker in t
 t=t.replace(marker,marker+'\n'+''.join('  '+json.dumps(k,ensure_ascii=False)+': '+json.dumps(row[i],ensure_ascii=False)+',\n' for row in keys for k in [row[0]]),1)
put(p,t)
print('External forms and three locales prepared, source untouched.')
