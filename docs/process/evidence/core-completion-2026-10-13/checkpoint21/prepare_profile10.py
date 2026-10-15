from pathlib import Path
import hashlib,json
s=Path(__file__).resolve().parent;r=s.parents[1]/'work/unimatch-calendar-materials';p='frontend/src/lib/store.tsx';raw=(r/p).read_bytes()
for folder in ['profile10-preimages','profile10-proposal']:
 q=s/folder/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(raw)
f=s/'profile10-proposal'/p;t=f.read_text();old='''      } else {
        await api.updateProfile(profile.id, profileDraft);
        if (gen !== opGenRef.current) return;
      }
      assertStoreOwner();
      const requestKey = crypto.randomUUID();''';assert t.count(old)==1;t=t.replace(old,'''      } else {
        const saved = await api.updateProfile(profile.id, profileDraft);
        if (gen !== opGenRef.current) return;
        assertStoreOwner();
        // This save is durable even if the following run-start request fails.
        // Reuse the ordinary save boundary, including server normalization
        // and newer typing; do not leave the read context on an older object.
        profile = saved;
        acceptStoredProfile(saved);
        const canonicalDraft = toDraft(saved);
        setBaseline(JSON.stringify(canonicalDraft));
        setDraft(current => JSON.stringify(current) === JSON.stringify(profileDraft) ? canonicalDraft : current);
        setDraftRestored(false);
      }
      assertStoreOwner();
      const requestKey = crypto.randomUUID();''');f.write_text(t)
(s/'PROFILE_10_PREPARATION.json').write_text(json.dumps({'status':'EXTERNAL_ONLY_NOT_GRANTED_NOT_APPLIED','paths':{p:hashlib.sha256(raw).hexdigest(),'frontend/src/lib/store.startRunProfile.test.tsx':None,'frontend/e2e/core-research-inputs.spec.ts':None},'scope':'Existing-profile startRun accepts durable normalized profile after generation+owner fence before later POST; samecase identity unchanged/newer typing preserved/old run andresults survive failed POST. Store controls+actual native profile-funding edit/PUT followed by one labelled aborted run POST, own old results unchanged and read-context warning. No rerank/newnetworkprovider/reset or old STOP change.'},indent=2)+'\n');print('External existing-profile save boundary proposal prepared.')
