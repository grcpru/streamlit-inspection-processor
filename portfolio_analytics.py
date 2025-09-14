"""
Multi-Building Portfolio Analytics Design
Hierarchical structure: Developer > Projects > Buildings > Units
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3

def generate_multi_building_portfolio_dashboard():
    """Portfolio dashboard for multiple buildings"""
    
    # Portfolio Header
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
                color: white; padding: 3rem 2rem; border-radius: 15px; margin: -1rem -1rem 3rem -1rem;">
        <h1 style="text-align: center; font-size: 3rem; margin: 0;">Portfolio Command Center</h1>
        <p style="text-align: center; font-size: 1.2rem; margin: 1rem 0 0 0;">Multi-Building Performance Management</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Get portfolio data
    portfolio_data = get_portfolio_data()
    
    if not portfolio_data['buildings']:
        st.warning("No buildings found in your portfolio.")
        return
    
    # Top-Level Portfolio KPIs
    st.markdown("### Portfolio Overview")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Projects", portfolio_data['total_projects'])
    
    with col2:
        st.metric("Total Buildings", portfolio_data['total_buildings'])
    
    with col3:
        st.metric("Total Units", f"{portfolio_data['total_units']:,}")
    
    with col4:
        portfolio_ready_pct = (portfolio_data['total_ready_units'] / portfolio_data['total_units'] * 100) if portfolio_data['total_units'] > 0 else 0
        st.metric("Portfolio Ready", f"{portfolio_ready_pct:.1f}%")
    
    with col5:
        st.metric("Total Urgent Issues", portfolio_data['total_urgent_defects'])
    
    # Portfolio Health Dashboard
    st.markdown("---")
    st.markdown("### Portfolio Health Dashboard")
    
    # Health indicators
    health_status = calculate_portfolio_health(portfolio_data)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if health_status['overall'] == 'Critical':
            st.error(f"Portfolio Status: {health_status['overall']}")
        elif health_status['overall'] == 'Warning':
            st.warning(f"Portfolio Status: {health_status['overall']}")
        else:
            st.success(f"Portfolio Status: {health_status['overall']}")
    
    with col2:
        avg_performance = portfolio_data['avg_portfolio_performance']
        st.metric("Avg Performance", f"{avg_performance:.1f}/100")
    
    with col3:
        financial_exposure = portfolio_data['revenue_at_risk']
        st.metric("Revenue at Risk", f"${financial_exposure:,.0f}")
    
    with col4:
        st.metric("Projects On Track", f"{health_status['projects_on_track']}/{portfolio_data['total_projects']}")
    
    # Main Portfolio Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Project Overview",
        "Building Comparison", 
        "Performance Matrix",
        "Risk Management",
        "Financial Dashboard"
    ])
    
    with tab1:
        show_project_overview(portfolio_data)
    
    with tab2:
        show_building_comparison(portfolio_data)
    
    with tab3:
        show_performance_matrix(portfolio_data)
    
    with tab4:
        show_risk_management(portfolio_data)
    
    with tab5:
        show_financial_dashboard(portfolio_data)

def show_project_overview(portfolio_data):
    """Project-level overview with drill-down capability"""
    st.markdown("### Project Portfolio Management")
    
    # Project selector for detailed view
    projects = portfolio_data['projects']
    selected_project = st.selectbox(
        "Select Project for Detailed Analysis:",
        options=["All Projects"] + [p['name'] for p in projects],
        key="project_selector"
    )
    
    if selected_project == "All Projects":
        # Show all projects summary
        st.markdown("#### All Projects Summary")
        
        project_summary_data = []
        for project in projects:
            project_summary_data.append({
                'Project Name': project['name'],
                'Buildings': project['building_count'],
                'Total Units': project['total_units'],
                'Ready Units': project['ready_units'],
                'Completion %': f"{project['completion_pct']:.1f}%",
                'Urgent Issues': project['urgent_defects'],
                'Performance Score': f"{project['performance_score']:.1f}/100",
                'Status': project['status'],
                'Last Updated': project['last_inspection']
            })
        
        df = pd.DataFrame(project_summary_data)
        
        # Color-code the dataframe
        st.dataframe(
            df,
            use_container_width=True,
            column_config={
                'Completion %': st.column_config.ProgressColumn(
                    'Completion %',
                    min_value=0,
                    max_value=100
                ),
                'Status': st.column_config.SelectboxColumn(
                    'Status',
                    options=['On Track', 'At Risk', 'Critical']
                )
            }
        )
        
        # Project performance insights
        best_project = max(projects, key=lambda p: p['performance_score'])
        worst_project = min(projects, key=lambda p: p['performance_score'])
        
        col1, col2 = st.columns(2)
        with col1:
            st.success(f"Top Performer: **{best_project['name']}** ({best_project['performance_score']:.1f}/100)")
        with col2:
            st.error(f"Needs Attention: **{worst_project['name']}** ({worst_project['performance_score']:.1f}/100)")
    
    else:
        # Show detailed project view
        project = next(p for p in projects if p['name'] == selected_project)
        show_detailed_project_view(project)

def show_detailed_project_view(project):
    """Detailed view for a specific project"""
    st.markdown(f"#### Project Details: {project['name']}")
    
    # Project KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Buildings", project['building_count'])
    with col2:
        st.metric("Total Units", project['total_units'])
    with col3:
        st.metric("Completion", f"{project['completion_pct']:.1f}%")
    with col4:
        st.metric("Performance", f"{project['performance_score']:.1f}/100")
    
    # Building breakdown for this project
    st.markdown("**Buildings in this Project:**")
    
    building_data = []
    for building in project['buildings']:
        building_data.append({
            'Building Name': building['name'],
            'Units': building['total_units'],
            'Ready Units': building['ready_units'],
            'Ready %': f"{building['ready_pct']:.1f}%",
            'Urgent Issues': building['urgent_defects'],
            'Last Inspection': building['last_inspection'],
            'Status': building['status']
        })
    
    df = pd.DataFrame(building_data)
    st.dataframe(df, use_container_width=True)
    
    # Project-specific insights
    st.markdown("**Project Insights:**")
    
    if project['urgent_defects'] > 0:
        st.error(f"Action Required: {project['urgent_defects']} urgent defects across project buildings")
    
    if project['completion_pct'] < 50:
        st.warning(f"Project behind schedule: {project['completion_pct']:.1f}% completion rate")
    
    if project['performance_score'] > 80:
        st.success("Project performing excellently")

def show_building_comparison(portfolio_data):
    """Building-by-building comparison matrix"""
    st.markdown("### Building Performance Comparison")
    
    # Building selector for filtering
    all_buildings = portfolio_data['buildings']
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        project_filter = st.selectbox(
            "Filter by Project:",
            options=["All Projects"] + list(set(b['project_name'] for b in all_buildings)),
            key="building_project_filter"
        )
    
    with col2:
        status_filter = st.selectbox(
            "Filter by Status:",
            options=["All Status", "On Track", "At Risk", "Critical"],
            key="building_status_filter"
        )
    
    with col3:
        sort_by = st.selectbox(
            "Sort by:",
            options=["Performance Score", "Completion %", "Urgent Issues", "Building Name"],
            key="building_sort"
        )
    
    # Apply filters
    filtered_buildings = all_buildings.copy()
    
    if project_filter != "All Projects":
        filtered_buildings = [b for b in filtered_buildings if b['project_name'] == project_filter]
    
    if status_filter != "All Status":
        filtered_buildings = [b for b in filtered_buildings if b['status'] == status_filter]
    
    # Sort buildings
    if sort_by == "Performance Score":
        filtered_buildings.sort(key=lambda b: b['performance_score'], reverse=True)
    elif sort_by == "Completion %":
        filtered_buildings.sort(key=lambda b: b['ready_pct'], reverse=True)
    elif sort_by == "Urgent Issues":
        filtered_buildings.sort(key=lambda b: b['urgent_defects'], reverse=True)
    else:
        filtered_buildings.sort(key=lambda b: b['name'])
    
    # Building comparison table
    building_comparison = []
    for building in filtered_buildings:
        building_comparison.append({
            'Building': building['name'],
            'Project': building['project_name'],
            'Units': building['total_units'],
            'Ready %': building['ready_pct'],
            'Urgent Issues': building['urgent_defects'],
            'Performance': building['performance_score'],
            'Status': building['status'],
            'Risk Level': building['risk_level']
        })
    
    df = pd.DataFrame(building_comparison)
    
    if len(df) > 0:
        st.dataframe(
            df,
            use_container_width=True,
            column_config={
                'Ready %': st.column_config.ProgressColumn(
                    'Ready %',
                    min_value=0,
                    max_value=100
                ),
                'Performance': st.column_config.NumberColumn(
                    'Performance',
                    min_value=0,
                    max_value=100,
                    format="%.1f"
                )
            }
        )
        
        # Comparison insights
        st.markdown("**Building Performance Insights:**")
        
        if len(df) > 1:
            top_building = df.loc[df['Performance'].idxmax()]
            bottom_building = df.loc[df['Performance'].idxmin()]
            
            col1, col2 = st.columns(2)
            with col1:
                st.success(f"Top Performer: {top_building['Building']} ({top_building['Performance']:.1f}/100)")
            with col2:
                st.error(f"Needs Attention: {bottom_building['Building']} ({bottom_building['Performance']:.1f}/100)")
    
    else:
        st.info("No buildings match the selected filters.")

def show_performance_matrix(portfolio_data):
    """Performance matrix with heatmap visualization"""
    st.markdown("### Portfolio Performance Matrix")
    
    # Performance matrix by project and building
    projects = portfolio_data['projects']
    
    # Create performance heatmap data
    matrix_data = []
    
    for project in projects:
        for building in project['buildings']:
            matrix_data.append({
                'Project': project['name'],
                'Building': building['name'],
                'Performance Score': building['performance_score'],
                'Completion %': building['ready_pct'],
                'Quality Score': building['quality_score'],
                'Risk Level': building['risk_level']
            })
    
    df = pd.DataFrame(matrix_data)
    
    if len(df) > 0:
        # Performance distribution
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Performance Distribution")
            
            excellent = len(df[df['Performance Score'] >= 80])
            good = len(df[(df['Performance Score'] >= 60) & (df['Performance Score'] < 80)])
            needs_improvement = len(df[(df['Performance Score'] >= 40) & (df['Performance Score'] < 60)])
            critical = len(df[df['Performance Score'] < 40])
            
            st.metric("Excellent (80+)", excellent)
            st.metric("Good (60-79)", good)
            st.metric("Needs Improvement (40-59)", needs_improvement)
            st.metric("Critical (<40)", critical)
        
        with col2:
            st.markdown("#### Risk Distribution")
            
            low_risk = len(df[df['Risk Level'] == 'Low'])
            medium_risk = len(df[df['Risk Level'] == 'Medium'])
            high_risk = len(df[df['Risk Level'] == 'High'])
            
            st.success(f"Low Risk: {low_risk} buildings")
            st.warning(f"Medium Risk: {medium_risk} buildings")
            st.error(f"High Risk: {high_risk} buildings")
        
        # Full performance matrix
        st.markdown("#### Complete Performance Matrix")
        st.dataframe(df, use_container_width=True)

def show_risk_management(portfolio_data):
    """Portfolio-wide risk management"""
    st.markdown("### Portfolio Risk Management")
    
    risks = assess_portfolio_risks(portfolio_data)
    
    # Risk summary
    col1, col2, col3 = st.columns(3)
    
    with col1:
        high_risks = len([r for r in risks if r['severity'] == 'High'])
        st.error(f"High Risk Items: {high_risks}")
    
    with col2:
        medium_risks = len([r for r in risks if r['severity'] == 'Medium'])
        st.warning(f"Medium Risk Items: {medium_risks}")
    
    with col3:
        low_risks = len([r for r in risks if r['severity'] == 'Low'])
        st.success(f"Low Risk Items: {low_risks}")
    
    # Risk details
    for risk in risks[:10]:  # Show top 10 risks
        if risk['severity'] == 'High':
            st.error(f"**{risk['category']}**: {risk['description']} (Affects: {risk['affected_buildings']} buildings)")
        elif risk['severity'] == 'Medium':
            st.warning(f"**{risk['category']}**: {risk['description']} (Affects: {risk['affected_buildings']} buildings)")
        else:
            st.info(f"**{risk['category']}**: {risk['description']} (Affects: {risk['affected_buildings']} buildings)")

def show_financial_dashboard(portfolio_data):
    """Financial impact across portfolio"""
    st.markdown("### Portfolio Financial Dashboard")
    
    # Financial KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_value = portfolio_data['total_portfolio_value']
        st.metric("Portfolio Value", f"${total_value:,.0f}")
    
    with col2:
        revenue_at_risk = portfolio_data['revenue_at_risk']
        st.metric("Revenue at Risk", f"${revenue_at_risk:,.0f}")
    
    with col3:
        resolution_cost = portfolio_data['total_resolution_cost']
        st.metric("Est. Resolution Cost", f"${resolution_cost:,.0f}")
    
    with col4:
        net_exposure = revenue_at_risk - resolution_cost
        st.metric("Net Exposure", f"${net_exposure:,.0f}")
    
    # Financial breakdown by project
    st.markdown("#### Financial Impact by Project")
    
    financial_data = []
    for project in portfolio_data['projects']:
        financial_data.append({
            'Project': project['name'],
            'Project Value': f"${project['project_value']:,.0f}",
            'Revenue at Risk': f"${project['revenue_at_risk']:,.0f}",
            'Resolution Cost': f"${project['resolution_cost']:,.0f}",
            'Risk %': f"{project['revenue_at_risk']/project['project_value']*100:.1f}%"
        })
    
    df = pd.DataFrame(financial_data)
    st.dataframe(df, use_container_width=True)

# Supporting functions for multi-building portfolio

def get_portfolio_data():
    """Get actual portfolio data from your database"""
    try:
        persistence_manager = DataPersistenceManager()
        conn = sqlite3.connect(persistence_manager.db_path)
        cursor = conn.cursor()
        
        # Get all buildings accessible to current user
        cursor.execute('''
            SELECT DISTINCT 
                pi.building_name,
                pi.total_units,
                SUM(CASE WHEN id.urgency = 'Urgent' THEN 1 ELSE 0 END) as urgent_defects,
                COUNT(id.id) as total_defects,
                MAX(pi.processed_at) as last_inspection
            FROM processed_inspections pi
            LEFT JOIN inspection_defects id ON pi.id = id.inspection_id
            WHERE pi.is_active = 1
            GROUP BY pi.building_name, pi.total_units
        ''')
        
        buildings = cursor.fetchall()
        conn.close()
        
        # Process real data
        portfolio_buildings = []
        total_units = 0
        total_urgent = 0
        
        for building in buildings:
            building_name, units, urgent, defects, last_inspection = building
            
            # Calculate readiness (simplified)
            ready_units = max(0, units - (defects // 3))  # Rough estimate
            
            portfolio_buildings.append({
                'name': building_name,
                'project_name': 'Default Project',  # You'd need project mapping
                'total_units': units,
                'ready_units': ready_units,
                'ready_pct': (ready_units / units * 100) if units > 0 else 0,
                'urgent_defects': urgent,
                'total_defects': defects,
                'last_inspection': last_inspection
            })
            
            total_units += units
            total_urgent += urgent
        
        return {
            'total_projects': 1,  # Until you add project structure
            'total_buildings': len(portfolio_buildings),
            'total_units': total_units,
            'total_urgent_defects': total_urgent,
            'buildings': portfolio_buildings
        }
        
    except Exception as e:
        st.error(f"Error loading portfolio data: {e}")
        return {'buildings': []}

def calculate_portfolio_health(portfolio_data):
    """Calculate overall portfolio health"""
    total_buildings = portfolio_data['total_buildings']
    critical_buildings = len([b for b in portfolio_data['buildings'] if b['status'] == 'Critical'])
    at_risk_buildings = len([b for b in portfolio_data['buildings'] if b['status'] == 'At Risk'])
    
    if critical_buildings > total_buildings * 0.2:
        overall = 'Critical'
    elif (critical_buildings + at_risk_buildings) > total_buildings * 0.4:
        overall = 'Warning'
    else:
        overall = 'Healthy'
    
    projects_on_track = len([p for p in portfolio_data['projects'] if p['status'] == 'On Track'])
    
    return {
        'overall': overall,
        'projects_on_track': projects_on_track
    }

def assess_portfolio_risks(portfolio_data):
    """Assess risks across the portfolio"""
    risks = []
    
    # Example risk assessments
    urgent_buildings = [b for b in portfolio_data['buildings'] if b['urgent_defects'] > 5]
    if urgent_buildings:
        risks.append({
            'category': 'Quality Risk',
            'description': 'Multiple buildings with high urgent defect counts',
            'severity': 'High',
            'affected_buildings': len(urgent_buildings)
        })
    
    low_completion_buildings = [b for b in portfolio_data['buildings'] if b['ready_pct'] < 30]
    if low_completion_buildings:
        risks.append({
            'category': 'Timeline Risk',
            'description': 'Buildings significantly behind completion schedule',
            'severity': 'High' if len(low_completion_buildings) > 2 else 'Medium',
            'affected_buildings': len(low_completion_buildings)
        })
    
    return risks