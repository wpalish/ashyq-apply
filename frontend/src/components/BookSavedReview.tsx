import { useState } from 'react';
import type { PreparationLesson, StudyAttempt } from '@/types';
import { BookPracticeView } from './BookPracticeView';
import { BookHelp } from './BookUI';

/** Presentation of an already validated saved review; never submits an attempt. */
export function BookSavedReview({lesson,attempt,notice,canRestart,onRestart,onBack}:{lesson:PreparationLesson;attempt:StudyAttempt;notice:string;canRestart:boolean;onRestart:()=>void;onBack:()=>void}) {
  const [material,setMaterial]=useState(false);
  const answers=Object.fromEntries(attempt.answers.map(answer=>[answer.question_id,'choice_id' in answer?answer.choice_id:answer.text]));
  const summary={id:lesson.id,version:lesson.version,track_id:lesson.track_id,title:lesson.title,question_count:lesson.questions.length};
  return <><BookPracticeView lesson={lesson} lessons={[summary]} submitted={new Set([JSON.stringify([lesson.id,lesson.version])])} answers={answers} materialOnly={material} frozen sending={false} error="" attempt={attempt} canRestart={canRestart} onMaterial={setMaterial} onAnswer={()=>{}} onSubmit={()=>{}} onRestart={onRestart} onNext={onBack} onBack={onBack} onLesson={()=>{}}/><BookHelp>{notice} Версия сохранённого материала: {attempt.version}. Отправка новой работы здесь не выполняется.</BookHelp></>;
}
