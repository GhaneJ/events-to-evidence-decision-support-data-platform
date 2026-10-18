SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    CREATE TABLE dbo.analytical_cohort (
        cohort_id NVARCHAR(128) NOT NULL
            CONSTRAINT PK_analytical_cohort PRIMARY KEY,
        source_id NVARCHAR(128) NOT NULL,
        name NVARCHAR(256) NOT NULL,
        selection_dimension NVARCHAR(64) NOT NULL,
        provider_concept_id NVARCHAR(128) NOT NULL,
        definition_note NVARCHAR(MAX) NOT NULL,
        created_at DATETIMEOFFSET(7) NOT NULL
            CONSTRAINT DF_analytical_cohort_created_at DEFAULT SYSDATETIMEOFFSET(),
        CONSTRAINT FK_analytical_cohort_source
            FOREIGN KEY (source_id)
            REFERENCES dbo.[source](source_id)
    );

    CREATE TABLE dbo.job_ad_observation (
        evidence_item_id NVARCHAR(128) NOT NULL
            CONSTRAINT PK_job_ad_observation PRIMARY KEY,
        headline NVARCHAR(MAX) NULL,
        occupation_concept_id NVARCHAR(128) NULL,
        occupation_label NVARCHAR(256) NULL,
        occupation_group_concept_id NVARCHAR(128) NULL,
        occupation_group_label NVARCHAR(256) NULL,
        occupation_field_concept_id NVARCHAR(128) NULL,
        occupation_field_label NVARCHAR(256) NULL,
        provider_experience_required BIT NULL,
        cohort_id NVARCHAR(128) NOT NULL,
        is_in_analytical_cohort BIT NOT NULL,
        experience_signal_status NVARCHAR(64) NULL,
        experience_audit_transformation_id NVARCHAR(128) NULL,
        created_at DATETIMEOFFSET(7) NOT NULL
            CONSTRAINT DF_job_ad_observation_created_at DEFAULT SYSDATETIMEOFFSET(),
        CONSTRAINT FK_job_ad_observation_evidence_item
            FOREIGN KEY (evidence_item_id)
            REFERENCES dbo.evidence_item(evidence_item_id),
        CONSTRAINT FK_job_ad_observation_cohort
            FOREIGN KEY (cohort_id)
            REFERENCES dbo.analytical_cohort(cohort_id),
        CONSTRAINT FK_job_ad_observation_experience_transformation
            FOREIGN KEY (experience_audit_transformation_id)
            REFERENCES dbo.transformation(transformation_id),
        CONSTRAINT CK_job_ad_observation_signal_status
            CHECK (
                experience_signal_status IS NULL
                OR experience_signal_status IN (
                    N'explicit_threshold_or_seniority',
                    N'qualitative_experience_only',
                    N'meritorious_experience_only',
                    N'unknown'
                )
            ),
        CONSTRAINT CK_job_ad_observation_audit_scope
            CHECK (
                (
                    is_in_analytical_cohort = 1
                    AND experience_signal_status IS NOT NULL
                    AND experience_audit_transformation_id IS NOT NULL
                )
                OR
                (
                    is_in_analytical_cohort = 0
                    AND experience_signal_status IS NULL
                    AND experience_audit_transformation_id IS NULL
                )
            )
    );

    CREATE TABLE dbo.job_ad_experience_signal (
        evidence_item_id NVARCHAR(128) NOT NULL,
        signal_ordinal INT NOT NULL,
        category NVARCHAR(64) NOT NULL,
        source_field NVARCHAR(128) NOT NULL,
        matched_text NVARCHAR(MAX) NOT NULL,
        snippet NVARCHAR(MAX) NOT NULL,
        CONSTRAINT PK_job_ad_experience_signal
            PRIMARY KEY (evidence_item_id, signal_ordinal),
        CONSTRAINT FK_job_ad_experience_signal_observation
            FOREIGN KEY (evidence_item_id)
            REFERENCES dbo.job_ad_observation(evidence_item_id)
            ON DELETE CASCADE,
        CONSTRAINT CK_job_ad_experience_signal_ordinal
            CHECK (signal_ordinal > 0),
        CONSTRAINT CK_job_ad_experience_signal_category
            CHECK (
                category IN (
                    N'quantified_experience',
                    N'qualitative_experience',
                    N'meritorious_experience',
                    N'seniority_language'
                )
            )
    );

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;
    THROW;
END CATCH;
