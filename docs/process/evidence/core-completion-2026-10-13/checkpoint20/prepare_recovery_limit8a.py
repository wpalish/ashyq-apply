from pathlib import Path
import hashlib,json
s=Path(__file__).resolve().parent;r=s.parents[1]/'work/unimatch-calendar-materials';paths=['frontend/src/components/AdmissionsRecoveryPanel.tsx','frontend/src/components/AdmissionsRecoveryPanel.test.tsx'];m={}
for p in paths:
 raw=(r/p).read_bytes();m[p]=hashlib.sha256(raw).hexdigest()
 for name in ['recovery8a-preimages','recovery8a-proposal']:
  q=s/name/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(raw)
p=s/'recovery8a-proposal'/paths[0];t=p.read_text();old="  const selectable = selected.filter(uuid => acknowledged.some(entry => entry.descriptor.client_write_uuid === uuid));";assert old in t;t=t.replace(old,old+"\n  // A full valid journal may replay existing requests or clear selected ACKs.\n  // Corruption/ownership failures remain blocked; the command layer revalidates.\n  const recoveryUnavailable = controller.journalError !== null && controller.journalError !== 'limit';");assert t.count('controller.sending || controller.journalError !== null')==3;t=t.replace('controller.sending || controller.journalError !== null','controller.sending || recoveryUnavailable');p.write_text(t)
p=s/'recovery8a-proposal'/paths[1];p.write_text(p.read_text()+'''
+it('keeps selected confirmed cleanup and original retry available at a valid capacity limit', async () => {
+  const model = await controller(); render(<AdmissionsRecoveryPanel controller={{ ...model, journalError: 'limit' }} />);
+  expect(screen.getByRole('button', { name: 'Retry original request' })).toBeEnabled();
+  expect(screen.getByRole('checkbox')).toBeEnabled();
+  fireEvent.click(screen.getByRole('checkbox'));
+  const clean = screen.getByRole('button', { name: 'Clear selected local confirmations' });
+  expect(clean).toBeEnabled(); fireEvent.click(clean);
+  await waitFor(() => expect(model.clearAcknowledged).toHaveBeenCalledWith([FIXTURE_UUID]));
+});
+'''.replace('\n+','\n'))
(s/'RECOVERY_8A_PREPARATION.json').write_text(json.dumps({'status':'EXTERNAL_ONLY_NOT_GRANTED_NOT_APPLIED','paths':m,'finding':'Source review: journal reserve limit disables all ACK checkboxes and cleanup, although raw current journal is valid64 and lower layer revalidates exactserver ACK before removal. Native8 currently running first real physical64 control; require original failure/cleanup before applying source fix.','scope':'Allow recovery only for explicit limit alongside null; invalid/ownership/drift stay blocked. No allocation/auto retry/delete change; underlying own server receipt/index/fence/hash checks unchanged.'},indent=2)+'\n');print('External-only limit recovery proposal prepared.')
