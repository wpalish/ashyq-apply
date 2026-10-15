/** Real owned server/browser: stale versions, explicit merge and dropped committed ACK.
 * Fault routes delay a real GET or abort a real committed response; no fake acceptance.
 */
import { test, expect, type Page } from '@playwright/test';
const auth = process.env.CORE_NATIVE_AUTH === 'true';
const PASSWORD = 'synthetic-profile-native-passphrase-2026';
async function signIn(page: Page, email: string, register = false) {
  if (!auth) return;
  await page.goto('/#/sign-in');
  if (register) {
    await page.getByTestId('auth-mode-toggle').click();
    await page.getByTestId('auth-name').fill('Synthetic Profile Protocol');
    await page.getByTestId('auth-organization').fill('Synthetic Profile Workspace');
  }
  await page.getByTestId('auth-email').fill(email);
  await page.getByTestId('auth-password').fill(PASSWORD);
  await page.getByTestId('auth-submit').click();
  await expect(page.getByRole('heading',{name:'Good to see you.'})).toBeVisible();
}
async function openProfile(page: Page, id?: string) {
  await page.goto('/#/profile');
  await expect(page.getByTestId('save-profile')).toBeEnabled();
  if (id) {
    await expect(page.locator('#case-switcher')).toContainText('Demo Applicant');
    await page.locator('#case-switcher').selectOption(id);
    await expect(page.locator('#case-switcher')).toHaveValue(id);
    await expect(page.getByTestId('save-profile')).toBeEnabled();
  }
}
async function createProfile(page: Page) {
  await openProfile(page);
  await page.getByTestId('load-demo-profile').click();
  const replace = page.getByTestId('confirm-replace');
  if (await replace.isVisible().catch(()=>false)) await replace.click();
  const reply = page.waitForResponse(r=>r.request().method()==='POST' && new URL(r.url()).pathname==='/api/profiles');
  await page.getByTestId('save-profile').click();
  const response=await reply;expect(response.status()).toBe(201);
  const body=await response.json();expect(body.revision).toBe(1);expect(body.write_receipt.kind).toBe('create');
  await expect(page.getByText('Saved',{exact:true})).toBeVisible();
  return body;
}
async function pause(page:Page) {
  await page.clock.install({time:new Date('2026-10-15T10:00:00Z')});
  await page.clock.pauseAt(new Date('2026-10-15T10:00:01Z'));
}
async function update(page:Page, id:string) {
  const pending=page.waitForResponse(r=>r.request().method()==='PUT' && new URL(r.url()).pathname===`/api/profiles/${id}`);
  await page.getByTestId('save-profile').click();return pending;
}
for (const sameField of [false,true]) {
  test(`profile native ${sameField?'same-field choice/newer typing':'different-field merge'} across two real contexts`,async({page,browser},info)=>{
    test.setTimeout(180000);
    const email=`profile-${Date.now()}-${sameField}-${process.pid}@synthetic.invalid`;
    await signIn(page,email,true);const original=await createProfile(page);await pause(page);
    const otherContext=await browser.newContext();const other=await otherContext.newPage();
    try {
      await signIn(other,email);await openProfile(other,original.id);await pause(other);
      const first=page.locator('#year');await first.fill('2028');
      const accepted=await update(page,original.id);expect(accepted.status()).toBe(200);
      const saved=await accepted.json();expect(saved.revision).toBe(2);
      expect(accepted.request().headers()['x-expected-profile-revision']).toBe('1');
      expect(accepted.request().postDataJSON()).not.toHaveProperty('revision');
      if (sameField) await other.locator('#year').fill('2029');else await other.locator('#citizenship').fill('Canada');
      let release!:()=>void;const held=new Promise<void>(resolve=>{release=resolve;});
      let started!:()=>void;const reading=new Promise<void>(resolve=>{started=resolve;});
      if (sameField) await other.route(`**/api/profiles/${original.id}`,async route=>{
        if (route.request().method()!=='GET') return route.continue();
        started();await held;await route.continue();
      });
      const rejected=await update(other,original.id);expect(rejected.status()).toBe(409);
      if (sameField) {await reading;await other.locator('#year').fill('2030');release();}
      const comparison=other.getByRole('region',{name:'Profile save recovery'});
      await expect(comparison.getByText('Saved version 2.',{exact:false})).toBeVisible();
      if (sameField) {
        await expect(other.locator('#year')).toHaveValue('2030');
        await comparison.getByRole('radio',{name:/Your current edits: 2030/}).check();
      }
      await comparison.getByRole('button',{name:'Apply comparison to draft',exact:true}).click();
      const still=await other.request.get(`/api/profiles/${original.id}`);expect((await still.json()).revision).toBe(2);
      expect((await still.json()).context.intake_year).toBe(2028);
      if (!sameField) {await expect(other.locator('#year')).toHaveValue('2028');await expect(other.locator('#citizenship')).toHaveValue('Canada');}
      const merged=await update(other,original.id);expect(merged.status()).toBe(200);
      const result=await merged.json();expect(result.revision).toBe(3);
      expect(merged.request().headers()['x-expected-profile-revision']).toBe('2');
      expect(merged.request().headers()['idempotency-key']).not.toBe(rejected.request().headers()['idempotency-key']);
      expect(result.context.intake_year).toBe(sameField?2030:2028);
      if (!sameField) expect(result.context.citizenship).toBe('Canada');
      for (const width of [320,768,1024,1440]) {
        await other.setViewportSize({width,height:900});
        await other.screenshot({path:info.outputPath(`profile-${sameField?'choice':'merge'}-${width}.png`),fullPage:true});
      }
      await info.attach('accepted-profile-metadata',{body:JSON.stringify({profile_id:original.id,initial_revision:1,first_revision:2,merged_revision:3,original_conflict_code:409,newer_typing:sameField}),contentType:'application/json'});
    } finally {await otherContext.close();}
  });
}

