from pathlib import Path
s=Path(__file__).resolve().parent;p=s/'native-core-journey-proposal.spec.ts';t=p.read_text()
old="  await page.goto('/#/preferences');\n";assert t.count(old)==1
new="""  await page.goto('/#/approved');
  await page.getByRole('button', { name: 'Add an application', exact: true }).click();
  await page.getByLabel('Application name', { exact: true }).fill('Synthetic manual application');
  await page.getByLabel('University, as entered by you', { exact: true }).fill('Synthetic Unknown University');
  await page.getByRole('checkbox', { name: 'I reviewed these personal details and confirm this is my own record.', exact: true }).check();
  const manualApp = await save(page);
  expect(manualApp.applied_delta.applications[0].target.result_id).toBeNull();
  await page.goto('/#/preferences');
""";t=t.replace(old,new)
old="  await page.goto('/#/documents');\n  const linked =";assert t.count(old)==1
new="""  const applicationCard = page.getByTestId('personal-application').filter({ has: page.getByRole('heading', { name: 'Synthetic core application', exact: true }) });
  await applicationCard.getByRole('button', { name: 'Start preparing this application', exact: true }).click();
  await expect(applicationCard).toContainText('Preparing');
  await applicationCard.getByRole('button', { name: 'Record my submission statement', exact: true }).click();
  await page.getByLabel('Your event date, if known', { exact: true }).fill('2026-10-14');
  await page.getByLabel('Submission channel, as entered by you', { exact: true }).fill('Synthetic own declaration');
  await page.getByRole('checkbox', { name: 'I reviewed these personal details and confirm this is my own record.', exact: true }).check();
  await save(page); await expect(applicationCard).toContainText('Submission · declared by you');
  await applicationCard.getByRole('button', { name: 'History', exact: true }).click();
  await page.getByRole('button', { name: 'Correct this declaration', exact: true }).click();
  await page.getByRole('checkbox', { name: 'I reviewed these personal details and confirm this is my own record.', exact: true }).check();
  await save(page); await expect(applicationCard).toContainText('Preparing');
  await page.goto('/#/documents');
  const linked =""";t=t.replace(old,new).replace('expect(state.state.applications[0].id).toBe(appId);','expect(state.state.applications.some((app: {id: string}) => app.id === appId)).toBe(true);')
p.write_text(t)
