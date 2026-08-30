-- ============================================================
-- CreditGuardian AI - Database & Schema Setup
-- ============================================================

CREATE DATABASE IF NOT EXISTS CREDITGUARDIAN_AI;
CREATE SCHEMA IF NOT EXISTS CREDITGUARDIAN_AI.CORE;

USE DATABASE CREDITGUARDIAN_AI;
USE SCHEMA CORE;

-- Stages
CREATE STAGE IF NOT EXISTS MACRO_FEED_STAGE
    DIRECTORY = (ENABLE = TRUE)
    COMMENT = 'Landing stage for external macro-economic data feeds (CPI, inflation, rates, FX)';

CREATE STAGE IF NOT EXISTS REGULATORY_DOCS_STAGE
    DIRECTORY = (ENABLE = TRUE)
    COMMENT = 'Storage for regulatory policy documents (RBI circulars, Basel norms, IRAC guidelines)';

CREATE STAGE IF NOT EXISTS REGULATORY_PDF_STAGE
    DIRECTORY = (ENABLE = TRUE)
    ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE')
    COMMENT = 'SSE-encrypted stage for regulatory PDFs (required for PARSE_DOCUMENT compatibility)';

CREATE STAGE IF NOT EXISTS STREAMLIT_STAGE
    DIRECTORY = (ENABLE = TRUE)
    COMMENT = 'Stage for Streamlit application files';
