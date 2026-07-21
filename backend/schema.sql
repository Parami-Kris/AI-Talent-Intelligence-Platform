CREATE DATABASE IF NOT EXISTS ai_resume_screening;

USE ai_resume_screening;

CREATE TABLE IF NOT EXISTS screening_runs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    run_name VARCHAR(255) NOT NULL,
    job_title VARCHAR(255),
    ranking_rule TEXT,
    source_file VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS candidates (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_candidate_email (email)
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

CREATE TABLE IF NOT EXISTS query_expansions (
    query_text VARCHAR(255) PRIMARY KEY,
    related_titles JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pipeline_reviews (
    thread_id VARCHAR(64) PRIMARY KEY,
    jd JSON NOT NULL,
    candidates JSON NOT NULL,
    batch_ranking JSON NOT NULL,
    reranked JSON NOT NULL,
    run_name VARCHAR(255),
    source_file VARCHAR(500),
    top_n INT,
    status VARCHAR(20) NOT NULL DEFAULT 'awaiting_review',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_candidate_events (candidate_id, event_type, created_at)
);
