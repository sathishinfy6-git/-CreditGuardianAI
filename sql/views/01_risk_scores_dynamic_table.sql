-- ============================================================
-- RISK_SCORES Dynamic Table
-- 7-component composite credit risk scoring model
-- Auto-refreshes with 1-hour target lag
-- ============================================================

create or replace dynamic table CREDITGUARDIAN_AI.CORE.RISK_SCORES(
    CUSTOMER_ID, COMPANY_NAME, SECTOR, INDUSTRY,
    FINANCIAL_HEALTH_SCORE, REPAYMENT_SCORE, CASHFLOW_BEHAVIOR_SCORE,
    COLLATERAL_SCORE, RATING_SCORE, INDUSTRY_SCORE, MACRO_ENVIRONMENT_SCORE,
    COMPOSITE_SCORE, RISK_GRADE, KEY_RISK_DRIVERS,
    CASHFLOW_RATIO, MIN_ACCOUNT_BALANCE, LATEST_CPI, LATEST_REPO_RATE, LATEST_NPA_RATIO,
    SCORED_AT
) target_lag = '1 hour' refresh_mode = AUTO initialize = ON_CREATE warehouse = SNOWHACK_WH
AS
WITH latest_financials AS (
    SELECT *,
        ROW_NUMBER() OVER (PARTITION BY CUSTOMER_ID ORDER BY FISCAL_YEAR DESC, FISCAL_QUARTER DESC) AS rn
    FROM CREDITGUARDIAN_AI.CORE.COMPANY_FINANCIALS
),
financial_scores AS (
    SELECT 
        CUSTOMER_ID,
        CASE WHEN DEBT_TO_EQUITY_RATIO < 0.5 THEN 10 WHEN DEBT_TO_EQUITY_RATIO < 1.0 THEN 8 WHEN DEBT_TO_EQUITY_RATIO < 1.5 THEN 6 WHEN DEBT_TO_EQUITY_RATIO < 2.5 THEN 4 WHEN DEBT_TO_EQUITY_RATIO < 4.0 THEN 2 ELSE 0 END AS de_score,
        CASE WHEN CURRENT_RATIO >= 2.0 THEN 8 WHEN CURRENT_RATIO >= 1.5 THEN 6 WHEN CURRENT_RATIO >= 1.2 THEN 4 WHEN CURRENT_RATIO >= 1.0 THEN 2 ELSE 0 END AS cr_score,
        CASE WHEN INTEREST_COVERAGE_RATIO >= 6.0 THEN 7 WHEN INTEREST_COVERAGE_RATIO >= 4.0 THEN 5 WHEN INTEREST_COVERAGE_RATIO >= 2.5 THEN 3 WHEN INTEREST_COVERAGE_RATIO >= 1.5 THEN 1 ELSE 0 END AS icr_score,
        CASE WHEN NET_PROFIT_MARGIN >= 0.15 THEN 5 WHEN NET_PROFIT_MARGIN >= 0.08 THEN 4 WHEN NET_PROFIT_MARGIN >= 0.04 THEN 3 WHEN NET_PROFIT_MARGIN >= 0.01 THEN 1 ELSE 0 END AS npm_score,
        DEBT_TO_EQUITY_RATIO, CURRENT_RATIO, INTEREST_COVERAGE_RATIO, NET_PROFIT_MARGIN
    FROM latest_financials WHERE rn = 1
),
repayment_scores AS (
    SELECT
        CUSTOMER_ID,
        MAX(DAYS_OVERDUE) AS max_days_overdue,
        ROUND(12.0 * SUM(CASE WHEN PAYMENT_STATUS = 'ON_TIME' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) AS ontime_score,
        CASE WHEN MAX(DAYS_OVERDUE) = 0 THEN 8 WHEN MAX(DAYS_OVERDUE) <= 15 THEN 6 WHEN MAX(DAYS_OVERDUE) <= 30 THEN 4 WHEN MAX(DAYS_OVERDUE) <= 60 THEN 2 ELSE 0 END AS overdue_score
    FROM CREDITGUARDIAN_AI.CORE.LOAN_REPAYMENT
    GROUP BY CUSTOMER_ID
),
cashflow_scores AS (
    SELECT
        CUSTOMER_ID,
        CASE WHEN SUM(CREDIT_AMOUNT) / NULLIF(SUM(DEBIT_AMOUNT), 0) >= 1.1 THEN 4 WHEN SUM(CREDIT_AMOUNT) / NULLIF(SUM(DEBIT_AMOUNT), 0) >= 1.0 THEN 3 WHEN SUM(CREDIT_AMOUNT) / NULLIF(SUM(DEBIT_AMOUNT), 0) >= 0.9 THEN 1 ELSE 0 END AS net_flow_score,
        CASE WHEN MIN(RUNNING_BALANCE) <= 0 THEN 0 WHEN MIN(RUNNING_BALANCE) / NULLIF(AVG(RUNNING_BALANCE), 0) >= 0.7 THEN 3 WHEN MIN(RUNNING_BALANCE) / NULLIF(AVG(RUNNING_BALANCE), 0) >= 0.4 THEN 2 ELSE 1 END AS balance_stability_score,
        CASE WHEN SUM(CASE WHEN RUNNING_BALANCE < 0 THEN 1 ELSE 0 END) = 0 THEN 3 WHEN SUM(CASE WHEN RUNNING_BALANCE < 0 THEN 1 ELSE 0 END) = 1 THEN 1 ELSE 0 END AS stress_score,
        MIN(RUNNING_BALANCE) AS min_balance,
        ROUND(SUM(CREDIT_AMOUNT) / NULLIF(SUM(DEBIT_AMOUNT), 0), 2) AS credit_debit_ratio
    FROM CREDITGUARDIAN_AI.CORE.BANK_TRANSACTIONS
    GROUP BY CUSTOMER_ID
),
collateral_scores AS (
    SELECT CUSTOMER_ID,
        CASE WHEN SUM(COLLATERAL_VALUE) / NULLIF(SUM(OUTSTANDING_BALANCE), 0) >= 2.0 THEN 13 WHEN SUM(COLLATERAL_VALUE) / NULLIF(SUM(OUTSTANDING_BALANCE), 0) >= 1.5 THEN 10 WHEN SUM(COLLATERAL_VALUE) / NULLIF(SUM(OUTSTANDING_BALANCE), 0) >= 1.2 THEN 7 WHEN SUM(COLLATERAL_VALUE) / NULLIF(SUM(OUTSTANDING_BALANCE), 0) >= 1.0 THEN 4 ELSE 2 END AS collateral_score
    FROM CREDITGUARDIAN_AI.CORE.LOAN_HISTORY WHERE LOAN_STATUS = 'ACTIVE'
    GROUP BY CUSTOMER_ID
),
rating_scores AS (
    SELECT CUSTOMER_ID, RATING, RATING_OUTLOOK,
        CASE WHEN RATING IN ('AAA','Aaa') THEN 10 WHEN RATING IN ('AA+','Aa1') THEN 9 WHEN RATING IN ('AA','Aa2') THEN 8 WHEN RATING IN ('AA-','Aa3') THEN 7 WHEN RATING IN ('A+','A1') THEN 6 WHEN RATING IN ('A','A2') THEN 6 WHEN RATING IN ('A-','A3','BBB+','Baa1') THEN 5 WHEN RATING IN ('BBB','Baa2') THEN 4 WHEN RATING IN ('BBB-','Baa3') THEN 3 WHEN RATING IN ('BB+','Ba1') THEN 2 WHEN RATING IN ('BB','Ba2','BB-','Ba3') THEN 1 ELSE 0 END AS rating_num_score,
        CASE WHEN RATING_OUTLOOK = 'Positive' THEN 3 WHEN RATING_OUTLOOK = 'Stable' THEN 2 WHEN RATING_OUTLOOK = 'Negative' THEN 0 ELSE 1 END AS outlook_score
    FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY CUSTOMER_ID ORDER BY RATING_DATE DESC) AS rn FROM CREDITGUARDIAN_AI.CORE.CREDIT_RATINGS) WHERE rn = 1
),
industry_scores AS (
    SELECT SECTOR, INDUSTRY,
        CASE WHEN DEFAULT_RATE_PCT < 1.0 THEN 4 WHEN DEFAULT_RATE_PCT < 2.0 THEN 3 WHEN DEFAULT_RATE_PCT < 3.5 THEN 2 WHEN DEFAULT_RATE_PCT < 5.0 THEN 1 ELSE 0 END AS default_rate_score,
        CASE WHEN OUTLOOK = 'POSITIVE' THEN 3 WHEN OUTLOOK = 'STABLE' THEN 2 WHEN OUTLOOK = 'WATCHLIST' THEN 1 WHEN OUTLOOK = 'NEGATIVE' THEN 0 ELSE 1 END AS industry_outlook_score,
        CASE WHEN REGULATORY_RISK_SCORE <= 2 THEN 3 WHEN REGULATORY_RISK_SCORE <= 3 THEN 2 WHEN REGULATORY_RISK_SCORE <= 5 THEN 1 ELSE 0 END AS reg_risk_score,
        OUTLOOK AS INDUSTRY_OUTLOOK, DEFAULT_RATE_PCT
    FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY SECTOR, INDUSTRY ORDER BY REPORT_DATE DESC) AS rn FROM CREDITGUARDIAN_AI.CORE.INDUSTRY_TRENDS) WHERE rn = 1
),
macro_scores AS (
    SELECT
        CASE WHEN MAX(CASE WHEN INDICATOR_NAME = 'CPI_GENERAL' THEN VALUE END) < 4.0 THEN 3 WHEN MAX(CASE WHEN INDICATOR_NAME = 'CPI_GENERAL' THEN VALUE END) < 5.5 THEN 2 WHEN MAX(CASE WHEN INDICATOR_NAME = 'CPI_GENERAL' THEN VALUE END) < 7.0 THEN 1 ELSE 0 END AS cpi_score,
        CASE WHEN MAX(CASE WHEN INDICATOR_NAME = 'REPO_RATE' THEN VALUE END) < 5.5 THEN 3 WHEN MAX(CASE WHEN INDICATOR_NAME = 'REPO_RATE' THEN VALUE END) < 6.5 THEN 2 WHEN MAX(CASE WHEN INDICATOR_NAME = 'REPO_RATE' THEN VALUE END) < 7.5 THEN 1 ELSE 0 END AS repo_score,
        CASE WHEN MAX(CASE WHEN INDICATOR_NAME = 'CREDIT_GROWTH_INDUSTRY' THEN VALUE END) >= 10 THEN 2 WHEN MAX(CASE WHEN INDICATOR_NAME = 'CREDIT_GROWTH_INDUSTRY' THEN VALUE END) >= 6 THEN 1 ELSE 0 END AS credit_growth_score,
        CASE WHEN MAX(CASE WHEN INDICATOR_NAME = 'GROSS_NPA_RATIO' THEN VALUE END) < 2.5 THEN 2 WHEN MAX(CASE WHEN INDICATOR_NAME = 'GROSS_NPA_RATIO' THEN VALUE END) < 4.0 THEN 1 ELSE 0 END AS system_npa_score,
        CASE WHEN MAX(CASE WHEN INDICATOR_NAME = 'INR_USD' THEN CHANGE_PCT END) < 1.0 THEN 2 WHEN MAX(CASE WHEN INDICATOR_NAME = 'INR_USD' THEN CHANGE_PCT END) < 3.0 THEN 1 ELSE 0 END AS fx_score,
        MAX(CASE WHEN INDICATOR_NAME = 'CPI_GENERAL' THEN VALUE END) AS LATEST_CPI,
        MAX(CASE WHEN INDICATOR_NAME = 'REPO_RATE' THEN VALUE END) AS LATEST_REPO_RATE,
        MAX(CASE WHEN INDICATOR_NAME = 'GROSS_NPA_RATIO' THEN VALUE END) AS LATEST_NPA_RATIO
    FROM (SELECT INDICATOR_NAME, VALUE, CHANGE_PCT, ROW_NUMBER() OVER (PARTITION BY INDICATOR_NAME ORDER BY REPORT_DATE DESC) AS rn FROM CREDITGUARDIAN_AI.CORE.MACRO_ECONOMIC_INDICATORS) WHERE rn = 1
)
SELECT
    c.CUSTOMER_ID, c.COMPANY_NAME, c.SECTOR, c.INDUSTRY,
    ROUND(COALESCE(f.de_score + f.cr_score + f.icr_score + f.npm_score, 0), 1) AS FINANCIAL_HEALTH_SCORE,
    ROUND(COALESCE(r.ontime_score + r.overdue_score, 0), 1) AS REPAYMENT_SCORE,
    COALESCE(cf.net_flow_score + cf.balance_stability_score + cf.stress_score, 0) AS CASHFLOW_BEHAVIOR_SCORE,
    COALESCE(col.collateral_score, 0) AS COLLATERAL_SCORE,
    COALESCE(rt.rating_num_score + rt.outlook_score, 0) AS RATING_SCORE,
    COALESCE(ind.default_rate_score + ind.industry_outlook_score + ind.reg_risk_score, 0) AS INDUSTRY_SCORE,
    COALESCE(m.cpi_score + m.repo_score + m.credit_growth_score + m.system_npa_score + m.fx_score, 0) AS MACRO_ENVIRONMENT_SCORE,
    ROUND(
        COALESCE(f.de_score + f.cr_score + f.icr_score + f.npm_score, 0) +
        COALESCE(r.ontime_score + r.overdue_score, 0) +
        COALESCE(cf.net_flow_score + cf.balance_stability_score + cf.stress_score, 0) +
        COALESCE(col.collateral_score, 0) +
        COALESCE(rt.rating_num_score + rt.outlook_score, 0) +
        COALESCE(ind.default_rate_score + ind.industry_outlook_score + ind.reg_risk_score, 0) +
        COALESCE(m.cpi_score + m.repo_score + m.credit_growth_score + m.system_npa_score + m.fx_score, 0)
    , 1) AS COMPOSITE_SCORE,
    CASE
        WHEN (COALESCE(f.de_score+f.cr_score+f.icr_score+f.npm_score,0)+COALESCE(r.ontime_score+r.overdue_score,0)+COALESCE(cf.net_flow_score+cf.balance_stability_score+cf.stress_score,0)+COALESCE(col.collateral_score,0)+COALESCE(rt.rating_num_score+rt.outlook_score,0)+COALESCE(ind.default_rate_score+ind.industry_outlook_score+ind.reg_risk_score,0)+COALESCE(m.cpi_score+m.repo_score+m.credit_growth_score+m.system_npa_score+m.fx_score,0)) >= 80 THEN 'A'
        WHEN (COALESCE(f.de_score+f.cr_score+f.icr_score+f.npm_score,0)+COALESCE(r.ontime_score+r.overdue_score,0)+COALESCE(cf.net_flow_score+cf.balance_stability_score+cf.stress_score,0)+COALESCE(col.collateral_score,0)+COALESCE(rt.rating_num_score+rt.outlook_score,0)+COALESCE(ind.default_rate_score+ind.industry_outlook_score+ind.reg_risk_score,0)+COALESCE(m.cpi_score+m.repo_score+m.credit_growth_score+m.system_npa_score+m.fx_score,0)) >= 60 THEN 'B'
        WHEN (COALESCE(f.de_score+f.cr_score+f.icr_score+f.npm_score,0)+COALESCE(r.ontime_score+r.overdue_score,0)+COALESCE(cf.net_flow_score+cf.balance_stability_score+cf.stress_score,0)+COALESCE(col.collateral_score,0)+COALESCE(rt.rating_num_score+rt.outlook_score,0)+COALESCE(ind.default_rate_score+ind.industry_outlook_score+ind.reg_risk_score,0)+COALESCE(m.cpi_score+m.repo_score+m.credit_growth_score+m.system_npa_score+m.fx_score,0)) >= 40 THEN 'C'
        WHEN (COALESCE(f.de_score+f.cr_score+f.icr_score+f.npm_score,0)+COALESCE(r.ontime_score+r.overdue_score,0)+COALESCE(cf.net_flow_score+cf.balance_stability_score+cf.stress_score,0)+COALESCE(col.collateral_score,0)+COALESCE(rt.rating_num_score+rt.outlook_score,0)+COALESCE(ind.default_rate_score+ind.industry_outlook_score+ind.reg_risk_score,0)+COALESCE(m.cpi_score+m.repo_score+m.credit_growth_score+m.system_npa_score+m.fx_score,0)) >= 20 THEN 'D'
        ELSE 'E'
    END AS RISK_GRADE,
    ARRAY_TO_STRING(ARRAY_COMPACT(ARRAY_CONSTRUCT(
        CASE WHEN COALESCE(f.de_score, 0) <= 4 THEN 'High leverage (D/E: ' || COALESCE(TO_VARCHAR(f.DEBT_TO_EQUITY_RATIO), 'N/A') || ')' END,
        CASE WHEN COALESCE(f.icr_score, 0) <= 3 THEN 'Weak interest coverage (' || COALESCE(TO_VARCHAR(f.INTEREST_COVERAGE_RATIO), 'N/A') || 'x)' END,
        CASE WHEN COALESCE(r.ontime_score, 0) < 10 THEN 'Repayment delays (max ' || COALESCE(TO_VARCHAR(r.max_days_overdue), '0') || ' days overdue)' END,
        CASE WHEN COALESCE(cf.net_flow_score, 0) <= 1 THEN 'Cash outflows exceed inflows (ratio: ' || COALESCE(TO_VARCHAR(cf.credit_debit_ratio), 'N/A') || ')' END,
        CASE WHEN COALESCE(cf.stress_score, 0) = 0 THEN 'Account stress: negative balance detected' END,
        CASE WHEN COALESCE(col.collateral_score, 0) <= 4 THEN 'Low collateral coverage' END,
        CASE WHEN COALESCE(ind.industry_outlook_score, 0) <= 1 THEN 'Adverse industry outlook (' || COALESCE(ind.INDUSTRY_OUTLOOK, 'N/A') || ')' END,
        CASE WHEN COALESCE(rt.rating_num_score, 0) <= 3 THEN 'Sub-investment grade rating (' || COALESCE(rt.RATING, 'N/A') || ')' END,
        CASE WHEN COALESCE(m.cpi_score, 0) = 0 THEN 'High inflation (CPI: ' || COALESCE(TO_VARCHAR(m.LATEST_CPI), 'N/A') || '%)' END
    )), '; ') AS KEY_RISK_DRIVERS,
    cf.credit_debit_ratio AS CASHFLOW_RATIO,
    cf.min_balance AS MIN_ACCOUNT_BALANCE,
    m.LATEST_CPI, m.LATEST_REPO_RATE, m.LATEST_NPA_RATIO,
    CURRENT_TIMESTAMP() AS SCORED_AT
FROM CREDITGUARDIAN_AI.CORE.CUSTOMERS c
LEFT JOIN financial_scores f ON c.CUSTOMER_ID = f.CUSTOMER_ID
LEFT JOIN repayment_scores r ON c.CUSTOMER_ID = r.CUSTOMER_ID
LEFT JOIN cashflow_scores cf ON c.CUSTOMER_ID = cf.CUSTOMER_ID
LEFT JOIN collateral_scores col ON c.CUSTOMER_ID = col.CUSTOMER_ID
LEFT JOIN rating_scores rt ON c.CUSTOMER_ID = rt.CUSTOMER_ID
LEFT JOIN industry_scores ind ON c.SECTOR = ind.SECTOR AND c.INDUSTRY = ind.INDUSTRY
CROSS JOIN macro_scores m;
