-- ============================================================
-- LOAD_REGULATORY_PDFS - Production-Grade PDF Ingestion Pipeline
-- Incremental, idempotent, error-resilient, chunked for large docs
-- ============================================================

CREATE OR REPLACE PROCEDURE CREDITGUARDIAN_AI.CORE.LOAD_REGULATORY_PDFS()
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
DECLARE
    v_run_id VARCHAR DEFAULT UUID_STRING();
    v_file_name VARCHAR;
    v_file_size NUMBER;
    v_file_hash VARCHAR;
    v_page_count NUMBER;
    v_parsed_text VARCHAR;
    v_files_detected NUMBER DEFAULT 0;
    v_files_new NUMBER DEFAULT 0;
    v_files_processed NUMBER DEFAULT 0;
    v_files_failed NUMBER DEFAULT 0;
    v_policies_before NUMBER DEFAULT 0;
    v_policies_after NUMBER DEFAULT 0;
    v_error_msg VARCHAR;
    v_chunk_start NUMBER;
    v_chunk_end NUMBER;
    v_chunk_size NUMBER DEFAULT 500;
    v_full_text VARCHAR;
    v_outer_error VARCHAR;
    
    c_files CURSOR FOR
        SELECT RELATIVE_PATH, SIZE, MD5
        FROM DIRECTORY(@CREDITGUARDIAN_AI.CORE.REGULATORY_PDF_STAGE)
        WHERE RELATIVE_PATH LIKE 'policies/%.pdf';
