import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { setLocale } from '@/lib/i18n';
import { ProfileRecoveryPanel } from './ProfileRecoveryPanel';
import type { ProfileRecoveryView } from '@/lib/store';
const mocks=vi.hoisted(()=>({view:null as ProfileRecoveryView|null,apply:vi.fn(),retry:vi.fn(),compare:vi.fn(),clear:vi.fn(),exportOriginal:vi.fn(()=>'{"original":true}') }));
vi.mock('@/lib/store',()=>({useStore:()=>({profileRecovery:mocks.view,profileDraft:{display_name:'Local name'},loading:false,retryProfileWrite:mocks.retry,compareSavedProfile:mocks.compare,applyProfileComparison:mocks.apply,clearConfirmedProfileWrites:mocks.clear,exportProfileWrites:mocks.exportOriginal}),toDraft:()=>({display_name:'Server name'})}));
beforeEach(()=>{setLocale('ru');vi.clearAllMocks();mocks.view={entry:null,base:{display_name:'Base name'},server:{revision:2} as NonNullable<ProfileRecoveryView['server']>,message:'Original diagnostic retained'};});
afterEach(()=>setLocale('en'));
it('requires an explicit conflicting value and applies only to the current draft',()=>{
 render(<ProfileRecoveryPanel/>);
 const apply=screen.getByRole('button',{name:'Применить к черновику'});
 expect(apply).toBeDisabled();
 expect(screen.getByText('Base name')).toBeInTheDocument();
 expect(mocks.apply).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('radio',{name:/Текущее значение на сервере/}));
 fireEvent.click(apply);
 expect(mocks.apply).toHaveBeenCalledWith({'["display_name"]':'server'},JSON.stringify({display_name:'Local name'}));
 expect(mocks.retry).not.toHaveBeenCalled();
});
it('opens the requested mounted form section without applying or retrying the original write',()=>{
 const continueEditing=vi.fn();render(<ProfileRecoveryPanel asPage onContinue={continueEditing}/>);
 fireEvent.click(screen.getByRole('link',{name:'Учёба'}));
 expect(continueEditing).toHaveBeenCalledWith('academics');
 expect(mocks.apply).not.toHaveBeenCalled();expect(mocks.retry).not.toHaveBeenCalled();
 expect(screen.getByText('Сначала проверь сохранение')).toBeInTheDocument();
});
it('keeps unknown original and current draft separate and confirms the original only on request',()=>{
 mocks.view={entry:{v:1,owner:'synthetic-owner',case_key:'synthetic-case',kind:'update',command:{command_id:'00000000-0000-4000-8000-000000000001',expected_revision:1},status:'unknown',body:{display_name:'Original sent name'},base:null,draft:{display_name:'Original sent name'}},base:{},message:'Unconfirmed'};
 render(<ProfileRecoveryPanel asPage/>);
 expect(screen.getByRole('heading',{name:'Проверяем сохранение'})).toHaveFocus();
 expect(screen.getByText('Original sent name')).toBeInTheDocument();
 expect(screen.getByText('Local name')).toBeInTheDocument();
 expect(screen.getByText('Не записано в журнале')).toBeInTheDocument();
 expect(mocks.retry).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:/Проверить исходное сохранение/}));
 expect(mocks.retry).toHaveBeenCalledTimes(1);
 expect(mocks.apply).not.toHaveBeenCalled();
});
