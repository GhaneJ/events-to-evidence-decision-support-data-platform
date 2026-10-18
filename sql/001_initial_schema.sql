SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    CREATE TABLE dbo.investigation_question (
        question_id NVARCHAR(128) NOT NULL
            CONSTRAINT PK_investigation_question PRIMARY KEY,
        question_text NVARCHAR(MAX) NOT NULL,
        decision_context NVARCHAR(MAX) NOT NULL,
        status NVARCHAR(16) NOT NULL
            CONSTRAINT DF_investigation_question_status DEFAULT N'active',
        created_at DATETIMEOFFSET(7) NOT NULL
            CONSTRAINT DF_investigation_question_created_at DEFAULT SYSDATETIMEOFFSET(),
        CONSTRAINT CK_investigation_question_status
            CHECK (status IN (N'active', N'complete', N'deferred'))
    );

    CREATE TABLE dbo.evidence_family (
        evidence_family_id NVARCHAR(128) NOT NULL
            CONSTRAINT PK_evidence_family PRIMARY KEY,
        name NVARCHAR(256) NOT NULL,
        ancestry_note NVARCHAR(MAX) NOT NULL
    );

    CREATE TABLE dbo.[source] (
        source_id NVARCHAR(128) NOT NULL
            CONSTRAINT PK_source PRIMARY KEY,
        name NVARCHAR(256) NOT NULL,
        publisher NVARCHAR(256) NOT NULL,
        source_url NVARCHAR(2048) NOT NULL,
        source_kind NVARCHAR(64) NOT NULL,
        evidence_family_id NVARCHAR(128) NOT NULL,
        collection_method NVARCHAR(MAX) NOT NULL,
        created_at DATETIMEOFFSET(7) NOT NULL
            CONSTRAINT DF_source_created_at DEFAULT SYSDATETIMEOFFSET(),
        CONSTRAINT FK_source_evidence_family
            FOREIGN KEY (evidence_family_id)
            REFERENCES dbo.evidence_family(evidence_family_id)
    );

    CREATE TABLE dbo.ingestion_batch (
        batch_id NVARCHAR(128) NOT NULL
            CONSTRAINT PK_ingestion_batch PRIMARY KEY,
        source_id NVARCHAR(128) NOT NULL,
        endpoint NVARCHAR(1024) NOT NULL,
        request_parameters NVARCHAR(MAX) NOT NULL
            CONSTRAINT DF_ingestion_batch_request_parameters DEFAULT N'{}',
        retrieved_at DATETIMEOFFSET(7) NOT NULL,
        raw_path NVARCHAR(2048) NOT NULL,
        raw_sha256 CHAR(64) NOT NULL,
        record_count INT NOT NULL,
        created_at DATETIMEOFFSET(7) NOT NULL
            CONSTRAINT DF_ingestion_batch_created_at DEFAULT SYSDATETIMEOFFSET(),
        CONSTRAINT FK_ingestion_batch_source
            FOREIGN KEY (source_id)
            REFERENCES dbo.[source](source_id),
        CONSTRAINT CK_ingestion_batch_request_parameters_json
            CHECK (ISJSON(request_parameters) = 1),
        CONSTRAINT CK_ingestion_batch_record_count
            CHECK (record_count >= 0)
    );

    CREATE TABLE dbo.evidence_item (
        evidence_item_id NVARCHAR(128) NOT NULL
            CONSTRAINT PK_evidence_item PRIMARY KEY,
        source_id NVARCHAR(128) NOT NULL,
        batch_id NVARCHAR(128) NULL,
        source_record_id NVARCHAR(256) NOT NULL,
        observed_at DATETIMEOFFSET(7) NULL,
        retrieved_at DATETIMEOFFSET(7) NOT NULL,
        raw_fingerprint CHAR(64) NOT NULL,
        raw_location NVARCHAR(2048) NULL,
        is_synthetic_test BIT NOT NULL
            CONSTRAINT DF_evidence_item_is_synthetic_test DEFAULT 0,
        generated_by_ai BIT NOT NULL
            CONSTRAINT DF_evidence_item_generated_by_ai DEFAULT 0,
        created_at DATETIMEOFFSET(7) NOT NULL
            CONSTRAINT DF_evidence_item_created_at DEFAULT SYSDATETIMEOFFSET(),
        CONSTRAINT FK_evidence_item_source
            FOREIGN KEY (source_id)
            REFERENCES dbo.[source](source_id),
        CONSTRAINT FK_evidence_item_batch
            FOREIGN KEY (batch_id)
            REFERENCES dbo.ingestion_batch(batch_id),
        CONSTRAINT CK_evidence_item_no_ai_evidence
            CHECK (generated_by_ai = 0),
        CONSTRAINT UQ_evidence_item_source_record
            UNIQUE (source_id, source_record_id, raw_fingerprint)
    );

    CREATE TABLE dbo.transformation (
        transformation_id NVARCHAR(128) NOT NULL
            CONSTRAINT PK_transformation PRIMARY KEY,
        name NVARCHAR(256) NOT NULL,
        code_version NVARCHAR(128) NOT NULL,
        description NVARCHAR(MAX) NOT NULL,
        created_at DATETIMEOFFSET(7) NOT NULL
            CONSTRAINT DF_transformation_created_at DEFAULT SYSDATETIMEOFFSET()
    );

    CREATE TABLE dbo.transformation_input (
        transformation_id NVARCHAR(128) NOT NULL,
        evidence_item_id NVARCHAR(128) NOT NULL,
        CONSTRAINT PK_transformation_input
            PRIMARY KEY (transformation_id, evidence_item_id),
        CONSTRAINT FK_transformation_input_transformation
            FOREIGN KEY (transformation_id)
            REFERENCES dbo.transformation(transformation_id)
            ON DELETE CASCADE,
        CONSTRAINT FK_transformation_input_evidence_item
            FOREIGN KEY (evidence_item_id)
            REFERENCES dbo.evidence_item(evidence_item_id)
    );

    CREATE TABLE dbo.evidence_statement (
        statement_id NVARCHAR(128) NOT NULL
            CONSTRAINT PK_evidence_statement PRIMARY KEY,
        statement_text NVARCHAR(MAX) NOT NULL,
        direction NVARCHAR(16) NOT NULL,
        classification NVARCHAR(32) NOT NULL,
        created_at DATETIMEOFFSET(7) NOT NULL
            CONSTRAINT DF_evidence_statement_created_at DEFAULT SYSDATETIMEOFFSET(),
        CONSTRAINT CK_evidence_statement_direction
            CHECK (direction IN (N'support', N'conflict', N'context')),
        CONSTRAINT CK_evidence_statement_classification
            CHECK (
                classification IN (
                    N'observed_fact',
                    N'statistical_association',
                    N'supported_interpretation',
                    N'hypothesis',
                    N'contested_explanation',
                    N'unresolved_question'
                )
            )
    );

    CREATE TABLE dbo.statement_evidence (
        statement_id NVARCHAR(128) NOT NULL,
        evidence_item_id NVARCHAR(128) NOT NULL,
        CONSTRAINT PK_statement_evidence
            PRIMARY KEY (statement_id, evidence_item_id),
        CONSTRAINT FK_statement_evidence_statement
            FOREIGN KEY (statement_id)
            REFERENCES dbo.evidence_statement(statement_id)
            ON DELETE CASCADE,
        CONSTRAINT FK_statement_evidence_item
            FOREIGN KEY (evidence_item_id)
            REFERENCES dbo.evidence_item(evidence_item_id)
    );

    CREATE TABLE dbo.assessment (
        assessment_id NVARCHAR(128) NOT NULL
            CONSTRAINT PK_assessment PRIMARY KEY,
        question_id NVARCHAR(128) NOT NULL,
        classification NVARCHAR(32) NOT NULL,
        uncertainty NVARCHAR(MAX) NOT NULL,
        counter_evidence_checked BIT NOT NULL
            CONSTRAINT DF_assessment_counter_evidence_checked DEFAULT 0,
        created_at DATETIMEOFFSET(7) NOT NULL
            CONSTRAINT DF_assessment_created_at DEFAULT SYSDATETIMEOFFSET(),
        CONSTRAINT FK_assessment_question
            FOREIGN KEY (question_id)
            REFERENCES dbo.investigation_question(question_id),
        CONSTRAINT CK_assessment_classification
            CHECK (
                classification IN (
                    N'observed_fact',
                    N'statistical_association',
                    N'supported_interpretation',
                    N'hypothesis',
                    N'contested_explanation',
                    N'unresolved_question'
                )
            )
    );

    CREATE TABLE dbo.assessment_statement (
        assessment_id NVARCHAR(128) NOT NULL,
        statement_id NVARCHAR(128) NOT NULL,
        CONSTRAINT PK_assessment_statement
            PRIMARY KEY (assessment_id, statement_id),
        CONSTRAINT FK_assessment_statement_assessment
            FOREIGN KEY (assessment_id)
            REFERENCES dbo.assessment(assessment_id)
            ON DELETE CASCADE,
        CONSTRAINT FK_assessment_statement_statement
            FOREIGN KEY (statement_id)
            REFERENCES dbo.evidence_statement(statement_id)
    );

    CREATE TABLE dbo.decision_artifact (
        artifact_id NVARCHAR(128) NOT NULL
            CONSTRAINT PK_decision_artifact PRIMARY KEY,
        assessment_id NVARCHAR(128) NOT NULL,
        intended_use NVARCHAR(MAX) NOT NULL,
        generated_at DATETIMEOFFSET(7) NOT NULL
            CONSTRAINT DF_decision_artifact_generated_at DEFAULT SYSDATETIMEOFFSET(),
        CONSTRAINT FK_decision_artifact_assessment
            FOREIGN KEY (assessment_id)
            REFERENCES dbo.assessment(assessment_id)
    );

    CREATE INDEX IX_evidence_item_source_retrieved
        ON dbo.evidence_item (source_id, retrieved_at DESC);

    CREATE INDEX IX_assessment_question_created
        ON dbo.assessment (question_id, created_at DESC);

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;
    THROW;
END CATCH;
