-- ============================================================
-- GENERATE_CREDIT_ASSESSMENT - AI-Powered Credit Assessment
-- Gathers borrower data + regulatory context → AI_COMPLETE narrative
-- ============================================================

CREATE OR REPLACE PROCEDURE CREDITGUARDIAN_AI.CORE.GENERATE_CREDIT_ASSESSMENT(P_CUSTOMER_ID VARCHAR)
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS CALLER
AS
$$
BEGIN
    LET v_assessment_id VARCHAR := 'CA-' || TO_VARCHAR(CURRENT_DATE(), 'YYYYMMDD') || '-' || :P_CUSTOMER_ID || '-' || TO_VARCHAR(UNIFORM(1000, 9999, RANDOM()));
    LET v_company_name VARCHAR;
    LET v_sector VARCHAR;
    LET v_industry VARCHAR;
    LET v_risk_score FLOAT;
    LET v_risk_grade VARCHAR;
    LET v_sma_category VARCHAR;
    LET v_key_risks VARCHAR;
    LET v_financials_text VARCHAR;
    LET v_repayment_text VARCHAR;
    LET v_industry_text VARCHAR;
    LET v_macro_text VARCHAR;
    LET v_search_results VARCHAR;
    LET v_prompt VARCHAR;
    LET v_narrative VARCHAR;
    LET v_ai_recommendation VARCHAR;

    -- Get risk classification
    SELECT COMPOSITE_SCORE, RISK_GRADE, SMA_CATEGORY, AI_LENDING_RECOMMENDATION, KEY_RISK_DRIVERS
    INTO :v_risk_score, :v_risk_grade, :v_sma_category, :v_ai_recommendation, :v_key_risks
    FROM CREDITGUARDIAN_AI.CORE.BORROWER_RISK_CLASSIFICATION
    WHERE CUSTOMER_ID = :P_CUSTOMER_ID;

    -- Get company info
    SELECT COMPANY_NAME, SECTOR, INDUSTRY
    INTO :v_company_name, :v_sector, :v_industry
    FROM CREDITGUARDIAN_AI.CORE.CUSTOMERS
    WHERE CUSTOMER_ID = :P_CUSTOMER_ID;

    -- Get latest financials
    SELECT 'Revenue: ' || TO_VARCHAR(REVENUE/1e7) || ' Cr, EBITDA: ' || TO_VARCHAR(EBITDA/1e7) || ' Cr, D/E: ' || TO_VARCHAR(DEBT_TO_EQUITY_RATIO) || ', ICR: ' || TO_VARCHAR(INTEREST_COVERAGE_RATIO) || 'x, NPM: ' || TO_VARCHAR(ROUND(NET_PROFIT_MARGIN*100,2)) || '%, FCF: ' || TO_VARCHAR(FREE_CASH_FLOW/1e7) || ' Cr'
    INTO :v_financials_text
    FROM (SELECT *, ROW_NUMBER() OVER (ORDER BY FISCAL_YEAR DESC) AS rn FROM CREDITGUARDIAN_AI.CORE.COMPANY_FINANCIALS WHERE CUSTOMER_ID = :P_CUSTOMER_ID)
    WHERE rn = 1;

    -- Get repayment summary
    SELECT 'Payments: ' || TO_VARCHAR(COUNT(*)) || ' total, On-time: ' || TO_VARCHAR(SUM(CASE WHEN PAYMENT_STATUS = 'ON_TIME' THEN 1 ELSE 0 END)) || ', Max overdue: ' || TO_VARCHAR(MAX(DAYS_OVERDUE)) || ' days'
    INTO :v_repayment_text
    FROM CREDITGUARDIAN_AI.CORE.LOAN_REPAYMENT
    WHERE CUSTOMER_ID = :P_CUSTOMER_ID;

    -- Get industry outlook
    SELECT 'Outlook: ' || OUTLOOK || ', Default Rate: ' || TO_VARCHAR(DEFAULT_RATE_PCT) || '%, Growth: ' || TO_VARCHAR(SECTOR_GROWTH_PCT) || '%'
    INTO :v_industry_text
    FROM (SELECT *, ROW_NUMBER() OVER (ORDER BY REPORT_DATE DESC) AS rn FROM CREDITGUARDIAN_AI.CORE.INDUSTRY_TRENDS WHERE SECTOR = :v_sector AND INDUSTRY = :v_industry)
    WHERE rn = 1;

    -- Get macro indicators
    SELECT 'CPI: ' || TO_VARCHAR(MAX(CASE WHEN INDICATOR_NAME = 'CPI_GENERAL' THEN VALUE END)) || '%, Repo: ' || TO_VARCHAR(MAX(CASE WHEN INDICATOR_NAME = 'REPO_RATE' THEN VALUE END)) || '%'
    INTO :v_macro_text
    FROM (SELECT INDICATOR_NAME, VALUE, ROW_NUMBER() OVER (PARTITION BY INDICATOR_NAME ORDER BY REPORT_DATE DESC) AS rn FROM CREDITGUARDIAN_AI.CORE.MACRO_ECONOMIC_INDICATORS) WHERE rn = 1;

    -- RAG: Search regulatory policies
    SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW('CREDITGUARDIAN_AI.CORE.REGULATORY_SEARCH_SERVICE', '{"query": "credit appraisal provisioning norms capital adequacy", "columns": ["TITLE","SECTION","CONTENT"], "limit": 2}')
    INTO :v_search_results;

    -- Build prompt and generate narrative
    v_prompt := 'You are a senior credit analyst at an Indian bank. Generate a credit assessment. BORROWER: ' || :v_company_name || ' (' || :v_industry || '). RISK SCORE: ' || TO_VARCHAR(:v_risk_score) || '/100 (Grade ' || :v_risk_grade || '). SMA: ' || :v_sma_category || '. RISKS: ' || COALESCE(:v_key_risks, 'None') || '. FINANCIALS: ' || COALESCE(:v_financials_text, 'N/A') || '. REPAYMENT: ' || COALESCE(:v_repayment_text, 'N/A') || '. INDUSTRY: ' || COALESCE(:v_industry_text, 'N/A') || '. MACRO: ' || COALESCE(:v_macro_text, 'N/A') || '. REGULATIONS: ' || LEFT(COALESCE(:v_search_results, ''), 1500) || '. Write: (1) Executive Summary (2) Financial Analysis (3) Risk Factors (4) Regulatory Compliance (5) RECOMMENDATION. Cite RBI norms.';

    v_narrative := SNOWFLAKE.CORTEX.COMPLETE('llama3.1-70b', :v_prompt);

    -- Store assessment with full audit trail
    INSERT INTO CREDITGUARDIAN_AI.CORE.CREDIT_ASSESSMENTS (ASSESSMENT_ID, CUSTOMER_ID, RISK_SCORE, RISK_GRADE, SMA_CATEGORY, AI_RECOMMENDATION, AI_NARRATIVE, REGULATORY_CITATIONS, CONFIDENCE_SCORE, MODEL_USED)
    VALUES (:v_assessment_id, :P_CUSTOMER_ID, :v_risk_score, :v_risk_grade, :v_sma_category, :v_ai_recommendation, :v_narrative, LEFT(:v_search_results, 2000), CASE WHEN :v_risk_score >= 80 THEN 0.95 WHEN :v_risk_score >= 60 THEN 0.85 WHEN :v_risk_score >= 40 THEN 0.70 ELSE 0.60 END, 'llama3.1-70b');

    RETURN 'Assessment generated: ' || :v_assessment_id || ' | Recommendation: ' || COALESCE(:v_ai_recommendation, 'PENDING') || ' | Score: ' || TO_VARCHAR(:v_risk_score);
END;
$$;
