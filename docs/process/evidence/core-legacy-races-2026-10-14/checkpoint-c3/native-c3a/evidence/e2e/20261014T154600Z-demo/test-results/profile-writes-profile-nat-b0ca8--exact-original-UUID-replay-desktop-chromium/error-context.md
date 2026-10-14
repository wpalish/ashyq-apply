# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: profile-writes.spec.ts >> profile native lost committed create ACK: reload and exact original UUID replay
- Location: ../../../../../../2026-10-12/g3-execution/source/frontend/e2e/profile-writes.spec.ts:97:1

# Error details

```
Error: expect(locator).toContainText(expected) failed

Locator: getByRole('region', { name: 'Profile save recovery' })
Expected substring: "response was lost"
Received string:    "Keep your profile editsThe server refused this command. Your edits are still here.Command: failed. This browser tab retains the original request; it is removed on sign-out.Clear confirmed refusal and keep editsExport profile recovery for this tabClear confirmed recovery history"
Timeout: 20000ms

Call log:
  - Expect "toContainText" with timeout 20000ms
  - waiting for getByRole('region', { name: 'Profile save recovery' })
    - locator resolved to <section class="panel" aria-label="Profile save recovery">…</section>
    - unexpected value "Keep your profile editsSaving the original profile command…Command: pending. This browser tab retains the original request; it is removed on sign-out.Confirm original saveExport profile recovery for this tabClear confirmed recovery history"
    43 × locator resolved to <section class="panel" aria-label="Profile save recovery">…</section>
       - unexpected value "Keep your profile editsThe server refused this command. Your edits are still here.Command: failed. This browser tab retains the original request; it is removed on sign-out.Clear confirmed refusal and keep editsExport profile recovery for this tabClear confirmed recovery history"

```

```yaml
- region "Profile save recovery":
  - heading "Keep your profile edits" [level=2]
  - status: The server refused this command. Your edits are still here.
  - paragraph: "Command: failed. This browser tab retains the original request; it is removed on sign-out."
  - button "Clear confirmed refusal and keep edits"
  - button "Export profile recovery for this tab"
  - button "Clear confirmed recovery history"
```

# Test source

