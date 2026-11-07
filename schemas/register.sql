PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS sources (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS opportunities (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events (
 id TEXT PRIMARY KEY,
 opportunity_id TEXT NOT NULL REFERENCES opportunities(id),
 dimension TEXT NOT NULL,
 event_date TEXT NOT NULL,
 payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS event_evidence (
 event_id TEXT REFERENCES events(id),
 source_id TEXT REFERENCES sources(id),
 payload TEXT NOT NULL,
 PRIMARY KEY(event_id,source_id)
);
CREATE TABLE IF NOT EXISTS current_state (
 opportunity_id TEXT REFERENCES opportunities(id),
 dimension TEXT NOT NULL,
 event_date TEXT NOT NULL,
 value_json TEXT NOT NULL,
 event_id TEXT REFERENCES events(id),
 conflict INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(opportunity_id,dimension)
);
CREATE TABLE IF NOT EXISTS source_health (
 run_id TEXT NOT NULL,
 source_id TEXT REFERENCES sources(id),
 success INTEGER NOT NULL,
 error TEXT,
 PRIMARY KEY(run_id,source_id)
);
-- Extensions for the live implementation. The demo uses immutable event
-- payloads for claims, and manually resolved opportunity and source IDs.
CREATE TABLE IF NOT EXISTS documents (
 id TEXT PRIMARY KEY, source_id TEXT REFERENCES sources(id),
 canonical_url TEXT NOT NULL, fetched_at TEXT NOT NULL,
 published_at TEXT, sha256 TEXT NOT NULL, content_path TEXT,
 language TEXT, parser_version TEXT, fetch_status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS entities (
 id TEXT PRIMARY KEY, legal_name TEXT NOT NULL, country TEXT,
 aliases_json TEXT NOT NULL, canadian_nexus_json TEXT NOT NULL,
 identifiers_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS claims (
 id TEXT PRIMARY KEY, document_id TEXT REFERENCES documents(id),
 subject_id TEXT REFERENCES entities(id), predicate TEXT NOT NULL,
 object_json TEXT NOT NULL, locator TEXT NOT NULL,
 original_support_span TEXT NOT NULL, english_rendering TEXT,
 event_date TEXT, effective_date TEXT, expires_on TEXT,
 evidence_status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reviews (
 id TEXT PRIMARY KEY, opportunity_id TEXT REFERENCES opportunities(id),
 reviewer TEXT NOT NULL, reviewed_at TEXT NOT NULL,
 decision TEXT NOT NULL, rationale TEXT NOT NULL
);
