import { expect, it } from 'vitest';
import type { ProgramResult } from '@/types';
import { bookRouteCardModel } from './bookSharePresentation';
const programme={id:'public-result',university:'Example university',program:'BSc Computing',country:'Netherlands',user_notes:'PRIVATE NOTE',total_cost:{private_budget:12345}} as unknown as ProgramResult;
it('uses only the selected public programme fields and explicit name disclosure',()=>{
 const model=bookRouteCardModel([programme],'Synthetic applicant',false,true);
 expect(model.title).toBe('Netherlands');expect(model.destinations[0]?.detail).toBe('BSc Computing · Netherlands');
 expect(JSON.stringify(model)).not.toContain('Synthetic applicant');expect(JSON.stringify(model)).not.toContain('PRIVATE NOTE');expect(JSON.stringify(model)).not.toContain('12345');
 expect(bookRouteCardModel([programme],'Synthetic applicant',true,true).signature).toBe('Synthetic applicant');
});
it('removes the destinations and destination title when programme disclosure is off',()=>{
 const model=bookRouteCardModel([programme],'Synthetic applicant',false,false);
 expect(model.destinations).toEqual([]);expect(model.title).toBe('Твой следующий шаг');
 expect(JSON.stringify(model)).not.toContain('Netherlands');expect(JSON.stringify(model)).not.toContain('Example university');expect(JSON.stringify(model)).not.toContain('BSc Computing');
});
