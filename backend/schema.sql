CREATE DATABASE IF NOT EXISTS ai_resume_screening;

USE ai_resume_screening;

-- Every recruiter/job-seeker account. One row is exactly one role - a user is
-- either a recruiter or a job seeker, matching the two personas the frontend
-- already has, not both. Individual-account tenancy: a recruiter's data is
-- scoped to their own owner_id everywhere below, not shared with other
-- recruiters even if they screen the same candidate (see candidates table
-- comment for why that matters).
CREATE TABLE IF NOT EXISTS users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('recruiter', 'job_seeker') NOT NULL,
    display_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_email (email)
);

-- owner_id is nullable so pre-auth rows created before this migration don't
-- break; they simply won't appear in anyone's "My Shortlists" history.
CREATE TABLE IF NOT EXISTS screening_runs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    run_name VARCHAR(255) NOT NULL,
    job_title VARCHAR(255),
    ranking_rule TEXT,
    source_file VARCHAR(500),
    owner_id BIGINT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES users(id),
    INDEX idx_screening_runs_owner (owner_id)
);

-- Global, not per-tenant - the same person screened by two unrelated
-- recruiters shares one row here (matched by email). That's fine for this
-- table alone (just name/contact info), but every read of comments/rankings
-- tied to a candidate_id MUST also filter by the requesting recruiter's own
-- owner_id/author_id, or one recruiter's private notes about a candidate
-- would leak to another recruiter who later screens the same person.
-- email_normalized/phone_normalized are lowercased/digits-only derivations
-- (computed by upsert_candidate) used for cross-run candidate_comments
-- lookups, since the raw regex-extracted email/phone aren't consistently
-- formatted across different resume uploads of the same person.
CREATE TABLE IF NOT EXISTS candidates (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    email_normalized VARCHAR(255),
    phone_normalized VARCHAR(32),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_candidate_email (email),
    INDEX idx_candidates_email_normalized (email_normalized),
    INDEX idx_candidates_phone_normalized (phone_normalized)
);

CREATE TABLE IF NOT EXISTS candidate_rankings (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    run_id BIGINT NOT NULL,
    candidate_id BIGINT NOT NULL,
    first_pass_rank INT,
    final_rank INT,
    is_eligible BOOLEAN,
    first_pass_overall_score DECIMAL(5, 2),
    final_score DECIMAL(5, 2),
    skill_score DECIMAL(5, 2),
    experience_years_score DECIMAL(5, 2),
    experience_relevance_score DECIMAL(5, 2),
    seniority_fit VARCHAR(50),
    domain_fit VARCHAR(50),
    missing_must_haves_count INT,
    ranking_json JSON,
    -- Explicit recruiter-controlled toggle so a run's persisted candidates can
    -- be pruned to an actual shortlist, beyond whatever the pipeline
    -- auto-saved. Defaults true since everything persisted today already went
    -- through the review step.
    is_shortlisted BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES screening_runs(id),
    FOREIGN KEY (candidate_id) REFERENCES candidates(id)
);

CREATE TABLE IF NOT EXISTS score_evidence (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ranking_id BIGINT NOT NULL,
    score_type VARCHAR(100) NOT NULL,
    evidence_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ranking_id) REFERENCES candidate_rankings(id)
);

-- author_id scopes every comment to the recruiter who wrote it - reads MUST
-- filter by author_id = the requesting user, never just candidate_id, since
-- candidates is a global table shared across all recruiters (see its
-- comment above). is_caution is an explicit checkbox in addition to the free
-- text: the LLM reasons over comment_text too, but is_caution guarantees a
-- caution surfaces even when the model's read of ambiguous phrasing is soft.
-- Cross-run matching (does this candidate reappear in a later job listing)
-- is done by email_normalized/phone_normalized, not by this table directly -
-- it depends entirely on the candidate's contact info matching between runs;
-- see the candidates table comment and pipeline/shortlist_reranker.py.
CREATE TABLE IF NOT EXISTS candidate_comments (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    candidate_id BIGINT NOT NULL,
    author_id BIGINT NOT NULL,
    comment_text TEXT NOT NULL,
    is_caution BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id),
    FOREIGN KEY (author_id) REFERENCES users(id),
    INDEX idx_candidate_comments_lookup (candidate_id, author_id)
);

