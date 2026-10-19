import {fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {beforeEach,expect,it,vi} from 'vitest';
import {UniversityCatalogue} from './UniversityCatalogue';
import {api} from '@/api/client';
import {setLocale} from '@/lib/i18n';
vi.mock('./OfficialProgrammeLibrary',()=>({OfficialProgrammeLibrary:()=>null}));
vi.mock('@/api/client',()=>({api:{universities:vi.fn()}}));
const startRun=vi.fn().mockResolvedValue(undefined);let savedProfile:{id:string}|null;let run:{id:string}|null;
vi.mock('@/lib/store',()=>({useStore:()=>({savedProfile,run,startRun,loading:false})}));
beforeEach(()=>{vi.clearAllMocks();setLocale('en');window.location.hash='#/shortlist?view=catalogue';savedProfile={id:'case-1'};run=null;vi.mocked(api.universities).mockResolvedValue({items:[{id:'mit-native',name:'Massachusetts Institute of Technology',aliases:['Massachusetts Institute of Technology (MIT)']} as never],total:1,catalogue_total:500,seed_count:500,countries:[]});});
it('browses all 500 locally and filters without requiring a live API or profile',()=>{
 savedProfile=null;render(<UniversityCatalogue/>);expect(screen.getByRole('status')).toHaveTextContent('500 of 500');expect(api.universities).not.toHaveBeenCalled();fireEvent.change(screen.getByRole('searchbox'),{target:{value:'Oxford'}});expect(screen.getByRole('button',{name:'University of Oxford'})).toBeInTheDocument();
 fireEvent.change(screen.getByRole('searchbox'),{target:{value:'unknown-xyz'}});expect(screen.getByText('No universities found')).toBeInTheDocument();fireEvent.click(screen.getByText('Reset filters'));expect(screen.getByRole('status')).toHaveTextContent('500 of 500');
});
it('opens a source-labelled history and restores its exact URL on reload',()=>{
 const view=render(<UniversityCatalogue/>);fireEvent.click(screen.getByRole('button',{name:'Massachusetts Institute of Technology (MIT)'}));expect(window.location.hash).toContain('university=qs2027-001');expect(screen.getByRole('link',{name:'History source ↗'})).toHaveAttribute('href','https://en.wikipedia.org/wiki/Massachusetts_Institute_of_Technology');view.unmount();render(<UniversityCatalogue/>);expect(screen.getByRole('region',{name:'University profile'})).toBeInTheDocument();
});
it('resolves selected identities only on explicit research and follows the resulting run',async()=>{
 const progress=vi.fn();const view=render(<UniversityCatalogue onProgress={progress}/>);const card=screen.getByRole('button',{name:'Massachusetts Institute of Technology (MIT)'}).closest('article')!;fireEvent.click(within(card).getByRole('checkbox'));expect(startRun).not.toHaveBeenCalled();fireEvent.click(screen.getByRole('button',{name:'Research selected (1)'}));await waitFor(()=>expect(startRun).toHaveBeenCalledWith(false,['mit-native']));run={id:'new-run'};view.rerender(<UniversityCatalogue onProgress={progress}/>);expect(progress).toHaveBeenCalledOnce();
});
it('ignores an identity lookup after switching cases',async()=>{
 let release!:(value:Awaited<ReturnType<typeof api.universities>>)=>void;vi.mocked(api.universities).mockReturnValueOnce(new Promise(resolve=>{release=resolve;}));const view=render(<UniversityCatalogue/>);fireEvent.click(within(screen.getByRole('button',{name:'Massachusetts Institute of Technology (MIT)'}).closest('article')!).getByRole('checkbox'));fireEvent.click(screen.getByRole('button',{name:'Research selected (1)'}));savedProfile={id:'case-2'};view.rerender(<UniversityCatalogue/>);release({items:[],total:0,catalogue_total:500,seed_count:500,countries:[]});await waitFor(()=>expect(screen.getByRole('button',{name:'Research selected (0)'})).toBeDisabled());expect(startRun).not.toHaveBeenCalled();
});
