SCHEMA_SQL = r"""
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL CHECK (source_type IN
        ('podcast_transcript','newsletter','report','article','note','other')),
    title TEXT NOT NULL,
    publisher TEXT,
    published_at TEXT,
    language TEXT NOT NULL DEFAULT 'da',
    original_path TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    sha256 TEXT NOT NULL UNIQUE,
    imported_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS extraction_runs (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    model TEXT,
    schema_version TEXT NOT NULL,
    extracted_at TEXT NOT NULL,
    imported_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS claims (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    run_id TEXT REFERENCES extraction_runs(id) ON DELETE SET NULL,
    fingerprint TEXT NOT NULL,
    claim_type TEXT NOT NULL CHECK (claim_type IN
        ('company_view','theme','macroeconomic','forecast','risk','mention')),
    summary TEXT NOT NULL,
    speaker TEXT,
    sentiment TEXT NOT NULL CHECK (sentiment IN
        ('positive','neutral','negative','mixed','unclear')),
    action TEXT NOT NULL CHECK (action IN
        ('owns','buying','hold','reduce','sold','watch','avoid','none','unclear')),
    time_horizon TEXT NOT NULL CHECK (time_horizon IN
        ('short_term','medium_term','long_term','unspecified')),
    discussion_depth TEXT NOT NULL CHECK (discussion_depth IN
        ('brief','moderate','detailed')),
    confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    review_status TEXT NOT NULL CHECK (review_status IN
        ('ai_extracted','approved','corrected','uncertain','rejected')),
    review_note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(source_id, fingerprint)
);

CREATE TABLE IF NOT EXISTS companies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    ticker TEXT,
    normalized_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS claim_companies (
    claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    company_id TEXT NOT NULL REFERENCES companies(id),
    role TEXT NOT NULL DEFAULT 'discussed' CHECK (role IN
        ('primary','discussed','comparison','mention')),
    PRIMARY KEY (claim_id, company_id)
);

CREATE TABLE IF NOT EXISTS themes (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS claim_themes (
    claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    theme_id TEXT NOT NULL REFERENCES themes(id),
    PRIMARY KEY (claim_id, theme_id)
);

CREATE TABLE IF NOT EXISTS claim_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    point_type TEXT NOT NULL CHECK (point_type IN
        ('thesis','risk','catalyst','condition')),
    position INTEGER NOT NULL,
    text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence (
    claim_id TEXT PRIMARY KEY REFERENCES claims(id) ON DELETE CASCADE,
    excerpt TEXT,
    start_ref TEXT,
    end_ref TEXT
);

CREATE INDEX IF NOT EXISTS idx_claims_source ON claims(source_id);
CREATE INDEX IF NOT EXISTS idx_claims_review ON claims(review_status, confidence);
CREATE INDEX IF NOT EXISTS idx_claim_points_claim ON claim_points(claim_id);
"""

