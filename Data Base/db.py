import os, psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
load_dotenv()

# ---- All app dates/times are India Standard Time, regardless of where the
# Colab/Docker host itself is running (usually UTC). A fixed +5:30 offset is
# used instead of zoneinfo("Asia/Kolkata") so this doesn't depend on the
# host having the tzdata package installed -- India doesn't observe DST, so
# a fixed offset is exact, not an approximation. mood_date/created_at/
# submitted_at are now set explicitly from this at insert time rather than
# relying on the DB server's own NOW()/CURRENT_DATE, which reflects the
# database host's timezone (often UTC) and would otherwise silently disagree
# with what an India-based user considers "today" for part of the day.
IST = timezone(timedelta(hours=5, minutes=30), name="IST")

def now_ist():
    return datetime.now(IST)

CFG = dict(host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT", "5432"),
           dbname=os.getenv("DB_NAME"), user=os.getenv("DB_USER"),
           password=os.getenv("DB_PASSWORD"), sslmode="require")

@contextmanager
def cursor(commit=False):
    conn = psycopg2.connect(**CFG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        yield cur
        if commit: conn.commit()
    finally:
        cur.close(); conn.close()

def init_db():
    with cursor(commit=True) as cur:
        cur.execute("""CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY, username VARCHAR(50) UNIQUE, email VARCHAR(255) UNIQUE,
            password_hash VARCHAR(255), is_verified BOOLEAN DEFAULT FALSE,
            role VARCHAR(20) NOT NULL DEFAULT 'employee')""")
        # Safe to run repeatedly: adds the column if this table already existed pre-role.
        cur.execute("""ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'employee'""")
        cur.execute("""CREATE TABLE IF NOT EXISTS otp_codes (
            id SERIAL PRIMARY KEY, email VARCHAR(255), code VARCHAR(6),
            purpose VARCHAR(20), expires_at TIMESTAMP, used BOOLEAN DEFAULT FALSE)""")

        # ---- One row per mood entry (manual pick OR journal/NLP submission OR face scan) ----
        # All entries — manual emoji picks, journal/file submissions, and face-scan
        # results — go into this ONE table, tied to the same user_id, so a person's
        # whole history (calendar, journal log, dashboard) always comes from one place.
        # `mood_date` is the calendar day the entry belongs to (defaults to submission day).
        # `created_at` is the full DATE+TIME the row was written — this is the
        # "emoji/journal saved with time" piece: every row already carries a timestamp.
        # `sentiment` stores one of the 5 labels: Amazing, Happy, Normal, Sad, Angry.
        # `compound_score` is VADER's -1..1 score, handy for charts (NULL for manual picks).
        # `confidence` is the emotion classifier's 0-1 certainty in its top label --
        # populated for NLP journal entries (BERT) and Face Scanner reads (DeepFace),
        # NULL for plain manual emoji picks where there's no model behind the label.
        # `emotion_scores` is the full per-label probability breakdown (JSONB), kept
        # alongside `emotion` (the single top label) so the Dashboard can optionally
        # show the full distribution, not just the argmax.
        # `source` marks how the row was created: 'manual' (emoji picker/face scan) or 'nlp' (journal/upload).
        cur.execute("""CREATE TABLE IF NOT EXISTS mood_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            mood_date DATE NOT NULL DEFAULT CURRENT_DATE,
            sentiment VARCHAR(20),
            emotion VARCHAR(30),
            compound_score REAL,
            confidence REAL,
            journal_text TEXT,
            source VARCHAR(10) NOT NULL DEFAULT 'manual',
            created_at TIMESTAMP NOT NULL DEFAULT NOW())""")
        cur.execute("""ALTER TABLE mood_logs ADD COLUMN IF NOT EXISTS source VARCHAR(10) NOT NULL DEFAULT 'manual'""")
        cur.execute("""ALTER TABLE mood_logs ADD COLUMN IF NOT EXISTS confidence REAL""")
        cur.execute("""ALTER TABLE mood_logs ADD COLUMN IF NOT EXISTS emotion_scores JSONB""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_mood_logs_user_date
            ON mood_logs(user_id, mood_date)""")

        # ---- "Analyze My Mood" — 12-question wellness check-in ----
        # A short questionnaire, separate from the free-text journal: 6 scored
        # ordinal questions feed a numeric wellness score/category, and 6
        # categorical questions (current mood, main factor, support preference,
        # willingness to talk, what would help, personalization consent) are
        # stored as context and used to tailor the recommendation shown after
        # submission, without affecting the score itself.
        cur.execute("""CREATE TABLE IF NOT EXISTS questionnaire_responses (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            submitted_at TIMESTAMP NOT NULL DEFAULT NOW(),
            answers JSONB NOT NULL,
            total_score INTEGER NOT NULL,
            max_score INTEGER NOT NULL,
            category VARCHAR(30) NOT NULL,
            wants_to_talk VARCHAR(10))""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_questionnaire_user_date
            ON questionnaire_responses(user_id, submitted_at)""")


# ---- The 5-point mood scale used everywhere (picker, calendar, dashboard, reports) ----
MOOD_LABELS = ["Amazing", "Happy", "Normal", "Sad", "Angry"]

# Maps the NLP pipeline's 3-way sentiment onto the closest of the 5 labels,
# so journal/file analysis results can still be plotted on the same scale.
NLP_TO_MOOD_LABEL = {
    "Positive": "Happy",
    "Neutral": "Normal",
    "Negative": "Sad",
}


# ---- Mood log helpers ----

def save_manual_mood(user_id, mood_label, emotion=None, confidence=None):
    """Employee taps an emoji on the 'How Do You Feel?' picker, OR the Face
    Scanner maps a detected facial emotion onto the 5-point scale — saves
    immediately (with the current IST date+time via created_at). `emotion`
    and `confidence` are optional: the plain emoji picker has neither (no
    model involved), while a Face Scanner save passes DeepFace's dominant
    emotion and its confidence (0-1) so that signal isn't thrown away."""
    now = now_ist()
    with cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO mood_logs (user_id, sentiment, emotion, confidence, source, mood_date, created_at)
               VALUES (%s, %s, %s, %s, 'manual', %s, %s)""",
            (user_id, mood_label, emotion, confidence, now.date(), now.replace(tzinfo=None)),
        )

def save_mood_log(user_id, sentiment, emotion, compound_score, journal_text,
                   confidence=None, emotion_scores=None):
    """Call this right after the NLP pipeline returns a result, so every
    journal entry (typed or uploaded) leaves a row — with date+time and the
    full journal text — for the calendar/journal-history/dashboard/report.
    `sentiment` here is the pipeline's Positive/Neutral/Negative label; it's
    mapped onto the 5-point scale so it plots consistently everywhere.
    `confidence` is the BERT emotion model's 0-1 certainty in `emotion`, and
    `emotion_scores` is its full per-label probability breakdown -- both are
    optional so older call sites that don't pass them still work."""
    import json as _json
    mood_label = NLP_TO_MOOD_LABEL.get(sentiment, "Normal")
    now = now_ist()
    with cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO mood_logs (user_id, sentiment, emotion, compound_score, confidence, journal_text, source, emotion_scores, mood_date, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, 'nlp', %s, %s, %s)""",
            (user_id, mood_label, emotion, compound_score, confidence, journal_text,
             _json.dumps(emotion_scores) if emotion_scores is not None else None,
             now.date(), now.replace(tzinfo=None)),
        )

def get_mood_logs_for_month(user_id, year, month):
    """Returns one row per day for a given user/month, latest entry per day.
    Used by the Home tab's calendar grid."""
    with cursor() as cur:
        cur.execute(
            """SELECT DISTINCT ON (mood_date) mood_date, sentiment, emotion, compound_score, confidence, created_at
               FROM mood_logs
               WHERE user_id = %s
                 AND EXTRACT(YEAR FROM mood_date) = %s
                 AND EXTRACT(MONTH FROM mood_date) = %s
               ORDER BY mood_date, created_at DESC""",
            (user_id, year, month),
        )
        return cur.fetchall()

def get_user_mood_history(user_id, limit=200):
    with cursor() as cur:
        cur.execute(
            """SELECT mood_date, sentiment, emotion, compound_score, confidence, emotion_scores, journal_text, source, created_at
               FROM mood_logs
               WHERE user_id = %s
               ORDER BY created_at DESC
               LIMIT %s""",
            (user_id, limit),
        )
        return cur.fetchall()

def get_all_employee_mood_logs(limit_days=30):
    cutoff = now_ist().date() - timedelta(days=limit_days)
    with cursor() as cur:
        cur.execute(
            """SELECT u.username, u.email, m.mood_date, m.sentiment, m.emotion, m.compound_score, m.confidence, m.created_at
               FROM mood_logs m
               JOIN users u ON u.id = m.user_id
               WHERE u.role = 'employee'
                 AND m.mood_date >= %s
               ORDER BY m.mood_date DESC, u.username""",
            (cutoff,),
        )
        return cur.fetchall()

def get_latest_mood_per_employee():
    """For managers: each employee's single most recent mood entry."""
    with cursor() as cur:
        cur.execute(
            """SELECT DISTINCT ON (u.id) u.username, u.email, m.mood_date, m.sentiment, m.emotion, m.confidence, m.created_at
               FROM users u
               JOIN mood_logs m ON m.user_id = u.id
               WHERE u.role = 'employee'
               ORDER BY u.id, m.created_at DESC"""
        )
        return cur.fetchall()

# ---- Risk detection: employees on a NEGATIVE STREAK, not just a bad day ----
# `get_latest_mood_per_employee` flags anyone whose single latest entry is
# Sad/Angry — that catches a one-off bad day too. This one only flags an
# employee if their most recent `streak` entries are ALL Sad/Angry, i.e.
# they've been *continuously* giving negative feedback.
RISK_STREAK = 3  # how many consecutive negative entries define "at risk"

def get_risk_detected_employees(streak=RISK_STREAK):
    """For managers: employees whose last `streak` mood entries are all
    Sad/Angry — a persistent negative pattern, separate from a single bad day."""
    with cursor() as cur:
        cur.execute(
            """SELECT username, email, sentiment, created_at FROM (
                   SELECT u.username, u.email, m.sentiment, m.created_at,
                          ROW_NUMBER() OVER (
                              PARTITION BY u.id ORDER BY m.created_at DESC
                          ) AS rn
                   FROM users u
                   JOIN mood_logs m ON m.user_id = u.id
                   WHERE u.role = 'employee'
               ) ranked
               WHERE rn <= %s
               ORDER BY username, created_at DESC""",
            (streak,),
        )
        rows = cur.fetchall()

    by_user = {}
    for row in rows:
        key = (row["username"], row["email"])
        by_user.setdefault(key, []).append(row)

    at_risk = []
    for (username, email), entries in by_user.items():
        if len(entries) < streak:
            continue  # not enough history yet to judge a streak
        if all(e["sentiment"] in ("Sad", "Angry") for e in entries):
            at_risk.append({
                "username": username,
                "email": email,
                "streak": streak,
                "last_entry": entries[0]["created_at"],
                "last_sentiment": entries[0]["sentiment"],
            })
    at_risk.sort(key=lambda r: r["last_entry"], reverse=True)
    return at_risk


# ---------------------------------------------------------------------------
# "Analyze My Mood" — 12-question wellness questionnaire
#
# Mix of scored ordinal items (mood rating, stress, energy, sleep, negative-
# emotion frequency, confidence -- used to compute a numeric wellness score)
# and categorical/context items (current mood, main factor, support
# preference, "want to talk", "what would help", personalize consent --
# stored for context and used to tailor the recommendation, not scored).
# ---------------------------------------------------------------------------

QUESTIONNAIRE_QUESTIONS = [
    {"id": "q1_current_mood", "text": "How are you feeling right now?", "scored": False,
     "options": ["Very Happy", "Happy", "Neutral", "Sad", "Angry", "Anxious/Fearful"]},

    {"id": "q2_overall_mood", "text": "How would you rate your overall mood today?", "scored": True, "reverse": False,
     "options": ["1 - Very Poor", "2 - Poor", "3 - Average", "4 - Good", "5 - Excellent"]},

    {"id": "q3_stress", "text": "How stressed do you feel right now?", "scored": True, "reverse": True,
     "options": ["Not stressed", "Slightly stressed", "Moderately stressed", "Highly stressed", "Extremely stressed"]},

    {"id": "q4_main_factor", "text": "What is the main thing affecting your mood today?", "scored": False,
     "options": ["Work/Studies", "Relationships", "Financial concerns", "Health", "Family",
                 "Sleep/Fatigue", "Personal concerns", "Nothing specific", "Other"]},

    {"id": "q5_energy", "text": "How would you describe your energy level today?", "scored": True, "reverse": False,
     "options": ["Very Low", "Low", "Moderate", "High", "Very High"]},

    {"id": "q6_sleep", "text": "How well did you sleep recently?", "scored": True, "reverse": False,
     "options": ["Very Poor", "Poor", "Average", "Good", "Very Good"]},

    {"id": "q7_support_pref", "text": "What kind of support would you prefer right now?", "scored": False,
     "options": ["Breathing/Relaxation Exercise", "Journaling Prompt", "Motivational Content",
                 "Cognitive Reframing", "Mindfulness Activity", "Professional Support Information"]},

    {"id": "q8_want_to_talk", "text": "Would you like to talk about what is bothering you?", "scored": False,
     "options": ["Yes", "Maybe", "No"]},

    {"id": "q9_negative_freq", "text": "How often have you been experiencing negative emotions recently?",
     "scored": True, "reverse": True,
     "options": ["Never", "Rarely", "Sometimes", "Often", "Very Often"]},

    {"id": "q10_confidence", "text": "How confident are you in managing your emotions today?",
     "scored": True, "reverse": False,
     "options": ["Not confident", "Slightly confident", "Moderately confident", "Very confident", "Extremely confident"]},

    {"id": "q11_help_now", "text": "What would help you feel better right now?", "scored": False,
     "options": ["Relaxation", "Someone to talk to", "Motivation", "Taking a break",
                 "Organizing my tasks", "Physical activity", "Sleep/rest", "I'm not sure"]},

    {"id": "q12_personalize", "text": "Would you like MoodMentor to personalize future recommendations based on your answers?",
     "scored": False, "options": ["Yes", "No"]},
]

_SCORED_QUESTIONS = [q for q in QUESTIONNAIRE_QUESTIONS if q["scored"]]
QUESTIONNAIRE_MAX_SCORE = len(_SCORED_QUESTIONS) * 5
QUESTIONNAIRE_MIN_SCORE = len(_SCORED_QUESTIONS) * 1


def score_questionnaire(answers: dict) -> dict:
    """
    answers: {question_id: selected_option_label, ...} for ALL 12 questions.
    Scored items contribute (1-5, reversed where noted); categorical items
    are ignored for scoring but returned for reference/tailoring.
    """
    total = 0
    for q in _SCORED_QUESTIONS:
        value = q["options"].index(answers[q["id"]]) + 1  # 1-based position
        total += (6 - value) if q["reverse"] else value

    if total >= 24:
        category = "Thriving"
    elif total >= 18:
        category = "Doing Well"
    elif total >= 12:
        category = "Needs Attention"
    else:
        category = "At Risk"

    return {"total_score": total, "max_score": QUESTIONNAIRE_MAX_SCORE, "category": category}


def save_questionnaire_response(user_id, answers: dict, total_score: int, category: str):
    import json as _json
    wants_to_talk = answers.get("q8_want_to_talk")
    with cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO questionnaire_responses (user_id, answers, total_score, max_score, category, wants_to_talk, submitted_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (user_id, _json.dumps(answers), total_score, QUESTIONNAIRE_MAX_SCORE, category, wants_to_talk,
             now_ist().replace(tzinfo=None)),
        )


def get_questionnaire_history(user_id, limit=100):
    with cursor() as cur:
        cur.execute(
            """SELECT submitted_at, answers, total_score, max_score, category, wants_to_talk
               FROM questionnaire_responses
               WHERE user_id = %s
               ORDER BY submitted_at DESC
               LIMIT %s""",
            (user_id, limit),
        )
        return cur.fetchall()


def get_all_questionnaire_responses(limit_days=30):
    """
    For manager Analytics Dashboard: every employee's questionnaire responses
    in the window. Includes username/email (for an opt-in "show names" view)
    plus `answers` (for aggregate-only stats like top stressor/support
    preference) -- callers building the default anonymous team view should
    use only the aggregate counts, never the username/email fields.
    """
    with cursor() as cur:
        cur.execute(
            """SELECT u.username, u.email, q.submitted_at, q.answers,
                      q.total_score, q.max_score, q.category, q.wants_to_talk
               FROM questionnaire_responses q
               JOIN users u ON u.id = q.user_id
               WHERE u.role = 'employee'
                 AND q.submitted_at >= %s
               ORDER BY q.submitted_at DESC, u.username""",
            (now_ist().replace(tzinfo=None) - timedelta(days=limit_days),),
        )
        return cur.fetchall()
