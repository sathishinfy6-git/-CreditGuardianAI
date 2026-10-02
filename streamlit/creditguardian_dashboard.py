import streamlit as st
from snowflake.snowpark.context import get_active_session
import pandas as pd
import json

session = get_active_session()

st.set_page_config(page_title="CreditGuardian AI", page_icon="🛡️", layout="wide")

# ─── ENTERPRISE STYLING ───
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    .block-container { padding-top: 1rem; max-width: 1400px; }
    .main-header {
        font-size: 1.8rem; font-weight: 700; color: #0F172A;
        margin-bottom: 0; letter-spacing: -0.02em;
    }
    .sub-header {
        font-size: 0.95rem; color: #64748B; margin-bottom: 1.2rem; font-weight: 400;
    }
    .kpi-card {
        background: linear-gradient(135deg, #1E293B 0%, #334155 100%);
        padding: 1rem 1.2rem; border-radius: 10px; color: white; text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.12);
    }
    .kpi-card-warn {
        background: linear-gradient(135deg, #DC2626 0%, #EF4444 100%);
        padding: 1rem 1.2rem; border-radius: 10px; color: white; text-align: center;
        box-shadow: 0 2px 8px rgba(220,38,38,0.25);
    }
    .kpi-card-success {
        background: linear-gradient(135deg, #059669 0%, #10B981 100%);
        padding: 1rem 1.2rem; border-radius: 10px; color: white; text-align: center;
        box-shadow: 0 2px 8px rgba(5,150,105,0.25);
    }
    .kpi-label { font-size: 0.75rem; font-weight: 500; opacity: 0.85; margin: 0; text-transform: uppercase; letter-spacing: 0.05em; }
    .kpi-value { font-size: 1.8rem; font-weight: 700; margin: 0.2rem 0 0 0; }
    .divider { border-top: 1px solid #E2E8F0; margin: 1.5rem 0 1rem 0; }
    .risk-badge { display: inline-block; padding: 2px 10px; border-radius: 4px; font-weight: 600; font-size: 0.85rem; }
    .risk-a { background: #D1FAE5; color: #065F46; }
    .risk-b { background: #DBEAFE; color: #1E40AF; }
    .risk-c { background: #FEF3C7; color: #92400E; }
    .risk-d { background: #FEE2E2; color: #991B1B; }
    .risk-e { background: #7C2D12; color: white; }
    .ai-response { background: #F8FAFC; border-left: 4px solid #3B82F6; padding: 1.2rem; border-radius: 0 8px 8px 0; margin: 1rem 0; }
    .ai-response h1, .ai-response h2, .ai-response h3 { color: #1E293B; }
    .ai-response table { width: 100%; border-collapse: collapse; margin: 0.8rem 0; }
    .ai-response th { background: #E2E8F0; padding: 6px 10px; text-align: left; font-size: 0.85rem; }
    .ai-response td { padding: 6px 10px; border-bottom: 1px solid #E2E8F0; font-size: 0.85rem; }
    .sidebar .sidebar-content { background: #0F172A; }
    .stRadio > div { gap: 0.2rem; }
    .status-pill { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
    .status-active { background: #D1FAE5; color: #065F46; }
    .status-npa { background: #FEE2E2; color: #991B1B; }
    .status-pending { background: #FEF3C7; color: #92400E; }
</style>
""", unsafe_allow_html=True)

# ─── SIDEBAR ───
with st.sidebar:
    st.markdown("### 🛡️ CreditGuardian AI")
    st.caption("Enterprise Credit Risk & Regulatory Intelligence Platform")
    st.markdown("---")
    page = st.radio("Navigation", [
        "📊 Portfolio Overview",
        "🔍 Borrower Deep Dive",
        "📋 Loan Applications",
        "🌐 Macro & Industry",
        "🤖 AI Risk Advisor",
        "📜 Regulatory Policies"
    ], label_visibility="collapsed")
    st.markdown("---")
    st.markdown("**Platform Info**")
    st.caption("Database: CREDITGUARDIAN_AI")
    st.caption("AI Models: Cortex LLM")
    st.caption("Refresh: Dynamic Tables (1hr)")
    st.caption("RAG: Cortex Search (20 policies)")
    st.markdown("---")
    st.caption("v2.0 | Powered by Snowflake Cortex AI")

# ═══════════════════════════════════════════
# PAGE 1: PORTFOLIO OVERVIEW
# ═══════════════════════════════════════════
if page == "📊 Portfolio Overview":
    st.markdown('<p class="main-header">Portfolio Risk Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Enterprise-wide credit risk monitoring with AI-powered early warning signals | 25 borrowers across 9 sectors</p>', unsafe_allow_html=True)

    risk_df = session.sql("SELECT * FROM CREDITGUARDIAN_AI.CORE.RISK_SCORES ORDER BY COMPOSITE_SCORE DESC").to_pandas()
    exposure_df = session.sql("SELECT SUM(OUTSTANDING_BALANCE) AS total_exp, SUM(CASE WHEN LOAN_STATUS='NPA' THEN OUTSTANDING_BALANCE ELSE 0 END) AS npa_exp, COUNT(DISTINCT CUSTOMER_ID) AS active_borrowers FROM CREDITGUARDIAN_AI.CORE.LOAN_HISTORY").to_pandas()

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(f'<div class="kpi-card"><p class="kpi-label">Total Borrowers</p><p class="kpi-value">{len(risk_df)}</p></div>', unsafe_allow_html=True)
    with col2:
        avg_score = risk_df['COMPOSITE_SCORE'].mean()
        st.markdown(f'<div class="kpi-card"><p class="kpi-label">Avg Risk Score</p><p class="kpi-value">{avg_score:.0f}/100</p></div>', unsafe_allow_html=True)
    with col3:
        high_risk = len(risk_df[risk_df['RISK_GRADE'].isin(['D','E'])])
        card_cls = "kpi-card-warn" if high_risk > 0 else "kpi-card"
        st.markdown(f'<div class="{card_cls}"><p class="kpi-label">High Risk (D+E)</p><p class="kpi-value">{high_risk}</p></div>', unsafe_allow_html=True)
    with col4:
        total_exp = exposure_df['TOTAL_EXP'].iloc[0] / 1e9 if exposure_df['TOTAL_EXP'].iloc[0] else 0
        st.markdown(f'<div class="kpi-card"><p class="kpi-label">Total Exposure</p><p class="kpi-value">₹{total_exp:.1f}B</p></div>', unsafe_allow_html=True)
    with col5:
        npa_exp = exposure_df['NPA_EXP'].iloc[0] / 1e9 if exposure_df['NPA_EXP'].iloc[0] else 0
        st.markdown(f'<div class="kpi-card-warn"><p class="kpi-label">NPA Exposure</p><p class="kpi-value">₹{npa_exp:.1f}B</p></div>', unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("Risk Grade Distribution")
        grade_counts = risk_df.groupby('RISK_GRADE').size().reset_index(name='Count').sort_values('RISK_GRADE')
        st.bar_chart(grade_counts.set_index('RISK_GRADE'))

    with col_right:
        st.subheader("SMA Category Breakdown")
        sma_df = session.sql("""
            SELECT Category, COUNT(DISTINCT CUSTOMER_ID) AS Count FROM (
                SELECT CUSTOMER_ID,
                    CASE WHEN MAX(DAYS_OVERDUE) > 90 THEN 'NPA'
                         WHEN MAX(DAYS_OVERDUE) > 60 THEN 'SMA-2'
                         WHEN MAX(DAYS_OVERDUE) > 30 THEN 'SMA-1'
                         WHEN MAX(DAYS_OVERDUE) > 0 THEN 'SMA-0'
                         ELSE 'Standard' END AS Category
                FROM CREDITGUARDIAN_AI.CORE.LOAN_REPAYMENT GROUP BY CUSTOMER_ID
            ) GROUP BY Category ORDER BY Count DESC
        """).to_pandas()
        st.bar_chart(sma_df.set_index('CATEGORY'))

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.subheader("Sector Risk Heatmap")
    sector_df = risk_df.groupby('SECTOR').agg(
        Borrowers=('CUSTOMER_ID', 'count'),
        Avg_Score=('COMPOSITE_SCORE', 'mean'),
        Min_Score=('COMPOSITE_SCORE', 'min'),
        High_Risk=('RISK_GRADE', lambda x: (x.isin(['D','E'])).sum())
    ).round(1).sort_values('Avg_Score')
    st.dataframe(sector_df, use_container_width=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.subheader("Full Portfolio Risk Scorecard")
    display_df = risk_df[['CUSTOMER_ID','COMPANY_NAME','SECTOR','COMPOSITE_SCORE','RISK_GRADE','KEY_RISK_DRIVERS']].copy()
    display_df.columns = ['ID','Company','Sector','Score','Grade','Key Risk Drivers']
    st.dataframe(display_df, use_container_width=True, height=400)

# ═══════════════════════════════════════════
# PAGE 2: BORROWER DEEP DIVE
# ═══════════════════════════════════════════
elif page == "🔍 Borrower Deep Dive":
    st.markdown('<p class="main-header">Borrower Credit Profile</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">360° credit analysis with AI-generated risk narrative and regulatory compliance check</p>', unsafe_allow_html=True)

    customers = session.sql("SELECT CUSTOMER_ID, COMPANY_NAME, RISK_TIER FROM CREDITGUARDIAN_AI.CORE.CUSTOMERS ORDER BY COMPANY_NAME").to_pandas()
    selected = st.selectbox("Select Borrower", customers['COMPANY_NAME'].tolist())
    cust_id = customers[customers['COMPANY_NAME'] == selected]['CUSTOMER_ID'].iloc[0]

    score_df = session.sql(f"""
        SELECT * FROM CREDITGUARDIAN_AI.CORE.RISK_SCORES WHERE CUSTOMER_ID = '{cust_id}'
    """).to_pandas()

    if not score_df.empty:
        row = score_df.iloc[0]
        grade = row['RISK_GRADE']
        grade_map = {'A': 'risk-a', 'B': 'risk-b', 'C': 'risk-c', 'D': 'risk-d', 'E': 'risk-e'}

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Composite Score", f"{row['COMPOSITE_SCORE']:.0f} / 100")
        col2.markdown(f"**Risk Grade:** <span class='risk-badge {grade_map.get(grade,'')}'>{grade}</span>", unsafe_allow_html=True)
        col3.metric("Financial Health", f"{row['FINANCIAL_HEALTH_SCORE']:.0f} / 30")
        col4.metric("Repayment Score", f"{row['REPAYMENT_SCORE']:.0f} / 20")

        if row['KEY_RISK_DRIVERS']:
            st.warning(f"**Key Risk Drivers:** {row['KEY_RISK_DRIVERS']}")

        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

        st.subheader("7-Component Risk Score Breakdown")
        components = pd.DataFrame({
            'Component': ['Financial (30)', 'Repayment (20)', 'Cash Flow (10)', 'Collateral (13)', 'Rating (13)', 'Industry (10)', 'Macro (12)'],
            'Score': [row['FINANCIAL_HEALTH_SCORE'], row['REPAYMENT_SCORE'], row['CASHFLOW_BEHAVIOR_SCORE'],
                     row['COLLATERAL_SCORE'], row['RATING_SCORE'], row['INDUSTRY_SCORE'], row['MACRO_ENVIRONMENT_SCORE']],
            'Max': [30, 20, 10, 13, 13, 10, 12]
        })
        st.bar_chart(components.set_index('Component')['Score'])

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.subheader("Financial Summary")
    fin_df = session.sql(f"""
        SELECT FISCAL_YEAR AS Year, ROUND(REVENUE/1e7,1) AS Revenue_Cr, ROUND(EBITDA/1e7,1) AS EBITDA_Cr, 
               ROUND(NET_PROFIT/1e7,1) AS Net_Profit_Cr, DEBT_TO_EQUITY_RATIO AS DE_Ratio, 
               INTEREST_COVERAGE_RATIO AS ICR, ROUND(NET_PROFIT_MARGIN*100,1) AS NPM_Pct,
               CURRENT_RATIO, ROUND(RETURN_ON_ASSETS*100,1) AS ROA_Pct
        FROM CREDITGUARDIAN_AI.CORE.COMPANY_FINANCIALS WHERE CUSTOMER_ID = '{cust_id}' ORDER BY FISCAL_YEAR
    """).to_pandas()
    if not fin_df.empty:
        st.dataframe(fin_df, use_container_width=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.subheader("Loan Exposure")
    loan_df = session.sql(f"""
        SELECT LOAN_ID, LOAN_TYPE, ROUND(SANCTIONED_AMOUNT/1e7,1) AS Sanctioned_Cr,
               ROUND(OUTSTANDING_BALANCE/1e7,1) AS Outstanding_Cr, 
               ROUND(COLLATERAL_VALUE/1e7,1) AS Collateral_Cr, LOAN_STATUS, 
               INTEREST_RATE AS Rate_Pct, PURPOSE
        FROM CREDITGUARDIAN_AI.CORE.LOAN_HISTORY WHERE CUSTOMER_ID = '{cust_id}' ORDER BY OUTSTANDING_BALANCE DESC
    """).to_pandas()
    if not loan_df.empty:
        st.dataframe(loan_df, use_container_width=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.subheader("Repayment Track Record")
    rep_df = session.sql(f"""
        SELECT DUE_DATE, ROUND(EMI_AMOUNT/1e5,1) AS EMI_Lakhs, PAYMENT_STATUS, DAYS_OVERDUE
        FROM CREDITGUARDIAN_AI.CORE.LOAN_REPAYMENT WHERE CUSTOMER_ID = '{cust_id}' ORDER BY DUE_DATE
    """).to_pandas()
    if not rep_df.empty:
        st.dataframe(rep_df, use_container_width=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.subheader("AI Credit Assessment Generator")
    st.caption("Generates audit-ready credit assessment with regulatory citations using Cortex AI")
    if st.button("Generate AI Credit Assessment", type="primary", use_container_width=True):
        with st.spinner("Analyzing borrower profile, financial metrics, repayment history, and regulatory compliance..."):
            try:
                result = session.sql(f"CALL CREDITGUARDIAN_AI.CORE.GENERATE_CREDIT_ASSESSMENT('{cust_id}')").collect()
                st.success(result[0][0])
                assessment = session.sql(f"""
                    SELECT AI_NARRATIVE, AI_RECOMMENDATION, RISK_SCORE, RISK_GRADE, SMA_CATEGORY
                    FROM CREDITGUARDIAN_AI.CORE.CREDIT_ASSESSMENTS 
                    WHERE CUSTOMER_ID = '{cust_id}' ORDER BY GENERATED_AT DESC LIMIT 1
                """).to_pandas()
                if not assessment.empty:
                    st.markdown(f'<div class="ai-response">{assessment["AI_NARRATIVE"].iloc[0]}</div>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Assessment generation error: {e}")

# ═══════════════════════════════════════════
# PAGE 3: LOAN APPLICATIONS
# ═══════════════════════════════════════════
elif page == "📋 Loan Applications":
    st.markdown('<p class="main-header">Loan Application Pipeline</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">AI-assisted credit decisioning with officer override workflow</p>', unsafe_allow_html=True)

    apps_df = session.sql("""
        SELECT la.APPLICATION_ID, c.COMPANY_NAME, la.LOAN_TYPE, 
               ROUND(la.REQUESTED_AMOUNT/1e7,1) AS Requested_Cr, la.APPLICATION_STATUS,
               la.AI_RECOMMENDATION, ROUND(la.AI_CONFIDENCE_SCORE*100,0) AS Confidence, la.OFFICER_DECISION,
               la.APPLICATION_DATE, la.AI_RECOMMENDATION_REASON
        FROM CREDITGUARDIAN_AI.CORE.LOAN_APPLICATIONS la
        JOIN CREDITGUARDIAN_AI.CORE.CUSTOMERS c ON la.CUSTOMER_ID = c.CUSTOMER_ID
        ORDER BY la.APPLICATION_DATE DESC
    """).to_pandas()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="kpi-card"><p class="kpi-label">Total Applications</p><p class="kpi-value">{len(apps_df)}</p></div>', unsafe_allow_html=True)
    with col2:
        pending = len(apps_df[apps_df['APPLICATION_STATUS'].isin(['PENDING','UNDER_REVIEW','ESCALATED'])])
        st.markdown(f'<div class="kpi-card"><p class="kpi-label">In Pipeline</p><p class="kpi-value">{pending}</p></div>', unsafe_allow_html=True)
    with col3:
        approved = len(apps_df[apps_df['APPLICATION_STATUS'] == 'APPROVED'])
        st.markdown(f'<div class="kpi-card-success"><p class="kpi-label">Approved</p><p class="kpi-value">{approved}</p></div>', unsafe_allow_html=True)
    with col4:
        rejected = len(apps_df[apps_df['APPLICATION_STATUS'] == 'REJECTED'])
        st.markdown(f'<div class="kpi-card-warn"><p class="kpi-label">Rejected</p><p class="kpi-value">{rejected}</p></div>', unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    status_filter = st.multiselect("Filter by Status", apps_df['APPLICATION_STATUS'].unique().tolist(), default=apps_df['APPLICATION_STATUS'].unique().tolist())
    filtered = apps_df[apps_df['APPLICATION_STATUS'].isin(status_filter)]
    st.dataframe(filtered.drop(columns=['AI_RECOMMENDATION_REASON']), use_container_width=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.subheader("AI vs Officer Decision Alignment")
    decided = apps_df[(apps_df['AI_RECOMMENDATION'].notna()) & (apps_df['OFFICER_DECISION'].notna())]
    if not decided.empty:
        agree = len(decided[decided['AI_RECOMMENDATION'].str.upper().str.contains('APPROVE') == decided['OFFICER_DECISION'].str.upper().str.contains('APPROVE')])
        col1, col2, col3 = st.columns(3)
        col1.metric("Agreement Rate", f"{100*agree/len(decided):.0f}%")
        col2.metric("AI Decisions Made", f"{len(apps_df[apps_df['AI_RECOMMENDATION'].notna()])} / {len(apps_df)}")
        col3.metric("Officer Decisions", f"{len(decided)} / {len(apps_df)}")

# ═══════════════════════════════════════════
# PAGE 4: MACRO & INDUSTRY
# ═══════════════════════════════════════════
elif page == "🌐 Macro & Industry":
    st.markdown('<p class="main-header">Macro-Economic & Industry Monitor</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Real-time indicators from streaming data feeds | Impact analysis on credit portfolio</p>', unsafe_allow_html=True)

    macro_df = session.sql("""
        SELECT INDICATOR_NAME, INDICATOR_CATEGORY, VALUE, PREVIOUS_VALUE, CHANGE_PCT, UNIT, REPORT_DATE, SOURCE
        FROM CREDITGUARDIAN_AI.CORE.MACRO_ECONOMIC_INDICATORS
        QUALIFY ROW_NUMBER() OVER (PARTITION BY INDICATOR_NAME ORDER BY REPORT_DATE DESC) = 1
        ORDER BY INDICATOR_CATEGORY, INDICATOR_NAME
    """).to_pandas()

    col1, col2, col3, col4, col5 = st.columns(5)
    for c, name, fmt in [(col1,'CPI Inflation','{}%'),(col2,'Repo Rate','{}%'),(col3,'GDP Growth Rate','{}%'),(col4,'USD/INR Rate','₹{}'),(col5,'Credit Growth','{}%')]:
        row = macro_df[macro_df['INDICATOR_NAME'] == name]
        if not row.empty:
            val = row['VALUE'].iloc[0]
            chg = row['CHANGE_PCT'].iloc[0]
            c.metric(name, fmt.format(val), f"{chg:+.1f}%")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.subheader("All Macro Indicators")
    st.dataframe(macro_df, use_container_width=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.subheader("Industry Sector Outlook")
    ind_df = session.sql("""
        SELECT SECTOR, INDUSTRY, OUTLOOK, DEFAULT_RATE_PCT AS Default_Rate, NPA_RATIO_PCT AS NPA_Ratio, 
               SECTOR_GROWTH_PCT AS Growth, KEY_RISK_FACTORS, REPORT_DATE
        FROM CREDITGUARDIAN_AI.CORE.INDUSTRY_TRENDS
        QUALIFY ROW_NUMBER() OVER (PARTITION BY SECTOR, INDUSTRY ORDER BY REPORT_DATE DESC) = 1
        ORDER BY DEFAULT_RATE_PCT DESC
    """).to_pandas()
    st.dataframe(ind_df, use_container_width=True, height=500)

# ═══════════════════════════════════════════
# PAGE 5: AI RISK ADVISOR (FIXED)
# ═══════════════════════════════════════════
elif page == "🤖 AI Risk Advisor":
    st.markdown('<p class="main-header">AI Risk Advisor</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Enterprise copilot for credit risk analysis, regulatory compliance, and portfolio intelligence — powered by Cortex AI + RAG</p>', unsafe_allow_html=True)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    st.markdown("**Quick Analysis Queries**")
    col1, col2, col3 = st.columns(3)
    quick_qs = [
        "Which borrowers are at highest risk and why?",
        "What are the RBI NPA classification and provisioning norms?",
        "Summarize our total loan exposure by sector with NPA breakdown",
        "What provisioning is required for our sub-standard and doubtful assets?",
        "Which loan applications need urgent officer review?",
        "What is the single borrower exposure limit under RBI Large Exposure Framework?"
    ]
    selected_q = None
    for i, q in enumerate(quick_qs):
        target_col = [col1, col2, col3][i % 3]
        if target_col.button(q[:45] + "..." if len(q) > 45 else q, key=f"qq_{i}", use_container_width=True):
            selected_q = q

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Display conversation history
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"**🧑 You:** {msg['content']}")
        else:
            st.markdown(f'<div class="ai-response">{msg["content"]}</div>', unsafe_allow_html=True)

    # Input form (compatible with SiS)
    with st.form("advisor_form", clear_on_submit=True):
        user_input = st.text_area("Ask CreditGuardian AI:", height=80, 
                                   placeholder="Ask about risk scores, regulatory norms, portfolio analytics, loan applications...")
        submitted = st.form_submit_button("🚀 Get AI Analysis", type="primary", use_container_width=True)

    question = selected_q or (user_input if submitted else None)
    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        st.markdown(f"**🧑 You:** {question}")

        with st.spinner("🔍 Analyzing with Cortex AI + Regulatory RAG..."):
            # Gather context
            data_context = ""
            q_lower = question.lower()
            try:
                if any(w in q_lower for w in ['risk', 'score', 'grade', 'borrower', 'high risk', 'critical', 'portfolio', 'npa exposure']):
                    df = session.sql("SELECT COMPANY_NAME, SECTOR, COMPOSITE_SCORE, RISK_GRADE, KEY_RISK_DRIVERS FROM CREDITGUARDIAN_AI.CORE.RISK_SCORES ORDER BY COMPOSITE_SCORE").to_pandas()
                    data_context += "PORTFOLIO RISK SCORES:\n" + df.to_csv(index=False) + "\n"
                if any(w in q_lower for w in ['loan', 'exposure', 'outstanding', 'collateral', 'npa', 'sector']):
                    df = session.sql("SELECT c.COMPANY_NAME, c.SECTOR, lh.LOAN_TYPE, lh.OUTSTANDING_BALANCE, lh.COLLATERAL_VALUE, lh.LOAN_STATUS FROM CREDITGUARDIAN_AI.CORE.LOAN_HISTORY lh JOIN CREDITGUARDIAN_AI.CORE.CUSTOMERS c ON lh.CUSTOMER_ID = c.CUSTOMER_ID ORDER BY lh.OUTSTANDING_BALANCE DESC").to_pandas()
                    data_context += "LOAN EXPOSURE DATA:\n" + df.to_csv(index=False) + "\n"
                if any(w in q_lower for w in ['application', 'pending', 'approved', 'rejected', 'review', 'officer']):
                    df = session.sql("SELECT c.COMPANY_NAME, la.LOAN_TYPE, la.REQUESTED_AMOUNT, la.APPLICATION_STATUS, la.AI_RECOMMENDATION, la.AI_RECOMMENDATION_REASON FROM CREDITGUARDIAN_AI.CORE.LOAN_APPLICATIONS la JOIN CREDITGUARDIAN_AI.CORE.CUSTOMERS c ON la.CUSTOMER_ID = c.CUSTOMER_ID ORDER BY la.APPLICATION_DATE DESC").to_pandas()
                    data_context += "APPLICATION PIPELINE:\n" + df.to_csv(index=False) + "\n"
                if any(w in q_lower for w in ['macro', 'cpi', 'inflation', 'repo', 'gdp', 'industry', 'sector', 'outlook']):
                    df = session.sql("SELECT INDICATOR_NAME, VALUE, CHANGE_PCT, REPORT_DATE FROM CREDITGUARDIAN_AI.CORE.MACRO_ECONOMIC_INDICATORS QUALIFY ROW_NUMBER() OVER (PARTITION BY INDICATOR_NAME ORDER BY REPORT_DATE DESC) = 1").to_pandas()
                    data_context += "MACRO INDICATORS:\n" + df.to_csv(index=False) + "\n"
                if not data_context:
                    df = session.sql("SELECT COMPANY_NAME, SECTOR, COMPOSITE_SCORE, RISK_GRADE, KEY_RISK_DRIVERS FROM CREDITGUARDIAN_AI.CORE.RISK_SCORES ORDER BY COMPOSITE_SCORE").to_pandas()
                    data_context = "PORTFOLIO RISK SCORES:\n" + df.to_csv(index=False)
            except Exception:
                pass

            # RAG search
            reg_context = ""
            try:
                escaped_q = question.replace("'", "''").replace("\\", "\\\\")
                search_result = session.sql(f"""
                    SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
                        'CREDITGUARDIAN_AI.CORE.REGULATORY_SEARCH_SERVICE',
                        '{{"query": "{escaped_q}", "columns": ["TITLE","SECTION","CONTENT"], "limit": 3}}'
                    ) AS result
                """).to_pandas()
                parsed = json.loads(search_result['RESULT'].iloc[0])
                for r in parsed.get('results', []):
                    reg_context += f"[{r.get('TITLE','')} - {r.get('SECTION','')}]: {r.get('CONTENT','')[:600]}\n\n"
            except Exception:
                pass

            # Build structured message array for better formatting
            system_msg = """You are CreditGuardian AI, a senior credit risk analyst at a major Indian bank.

FORMAT RULES (you MUST follow these exactly):
1. Start with a heading line: ## Topic Name
2. Use ### for sub-sections
3. Present data in markdown tables with | Column1 | Column2 | format
4. Use bullet points (- ) for findings
5. End with ### Recommendation section
6. Use **bold** for emphasis on key numbers
7. Never output raw data dumps - always organize into sections and tables

Risk grade scale: A (80+)=Low, B (60-79)=Moderate, C (40-59)=Elevated, D (20-39)=High, E (0-19)=Critical"""

            user_msg = f"""Question: {question}

Portfolio Data:
{data_context[:2500]}

Regulatory Context:
{reg_context[:1500]}

Answer with proper markdown formatting: headings, tables, bullet points."""

            try:
                from snowflake.snowpark.functions import lit, col, call_function
                
                full_prompt = system_msg + "\n\n" + user_msg
                
                prompt_df = session.create_dataframe([{"prompt": full_prompt}])
                result_df = prompt_df.select(
                    call_function("AI_COMPLETE", lit("llama3.1-8b"), col("prompt")).alias("response")
                ).to_pandas()
                
                response = result_df['RESPONSE'].iloc[0]
                if response is None:
                    response = "No response generated."
                response = str(response)
                # Fix literal \n that the model sometimes outputs
                response = response.replace('\\n', '\n').replace('\\t', '\t')
                # Clean up any pipe-table formatting issues
                response = response.replace('|\\n|', '|\n|')
                
                st.markdown("---")
                st.markdown("### 🛡️ CreditGuardian AI Analysis")
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.error(f"AI Error: {e}")

# ═══════════════════════════════════════════
# PAGE 6: REGULATORY POLICIES
# ═══════════════════════════════════════════
elif page == "📜 Regulatory Policies":
    st.markdown('<p class="main-header">Regulatory Policy Library</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">20 regulatory policies from RBI, Basel III, and IBC — indexed for semantic search via Cortex Search</p>', unsafe_allow_html=True)

    policies_df = session.sql("""
        SELECT POLICY_ID, TITLE, ISSUING_AUTHORITY, CATEGORY, SECTION, 
               LEFT(CONTENT, 200) || '...' AS CONTENT_PREVIEW, EFFECTIVE_DATE
        FROM CREDITGUARDIAN_AI.CORE.REGULATORY_POLICIES
        ORDER BY POLICY_ID
    """).to_pandas()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Policies", len(policies_df))
    authorities = policies_df['ISSUING_AUTHORITY'].nunique()
    col2.metric("Issuing Authorities", authorities)
    categories = policies_df['CATEGORY'].nunique()
    col3.metric("Policy Categories", categories)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    cat_filter = st.multiselect("Filter by Category", policies_df['CATEGORY'].unique().tolist(), default=policies_df['CATEGORY'].unique().tolist())
    filtered = policies_df[policies_df['CATEGORY'].isin(cat_filter)]
    st.dataframe(filtered, use_container_width=True, height=500)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.subheader("Semantic Policy Search")
    st.caption("Search across all regulatory policies using natural language (powered by Cortex Search)")
    search_q = st.text_input("Search regulatory policies...", placeholder="e.g., NPA provisioning requirements for doubtful assets")
    if search_q:
        try:
            escaped = search_q.replace("'", "''").replace("\\", "\\\\")
            result = session.sql(f"""
                SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
                    'CREDITGUARDIAN_AI.CORE.REGULATORY_SEARCH_SERVICE',
                    '{{"query": "{escaped}", "columns": ["TITLE","SECTION","CONTENT","CATEGORY"], "limit": 5}}'
                ) AS result
            """).to_pandas()
            parsed = json.loads(result['RESULT'].iloc[0])
            for r in parsed.get('results', []):
                with st.expander(f"**{r.get('TITLE','')}** — {r.get('SECTION','')}"):
                    st.caption(f"Category: {r.get('CATEGORY','')}")
                    st.markdown(r.get('CONTENT',''))
        except Exception as e:
            st.error(f"Search error: {e}")
