"""
Property Developer Dashboard Module  
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from .shared_components import show_system_status_widget, get_corrected_database_stats
from permission_manager import get_permission_manager, check_permission_ui
from secure_ui_helpers import create_secure_ui, secure_section_header

class DeveloperDashboard:
    def __init__(self):
        self.user = self.get_current_user()
    
    def get_current_user(self):
        return {
            "username": st.session_state.get("username", ""),
            "name": st.session_state.get("user_name", "Developer"),
            "email": st.session_state.get("user_email", ""),
            "role": st.session_state.get("user_role", "property_developer")
        }
    
    def show(self):
        """Main developer dashboard display"""
        st.markdown(f"""
        <div class="main-header">
            <h1>Portfolio Management Dashboard</h1>
            <p>Property Developer Interface</p>
            <div style="margin-top: 1rem; opacity: 0.9; font-size: 0.9em;">
                <span>Welcome back, <strong>{self.user['name']}</strong>!</span>
                <span style="margin-left: 2rem;">Role: <strong>Property Developer</strong></span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Show system status
        show_system_status_widget()
        
        if st.session_state.metrics is not None:
            self.show_portfolio_analytics()
        else:
            st.warning("No inspection data available. Contact your team to process inspection data.")
    
    def show_portfolio_analytics(self):
        """Portfolio analytics for developers"""
        metrics = st.session_state.metrics
        
        # Executive summary
        st.markdown("### Current Building Analysis")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Building", metrics['building_name'])
        with col2:
            st.metric("Total Units", metrics['total_units'])
        with col3:
            st.metric("Ready for Settlement", f"{metrics['ready_units']} ({metrics['ready_pct']:.1f}%)")
        with col4:
            st.metric("Urgent Issues", metrics['urgent_defects'])
        
        # Financial analysis section
        self.show_financial_analysis()
        
        # Executive reports
        self.show_executive_reports()
    
    def show_financial_analysis(self):
        """Financial analysis with optional building value input"""
        metrics = st.session_state.metrics
        
        st.markdown("---")
        st.markdown("### Portfolio Analytics")
        
        # Optional building value input
        st.markdown("#### Optional: Building Financial Data")
        col1, col2 = st.columns(2)
        
        with col1:
            building_value = st.number_input(
                "Building Value (AUD)", 
                min_value=0, 
                value=0,
                step=1000000,
                help="Enter actual building value for financial analysis (optional)"
            )
        
        with col2:
            if building_value > 0:
                calculated_unit_value = building_value / metrics['total_units']
                st.metric("Calculated Unit Value", f"${calculated_unit_value:,.0f}")
                st.caption("Automatically calculated from building value")
            else:
                st.info("Enter building value to see unit calculations")
        
        # Performance overview
        self.show_performance_overview(building_value)
    
    def show_performance_overview(self, building_value):
        """Executive performance overview"""
        metrics = st.session_state.metrics
        
        st.markdown("#### Executive Performance Overview")
        
        # Calculate performance metrics
        avg_defects_per_unit = metrics['avg_defects_per_unit']
        
        # Performance grade
        if avg_defects_per_unit <= 2:
            performance_grade = "A"
            grade_color = "success"
            grade_description = "Excellent Quality"
        elif avg_defects_per_unit <= 5:
            performance_grade = "B"
            grade_color = "info"
            grade_description = "Good Quality"
        elif avg_defects_per_unit <= 10:
            performance_grade = "C"
            grade_color = "warning"
            grade_description = "Needs Improvement"
        else:
            performance_grade = "D"
            grade_color = "error"
            grade_description = "Critical Quality Issues"
        
        # Display performance metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if grade_color == "success":
                st.success(f"Quality Grade: **{performance_grade}**")
            elif grade_color == "info":
                st.info(f"Quality Grade: **{performance_grade}**")
            elif grade_color == "warning":
                st.warning(f"Quality Grade: **{performance_grade}**")
            else:
                st.error(f"Quality Grade: **{performance_grade}**")
            st.caption(grade_description)
        
        with col2:
            completion_score = metrics['ready_pct']
            st.metric("Settlement Readiness", f"{completion_score:.1f}%")
        
        with col3:
            risk_level = "Low" if metrics['urgent_defects'] == 0 else "Medium" if metrics['urgent_defects'] <= 3 else "High"
            if risk_level == "Low":
                st.success(f"Risk Level: **{risk_level}**")
            elif risk_level == "Medium":
                st.warning(f"Risk Level: **{risk_level}**")
            else:
                st.error(f"Risk Level: **{risk_level}**")
        
        with col4:
            days_since_inspection = 7  # Placeholder
            velocity = metrics['ready_units'] / max(days_since_inspection / 7, 1)
            st.metric("Completion Velocity", f"{velocity:.1f} units/week")
        
        # Financial analysis (only if building value provided)
        if building_value > 0:
            self.show_financial_impact_analysis(building_value)
    
    def show_financial_impact_analysis(self, building_value):
        """Financial impact analysis"""
        metrics = st.session_state.metrics
        
        st.markdown("#### Financial Impact Analysis")
        
        unit_value = building_value / metrics['total_units']
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            ready_value = metrics['ready_units'] * unit_value
            st.metric("Ready Unit Value", f"${ready_value:,.0f}")
        
        with col2:
            incomplete_units = metrics['total_units'] - metrics['ready_units']
            revenue_at_risk = incomplete_units * unit_value * 0.02
            st.metric("Revenue at Risk", f"${revenue_at_risk:,.0f}")
        
        with col3:
            estimated_resolution_cost = metrics['total_defects'] * 1500
            st.metric("Est. Resolution Cost", f"${estimated_resolution_cost:,.0f}")
        
        with col4:
            if revenue_at_risk > estimated_resolution_cost:
                roi = ((revenue_at_risk - estimated_resolution_cost) / estimated_resolution_cost) * 100
                st.success(f"Positive ROI: {roi:.0f}%")
            else:
                st.info("Cost-benefit analysis")
    
    def show_executive_reports(self):
        """Executive report generation"""
        st.markdown("---")
        st.markdown("### Executive Reports")
        
        # Portfolio Analytics button
        if st.button("Portfolio Analytics Dashboard", type="secondary", use_container_width=True):
            try:
                from portfolio_analytics import generate_portfolio_analytics_report
                generate_portfolio_analytics_report()
            except ImportError:
                st.error("Portfolio analytics module not available")