test('profile native lost committed create ACK: reload and exact original UUID replay',async({page},info)=>{
  test.setTimeout(180000);
  const email=`profile-replay-${Date.now()}-${process.pid}@synthetic.invalid`;
  await signIn(page,email,true);await openProfile(page);await pause(page);
  await page.getByTestId('load-demo-profile').click();
  const replace=page.getByTestId('confirm-replace');if(await replace.isVisible().catch(()=>false))await replace.click();
  let committed!:Record<string,unknown>;let originalHeaders!:Record<string,string>;let originalBody!:unknown;
  await page.route('**/api/profiles',async route=>{
    if(route.request().method()!=='POST')return route.continue();
    originalHeaders=route.request().headers();originalBody=route.request().postDataJSON();
    const response=await route.fetch();expect(response.status()).toBe(201);committed=await response.json();
    await route.abort('failed'); // discard ONLY the real committed response
  },{times:1});
  await page.getByTestId('save-profile').click();
  await expect(page.getByRole('region',{name:'Profile save recovery'})).toContainText('response was lost');
  const before=await page.request.get('/api/profiles');const beforeIds=(await before.json()).map((p:{id:string})=>p.id);
  expect(beforeIds).toContain(committed.id);
  await page.reload();
  const recovery=page.getByRole('region',{name:'Profile save recovery'});await expect(recovery).toBeVisible();
  const reply=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname==='/api/profiles');
  await recovery.getByRole('button',{name:'Confirm original save',exact:true}).click();
  const accepted=await reply;expect(accepted.status()).toBe(201);const body=await accepted.json();
  expect(body.id).toBe(committed.id);expect(body.revision).toBe(1);
  expect(accepted.request().headers()['idempotency-key']).toBe(originalHeaders['idempotency-key']);
  expect(accepted.request().headers()['x-profile-creation-identity']).toBe(originalHeaders['x-profile-creation-identity']);
  expect(accepted.request().postDataJSON()).toEqual(originalBody);
  const after=await page.request.get('/api/profiles');expect((await after.json()).map((p:{id:string})=>p.id).sort()).toEqual(beforeIds.sort());
  await expect(page.getByText('Saved',{exact:true})).toBeVisible();
  await info.attach('original-command-recovery',{body:JSON.stringify({profile_id:body.id,revision:1,same_uuid:true,same_body:true,no_duplicate:true,committed_ack_dropped:true}),contentType:'application/json'});
});