CREATE TABLE IF NOT EXISTS query_expansions (
    query_text VARCHAR(255) PRIMARY KEY,
    related_titles JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- owner_id is threaded through so the durable /pipeline/resume fallback path
-- (reads this row directly when the in-memory LangGraph checkpoint is gone)
-- still knows which recruiter to attribute the persisted screening_runs row
-- to, without trusting a client-supplied owner id.
CREATE TABLE IF NOT EXISTS pipeline_reviews (
    thread_id VARCHAR(64) PRIMARY KEY,
    jd JSON NOT NULL,
    candidates JSON NOT NULL,
    batch_ranking JSON NOT NULL,
    reranked JSON NOT NULL,
    run_name VARCHAR(255),
    source_file VARCHAR(500),
    top_n INT,
    owner_id BIGINT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'awaiting_review',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL,
    FOREIGN KEY (owner_id) REFERENCES users(id)
);

-- candidate_id is an opaque string, not a foreign key into `candidates` above (that
-- table is recruiter-side, keyed by email, populated from screening runs). Job
-- seeker identity is currently just a client-generated id stored in localStorage -
-- see docs/PROJECT_OBJECTIVES.md's job-search recommendation notes. Job details are
-- denormalized (job_title/company/location) rather than foreign-keyed, since the
-- source jobs (SerpApi/Bright Data results) aren't persisted anywhere else and can
-- disappear or change between searches.
CREATE TABLE IF NOT EXISTS candidate_job_events (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    candidate_id VARCHAR(64) NOT NULL,
    event_type ENUM('searched', 'viewed', 'applied', 'liked') NOT NULL,
    query_text VARCHAR(255),
    job_source VARCHAR(32),
    job_external_id VARCHAR(255),
    job_title VARCHAR(255),
    company VARCHAR(255),
    location VARCHAR(255),
    job_url VARCHAR(1024),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_candidate_events (candidate_id, event_type, created_at)
);

-- One saved resume per job-seeker account (latest wins, no versioning in v1).
-- parsed_resume mirrors the same candidate JSON shape already produced by
-- /upload/parse, so it can be fed straight into /analyze-profile-gap without
-- re-parsing.
CREATE TABLE IF NOT EXISTS job_seeker_profiles (
    user_id BIGINT PRIMARY KEY,
    resume_filename VARCHAR(500),
    parsed_resume JSON,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- One row per user per day, incremented each time a personalized-matches batch
-- scores N jobs. Enforces job_matching_service.JOB_MATCH_DAILY_LIMIT server-side
-- - the Mistral/Groq quotas backing this feature are shared org-wide, not
-- per-user, so without this a single active user could exhaust the platform's
-- shared LLM budget for everyone else.
CREATE TABLE IF NOT EXISTS job_match_usage (
    user_id BIGINT NOT NULL,
    usage_date DATE NOT NULL,
    jobs_scored INT NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, usage_date),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ---------------------------------------------------------------------------
-- Migrating an EXISTING database (e.g. the live TiDB Cloud instance) rather
-- than creating a fresh one: this script's CREATE TABLE IF NOT EXISTS
-- statements won't retroactively add new columns to tables that already
-- exist. Run these statements once, directly, against the existing DB
-- (see docs/deployment notes for the general "new column on an old table"
-- gotcha with this script):
--
-- ALTER TABLE screening_runs ADD COLUMN owner_id BIGINT NULL, ADD FOREIGN KEY (owner_id) REFERENCES users(id);
-- ALTER TABLE candidates ADD COLUMN email_normalized VARCHAR(255), ADD COLUMN phone_normalized VARCHAR(32);
-- ALTER TABLE candidate_rankings ADD COLUMN is_shortlisted BOOLEAN NOT NULL DEFAULT TRUE;
-- ALTER TABLE pipeline_reviews ADD COLUMN owner_id BIGINT NULL, ADD FOREIGN KEY (owner_id) REFERENCES users(id);
-- (users, candidate_comments, job_seeker_profiles, and the two new indexes on candidates
--  are wholly new tables/indexes, so the CREATE TABLE IF NOT EXISTS / regular index-creation
--  statements above already handle them - just run those statements directly.)
-- ---------------------------------------------------------------------------