```ts
  11  |     await page.getByTestId('auth-mode-toggle').click();
  12  |     await page.getByTestId('auth-name').fill('Synthetic Profile Protocol');
  13  |     await page.getByTestId('auth-organization').fill('Synthetic Profile Workspace');
  14  |   }
  15  |   await page.getByTestId('auth-email').fill(email);
  16  |   await page.getByTestId('auth-password').fill(PASSWORD);
  17  |   await page.getByTestId('auth-submit').click();
  18  |   await expect(page.getByRole('heading',{name:'Good to see you.'})).toBeVisible();
  19  | }
  20  | async function openProfile(page: Page, id?: string) {
  21  |   await page.goto('/#/profile');
  22  |   await expect(page.getByTestId('save-profile')).toBeEnabled();
  23  |   if (id) {
  24  |     await expect(page.locator('#case-switcher')).toContainText('Demo Applicant');
  25  |     await page.locator('#case-switcher').selectOption(id);
  26  |     await expect(page.locator('#case-switcher')).toHaveValue(id);
  27  |     await expect(page.getByTestId('save-profile')).toBeEnabled();
  28  |   }
  29  | }
  30  | async function createProfile(page: Page) {
  31  |   await openProfile(page);
  32  |   await page.getByTestId('load-demo-profile').click();
  33  |   const replace = page.getByTestId('confirm-replace');
  34  |   if (await replace.isVisible().catch(()=>false)) await replace.click();
  35  |   const reply = page.waitForResponse(r=>r.request().method()==='POST' && new URL(r.url()).pathname==='/api/profiles');
  36  |   await page.getByTestId('save-profile').click();
  37  |   const response=await reply;expect(response.status()).toBe(201);
  38  |   const body=await response.json();expect(body.revision).toBe(1);expect(body.write_receipt.kind).toBe('create');
  39  |   await expect(page.getByText('Saved',{exact:true})).toBeVisible();
  40  |   return body;
  41  | }
  42  | async function pause(page:Page) {
  43  |   await page.clock.install({time:new Date('2026-10-15T10:00:00Z')});
  44  |   await page.clock.pauseAt(new Date('2026-10-15T10:00:01Z'));
  45  | }
  46  | async function update(page:Page, id:string) {
  47  |   const pending=page.waitForResponse(r=>r.request().method()==='PUT' && new URL(r.url()).pathname===`/api/profiles/${id}`);
  48  |   await page.getByTestId('save-profile').click();return pending;
  49  | }
  50  | for (const sameField of [false,true]) {
  51  |   test(`profile native ${sameField?'same-field choice/newer typing':'different-field merge'} across two real contexts`,async({page,browser},info)=>{
  52  |     test.setTimeout(180000);
  53  |     const email=`profile-${Date.now()}-${sameField}-${process.pid}@synthetic.invalid`;
  54  |     await signIn(page,email,true);const original=await createProfile(page);await pause(page);
  55  |     const otherContext=await browser.newContext();const other=await otherContext.newPage();
  56  |     try {
  57  |       await signIn(other,email);await openProfile(other,original.id);await pause(other);
  58  |       const first=page.locator('#year');await first.fill('2028');
  59  |       const accepted=await update(page,original.id);expect(accepted.status()).toBe(200);
  60  |       const saved=await accepted.json();expect(saved.revision).toBe(2);
  61  |       expect(accepted.request().headers()['x-expected-profile-revision']).toBe('1');
  62  |       expect(accepted.request().postDataJSON()).not.toHaveProperty('revision');
  63  |       if (sameField) await other.locator('#year').fill('2029');else await other.locator('#citizenship').fill('Canada');
  64  |       let release!:()=>void;const held=new Promise<void>(resolve=>{release=resolve;});
  65  |       let started!:()=>void;const reading=new Promise<void>(resolve=>{started=resolve;});
  66  |       if (sameField) await other.route(`**/api/profiles/${original.id}`,async route=>{
  67  |         if (route.request().method()!=='GET') return route.continue();
  68  |         started();await held;await route.continue();
  69  |       });
  70  |       const rejected=await update(other,original.id);expect(rejected.status()).toBe(409);
  71  |       if (sameField) {await reading;await other.locator('#year').fill('2030');release();}
  72  |       const comparison=other.getByRole('region',{name:'Profile save recovery'});
  73  |       await expect(comparison.getByText('Saved version 2.',{exact:false})).toBeVisible();
  74  |       if (sameField) {
  75  |         await expect(other.locator('#year')).toHaveValue('2030');
  76  |         await comparison.getByRole('radio',{name:/Your current edits: 2030/}).check();
  77  |       }
  78  |       await comparison.getByRole('button',{name:'Apply comparison to draft',exact:true}).click();
  79  |       const still=await other.request.get(`/api/profiles/${original.id}`);expect((await still.json()).revision).toBe(2);
  80  |       expect((await still.json()).context.intake_year).toBe(2028);
  81  |       if (!sameField) {await expect(other.locator('#year')).toHaveValue('2028');await expect(other.locator('#citizenship')).toHaveValue('Canada');}
  82  |       const merged=await update(other,original.id);expect(merged.status()).toBe(200);
  83  |       const result=await merged.json();expect(result.revision).toBe(3);
  84  |       expect(merged.request().headers()['x-expected-profile-revision']).toBe('2');
  85  |       expect(merged.request().headers()['idempotency-key']).not.toBe(rejected.request().headers()['idempotency-key']);
  86  |       expect(result.context.intake_year).toBe(sameField?2030:2028);
  87  |       if (!sameField) expect(result.context.citizenship).toBe('Canada');
  88  |       for (const width of [320,768,1024,1440]) {
  89  |         await other.setViewportSize({width,height:900});
  90  |         await other.screenshot({path:info.outputPath(`profile-${sameField?'choice':'merge'}-${width}.png`),fullPage:true});
  91  |       }
  92  |       await info.attach('accepted-profile-metadata',{body:JSON.stringify({profile_id:original.id,initial_revision:1,first_revision:2,merged_revision:3,original_conflict_code:409,newer_typing:sameField}),contentType:'application/json'});
  93  |     } finally {await otherContext.close();}
  94  |   });
  95  | }
  96  | 
  97  | test('profile native lost committed create ACK: reload and exact original UUID replay',async({page},info)=>{
  98  |   test.setTimeout(180000);
  99  |   const email=`profile-replay-${Date.now()}-${process.pid}@synthetic.invalid`;
  100 |   await signIn(page,email,true);await openProfile(page);await pause(page);
  101 |   await page.getByTestId('load-demo-profile').click();
  102 |   const replace=page.getByTestId('confirm-replace');if(await replace.isVisible().catch(()=>false))await replace.click();
  103 |   let committed!:Record<string,unknown>;let originalHeaders!:Record<string,string>;let originalBody!:unknown;
  104 |   await page.route('**/api/profiles',async route=>{
  105 |     if(route.request().method()!=='POST')return route.continue();
  106 |     originalHeaders=route.request().headers();originalBody=route.request().postDataJSON();
  107 |     const response=await route.fetch();expect(response.status()).toBe(201);committed=await response.json();
  108 |     await route.abort('failed'); // discard ONLY the real committed response
  109 |   },{times:1});
  110 |   await page.getByTestId('save-profile').click();
> 111 |   await expect(page.getByRole('region',{name:'Profile save recovery'})).toContainText('response was lost');
      |                                                                         ^ Error: expect(locator).toContainText(expected) failed
  112 |   const before=await page.request.get('/api/profiles');const beforeIds=(await before.json()).map((p:{id:string})=>p.id);
  113 |   expect(beforeIds).toContain(committed.id);
  114 |   await page.reload();
  115 |   const recovery=page.getByRole('region',{name:'Profile save recovery'});await expect(recovery).toBeVisible();
  116 |   const reply=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname==='/api/profiles');
  117 |   await recovery.getByRole('button',{name:'Confirm original save',exact:true}).click();
  118 |   const accepted=await reply;expect(accepted.status()).toBe(201);const body=await accepted.json();
  119 |   expect(body.id).toBe(committed.id);expect(body.revision).toBe(1);
  120 |   expect(accepted.request().headers()['idempotency-key']).toBe(originalHeaders['idempotency-key']);
  121 |   expect(accepted.request().headers()['x-profile-creation-identity']).toBe(originalHeaders['x-profile-creation-identity']);
  122 |   expect(accepted.request().postDataJSON()).toEqual(originalBody);
  123 |   const after=await page.request.get('/api/profiles');expect((await after.json()).map((p:{id:string})=>p.id).sort()).toEqual(beforeIds.sort());
  124 |   await expect(page.getByText('Saved',{exact:true})).toBeVisible();
  125 |   await info.attach('original-command-recovery',{body:JSON.stringify({profile_id:body.id,revision:1,same_uuid:true,same_body:true,no_duplicate:true,committed_ack_dropped:true}),contentType:'application/json'});
  126 | });
  127 | 
```