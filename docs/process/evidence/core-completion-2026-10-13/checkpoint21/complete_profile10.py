from pathlib import Path
import json,hashlib
s=Path(__file__).resolve().parent;r=s.parents[1]/'work/unimatch-calendar-materials';p=s/'profile10-proposal/frontend/src/lib/store.tsx';t=p.read_text();start=t.index('  const saveProfile = useCallback(async () => {');a=t.index('      const nextCases = await api.cases();',start);end=t.index('    } catch (e) {',a)
old=t[a:end];assert 'acceptStoredProfile(saved);' in old
new='''      // Publish the confirmed profile before optional case-list metadata.
      publishProfileSave(saved, profileDraft, previousCaseKey);
      try {
        const nextCases = await api.cases();
        if (gen !== opGenRef.current) return;
        assertStoreOwner();
        setCases(nextCases);
      } catch (metadataError) {
        if (gen === opGenRef.current) fail(metadataError);
      }
''';t=t[:a]+new+t[end:]
helper='''  const publishProfileSave = useCallback((saved: StoredProfile, capturedDraft: Record<string, unknown>, previousCaseKey: string | null) => {
    acceptStoredProfile(saved);
    setLocalCaseKey(null);
    writePointer('profile', saved.id, storageScope);
    const canonicalDraft = toDraft(saved);
    setBaseline(JSON.stringify(canonicalDraft));
    setDraft(current => JSON.stringify(current) === JSON.stringify(capturedDraft) ? canonicalDraft : current);
    setDraftRestored(false);
    if (previousCaseKey !== null) clearDraftSlot(previousCaseKey, storageScope);
  }, [acceptStoredProfile, storageScope]);

''';a='  const saveProfile = useCallback(async () => {';assert t.count(a)==1;t=t.replace(a,helper+a,1)
a='[profileDraft, savedProfile, localCaseKey, fail, storageScope, assertStoreOwner, acceptStoredProfile]);';assert t.count(a)==2;t=t.replace(a,'[profileDraft, savedProfile, localCaseKey, fail, assertStoreOwner, publishProfileSave]);',1)
start=t.index('  const startRun = useCallback(');a=t.index('        const nextCases = await api.cases();',start);end=t.index('      } else {',a);old=t[a:end];assert 'acceptStoredProfile(profile);' in old
new='''        publishProfileSave(profile, profileDraft, previousCaseKey);
        try {
          const nextCases = await api.cases();
          if (gen !== opGenRef.current) return;
          assertStoreOwner();
          setCases(nextCases);
        } catch (metadataError) {
          if (gen === opGenRef.current) fail(metadataError);
        }
''';t=t[:a]+new+t[end:]
a='''        acceptStoredProfile(saved);
        const canonicalDraft = toDraft(saved);
        setBaseline(JSON.stringify(canonicalDraft));
        setDraft(current => JSON.stringify(current) === JSON.stringify(profileDraft) ? canonicalDraft : current);
        setDraftRestored(false);''';assert t.count(a)==1;t=t.replace(a,'        publishProfileSave(saved, profileDraft, saved.id);')
a='[profileDraft, savedProfile, localCaseKey, fail, storageScope, assertStoreOwner, acceptStoredProfile]);';assert t.count(a)==1;t=t.replace(a,'[profileDraft, savedProfile, localCaseKey, fail, storageScope, assertStoreOwner, publishProfileSave]);');p.write_text(t)
m=json.loads((s/'PROFILE_10_PREPARATION.json').read_text())
for rel in ['frontend/src/App.tsx','frontend/src/lib/i18n.ts']:
 raw=(r/rel).read_bytes();m['paths'][rel]=hashlib.sha256(raw).hexdigest()
 for folder in ['profile10-preimages','profile10-proposal']:
  q=s/folder/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(raw)
p=s/'profile10-proposal/frontend/src/App.tsx';t=p.read_text();a='              {cases.map((item) => (';assert t.count(a)==1;t=t.replace(a,"              {savedProfile && !cases.some(item => item.id === savedProfile.id) && <option value={savedProfile.id}>{savedProfile.display_name} · {t('topbar.caseListUnavailable')}</option>}\n"+a);p.write_text(t)
p=s/'profile10-proposal/frontend/src/lib/i18n.ts';t=p.read_text();a="  'topbar.newApplicant':";print('key matches',t.count(a))
# Locate each locale's existing topbar key, preserving its quoting/style.
lines=t.splitlines();out=[];index=0
for line in lines:
 out.append(line)
 if '"topbar.newApplicant":' in line or "'topbar.newApplicant':" in line:
  value=['List details unavailable','Сведения списка недоступны','Тізім мәліметтері қолжетімсіз'][index];index+=1
  out.append('  "topbar.caseListUnavailable": '+json.dumps(value,ensure_ascii=False)+',')
assert index==3;p.write_text('\n'.join(out)+'\n')
m['scope']+=' Confirmed save published before optional cases GET for ordinary/new-profile saves; optional metadata failure retains ACK/pointer/normalized snapshot/newer typing and known display-name fallback without invented counts. API primary write failure still propagates.';(s/'PROFILE_10_PREPARATION.json').write_text(json.dumps(m,indent=2)+'\n')
p=s/'profile10-proposal/frontend/e2e/core-research-inputs.spec.ts';t=p.read_text();a="  await page.getByTestId('save-profile').click(); const profileResponse = await saved;";assert t.count(a)==1;t=t.replace(a,"  let metadataDropped = false;\n  await page.route('**/api/cases', async route => { if (!metadataDropped) { metadataDropped = true; const actual = await route.fetch(); expect(actual.status()).toBe(200); await route.abort('failed'); } else await route.continue(); });\n"+a);a="  await page.goto('/#/preferences'); await page.getByTestId('start-research').click();";assert t.count(a)==1;t=t.replace(a,"  await expect(page.getByText('Saved', { exact: true })).toBeVisible();\n  await expect(page.getByRole('combobox', { name: 'Applicant', exact: true })).toHaveValue(profile.id);\n  await page.unroute('**/api/cases');\n"+a);t=t.replace("  await expect(page.getByText('Unsaved changes', { exact: true })).toHaveCount(0);","  await expect(page.getByTestId('save-profile')).toBeVisible();\n  expect(await page.getByText('Unsaved changes', { exact: true }).count()).toBe(0);");p.write_text(t)
print('External5 proposal completes ordinary/new save ACK before optional metadata plus existing start save; native primary assertions retained.')
