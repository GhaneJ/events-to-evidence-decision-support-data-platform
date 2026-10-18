SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    CREATE TABLE dbo.evidence_statement_derivation (
        statement_id NVARCHAR(128) NOT NULL,
        transformation_id NVARCHAR(128) NOT NULL,
        CONSTRAINT PK_evidence_statement_derivation
            PRIMARY KEY (statement_id, transformation_id),
        CONSTRAINT FK_evidence_statement_derivation_statement
            FOREIGN KEY (statement_id)
            REFERENCES dbo.evidence_statement(statement_id)
            ON DELETE CASCADE,
        CONSTRAINT FK_evidence_statement_derivation_transformation
            FOREIGN KEY (transformation_id)
            REFERENCES dbo.transformation(transformation_id)
    );

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;
    THROW;
END CATCH;
