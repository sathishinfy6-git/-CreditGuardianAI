-- ============================================================
-- CREDIT_RISK_SIGNALS View
-- Uses Cortex AI_EXTRACT to generate risk signal narratives
-- ============================================================

create or replace view CREDITGUARDIAN_AI.CORE.CREDIT_RISK_SIGNALS AS
WITH borrower_profiles AS (
    SELECT 
        c.CUSTOMER_ID, c.COMPANY_NAME, c.SECTOR, c.INDUSTRY,
        'Company: ' || c.COMPANY_NAME || ' (' || c.INDUSTRY || '). ' ||
        'Financials: Revenue ' || COALESCE(TO_VARCHAR(f.REVENUE/1e7, '999,999') || ' Cr', 'N/A') || 
        ', EBITDA ' || COALESCE(TO_VARCHAR(f.EBITDA/1e7, '999,999') || ' Cr', 'N/A') ||
        ', Debt-to-Equity: ' || COALESCE(TO_VARCHAR(f.DEBT_TO_EQUITY_RATIO), 'N/A') ||
        ', Interest Coverage: ' || COALESCE(TO_VARCHAR(f.INTEREST_COVERAGE_RATIO), 'N/A') || 'x' ||
        ', Current Ratio: ' || COALESCE(TO_VARCHAR(f.CURRENT_RATIO), 'N/A') ||
        ', Net Profit Margin: ' || COALESCE(TO_VARCHAR(ROUND(f.NET_PROFIT_MARGIN * 100, 2)), 'N/A') || '%' ||
        ', Free Cash Flow: ' || COALESCE(TO_VARCHAR(f.FREE_CASH_FLOW/1e7, '999,999') || ' Cr', 'N/A') || '. ' ||
        'Loan Exposure: Outstanding ' || COALESCE(TO_VARCHAR(l.total_outstanding/1e7, '999,999') || ' Cr', 'N/A') ||
        ', Collateral: ' || COALESCE(TO_VARCHAR(l.total_collateral/1e7, '999,999') || ' Cr', 'N/A') || '. ' ||
        'Payment History: ' || COALESCE(TO_VARCHAR(r.on_time_pct) || '% on-time, max ' || TO_VARCHAR(r.max_overdue) || ' days overdue', 'No payment data') || '. ' ||
        'Industry Outlook: ' || COALESCE(it.OUTLOOK, 'N/A') || ', Default Rate: ' || COALESCE(TO_VARCHAR(it.DEFAULT_RATE_PCT), 'N/A') || '%.'
        AS profile_text
    FROM CREDITGUARDIAN_AI.CORE.CUSTOMERS c
    LEFT JOIN (SELECT *, ROW_NUMBER() OVER (PARTITION BY CUSTOMER_ID ORDER BY FISCAL_YEAR DESC) AS rn FROM CREDITGUARDIAN_AI.CORE.COMPANY_FINANCIALS) f ON c.CUSTOMER_ID = f.CUSTOMER_ID AND f.rn = 1
    LEFT JOIN (SELECT CUSTOMER_ID, SUM(OUTSTANDING_BALANCE) AS total_outstanding, SUM(COLLATERAL_VALUE) AS total_collateral FROM CREDITGUARDIAN_AI.CORE.LOAN_HISTORY WHERE LOAN_STATUS = 'ACTIVE' GROUP BY CUSTOMER_ID) l ON c.CUSTOMER_ID = l.CUSTOMER_ID
    LEFT JOIN (SELECT CUSTOMER_ID, ROUND(100.0 * SUM(CASE WHEN PAYMENT_STATUS = 'ON_TIME' THEN 1 ELSE 0 END) / COUNT(*), 1) AS on_time_pct, MAX(DAYS_OVERDUE) AS max_overdue FROM CREDITGUARDIAN_AI.CORE.LOAN_REPAYMENT GROUP BY CUSTOMER_ID) r ON c.CUSTOMER_ID = r.CUSTOMER_ID
    LEFT JOIN (SELECT *, ROW_NUMBER() OVER (PARTITION BY SECTOR, INDUSTRY ORDER BY REPORT_DATE DESC) AS rn FROM CREDITGUARDIAN_AI.CORE.INDUSTRY_TRENDS) it ON c.SECTOR = it.SECTOR AND c.INDUSTRY = it.INDUSTRY AND it.rn = 1
)
SELECT
    CUSTOMER_ID, COMPANY_NAME, SECTOR, INDUSTRY, profile_text,
    SNOWFLAKE.CORTEX.AI_EXTRACT(
        profile_text,
        ['debt_sustainability', 'liquidity_risk', 'repayment_risk', 'collateral_adequacy', 'revenue_stability', 'overall_risk_narrative']
    ) AS risk_signals_raw,
    risk_signals_raw:response:debt_sustainability::VARCHAR AS DEBT_SUSTAINABILITY,
    risk_signals_raw:response:liquidity_risk::VARCHAR AS LIQUIDITY_RISK,
    risk_signals_raw:response:repayment_risk::VARCHAR AS REPAYMENT_RISK,
    risk_signals_raw:response:collateral_adequacy::VARCHAR AS COLLATERAL_ADEQUACY,
    risk_signals_raw:response:revenue_stability::VARCHAR AS REVENUE_STABILITY,
    risk_signals_raw:response:overall_risk_narrative::VARCHAR AS OVERALL_RISK_NARRATIVE
FROM borrower_profiles;