BEGIN
    -- ========================================================
    -- STEP 0: Initialize
    -- ========================================================
    INSERT INTO CREDITGUARDIAN_AI.CORE.PDF_PROCESSING_LOG (RUN_ID, STATUS)
    VALUES (:v_run_id, 'RUNNING');

    ALTER STAGE CREDITGUARDIAN_AI.CORE.REGULATORY_PDF_STAGE REFRESH;
    SELECT COUNT(*) INTO :v_policies_before FROM CREDITGUARDIAN_AI.CORE.REGULATORY_POLICIES;

    -- ========================================================
    -- STEP 1: Incremental file detection & parsing
    -- ========================================================
    FOR file_rec IN c_files DO
        v_file_name := file_rec.RELATIVE_PATH;
        v_file_size := file_rec.SIZE;
        v_file_hash := file_rec.MD5;
        v_files_detected := v_files_detected + 1;

        LET v_existing_count NUMBER := 0;
        SELECT COUNT(*) INTO :v_existing_count
        FROM CREDITGUARDIAN_AI.CORE.REGULATORY_DOCS_RAW
        WHERE FILE_NAME = :v_file_name
          AND FILE_HASH = :v_file_hash
          AND PROCESSING_STATUS = 'SUCCESS';

        IF (v_existing_count > 0) THEN
            CONTINUE;
        END IF;

        v_files_new := v_files_new + 1;

        BEGIN
            DELETE FROM CREDITGUARDIAN_AI.CORE.REGULATORY_DOCS_RAW
            WHERE FILE_NAME = :v_file_name;

            -- Get page count (cheap: parse only 1 page for metadata)
            SELECT SNOWFLAKE.CORTEX.PARSE_DOCUMENT(
                @CREDITGUARDIAN_AI.CORE.REGULATORY_PDF_STAGE,
                :v_file_name,
                {'mode': 'LAYOUT', 'page_filter': [{'start': 0, 'end': 1}]}
            ):metadata:pageCount::NUMBER INTO :v_page_count;

            IF (v_page_count <= 500) THEN
                -- Small/medium doc: single pass
                SELECT SNOWFLAKE.CORTEX.PARSE_DOCUMENT(
                    @CREDITGUARDIAN_AI.CORE.REGULATORY_PDF_STAGE,
                    :v_file_name,
                    {'mode': 'LAYOUT'}
                ):content::VARCHAR INTO :v_parsed_text;
            ELSE
                -- Large doc: chunked parsing via page_filter
                v_full_text := '';
                v_chunk_start := 0;
                WHILE (v_chunk_start < v_page_count) DO
                    v_chunk_end := LEAST(v_chunk_start + :v_chunk_size, v_page_count);
                    LET v_chunk_text VARCHAR := '';
                    SELECT SNOWFLAKE.CORTEX.PARSE_DOCUMENT(
                        @CREDITGUARDIAN_AI.CORE.REGULATORY_PDF_STAGE,
                        :v_file_name,
                        {'mode': 'LAYOUT', 'page_filter': [{'start': :v_chunk_start, 'end': :v_chunk_end}]}
                    ):content::VARCHAR INTO :v_chunk_text;
                    v_full_text := v_full_text || '\n\n' || v_chunk_text;
                    v_chunk_start := v_chunk_end;
                END WHILE;
                v_parsed_text := v_full_text;
            END IF;

            INSERT INTO CREDITGUARDIAN_AI.CORE.REGULATORY_DOCS_RAW 
                (FILE_NAME, FILE_URL, PARSED_TEXT, FILE_SIZE, FILE_HASH, PAGE_COUNT, PROCESSING_STATUS, PROCESSED_AT)
            VALUES (
                :v_file_name,
                BUILD_SCOPED_FILE_URL(@CREDITGUARDIAN_AI.CORE.REGULATORY_PDF_STAGE, :v_file_name),
                :v_parsed_text,
                :v_file_size,
                :v_file_hash,
                :v_page_count,
                'SUCCESS',
                CURRENT_TIMESTAMP()
            );
            v_files_processed := v_files_processed + 1;

        EXCEPTION
            WHEN OTHER THEN
                v_error_msg := SQLERRM;
                v_files_failed := v_files_failed + 1;
                INSERT INTO CREDITGUARDIAN_AI.CORE.REGULATORY_DOCS_RAW
                    (FILE_NAME, FILE_SIZE, FILE_HASH, PROCESSING_STATUS, ERROR_MESSAGE, PROCESSED_AT)
                VALUES (:v_file_name, :v_file_size, :v_file_hash, 'FAILED', :v_error_msg, CURRENT_TIMESTAMP());
        END;
    END FOR;

    -- ========================================================
    -- STEP 2: AI_EXTRACT on newly parsed docs
    -- ========================================================
    IF (v_files_processed > 0) THEN
        CREATE OR REPLACE TEMPORARY TABLE CREDITGUARDIAN_AI.CORE._TMP_REGULATORY_EXTRACTED AS
        SELECT 
            FILE_NAME, PARSED_TEXT,
            SNOWFLAKE.CORTEX.AI_EXTRACT(
                PARSED_TEXT,
                {
                    'title': 'The main title of the regulatory document',
                    'issuing_authority': 'The organization that issued the document',
                    'reference_number': 'The reference or circular number',
                    'effective_date': 'The date of issue or effective date in YYYY-MM-DD format',
                    'category': 'One of: ASSET_CLASSIFICATION, PROVISIONING, CAPITAL_ADEQUACY, EXPOSURE_LIMITS, RESOLUTION, INSOLVENCY'
                }
            ) AS EXTRACTED
        FROM CREDITGUARDIAN_AI.CORE.REGULATORY_DOCS_RAW
        WHERE PROCESSING_STATUS = 'SUCCESS'
          AND PROCESSED_AT >= DATEADD('HOUR', -1, CURRENT_TIMESTAMP());

        -- ========================================================
        -- STEP 3: Split on markdown ## headers → MERGE into REGULATORY_POLICIES
        -- ========================================================
        DELETE FROM CREDITGUARDIAN_AI.CORE.REGULATORY_POLICIES
        WHERE TITLE IN (
            SELECT EXTRACTED:response:title::VARCHAR 
            FROM CREDITGUARDIAN_AI.CORE._TMP_REGULATORY_EXTRACTED
        );

        INSERT INTO CREDITGUARDIAN_AI.CORE.REGULATORY_POLICIES 
            (POLICY_ID, TITLE, ISSUING_AUTHORITY, DOCUMENT_TYPE, SECTION, CONTENT,
             EFFECTIVE_DATE, REFERENCE_NUMBER, CATEGORY, RELEVANCE_TO_LENDING)
        SELECT 
            'REG' || LPAD(
                (COALESCE((SELECT MAX(TRY_TO_NUMBER(REPLACE(POLICY_ID, 'REG', ''))) FROM CREDITGUARDIAN_AI.CORE.REGULATORY_POLICIES), 0)
                 + ROW_NUMBER() OVER (ORDER BY e.FILE_NAME, s.INDEX))::VARCHAR,
                3, '0'
            ),
            e.EXTRACTED:response:title::VARCHAR,
            e.EXTRACTED:response:issuing_authority::VARCHAR,
            'Master Circular',
            TRIM(REGEXP_SUBSTR(s.VALUE::VARCHAR, '^[^\n]+')),
            TRIM(REGEXP_SUBSTR(s.VALUE::VARCHAR, '\n(.+)', 1, 1, 's', 1)),
            TRY_TO_DATE(e.EXTRACTED:response:effective_date::VARCHAR),
            e.EXTRACTED:response:reference_number::VARCHAR,
            e.EXTRACTED:response:category::VARCHAR,
            'Production pipeline | Run: ' || :v_run_id
        FROM CREDITGUARDIAN_AI.CORE._TMP_REGULATORY_EXTRACTED e,
            LATERAL FLATTEN(input => SPLIT(e.PARSED_TEXT, '## ')) s
        WHERE TRIM(s.VALUE::VARCHAR) != ''
          AND LENGTH(TRIM(s.VALUE::VARCHAR)) > 10;

        DROP TABLE IF EXISTS CREDITGUARDIAN_AI.CORE._TMP_REGULATORY_EXTRACTED;
    END IF;

    -- ========================================================
    -- STEP 4: Finalize log
    -- ========================================================
    SELECT COUNT(*) INTO :v_policies_after FROM CREDITGUARDIAN_AI.CORE.REGULATORY_POLICIES;

    LET v_error_summary VARCHAR := '';
    IF (v_files_failed > 0) THEN
        SELECT LISTAGG(FILE_NAME || ': ' || ERROR_MESSAGE, ' | ') INTO :v_error_summary
        FROM CREDITGUARDIAN_AI.CORE.REGULATORY_DOCS_RAW 
        WHERE PROCESSING_STATUS = 'FAILED';
    END IF;

    UPDATE CREDITGUARDIAN_AI.CORE.PDF_PROCESSING_LOG
    SET RUN_COMPLETED_AT = CURRENT_TIMESTAMP(),
        FILES_DETECTED = :v_files_detected,
        FILES_NEW = :v_files_new,
        FILES_PROCESSED = :v_files_processed,
        FILES_FAILED = :v_files_failed,
        POLICIES_LOADED = :v_policies_after - :v_policies_before,
        STATUS = CASE WHEN :v_files_failed > 0 THEN 'PARTIAL' ELSE 'SUCCESS' END,
        ERROR_SUMMARY = :v_error_summary
    WHERE RUN_ID = :v_run_id;

    RETURN 'Run ' || :v_run_id || ' complete. ' ||
           'Detected: ' || :v_files_detected || ' | ' ||
           'New: ' || :v_files_new || ' | ' ||
           'Processed: ' || :v_files_processed || ' | ' ||
           'Failed: ' || :v_files_failed || ' | ' ||
           'Policies loaded: ' || (:v_policies_after - :v_policies_before);

EXCEPTION
    WHEN OTHER THEN
        v_outer_error := SQLERRM;
        UPDATE CREDITGUARDIAN_AI.CORE.PDF_PROCESSING_LOG
        SET RUN_COMPLETED_AT = CURRENT_TIMESTAMP(),
            STATUS = 'FAILED',
            ERROR_SUMMARY = :v_outer_error
        WHERE RUN_ID = :v_run_id;
        RETURN 'Run ' || :v_run_id || ' FAILED: ' || :v_outer_error;
END;
$$;
