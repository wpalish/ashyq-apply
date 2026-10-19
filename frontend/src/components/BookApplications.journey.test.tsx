import {render,screen} from '@testing-library/react';
import {it,expect,vi} from 'vitest';
import {BookApplications} from './BookApplications';
import {manualFixture} from '@/test/manualAdmissionsFixtures';
import {acceptedActions} from '@/test/admissionsFixtures';
import {setLocale} from '@/lib/i18n';
it('retains an exact application/document path and marks older prepared reports for review',()=>{
 setLocale('ru');const app=manualFixture().current.state!.applications[0]!;
 const task=structuredClone(acceptedActions().current.state!.document_tasks[0]!);task.application_id=app.id;task.report.state='prepared_reported';
 render(<BookApplications applications={[app]} tasks={[task]} results={[]} opened={app} pageHeading canEdit links={[]} reviews={[task.id]} onOpen={vi.fn()} onBack={vi.fn()} onAdd={vi.fn()} onEdit={vi.fn()} onPrepare={vi.fn()} onHistory={vi.fn()}/>);
 const link=screen.getByRole('link',{name:/Synthetic document task.*Нужна повторная проверка/});
 expect(link).toHaveAttribute('href',`#/documents?case=${app.profile_id}&kind=document_task&id=${task.id}`);
 expect(screen.queryByText('Подготовка отмечена тобой')).toBeNull();
 expect(screen.getByRole('link',{name:'Подготовить документы этой заявки →'}).getAttribute('href')).toContain(`application=${app.id}`);
});
