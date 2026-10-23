import { expect,it } from 'vitest';
import { journeyHref,parseJourneyRoute } from './programmeJourney';
it.each(['shortlist','approved','documents','applications'] as const)('keeps exact IDs through the %s route without placing personal data in URLs',screen=>{
 const route={screen,profileId:'own/case',resultId:'programme+1'};
 expect(parseJourneyRoute(journeyHref(route))).toEqual(route);
});
it('keeps the selected application and programme together for document preparation',()=>{
 const route={screen:'documents' as const,profileId:'A',resultId:'r1',applicationId:'a1',action:'bind' as const};
 expect(parseJourneyRoute(journeyHref(route))).toEqual(route);
});
it.each(['#/documents?case=A&programme=r&case=B','#/applications?case=A&programme=r&name=Person','#/documents?case=A&programme=r&action=new','#/applications?case=A&programme=r&action=bind','#/approved?case=A&programme=%20r','#/documents?case=A&programme=','#/documents?case=A&kind=document_task&id=t'])('rejects ambiguous or unsupported journey links: %s',hash=>expect(parseJourneyRoute(hash)).toBeNull());
