---
workflow: general-video
flow: companion
storyboard: yes
message: "ASHYQ Apply считает, сколько на самом деле будет стоить учёба — после гранта, с источником у каждой цифры"
destination: tiktok-reels-shorts
aspect: 1080x1920
language: ru
audience: "школьники 15–17 лет в Казахстане, которые думают об учёбе за рубежом"
length: 22s
angle: myth-check
voice: fish-audio
---

## Intent

A paid social ad for awareness, not conversion. It runs on TikTok, Instagram Reels and YouTube
Shorts, aimed at school students. Idea 1 of three (owner's pick, 2026-09-29): «Бесплатно — это
сколько?».

The hook questions a belief the audience already holds: a grant means studying is free. The
product answers it with arithmetic and a source. The tone is a friend who has checked, not an ad
voice or a lecture. It addresses the viewer as «ты».

## Assets

- The «Горизонт» design system from PR #20: the «Солнце» tokens, Montserrat 800 + Onest, the
  dotted globe and the sun brand mark (`frontend/src/styles/tokens.css`, `frontend/src/lib/globe*`).
- The numbers come from the demo run and corpus (`backend/app/corpus/data.py`, the Groningen
  entry). They are synthetic: real university names, invented figures.

## Customizations

- Voice-over from Fish Audio (API, owner's key; kept out of the repository). The voice must be
  neutral, not a clone of a real person.
- Burned-in captions, because most people watch feed video with the sound off.
- The key figures are counted up, as arithmetic.

## Notes

- Invariants (AGENTS.md §6, skills `applicant-fit-scoring` and `scholarship-audit`):
  - no chance, % or guarantee;
  - the grant is «учёба и проживание», never «покрывает всё»;
  - the price is per year, after the grant, with the rate and its date;
  - every figure has its source and date;
  - demo data is labelled on screen.
- Captions and key content stay out of the platform UI zones: the top 220 px, the bottom 380 px
  and the right 140 px.
- There is no public URL, so the call to action is the name only («Узнай настоящую цену учёбы»).
  The price (4 990 ₸) is not mentioned: this ad builds awareness.
