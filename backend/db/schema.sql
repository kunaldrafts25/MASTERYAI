CREATE TABLE IF NOT EXISTS learners (
    learner_id TEXT PRIMARY KEY,
    name VARCHAR(100) NOT NULL DEFAULT '',
    experience_level VARCHAR(20) NOT NULL DEFAULT 'beginner',
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_learners_last_active ON learners (last_active DESC);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    learner_id TEXT NOT NULL REFERENCES learners(learner_id),
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_sessions_learner ON sessions (learner_id, created_at DESC);

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    learner_id TEXT REFERENCES learners(learner_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
