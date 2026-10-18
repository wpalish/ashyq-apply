import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { BookSavedReview } from './BookSavedReview';
import type { PreparationLesson, StudyAttempt } from '@/types';
const lesson:PreparationLesson={id:'reading',track_id:'ielts',title:'Saved reading',version:'saved-v1',unofficial:true,introduction:'## Read the evidence\n\nOriginal saved text.',questions:[{id:'one',prompt:'First question',choices:[{id:'a',text:'Selected wrong answer'},{id:'b',text:'Confirmed correct answer'}]},{id:'two',prompt:'Second question',answer_format:'short_answer',max_words:2}]};
const attempt:StudyAttempt={id:'saved',profile_id:'case-A',attempt_id:'original-id',lesson_id:'reading',version:'saved-v1',created_at:'2026-10-18',answers:[{question_id:'one',choice_id:'a'},{question_id:'two',text:'library'}],correct:1,total:2,feedback:[{question_id:'one',selected_choice_id:'a',correct_choice_id:'b',correct:false,explanation:'The passage supports B.'},{question_id:'two',selected_text:'library',accepted_answers:['library'],correct:true,explanation:'The answer is directly stated.'}]};
afterEach(cleanup);
it('reads saved feedback and navigates questions while new practice remains locked',()=>{
 const restart=vi.fn(),back=vi.fn();const original=JSON.stringify(attempt);
 render(<BookSavedReview lesson={lesson} attempt={attempt} notice="Saved server review" canRestart={false} onRestart={restart} onBack={back}/>);
 expect(screen.getByRole('heading',{level:1})).toHaveTextContent('Разбор ответа');
 expect(screen.getByText('The passage supports B.')).toBeInTheDocument();
 expect(screen.queryByRole('radio')).not.toBeInTheDocument();
 expect(screen.getByRole('button',{name:'Попробовать ещё раз'})).toBeDisabled();
 fireEvent.click(screen.getByRole('button',{name:'Следующий разбор'}));
 expect(screen.getByText('The answer is directly stated.')).toBeInTheDocument();
 expect(screen.getByRole('textbox')).toBeDisabled();
 expect(screen.getByRole('textbox')).toHaveValue('library');
 fireEvent.click(screen.getByRole('button',{name:'К материалам'}));
 expect(back).toHaveBeenCalledOnce();expect(restart).not.toHaveBeenCalled();
 expect(JSON.stringify(attempt)).toBe(original);
});
it('opens the saved teaching text with a heading below the page title',()=>{
 render(<BookSavedReview lesson={lesson} attempt={attempt} notice="Saved server review" canRestart onRestart={()=>{}} onBack={()=>{}}/>);
 fireEvent.click(screen.getByRole('button',{name:'Учебный материал'}));
 expect(screen.getByRole('heading',{level:2,name:'Read the evidence'})).toBeInTheDocument();
 expect(screen.getByText('Original saved text.')).toBeInTheDocument();
});
