# Swedish Learning Website Plan

## Goal

Build a practical Swedish learning workspace for beginners and intermediate learners. The website should help learners understand words, hear pronunciation, build sentences, learn grammar, and track improvement.

## Current Features

- Vocabulary browser with 760 Swedish words and phrases
- Swedish, English, and Hindi meanings
- Categories, levels, study sets, types, and search
- Vocabulary cards and table view
- Swedish pronunciation play buttons
- Full pronunciation practice for all vocabulary
- Grouped Swedish grammar lessons
- Grammar rules, examples, reasons, and exceptions
- Sentence-building practice
- Multiple-choice practice test
- Light and dark themes
- Flask service suitable for Cloud Run
- Health and manifest API endpoints

## Development Phases

### Phase 1: Strong Learning Basics — Implemented

Priority: High

- Add favourites for important words
- Add learned and not-learned status
- Add a Review tab for words needing practice
- Save learner progress in browser storage
- Add a daily practice goal
- Add a progress counter and learning streak
- Add a reset-progress action

Success criteria:

- A learner can mark a word as learned
- Learned status remains after refreshing the page
- Review mode shows unfinished or missed words
- Progress is visible without needing an account

### Phase 2: Better Practice — Implemented

Priority: High

- Add Swedish-to-English questions
- Add English-to-Swedish questions
- Add Hindi-to-Swedish questions
- Add spelling questions
- Add listening questions
- Add grammar fill-in-the-blank questions
- Add sentence-order questions
- Add instant explanations after an answer
- Store wrong answers for later review

Success criteria:

- Each test has a clear start, answer, result, and next-question flow
- Wrong answers are added to Review
- Practice uses the selected level and category filters
- Scores are shown for the current session

### Phase 3: Pronunciation and Listening — Implemented

Priority: High

- Keep a play button beside every vocabulary word
- Add sentence audio
- Add slow, normal, and fast playback speeds
- Show the selected Swedish voice
- Add a browser voice compatibility message
- Add listening-only tests where the answer is hidden
- Add pronunciation guidance for Swedish sounds: å, ä, ö, sj, tj, and rs

Success criteria:

- Audio always uses a Swedish voice when available
- The interface never presents an English voice as Swedish
- Learners can replay a word or sentence easily
- Listening tests work on supported browsers

### Phase 4: Grammar Course

Priority: High

Organize grammar into short levels and lessons:

- Nouns: en, ett, plural, definite forms
- Pronouns: subject, object, possessive, reflexive
- Verbs: present, past, perfect, future, modal verbs
- Sentence order: V2, questions, negation, subordinate clauses
- Adjectives: agreement, definite forms, comparison
- Prepositions: place, time, movement, verb combinations
- Special patterns: passive, commands, existence, spoken forms

Each lesson should contain:

- One simple rule
- Two or more Swedish examples
- A short reason explaining when the rule matters
- Common mistakes
- Exceptions
- One short exercise

Success criteria:

- Lessons are grouped by topic and level
- The learner sees the simple rule before advanced detail
- Every rule has examples and exception guidance
- Grammar exercises use the lesson being studied

### Phase 5: Real-Life Swedish

Priority: Medium

Add practical conversation modules:

- Introducing yourself
- Shopping and paying
- Visiting a doctor
- Calling a school or office
- Public transport
- Renting a home
- Workplace conversations
- Job interviews
- Talking with neighbours
- Emergency situations

Each module should include:

- Key vocabulary
- A short dialogue
- Audio for each line
- Translation support
- Missing-word practice
- Role-play prompts

### Phase 6: Progress and Accounts

Priority: Medium

Start with local browser storage, then add accounts through the backend.

Local version:

- Daily goal
- Streak
- Learned words
- Test scores
- Review queue
- Last studied date

Backend version:

- User registration and login
- Cloud-saved progress
- Multiple devices
- Personal vocabulary lists
- Progress dashboard
- Teacher or administrator view

## Backend Plan

### Current Backend

- Python Flask
- Gunicorn for production
- Dockerfile for Cloud Run
- `GET /api/health`
- `GET /api/manifest`
- Static frontend served by Flask

### Planned API

- `GET /api/chapters`
- `GET /api/words`
- `GET /api/grammar`
- `POST /api/progress`
- `GET /api/progress`
- `POST /api/review`
- `GET /api/review`
- `POST /api/test-results`

### Suggested Backend Storage

For the first backend release:

- SQLite for local development
- PostgreSQL or Cloud SQL for production
- SQLAlchemy for database access
- Flask-CORS only when a separate frontend domain is required
- Environment variables for database URL and secret configuration

Do not add login until local progress tracking and review logic are stable.

## Suggested Data Models

### Word Progress

- `user_id`
- `word_id`
- `learned`
- `favourite`
- `correct_count`
- `wrong_count`
- `last_reviewed_at`
- `next_review_at`

### Test Result

- `user_id`
- `test_type`
- `level`
- `category`
- `score`
- `total_questions`
- `created_at`

### Grammar Lesson

- `id`
- `group`
- `level`
- `title`
- `rule`
- `reason`
- `examples`
- `exceptions`
- `exercise_items`

## Recommended Next Build

Implement Phase 1 first:

1. Add favourite and learned buttons to vocabulary cards
2. Store status in `localStorage`
3. Add a Review tab
4. Add a simple progress summary
5. Add wrong-answer tracking from the practice test

This gives the learner a useful personal study loop without requiring accounts or a database.

## Quality Checks

Run these checks after changes:

```bash
node --check docs/app.js
node scripts/validate-vocabulary.mjs
python3 -m py_compile server.py
```

Also verify manually:

- Vocabulary filters
- Play buttons in Cards and Table views
- All grammar groups open correctly
- Sentence practice
- Practice test scoring
- Mobile layout
- Dark theme
- `/api/health`
- `/api/manifest`