for (const create of [false,true]) {
  test(`profile native ordinary delayed ${create?'create':'update'} ACK retains newer typing on immediate reload`,async({page},info)=>{
    test.setTimeout(180000);
    const email=`profile-delayed-${Date.now()}-${create}-${process.pid}@synthetic.invalid`;
    await signIn(page,email,true);
    const original=create?null:await createProfile(page);
    if(create){await openProfile(page);await page.getByTestId('load-demo-profile').click();const replace=page.getByTestId('confirm-replace');if(await replace.isVisible().catch(()=>false))await replace.click();}
    await pause(page);await page.locator('#year').fill('2028');
    let release!:()=>void;const held=new Promise<void>(resolve=>{release=resolve;});
    let committed!:Record<string,unknown>;let acknowledge!:()=>void;const committedReply=new Promise<void>(resolve=>{acknowledge=resolve;});
    const path=create?'**/api/profiles':`**/api/profiles/${original.id}`;
    await page.route(path,async route=>{
      if(route.request().method()!==(create?'POST':'PUT'))return route.continue();
      const response=await route.fetch();expect(response.status()).toBe(create?201:200);committed=await response.json();acknowledge();await held;await route.fulfill({response});
    },{times:1});
    await page.getByTestId('save-profile').click();await committedReply;
    await page.locator('#year').fill('2029');
    const accepted=page.waitForResponse(r=>r.request().method()===(create?'POST':'PUT')&&new URL(r.url()).pathname===(create?'/api/profiles':`/api/profiles/${original.id}`));
    release();await accepted;await expect(page.getByRole('region',{name:'Profile save recovery'})).not.toBeVisible();
    await expect(page.locator('#case-switcher')).toHaveValue(String(committed.id));
    await expect(page.locator('#year')).toHaveValue('2029');await expect(page.getByText('Saved',{exact:true})).not.toBeVisible();
    await page.reload();await expect(page.locator('#year')).toHaveValue('2029');
    const server=await page.request.get(`/api/profiles/${committed.id}`);expect((await server.json()).context.intake_year).toBe(2028);
    await info.attach('delayed-ack-reload',{body:JSON.stringify({profile_id:committed.id,server_year:2028,draft_year:2029,create,real_committed_ack:true}),contentType:'application/json'});
  });
}
test('profile native abandons research before POST while optional metadata is delayed',async({page},info)=>{
  test.setTimeout(180000);
  const email=`profile-abandon-${Date.now()}-${process.pid}@synthetic.invalid`;
  await signIn(page,email,true);const profile=await createProfile(page);await pause(page);
  let release!:()=>void;const held=new Promise<void>(resolve=>{release=resolve;});
  let reached!:()=>void;const reading=new Promise<void>(resolve=>{reached=resolve;});
  await page.route('**/api/cases',async route=>{const response=await route.fetch();reached();await held;await route.fulfill({response});},{times:1});
  const researchPosts:string[]=[];page.on('request',request=>{if(request.method()==='POST'&&new URL(request.url()).pathname==='/api/runs')researchPosts.push(request.url());});
  await page.goto('/#/preferences');await expect(page.getByTestId('start-research')).toBeEnabled();
  await page.getByTestId('start-research').click();await reading;
  await page.locator('#case-switcher').selectOption('');
  await expect(page.locator('#case-switcher')).toHaveValue('');
  release();await page.clock.runFor(100);
  const runs=await page.request.get(`/api/runs?profile_id=${profile.id}`);
  expect(researchPosts).toEqual([]);
  expect(runs.status()).toBe(200);expect(await runs.json()).toEqual([]);
  await info.attach('abandoned-research',{body:JSON.stringify({profile_id:profile.id,research_posts:researchPosts,run_list_status:runs.status()}),contentType:'application/json'});
});
