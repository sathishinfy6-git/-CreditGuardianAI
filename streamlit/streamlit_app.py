import streamlit as st
from snowflake.snowpark.context import get_active_session
import pandas as pd

session = get_active_session()

st.set_page_config(page_title="CreditGuardian AI", page_icon="🛡️", layout="wide")

# ─── CUSTOM STYLING ───
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1B2838;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #5A6B7B;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.2rem;
        border-radius: 12px;
        color: white;
        text-align: center;
    }
    .metric-card h3 {
        font-size: 0.85rem;
        font-weight: 400;
        margin: 0;
        opacity: 0.9;
    }
    .metric-card h1 {
        font-size: 2rem;
        font-weight: 700;
        margin: 0.3rem 0 0 0;
    }
    .risk-a { color: #10B981; font-weight: 700; }
    .risk-b { color: #3B82F6; font-weight: 700; }
    .risk-c { color: #F59E0B; font-weight: 700; }
    .risk-d { color: #EF4444; font-weight: 700; }
    .risk-e { color: #7C2D12; font-weight: 700; }
    .section-divider {
        border-top: 2px solid #E5E7EB;
        margin: 2rem 0 1.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ─── SIDEBAR ───
st.sidebar.markdown("## 🛡️ CreditGuardian AI")
st.sidebar.markdown("*Credit Risk & Regulatory Intelligence*")
st.sidebar.markdown("---")
page = st.sidebar.radio("", [
    "📊 Portfolio Overview",
    "🔍 Borrower Deep Dive",
    "📋 Loan Applications",
    "🌐 Market & Industry",
    "🤖 AI Risk Advisor"
], label_visibility="collapsed")
st.sidebar.markdown("---")
st.sidebar.caption("Powered by Snowflake Cortex AI")

# ─── PAGE 1: PORTFOLIO OVERVIEW ───
if page == "📊 Portfolio Overview":
    st.markdown('<p class="main-header">Portfolio Risk Overview</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Real-time credit risk monitoring across your lending portfolio</p>', unsafe_allow_html=True)

    risk_df = session.sql("SELECT * FROM CREDITGUARDIAN_AI.CORE.RISK_SCORES ORDER BY COMPOSITE_SCORE DESC").to_pandas()
    exposure_df = session.sql("SELECT SUM(OUTSTANDING_BALANCE)/1e9 AS exp_bn FROM CREDITGUARDIAN_AI.CORE.LOAN_HISTORY WHERE LOAN_STATUS='ACTIVE'").to_pandas()

    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""<div class="metric-card"><h3>Total Borrowers</h3><h1>{len(risk_df)}</h1></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="metric-card"><h3>Avg Risk Score</h3><h1>{risk_df['COMPOSITE_SCORE'].mean():.0f}</h1></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="metric-card"><h3>High Risk (D+E)</h3><h1>{len(risk_df[risk_df['RISK_GRADE'].isin(['D','E'])])}</h1></div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""<div class="metric-card"><h3>Total Exposure</h3><h1>₹{exposure_df['EXP_BN'].iloc[0]:.1f}B</h1></div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Risk Grade Distribution")
        grade_counts = risk_df.groupby('RISK_GRADE').size().reset_index(name='Count')
        grade_counts = grade_counts.sort_values('RISK_GRADE')
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
                FROM CREDITGUARDIAN_AI.CORE.LOAN_REPAYMENT
                GROUP BY CUSTOMER_ID
            )
            GROUP BY Category ORDER BY Count DESC
        """).to_pandas()
        st.bar_chart(sma_df.set_index('CATEGORY'))

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    st.subheader("Sector Risk Summary")
    sector_df = risk_df.groupby('SECTOR').agg(
        Borrowers=('CUSTOMER_ID', 'count'),
        Avg_Score=('COMPOSITE_SCORE', 'mean'),
        High_Risk=('RISK_GRADE', lambda x: (x.isin(['D','E'])).sum())
    ).round(1).sort_values('Avg_Score')
    st.dataframe(sector_df, use_container_width=True)

# ─── PAGE 2: BORROWER DEEP DIVE ───
elif page == "🔍 Borrower Deep Dive":
    st.markdown('<p class="main-header">Borrower Deep Dive</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Comprehensive credit profile analysis for individual borrowers</p>', unsafe_allow_html=True)

    customers = session.sql("SELECT CUSTOMER_ID, COMPANY_NAME FROM CREDITGUARDIAN_AI.CORE.CUSTOMERS ORDER BY COMPANY_NAME").to_pandas()
    selected = st.selectbox("Select Borrower", customers['COMPANY_NAME'].tolist())
    cust_id = customers[customers['COMPANY_NAME'] == selected]['CUSTOMER_ID'].iloc[0]

    # Risk Score Breakdown
    score_df = session.sql(f"""
        SELECT FINANCIAL_HEALTH_SCORE, REPAYMENT_SCORE, CASHFLOW_BEHAVIOR_SCORE,
               COLLATERAL_SCORE, RATING_SCORE, INDUSTRY_SCORE, MACRO_ENVIRONMENT_SCORE,
               COMPOSITE_SCORE, RISK_GRADE, KEY_RISK_DRIVERS
        FROM CREDITGUARDIAN_AI.CORE.RISK_SCORES WHERE CUSTOMER_ID = '{cust_id}'
    """).to_pandas()

    if not score_df.empty:
        col1, col2, col3 = st.columns(3)
        grade = score_df['RISK_GRADE'].iloc[0]
        grade_class = f"risk-{grade.lower()}"
        col1.metric("Composite Score", f"{score_df['COMPOSITE_SCORE'].iloc[0]:.0f}/100")
        col2.markdown(f"**Risk Grade:** <span class='{grade_class}'>{grade}</span>", unsafe_allow_html=True)
        drivers = score_df['KEY_RISK_DRIVERS'].iloc[0]
        col3.markdown(f"**Key Risks:** {drivers[:80]}..." if drivers and len(drivers) > 80 else f"**Key Risks:** {drivers or 'None identified'}")

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

        st.subheader("Score Components")
        components = pd.DataFrame({
            'Component': ['Financial Health (30)', 'Repayment (20)', 'Cash Flow (10)', 'Collateral (13)', 'Rating (13)', 'Industry (10)', 'Macro (12)'],
            'Score': [score_df['FINANCIAL_HEALTH_SCORE'].iloc[0], score_df['REPAYMENT_SCORE'].iloc[0],
                     score_df['CASHFLOW_BEHAVIOR_SCORE'].iloc[0], score_df['COLLATERAL_SCORE'].iloc[0],
                     score_df['RATING_SCORE'].iloc[0], score_df['INDUSTRY_SCORE'].iloc[0],
                     score_df['MACRO_ENVIRONMENT_SCORE'].iloc[0]]
        })
        st.bar_chart(components.set_index('Component')['Score'])

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Financial Summary")
        fin_df = session.sql(f"""
            SELECT FISCAL_YEAR, REVENUE/1e7 AS REVENUE_CR, EBITDA/1e7 AS EBITDA_CR, 
                   DEBT_TO_EQUITY_RATIO AS DE_RATIO, INTEREST_COVERAGE_RATIO AS ICR, 
                   ROUND(NET_PROFIT_MARGIN*100, 2) AS NPM_PCT
            FROM CREDITGUARDIAN_AI.CORE.COMPANY_FINANCIALS 
            WHERE CUSTOMER_ID = '{cust_id}' ORDER BY FISCAL_YEAR
        """).to_pandas()
        if not fin_df.empty:
            st.dataframe(fin_df, use_container_width=True)

    with col_right:
        st.subheader("Repayment History")
        rep_df = session.sql(f"""
            SELECT DUE_DATE, EMI_AMOUNT/1e5 AS EMI_LAKHS, PAYMENT_STATUS, DAYS_OVERDUE
            FROM CREDITGUARDIAN_AI.CORE.LOAN_REPAYMENT 
            WHERE CUSTOMER_ID = '{cust_id}' ORDER BY DUE_DATE
        """).to_pandas()
        if not rep_df.empty:
            st.dataframe(rep_df, use_container_width=True)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # Generate Assessment
    st.subheader("AI Credit Assessment")
    if st.button("🤖 Generate Assessment Report", type="primary", use_container_width=True):
        with st.spinner("Generating AI credit assessment with regulatory citations..."):
            result = session.sql(f"CALL CREDITGUARDIAN_AI.CORE.GENERATE_CREDIT_ASSESSMENT('{cust_id}')").collect()
            st.success(result[0][0])
            
            assessment = session.sql(f"""
                SELECT AI_NARRATIVE FROM CREDITGUARDIAN_AI.CORE.CREDIT_ASSESSMENTS 
                WHERE CUSTOMER_ID = '{cust_id}' ORDER BY GENERATED_AT DESC LIMIT 1
            """).to_pandas()
            if not assessment.empty:
                with st.expander("📄 Full Assessment Report", expanded=True):
                    st.markdown(assessment['AI_NARRATIVE'].iloc[0])

# ─── PAGE 3: LOAN APPLICATIONS ───
elif page == "📋 Loan Applications":
    st.markdown('<p class="main-header">Loan Application Pipeline</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Track applications from submission through AI-assisted decisioning</p>', unsafe_allow_html=True)

    apps_df = session.sql("""
        SELECT la.APPLICATION_ID, c.COMPANY_NAME, la.LOAN_TYPE, 
               la.REQUESTED_AMOUNT/1e7 AS REQUESTED_CR, la.APPLICATION_STATUS,
               la.AI_RECOMMENDATION, la.AI_CONFIDENCE_SCORE, la.OFFICER_DECISION,
               la.APPLICATION_DATE
        FROM CREDITGUARDIAN_AI.CORE.LOAN_APPLICATIONS la
        JOIN CREDITGUARDIAN_AI.CORE.CUSTOMERS c ON la.CUSTOMER_ID = c.CUSTOMER_ID
        ORDER BY la.APPLICATION_DATE DESC
    """).to_pandas()

    # Status KPIs
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""<div class="metric-card"><h3>Total Applications</h3><h1>{len(apps_df)}</h1></div>""", unsafe_allow_html=True)
    with col2:
        pending = len(apps_df[apps_df['APPLICATION_STATUS'].isin(['PENDING','UNDER_REVIEW','ESCALATED'])])
        st.markdown(f"""<div class="metric-card"><h3>In Pipeline</h3><h1>{pending}</h1></div>""", unsafe_allow_html=True)
    with col3:
        approved = len(apps_df[apps_df['APPLICATION_STATUS'] == 'APPROVED'])
        st.markdown(f"""<div class="metric-card"><h3>Approved</h3><h1>{approved}</h1></div>""", unsafe_allow_html=True)
    with col4:
        rejected = len(apps_df[apps_df['APPLICATION_STATUS'] == 'REJECTED'])
        st.markdown(f"""<div class="metric-card"><h3>Rejected</h3><h1>{rejected}</h1></div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # Filter
    status_filter = st.multiselect("Filter by Status", apps_df['APPLICATION_STATUS'].unique().tolist(), default=apps_df['APPLICATION_STATUS'].unique().tolist())
    filtered = apps_df[apps_df['APPLICATION_STATUS'].isin(status_filter)]
    st.dataframe(filtered, use_container_width=True)

    # AI vs Officer agreement
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.subheader("AI vs Officer Decision Alignment")
    decided = apps_df[(apps_df['AI_RECOMMENDATION'].notna()) & (apps_df['OFFICER_DECISION'].notna())]
    if not decided.empty:
        agree = len(decided[decided['AI_RECOMMENDATION'].str.upper().str.contains('APPROVE') == decided['OFFICER_DECISION'].str.upper().str.contains('APPROVE')])
        col1, col2 = st.columns(2)
        col1.metric("Agreement Rate", f"{100*agree/len(decided):.0f}%")
        col2.metric("Decisions Made", f"{len(decided)} / {len(apps_df)}")

# ─── PAGE 4: MARKET & INDUSTRY ───
elif page == "🌐 Market & Industry":
    st.markdown('<p class="main-header">Market & Industry Monitor</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Real-time macro-economic indicators and sector outlook from streaming data feeds</p>', unsafe_allow_html=True)

    st.subheader("Latest Macro-Economic Indicators")
    macro_df = session.sql("""
        SELECT INDICATOR_NAME, INDICATOR_CATEGORY, VALUE, PREVIOUS_VALUE, CHANGE_PCT, UNIT, REPORT_DATE, SOURCE
        FROM CREDITGUARDIAN_AI.CORE.MACRO_ECONOMIC_INDICATORS
        QUALIFY ROW_NUMBER() OVER (PARTITION BY INDICATOR_NAME ORDER BY REPORT_DATE DESC) = 1
        ORDER BY INDICATOR_CATEGORY, INDICATOR_NAME
    """).to_pandas()

    # Show key metrics as cards
    col1, col2, col3, col4 = st.columns(4)
    cpi_row = macro_df[macro_df['INDICATOR_NAME'] == 'CPI_GENERAL']
    repo_row = macro_df[macro_df['INDICATOR_NAME'] == 'REPO_RATE']
    fx_row = macro_df[macro_df['INDICATOR_NAME'] == 'INR_USD']
    crude_row = macro_df[macro_df['INDICATOR_NAME'] == 'CRUDE_OIL_BRENT']

    if not cpi_row.empty:
        col1.metric("CPI Inflation", f"{cpi_row['VALUE'].iloc[0]}%", f"{cpi_row['CHANGE_PCT'].iloc[0]:+.1f}%")
    if not repo_row.empty:
        col2.metric("Repo Rate", f"{repo_row['VALUE'].iloc[0]}%", f"{repo_row['CHANGE_PCT'].iloc[0]:+.1f}%")
    if not fx_row.empty:
        col3.metric("INR/USD", f"₹{fx_row['VALUE'].iloc[0]}", f"{fx_row['CHANGE_PCT'].iloc[0]:+.2f}%")
    if not crude_row.empty:
        col4.metric("Brent Crude", f"${crude_row['VALUE'].iloc[0]}", f"{crude_row['CHANGE_PCT'].iloc[0]:+.1f}%")

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    st.subheader("All Indicators")
    st.dataframe(macro_df, use_container_width=True)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    st.subheader("Industry Outlook")
    ind_df = session.sql("""
        SELECT SECTOR, INDUSTRY, OUTLOOK, DEFAULT_RATE_PCT, NPA_RATIO_PCT, SECTOR_GROWTH_PCT, REPORT_DATE
        FROM CREDITGUARDIAN_AI.CORE.INDUSTRY_TRENDS
        QUALIFY ROW_NUMBER() OVER (PARTITION BY SECTOR, INDUSTRY ORDER BY REPORT_DATE DESC) = 1
        ORDER BY DEFAULT_RATE_PCT DESC
    """).to_pandas()
    st.dataframe(ind_df, use_container_width=True)

# ─── PAGE 5: AI RISK ADVISOR ───
elif page == "🤖 AI Risk Advisor":
    st.markdown('<p class="main-header">AI Risk Advisor</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Your intelligent copilot for credit risk analysis and regulatory compliance — powered by Cortex AI</p>', unsafe_allow_html=True)

    # Initialize session state
    if "copilot_question" not in st.session_state:
        st.session_state.copilot_question = ""

    # Quick questions in a nice grid
    st.markdown("**Quick Actions**")
    col1, col2 = st.columns(2)
    quick_qs = [
        ("📊", "Which borrowers have the highest risk?"),
        ("📜", "What are the NPA classification criteria?"),
        ("💰", "What is the total outstanding loan exposure?"),
        ("⚖️", "What provisioning is required for sub-standard assets?"),
        ("📋", "Show me all pending loan applications"),
        ("🏦", "What is the single borrower exposure limit?")
    ]
    for i, (icon, q) in enumerate(quick_qs):
        target_col = col1 if i % 2 == 0 else col2
        if target_col.button(f"{icon} {q}", key=f"qq_{i}", use_container_width=True):
            st.session_state.copilot_question = q

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # Chat form
    with st.form("copilot_form"):
        user_question = st.text_area("Ask CreditGuardian AI anything:", value=st.session_state.copilot_question, height=80, placeholder="e.g., Which sectors have the worst NPA outlook? What are my top 3 riskiest exposures?")
        submitted = st.form_submit_button("🚀 Get AI Analysis", type="primary", use_container_width=True)

    if submitted and user_question:
        st.session_state.copilot_question = user_question
        with st.spinner("🤖 CreditGuardian AI is analyzing..."):
            from snowflake.snowpark.functions import col, lit, call_function
            import json

            # Step 1: Query relevant data based on keywords
            data_context = ""
            data_df = None
            q_lower = user_question.lower()
            try:
                if any(w in q_lower for w in ['risk', 'score', 'grade', 'borrower', 'high risk', 'critical']):
                    data_df = session.sql(
                        "SELECT COMPANY_NAME, COMPOSITE_SCORE, RISK_GRADE, KEY_RISK_DRIVERS FROM CREDITGUARDIAN_AI.CORE.RISK_SCORES ORDER BY COMPOSITE_SCORE"
                    ).to_pandas()
                    data_context = "RISK SCORES DATA:\n" + data_df.head(15).to_string(index=False)
                elif any(w in q_lower for w in ['loan', 'exposure', 'outstanding', 'collateral']):
                    data_df = session.sql(
                        "SELECT c.COMPANY_NAME, lh.LOAN_TYPE, lh.OUTSTANDING_BALANCE, lh.COLLATERAL_VALUE, lh.LOAN_STATUS FROM CREDITGUARDIAN_AI.CORE.LOAN_HISTORY lh JOIN CREDITGUARDIAN_AI.CORE.CUSTOMERS c ON lh.CUSTOMER_ID = c.CUSTOMER_ID WHERE lh.LOAN_STATUS = 'ACTIVE' ORDER BY lh.OUTSTANDING_BALANCE DESC"
                    ).to_pandas()
                    data_context = "LOAN DATA:\n" + data_df.head(15).to_string(index=False)
                elif any(w in q_lower for w in ['application', 'pending', 'approved', 'rejected']):
                    data_df = session.sql(
                        "SELECT c.COMPANY_NAME, la.LOAN_TYPE, la.REQUESTED_AMOUNT, la.APPLICATION_STATUS, la.AI_RECOMMENDATION FROM CREDITGUARDIAN_AI.CORE.LOAN_APPLICATIONS la JOIN CREDITGUARDIAN_AI.CORE.CUSTOMERS c ON la.CUSTOMER_ID = c.CUSTOMER_ID ORDER BY la.APPLICATION_DATE DESC"
                    ).to_pandas()
                    data_context = "APPLICATION DATA:\n" + data_df.head(15).to_string(index=False)
                elif any(w in q_lower for w in ['macro', 'cpi', 'inflation', 'repo', 'gdp', 'industry', 'sector', 'outlook']):
                    data_df = session.sql(
                        "SELECT INDICATOR_NAME, VALUE, CHANGE_PCT, REPORT_DATE, SOURCE FROM CREDITGUARDIAN_AI.CORE.MACRO_ECONOMIC_INDICATORS QUALIFY ROW_NUMBER() OVER (PARTITION BY INDICATOR_NAME ORDER BY REPORT_DATE DESC) = 1"
                    ).to_pandas()
                    data_context = "MACRO DATA:\n" + data_df.to_string(index=False)
            except Exception as e:
                st.warning(f"Data query issue: {e}")

            # Step 2: Search regulatory context
            reg_summary = ""
            try:
                escaped_q = user_question.replace("'", "''")
                search_result = session.sql(f"""
                    SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
                        'CREDITGUARDIAN_AI.CORE.REGULATORY_SEARCH_SERVICE',
                        '{{"query": "{escaped_q}", "columns": ["TITLE","CONTENT"], "limit": 2}}'
                    ) AS result
                """).to_pandas()
                raw_json = search_result['RESULT'].iloc[0]
                parsed = json.loads(raw_json)
                reg_parts = []
                for r in parsed.get('results', []):
                    title = r.get('TITLE', '')
                    content = r.get('CONTENT', '')[:500]
                    reg_parts.append(f"{title}: {content}")
                reg_summary = "\n".join(reg_parts)
            except Exception:
                reg_summary = ""

            # Step 3: Build prompt and call COMPLETE via Snowpark DataFrame API
            prompt_text = (
                "You are CreditGuardian AI, a credit risk and regulatory compliance copilot for an Indian bank. "
                "Answer the following question using the provided data and regulatory context. "
                "Cite RBI circular references where applicable. Use markdown formatting for readability. "
                "Risk grades: A (80+) Low Risk, B (60-79) Moderate, C (40-59) Elevated, D (20-39) High, E (0-19) Critical.\n\n"
                f"QUESTION: {user_question}\n\n"
                f"{data_context[:2500]}\n\n"
                f"REGULATORY CONTEXT: {reg_summary[:1500]}\n\n"
                "Provide a clear, structured answer with specific numbers from the data. Use tables where helpful."
            )

            try:
                result_df = session.create_dataframe([{"prompt": prompt_text}]).select(
                    call_function("SNOWFLAKE.CORTEX.COMPLETE", lit("llama3.1-70b"), col("prompt")).alias("response")
                ).to_pandas()
                st.markdown("---")
                st.markdown("### 💡 Analysis")
                st.markdown(result_df['RESPONSE'].iloc[0])
            except Exception as e:
                st.error(f"Error generating response: {str(e)}")

            # Show source data if available
            if data_df is not None and not data_df.empty:
                with st.expander("📊 View Source Data"):
                    st.dataframe(data_df, use_container_width=True)
