BEGIN;

CREATE TABLE investigation_question (
    question_id TEXT PRIMARY KEY,
    question_text TEXT NOT NULL,
    decision_context TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'complete', 'deferred')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE evidence_family (
    evidence_family_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    ancestry_note TEXT NOT NULL
);

CREATE TABLE source (
    source_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    publisher TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    evidence_family_id TEXT NOT NULL REFERENCES evidence_family(evidence_family_id),
    collection_method TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE ingestion_batch (
    batch_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES source(source_id),
    endpoint TEXT NOT NULL,
    request_parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    retrieved_at TIMESTAMPTZ NOT NULL,
    raw_path TEXT NOT NULL,
    raw_sha256 CHAR(64) NOT NULL,
    record_count INTEGER NOT NULL CHECK (record_count >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE evidence_item (
    evidence_item_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES source(source_id),
    batch_id TEXT REFERENCES ingestion_batch(batch_id),
    source_record_id TEXT NOT NULL,
    observed_at TIMESTAMPTZ,
    retrieved_at TIMESTAMPTZ NOT NULL,
    raw_fingerprint CHAR(64) NOT NULL,
    raw_location TEXT,
    is_synthetic_test BOOLEAN NOT NULL DEFAULT FALSE,
    generated_by_ai BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT evidence_item_no_ai_evidence CHECK (generated_by_ai = FALSE),
    CONSTRAINT uq_evidence_item_source_record UNIQUE (source_id, source_record_id, raw_fingerprint)
);

CREATE TABLE transformation (
    transformation_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    code_version TEXT NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE transformation_input (
    transformation_id TEXT NOT NULL REFERENCES transformation(transformation_id) ON DELETE CASCADE,
    evidence_item_id TEXT NOT NULL REFERENCES evidence_item(evidence_item_id),
    PRIMARY KEY (transformation_id, evidence_item_id)
);

CREATE TABLE evidence_statement (
    statement_id TEXT PRIMARY KEY,
    statement_text TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('support', 'conflict', 'context')),
    classification TEXT NOT NULL CHECK (
        classification IN (
            'observed_fact',
            'statistical_association',
            'supported_interpretation',
            'hypothesis',
            'contested_explanation',
            'unresolved_question'
        )
    ),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE statement_evidence (
    statement_id TEXT NOT NULL REFERENCES evidence_statement(statement_id) ON DELETE CASCADE,
    evidence_item_id TEXT NOT NULL REFERENCES evidence_item(evidence_item_id),
    PRIMARY KEY (statement_id, evidence_item_id)
);

CREATE TABLE assessment (
    assessment_id TEXT PRIMARY KEY,
    question_id TEXT NOT NULL REFERENCES investigation_question(question_id),
    classification TEXT NOT NULL CHECK (
        classification IN (
            'observed_fact',
            'statistical_association',
            'supported_interpretation',
            'hypothesis',
            'contested_explanation',
            'unresolved_question'
        )
    ),
    uncertainty TEXT NOT NULL,
    counter_evidence_checked BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE assessment_statement (
    assessment_id TEXT NOT NULL REFERENCES assessment(assessment_id) ON DELETE CASCADE,
    statement_id TEXT NOT NULL REFERENCES evidence_statement(statement_id),
    PRIMARY KEY (assessment_id, statement_id)
);

CREATE TABLE decision_artifact (
    artifact_id TEXT PRIMARY KEY,
    assessment_id TEXT NOT NULL REFERENCES assessment(assessment_id),
    intended_use TEXT NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_evidence_item_source_retrieved
    ON evidence_item (source_id, retrieved_at DESC);

CREATE INDEX idx_assessment_question_created
    ON assessment (question_id, created_at DESC);

COMMIT;
