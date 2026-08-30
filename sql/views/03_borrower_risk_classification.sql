-- ============================================================
-- BORROWER_RISK_CLASSIFICATION View
-- SMA classification (RBI IRAC norms) + AI lending recommendation
-- ============================================================

create or replace view CREDITGUARDIAN_AI.CORE.BORROWER_RISK_CLASSIFICATION AS
WITH borrower_context AS (
    SELECT 
        c.CUSTOMER_ID, c.COMPANY_NAME, c.SECTOR, c.INDUSTRY,
        rs.COMPOSITE_SCORE, rs.RISK_GRADE, rs.KEY_RISK_DRIVERS,
        COALESCE(r.max_overdue, 0) AS max_days_overdue,
        COALESCE(r.on_time_pct, 0) AS on_time_pct,
        c.COMPANY_NAME || ' (' || c.INDUSTRY || '): ' ||
        'Risk Score ' || COALESCE(TO_VARCHAR(rs.COMPOSITE_SCORE), 'N/A') || '/100 (Grade ' || COALESCE(rs.RISK_GRADE, 'N/A') || '). ' ||
        'Max days overdue: ' || COALESCE(TO_VARCHAR(r.max_overdue), '0') || '. ' ||
        'D/E Ratio: ' || COALESCE(TO_VARCHAR(f.DEBT_TO_EQUITY_RATIO), 'N/A') || '. ' ||
        'Interest Coverage: ' || COALESCE(TO_VARCHAR(f.INTEREST_COVERAGE_RATIO), 'N/A') || 'x. ' ||
        'Payment on-time rate: ' || COALESCE(TO_VARCHAR(r.on_time_pct), '0') || '%. ' ||
        'Key risks: ' || COALESCE(rs.KEY_RISK_DRIVERS, 'None identified') || '.'
        AS classification_text
    FROM CREDITGUARDIAN_AI.CORE.CUSTOMERS c
    LEFT JOIN CREDITGUARDIAN_AI.CORE.RISK_SCORES rs ON c.CUSTOMER_ID = rs.CUSTOMER_ID
    LEFT JOIN (SELECT CUSTOMER_ID, ROUND(100.0 * SUM(CASE WHEN PAYMENT_STATUS = 'ON_TIME' THEN 1 ELSE 0 END) / COUNT(*), 1) AS on_time_pct, MAX(DAYS_OVERDUE) AS max_overdue FROM CREDITGUARDIAN_AI.CORE.LOAN_REPAYMENT GROUP BY CUSTOMER_ID) r ON c.CUSTOMER_ID = r.CUSTOMER_ID
    LEFT JOIN (SELECT *, ROW_NUMBER() OVER (PARTITION BY CUSTOMER_ID ORDER BY FISCAL_YEAR DESC) AS rn FROM CREDITGUARDIAN_AI.CORE.COMPANY_FINANCIALS) f ON c.CUSTOMER_ID = f.CUSTOMER_ID AND f.rn = 1
)
SELECT
    CUSTOMER_ID, COMPANY_NAME, SECTOR, INDUSTRY,
    COMPOSITE_SCORE, RISK_GRADE, max_days_overdue, on_time_pct,
    CASE
        WHEN max_days_overdue > 90 THEN 'NPA'
        WHEN max_days_overdue > 60 THEN 'SMA_2'
        WHEN max_days_overdue > 30 THEN 'SMA_1'
        WHEN max_days_overdue > 0 OR COMPOSITE_SCORE < 40 THEN 'SMA_0'
        ELSE 'STANDARD'
    END AS SMA_CATEGORY,
    SNOWFLAKE.CORTEX.AI_CLASSIFY(
        classification_text,
        ['APPROVE', 'CONDITIONAL_APPROVE', 'ESCALATE', 'REJECT']
    ):labels[0]::VARCHAR AS AI_LENDING_RECOMMENDATION,
    KEY_RISK_DRIVERS
FROM borrower_context;
