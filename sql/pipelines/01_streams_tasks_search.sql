-- ============================================================
-- Streams, Tasks, and Cortex Search Service
-- Macro-economic data streaming + regulatory PDF ingestion
-- ============================================================

-- Stream: CDC on raw macro data
create or replace stream CREDITGUARDIAN_AI.CORE.MACRO_ECONOMIC_STREAM
    on table CREDITGUARDIAN_AI.CORE.MACRO_ECONOMIC_RAW
    append_only = true;

-- Task: Process macro data when stream has data (daily 6AM IST)
create or replace task CREDITGUARDIAN_AI.CORE.PROCESS_MACRO_DATA_TASK
    warehouse = SNOWHACK_WH
    schedule = 'USING CRON 0 6 * * * Asia/Kolkata'
    when SYSTEM$STREAM_HAS_DATA('CREDITGUARDIAN_AI.CORE.MACRO_ECONOMIC_STREAM')
as
BEGIN
    INSERT INTO CREDITGUARDIAN_AI.CORE.MACRO_ECONOMIC_INDICATORS
        (INDICATOR_ID, INDICATOR_NAME, INDICATOR_CATEGORY, VALUE, PREVIOUS_VALUE, CHANGE_PCT, UNIT, REPORT_DATE, FREQUENCY, SOURCE, REGION)
    SELECT
        RAW_DATA:indicator_id::VARCHAR,
        RAW_DATA:indicator_name::VARCHAR,
        RAW_DATA:category::VARCHAR,
        RAW_DATA:value::FLOAT,
        RAW_DATA:previous_value::FLOAT,
        RAW_DATA:change_pct::FLOAT,
        RAW_DATA:unit::VARCHAR,
        RAW_DATA:report_date::DATE,
        RAW_DATA:frequency::VARCHAR,
        RAW_DATA:source::VARCHAR,
        COALESCE(RAW_DATA:region::VARCHAR, 'India')
    FROM CREDITGUARDIAN_AI.CORE.MACRO_ECONOMIC_STREAM;

    ALTER DYNAMIC TABLE CREDITGUARDIAN_AI.CORE.RISK_SCORES REFRESH;
END;

-- Task: Daily regulatory PDF ingestion (6AM IST)
create or replace task CREDITGUARDIAN_AI.CORE.REGULATORY_PDF_LOAD_TASK
    warehouse = SNOWHACK_WH
    schedule = 'USING CRON 0 6 * * * Asia/Kolkata'
    COMMENT = 'Daily task to parse regulatory PDFs from stage and load into REGULATORY_POLICIES table'
as
    CALL CREDITGUARDIAN_AI.CORE.LOAD_REGULATORY_PDFS();

-- Cortex Search Service: Semantic search over regulatory policies
create or replace cortex search service CREDITGUARDIAN_AI.CORE.REGULATORY_SEARCH_SERVICE
    ON CONTENT
    attributes TITLE, ISSUING_AUTHORITY, SECTION, REFERENCE_NUMBER, CATEGORY
    warehouse = 'SNOWHACK_WH'
    target_lag = '1 hour'
    refresh_mode = INCREMENTAL
as (
    SELECT
        POLICY_ID, TITLE, ISSUING_AUTHORITY, DOCUMENT_TYPE,
        SECTION, CONTENT, REFERENCE_NUMBER, CATEGORY, RELEVANCE_TO_LENDING
    FROM CREDITGUARDIAN_AI.CORE.REGULATORY_POLICIES
);

-- Resume tasks (run after initial setup)
-- ALTER TASK CREDITGUARDIAN_AI.CORE.PROCESS_MACRO_DATA_TASK RESUME;
-- ALTER TASK CREDITGUARDIAN_AI.CORE.REGULATORY_PDF_LOAD_TASK RESUME;
