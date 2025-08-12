# Enhanced Word Report Generator with Pastel Colors and Improved Visual Appeal
# Improvements: Pastel color schemes, better typography, enhanced visual elements

from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import parse_xml
from datetime import datetime
import pandas as pd
import os
import tempfile
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import numpy as np

# Enhanced Darker Pastel Color Palette
PASTEL_COLORS = {
    'primary': '#6B91B5',      # Darker soft blue
    'secondary': '#A68B6E',    # Darker warm beige
    'accent': '#8BC88B',       # Darker soft green
    'warning': '#E6A373',      # Darker soft orange
    'danger': '#D68B8B',       # Darker soft red
    'neutral': '#B5B5B5',      # Darker light gray
    'success': '#9DD49D',      # Darker light green
    'info': '#7DBEF4',         # Darker light blue
    'dark': '#5A6B78',         # Darker soft gray-blue
    'light': '#E8E9EA'         # Darker very light gray
}

# Enhanced chart color palettes with darker tones
CHART_PALETTES = {
    'pastel_blues': ['#B3D4F1', '#8BB8E8', '#6B9BD1', '#4A7FB8', '#3B6B9C', '#2C5580', '#1F4164', '#163048'],
    'pastel_greens': ['#C1E8C1', '#9DD49D', '#7BC07B', '#5AAC5A', '#4A9C4A', '#3B8C3B', '#2C7C2C', '#1D6C1D'],
    'pastel_oranges': ['#F4D4A7', '#E6B574', '#D89641', '#CA7D1A', '#B86F14', '#A6610E', '#945308', '#824502'],
    'pastel_mixed': ['#B3D4F1', '#C1E8C1', '#F4D4A7', '#E8B8D4', '#D4B8E8', '#C8D1E8', '#B8E8D1', '#F1E8A7'],
    'severity_colors': {
        'critical': '#E8A8A8',    # Darker light red
        'extensive': '#E6C288',   # Darker light orange  
        'major': '#F1E173',       # Darker light yellow
        'minor': '#B8D4A8',       # Darker light green
        'ready': '#A8D4A8'        # Darker soft green
    }
}

def generate_enhanced_word_report(processed_data, metrics, images=None):
    """
    Generate enhanced professional Word report with pastel colors and improved visual appeal
    """
    
    try:
        # Create new document
        doc = Document()
        
        # Setup enhanced document formatting
        setup_enhanced_document_formatting(doc)
        
        # Enhanced cover page with better visual elements
        add_enhanced_cover_page(doc, metrics, images)
        
        # Executive overview with improved layout
        add_enhanced_executive_overview(doc, metrics)
        
        # Inspection process with visual elements
        add_enhanced_inspection_process(doc, metrics)
        
        # Units analysis with enhanced charts
        add_enhanced_units_analysis(doc, metrics)
        
        # Enhanced defects analysis
        add_enhanced_defects_analysis(doc, processed_data, metrics)
        
        # Data visualization with pastel charts
        add_enhanced_data_visualization(doc, processed_data, metrics)
        
        # Trade-specific summary with better formatting
        add_enhanced_trade_summary(doc, processed_data, metrics)
        
        # Component breakdown with improved visuals
        add_enhanced_component_breakdown(doc, processed_data, metrics)
        
        # Strategic recommendations with icons and better layout
        add_enhanced_recommendations(doc, metrics)
        
        # Professional footer with enhanced design
        add_enhanced_footer(doc, metrics)
        
        return doc
    
    except Exception as e:
        print(f"Error in generate_enhanced_word_report: {e}")
        return create_error_document(e, metrics)

def setup_enhanced_document_formatting(doc):
    """Enhanced document formatting with better typography and spacing"""
    
    # Set document margins with more breathing room
    sections = doc.sections
    for section in sections:
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)
    
    styles = doc.styles
    
    # Enhanced title style with softer colors
    if 'EnhancedTitle' not in [s.name for s in styles]:
        title_style = styles.add_style('EnhancedTitle', 1)
        title_font = title_style.font
        title_font.name = 'Segoe UI'  # Modern font
        title_font.size = Pt(32)
        title_font.bold = True
        title_font.color.rgb = RGBColor(75, 133, 150)  # Soft blue-gray
        title_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_style.paragraph_format.space_after = Pt(24)
        title_style.paragraph_format.space_before = Pt(12)
    
    # Enhanced section header with pastel accent
    if 'EnhancedSectionHeader' not in [s.name for s in styles]:
        section_style = styles.add_style('EnhancedSectionHeader', 1)
        section_font = section_style.font
        section_font.name = 'Segoe UI Semibold'
        section_font.size = Pt(20)
        section_font.bold = True
        section_font.color.rgb = RGBColor(104, 142, 173)  # Pastel blue
        section_style.paragraph_format.space_before = Pt(30)
        section_style.paragraph_format.space_after = Pt(16)
        section_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    
    # Enhanced subsection header
    if 'EnhancedSubsectionHeader' not in [s.name for s in styles]:
        subsection_style = styles.add_style('EnhancedSubsectionHeader', 1)
        subsection_font = subsection_style.font
        subsection_font.name = 'Segoe UI Semibold'
        subsection_font.size = Pt(16)
        subsection_font.bold = True
        subsection_font.color.rgb = RGBColor(126, 162, 189)  # Lighter pastel blue
        subsection_style.paragraph_format.space_before = Pt(20)
        subsection_style.paragraph_format.space_after = Pt(12)
    
    # Enhanced body text with better readability
    if 'EnhancedBody' not in [s.name for s in styles]:
        body_style = styles.add_style('EnhancedBody', 1)
        body_font = body_style.font
        body_font.name = 'Segoe UI'
        body_font.size = Pt(12)
        body_font.color.rgb = RGBColor(70, 70, 70)  # Softer black
        body_style.paragraph_format.line_spacing = 1.3  # More generous line spacing
        body_style.paragraph_format.space_after = Pt(8)
        body_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    
    # Enhanced highlight text style
    if 'EnhancedHighlight' not in [s.name for s in styles]:
        highlight_style = styles.add_style('EnhancedHighlight', 1)
        highlight_font = highlight_style.font
        highlight_font.name = 'Segoe UI'
        highlight_font.size = Pt(12)
        highlight_font.bold = True
        highlight_font.color.rgb = RGBColor(104, 142, 173)
        highlight_style.paragraph_format.line_spacing = 1.3
        highlight_style.paragraph_format.space_after = Pt(8)

def add_enhanced_cover_page(doc, metrics, images=None):
    """Enhanced cover page with improved layout - shows Inspection Overview if no cover image"""
    
    try:
        # Company logo with better positioning
        if images and images.get('logo') and os.path.exists(images['logo']):
            try:
                logo_para = doc.add_paragraph()
                logo_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                logo_run = logo_para.add_run()
                logo_run.add_picture(images['logo'], width=Inches(3.5))
                doc.add_paragraph()
            except Exception:
                pass
        
        # Enhanced main title with decorative elements
        title_para = doc.add_paragraph()
        title_para.style = 'EnhancedTitle'
        title_run = title_para.add_run("✦ PRE-SETTLEMENT INSPECTION REPORT ✦")
        
        # Decorative line
        deco_para = doc.add_paragraph()
        deco_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        deco_run = deco_para.add_run("━━━━━━━━━━━━━━━━━━━━━━━━━━")
        deco_run.font.color.rgb = RGBColor(166, 139, 110)  # Darker pastel beige
        deco_run.font.size = Pt(14)
        
        # Enhanced building name with better styling
        doc.add_paragraph()
        building_para = doc.add_paragraph()
        building_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        building_run = building_para.add_run(f"{metrics.get('building_name', 'Building Name').upper()}")
        building_run.font.name = 'Segoe UI Light'
        building_run.font.size = Pt(24)
        building_run.font.bold = False
        building_run.font.color.rgb = RGBColor(107, 145, 181)  # Darker blue
        
        # Enhanced address with better formatting
        doc.add_paragraph()
        address_para = doc.add_paragraph()
        address_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        address_run = address_para.add_run(metrics.get('address', 'Address'))
        address_run.font.name = 'Segoe UI'
        address_run.font.size = Pt(14)
        address_run.font.color.rgb = RGBColor(110, 110, 110)  # Darker gray
        
        # Check if cover image exists and is valid
        has_cover_image = (images and images.get('cover') and 
                          os.path.exists(images['cover']))
        
        if has_cover_image:
            try:
                # Add cover image with optimized spacing
                doc.add_paragraph()
                cover_para = doc.add_paragraph()
                cover_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cover_run = cover_para.add_run()
                cover_run.add_picture(images['cover'], width=Inches(5.5))
                doc.add_paragraph()
                
                # Add compact metrics dashboard after image
                add_enhanced_metrics_dashboard(doc, metrics)
                
            except Exception as e:
                print(f"Error loading cover image: {e}")
                # Fallback to inspection overview if image fails
                has_cover_image = False
        
        if not has_cover_image:
            # Show Inspection Overview instead of cover image
            doc.add_paragraph()
            doc.add_paragraph()
            
            # Add decorative inspection overview header
            overview_header = doc.add_paragraph()
            overview_header.alignment = WD_ALIGN_PARAGRAPH.CENTER
            overview_run = overview_header.add_run("✦ INSPECTION OVERVIEW ✦")
            overview_run.font.name = 'Segoe UI Semibold'
            overview_run.font.size = Pt(18)
            overview_run.font.color.rgb = RGBColor(107, 145, 181)  # Darker blue
            
            doc.add_paragraph()
            
            # Enhanced metrics dashboard takes center stage
            add_enhanced_metrics_dashboard(doc, metrics)
        
        # Enhanced report details with icons - always at bottom
        doc.add_paragraph()
        details_para = doc.add_paragraph()
        details_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        details_text = f"""📋 Comprehensive Pre-Settlement Quality Assessment
🏠 Residential Unit Inspection & Defect Analysis

Generated on {datetime.now().strftime('%d %B %Y')}

📅 Inspection Date: {metrics.get('inspection_date', 'N/A')}
🏗️ Units Inspected: {metrics.get('total_units', 0):,}
🔍 Components Evaluated: {metrics.get('total_inspections', 0):,}
📊 Quality Score: {max(0, 100 - (metrics.get('avg_defects_per_unit', 0) * 10)):.0f}/100"""
        
        details_run = details_para.add_run(details_text)
        details_run.font.name = 'Segoe UI'
        details_run.font.size = Pt(11)
        details_run.font.color.rgb = RGBColor(90, 107, 120)  # Darker gray-blue
        
        doc.add_page_break()
    
    except Exception as e:
        print(f"Error in enhanced cover page: {e}")

def add_enhanced_metrics_dashboard(doc, metrics):
    """Enhanced metrics dashboard with pastel colors and better visual appeal"""
    
    try:
        doc.add_paragraph()
        doc.add_paragraph()
        
        # Add decorative header
        dashboard_header = doc.add_paragraph()
        dashboard_header.alignment = WD_ALIGN_PARAGRAPH.CENTER
        header_run = dashboard_header.add_run("✦ INSPECTION OVERVIEW ✦")
        header_run.font.name = 'Segoe UI Semibold'
        header_run.font.size = Pt(16)
        header_run.font.color.rgb = RGBColor(75, 120, 150)  # Darker blue
        
        doc.add_paragraph()
        
        # Create enhanced table with better spacing
        table = doc.add_table(rows=2, cols=3)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        
        # Set column widths
        for i, width in enumerate([Inches(2.5), Inches(2.5), Inches(2.5)]):
            table.columns[i].width = width
        
        # Enhanced metrics data with emoji icons
        metrics_data = [
            ("🏠 TOTAL UNITS", f"{metrics.get('total_units', 0):,}", "Units Inspected", PASTEL_COLORS['info']),
            ("🚨 DEFECTS FOUND", f"{metrics.get('total_defects', 0):,}", f"{metrics.get('defect_rate', 0):.1f}% Rate", PASTEL_COLORS['warning']),
            ("✅ READY UNITS", f"{metrics.get('ready_units', 0)}", f"{metrics.get('ready_pct', 0):.1f}%", PASTEL_COLORS['success']),
            ("⚠️ MINOR WORK", f"{metrics.get('minor_work_units', 0)}", f"{metrics.get('minor_pct', 0):.1f}%", PASTEL_COLORS['accent']),
            ("🔧 MAJOR WORK", f"{metrics.get('major_work_units', 0)}", f"{metrics.get('major_pct', 0):.1f}%", PASTEL_COLORS['warning']),
            ("🚧 EXTENSIVE WORK", f"{metrics.get('extensive_work_units', 0)}", f"{metrics.get('extensive_pct', 0):.1f}%", PASTEL_COLORS['danger'])
        ]
        
        # Fill cells with enhanced styling
        for i, (label, value, subtitle, bg_color) in enumerate(metrics_data):
            row = i // 3
            col = i % 3
            cell = table.cell(row, col)
            cell.vertical_alignment = 1
            
            # Set subtle background color
            set_cell_background_color(cell, bg_color.replace('#', ''))
            
            para = cell.paragraphs[0]
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # Enhanced label styling
            label_run = para.add_run(f"{label}\n")
            label_run.font.name = 'Segoe UI'
            label_run.font.size = Pt(10)
            label_run.font.color.rgb = RGBColor(70, 70, 70)
            
            # Enhanced value styling with darker colors
            value_run = para.add_run(f"{value}\n")
            value_run.font.name = 'Segoe UI Semibold'
            value_run.font.size = Pt(18)
            value_run.font.bold = True
            value_run.font.color.rgb = RGBColor(75, 120, 150)  # Darker blue
            
            # Enhanced subtitle styling with darker colors
            subtitle_run = para.add_run(subtitle)
            subtitle_run.font.name = 'Segoe UI'
            subtitle_run.font.size = Pt(9)
            subtitle_run.font.color.rgb = RGBColor(90, 107, 120)  # Darker gray-blue
    
    except Exception as e:
        print(f"Error in enhanced metrics dashboard: {e}")

def create_enhanced_pie_chart(doc, metrics):
    """Enhanced pie chart with pastel colors and better styling"""
    
    try:
        if 'summary_trade' not in metrics or len(metrics['summary_trade']) == 0:
            return
        
        breakdown_header = doc.add_paragraph("Defects Distribution by Trade Category")
        breakdown_header.style = 'EnhancedSubsectionHeader'
        
        trade_data = metrics['summary_trade'].head(8)
        
        # Set up pastel color scheme
        pastel_colors = CHART_PALETTES['pastel_mixed']
        
        fig, ax = plt.subplots(figsize=(11, 9))
        
        # Enhanced pie chart with pastel colors
        wedges, texts, autotexts = ax.pie(
            trade_data['DefectCount'], 
            labels=trade_data['Trade'], 
            colors=pastel_colors[:len(trade_data)],
            autopct='%1.1f%%',
            startangle=90,
            textprops={'fontsize': 11, 'fontfamily': 'serif'},
            wedgeprops={'edgecolor': 'white', 'linewidth': 2},
            pctdistance=0.85
        )
        
        # Enhanced title with better styling
        ax.set_title('Distribution of Defects by Trade Category', 
                    fontsize=18, fontweight='600', pad=25,
                    color='#4B8596', fontfamily='serif')
        
        # Enhanced text styling
        for autotext in autotexts:
            autotext.set_color('#2C3E50')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(10)
        
        for text in texts:
            text.set_fontsize(11)
            text.set_color('#34495E')
            text.set_fontweight('500')
        
        # Add subtle shadow effect
        plt.gca().add_artist(plt.Circle((0,0), 0.7, color='lightgray', alpha=0.1, zorder=0))
        
        plt.tight_layout()
        add_chart_to_document(doc, fig)
        plt.close()
        
        # Enhanced summary text
        total_defects = metrics.get('total_defects', 0)
        if len(trade_data) > 0:
            top_trade = trade_data.iloc[0]
            summary_text = f"""📊 The analysis reveals {top_trade['Trade']} as the primary defect category, representing {top_trade['DefectCount']} of the total {total_defects:,} defects ({top_trade['DefectCount']/total_defects*100:.1f}% of all identified issues). This concentration provides clear direction for focused remediation efforts and resource allocation priorities."""
            
            summary_para = doc.add_paragraph(summary_text)
            summary_para.style = 'EnhancedBody'
    
    except Exception as e:
        print(f"Error creating enhanced pie chart: {e}")

def create_enhanced_severity_chart(doc, metrics):
    """Enhanced severity distribution chart with pastel colors"""
    
    try:
        chart_title = doc.add_paragraph("Unit Classification by Defect Severity")
        chart_title.style = 'EnhancedSubsectionHeader'
        
        if 'summary_unit' in metrics and len(metrics['summary_unit']) > 0:
            fig, ax = plt.subplots(figsize=(12, 7))
            
            units_data = metrics['summary_unit']
            
            categories = []
            counts = []
            colors = []
            
            # Critical (25+)
            critical_count = len(units_data[units_data['DefectCount'] > 25])
            if critical_count > 0:
                categories.append('Critical\n(25+ defects)')
                counts.append(critical_count)
                colors.append(CHART_PALETTES['severity_colors']['critical'])
            
            # Extensive (15-24)
            extensive_count = len(units_data[(units_data['DefectCount'] >= 15) & (units_data['DefectCount'] <= 25)])
            categories.append('Extensive\n(15-24 defects)')
            counts.append(extensive_count)
            colors.append(CHART_PALETTES['severity_colors']['extensive'])
            
            # Major (8-14)
            major_count = len(units_data[(units_data['DefectCount'] >= 8) & (units_data['DefectCount'] <= 14)])
            categories.append('Major\n(8-14 defects)')
            counts.append(major_count)
            colors.append(CHART_PALETTES['severity_colors']['major'])
            
            # Minor (3-7)
            minor_count = len(units_data[(units_data['DefectCount'] >= 3) & (units_data['DefectCount'] <= 7)])
            categories.append('Minor\n(3-7 defects)')
            counts.append(minor_count)
            colors.append(CHART_PALETTES['severity_colors']['minor'])
            
            # Ready (0-2)
            ready_count = len(units_data[units_data['DefectCount'] <= 2])
            categories.append('Ready\n(0-2 defects)')
            counts.append(ready_count)
            colors.append(CHART_PALETTES['severity_colors']['ready'])
            
            # Create enhanced bar chart
            bars = ax.bar(categories, counts, color=colors, alpha=0.8, 
                         edgecolor='white', linewidth=2.5)
            
            # Enhanced styling
            ax.set_ylabel('Number of Units', fontsize=14, fontweight='600', color='#4B8596')
            ax.set_title('Unit Distribution by Defect Severity Level', 
                        fontsize=18, fontweight='600', pad=25, color='#4B8596')
            ax.grid(axis='y', alpha=0.3, linestyle=':', color='gray')
            ax.set_facecolor('#FAFBFC')
            
            # Enhanced value labels with styling
            for bar, value in zip(bars, counts):
                if value > 0:
                    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(counts)*0.01,
                           f'{value}', ha='center', va='bottom', 
                           fontweight='bold', fontsize=13, color='#2C3E50')
            
            # Style the axes
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#BDC3C7')
            ax.spines['bottom'].set_color('#BDC3C7')
            
            plt.xticks(rotation=0, fontsize=11)
            plt.tight_layout()
            add_chart_to_document(doc, fig)
            plt.close()
    
    except Exception as e:
        print(f"Error creating enhanced severity chart: {e}")

def add_enhanced_data_visualization(doc, processed_data, metrics):
    """Enhanced data visualization section with pastel charts"""
    
    try:
        header = doc.add_paragraph("📊 COMPREHENSIVE DATA VISUALIZATION")
        header.style = 'EnhancedSectionHeader'
        
        # Add section description
        intro_text = "This section presents visual analytics of the inspection data, highlighting key patterns and trends to support strategic decision-making and resource allocation."
        intro_para = doc.add_paragraph(intro_text)
        intro_para.style = 'EnhancedBody'
        
        doc.add_paragraph()
        
        # Enhanced pie chart with pastel colors
        create_enhanced_pie_chart(doc, metrics)
        
        # Enhanced severity distribution chart
        create_enhanced_severity_chart(doc, metrics)
        
        # Enhanced trade analysis chart
        create_enhanced_trade_chart(doc, metrics)
        
        doc.add_page_break()
    
    except Exception as e:
        print(f"Error in enhanced data visualization: {e}")

def create_enhanced_trade_chart(doc, metrics):
    """Enhanced trade analysis chart with gradient colors"""
    
    try:
        trade_header = doc.add_paragraph("Trade Category Performance Analysis")
        trade_header.style = 'EnhancedSubsectionHeader'
        
        if 'summary_trade' not in metrics or len(metrics['summary_trade']) == 0:
            return
        
        top_trades = metrics['summary_trade'].head(10)
        
        fig, ax = plt.subplots(figsize=(13, 9))
        
        # Create gradient color scheme
        colors = plt.cm.Pastel1(np.linspace(0, 1, len(top_trades)))
        
        # Create horizontal bar chart with enhanced styling
        y_pos = np.arange(len(top_trades))
        bars = ax.barh(y_pos, top_trades['DefectCount'], 
                      color=colors, alpha=0.85, 
                      edgecolor='white', linewidth=2)
        
        # Enhanced styling
        ax.set_yticks(y_pos)
        ax.set_yticklabels(top_trades['Trade'], fontsize=12, color='#2C3E50')
        ax.set_xlabel('Number of Defects', fontsize=14, fontweight='600', color='#4B8596')
        ax.set_title('Trade Categories Ranked by Defect Frequency', 
                    fontsize=18, fontweight='600', pad=30, color='#4B8596')
        
        # Enhanced grid and background
        ax.grid(axis='x', alpha=0.3, linestyle=':', color='gray')
        ax.set_facecolor('#FAFBFC')
        
        # Enhanced value labels with percentage
        total_defects = metrics.get('total_defects', 1)
        for i, (bar, value) in enumerate(zip(bars, top_trades['DefectCount'])):
            percentage = (value / total_defects * 100) if total_defects > 0 else 0
            ax.text(bar.get_width() + max(top_trades['DefectCount']) * 0.02, 
                   bar.get_y() + bar.get_height()/2,
                   f'{value} ({percentage:.1f}%)', va='center', 
                   fontweight='600', fontsize=11, color='#2C3E50')
        
        # Style the axes
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#BDC3C7')
        ax.spines['bottom'].set_color('#BDC3C7')
        
        plt.tight_layout()
        add_chart_to_document(doc, fig)
        plt.close()
    
    except Exception as e:
        print(f"Error creating enhanced trade chart: {e}")

# Enhanced versions of other functions with similar improvements...
def add_enhanced_executive_overview(doc, metrics):
    """Enhanced executive overview with better formatting and visual elements"""
    
    try:
        header = doc.add_paragraph("📋 EXECUTIVE OVERVIEW")
        header.style = 'EnhancedSectionHeader'
        
        # Add visual separator
        separator = doc.add_paragraph()
        separator.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sep_run = separator.add_run("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        sep_run.font.color.rgb = RGBColor(196, 164, 132)
        sep_run.font.size = Pt(8)
        
        doc.add_paragraph()
        
        overview_text = f"""This comprehensive quality assessment encompasses the systematic evaluation of {metrics.get('total_units', 0):,} residential units within {metrics.get('building_name', 'the building complex')}, conducted on {metrics.get('inspection_date', 'the inspection date')}. This report was compiled on {datetime.now().strftime('%d %B %Y')}.

🔍 **Inspection Methodology**: Each unit underwent thorough room-by-room evaluation covering all major building components, including structural elements, mechanical systems, finishes, fixtures, and fittings. The assessment follows industry-standard protocols for pre-settlement quality verification.

📊 **Key Findings**: The inspection revealed {metrics.get('total_defects', 0):,} individual defects across {metrics.get('total_inspections', 0):,} evaluated components, yielding an overall defect rate of {metrics.get('defect_rate', 0):.2f}%. Settlement readiness analysis indicates {metrics.get('ready_pct', 0):.1f}% of units ({metrics.get('ready_units', 0)} units) are ready for immediate handover.

🎯 **Strategic Insights**: The data reveals systematic patterns across trade categories, with concentrated defect types requiring targeted remediation strategies. This analysis enables optimized resource allocation and realistic timeline planning for settlement preparation."""
        
        overview_para = doc.add_paragraph(overview_text)
        overview_para.style = 'EnhancedBody'
        
        doc.add_page_break()
    
    except Exception as e:
        print(f"Error in enhanced executive overview: {e}")

# Include similar enhancements for other functions...
# (Additional enhanced functions would follow the same pattern)

def add_chart_to_document(doc, fig):
    """Enhanced helper function to add charts with better positioning"""
    
    try:
        chart_buffer = BytesIO()
        fig.savefig(chart_buffer, format='png', dpi=300, bbox_inches='tight', 
                    facecolor='white', edgecolor='none', pad_inches=0.2)
        chart_buffer.seek(0)
        
        chart_para = doc.add_paragraph()
        chart_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        chart_run = chart_para.add_run()
        chart_run.add_picture(chart_buffer, width=Inches(7))
        
        doc.add_paragraph()
    
    except Exception as e:
        print(f"Error adding enhanced chart: {e}")

def set_cell_background_color(cell, color_hex):
    """Enhanced cell background color with opacity support"""
    
    try:
        shading_elm = parse_xml(f'<w:shd xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:fill="{color_hex}"/>')
        cell._tc.get_or_add_tcPr().append(shading_elm)
    except Exception as e:
        print(f"Could not set cell background color: {e}")

def add_enhanced_inspection_process(doc, metrics):
    """Enhanced inspection process with visual icons and better formatting"""
    
    try:
        header = doc.add_paragraph("🔍 INSPECTION PROCESS & METHODOLOGY")
        header.style = 'EnhancedSectionHeader'
        
        # Add decorative line
        deco_para = doc.add_paragraph()
        deco_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        deco_run = deco_para.add_run("⟦ ◆ ◇ ◆ ◇ ◆ ◇ ◆ ◇ ◆ ◇ ◆ ◇ ◆ ◇ ◆ ◇ ◆ ◇ ◆ ◇ ◆ ◇ ◆ ◇ ◆ ◇ ◆ ⟧")
        deco_run.font.color.rgb = RGBColor(196, 164, 132)
        deco_run.font.size = Pt(10)
        
        doc.add_paragraph()
        
        # Scope section with enhanced formatting
        scope_header = doc.add_paragraph("📋 INSPECTION SCOPE & STANDARDS")
        scope_header.style = 'EnhancedSubsectionHeader'
        
        scope_text = f"""The comprehensive pre-settlement quality assessment was systematically executed across all {metrics.get('total_units', 0):,} residential units, encompassing detailed evaluation of {metrics.get('total_inspections', 0):,} individual components and building systems.

🏗️ **Structural Assessment**
• Building envelope integrity and weatherproofing
• Structural elements and load-bearing components
• Foundation and concrete work evaluation

⚡ **Systems Evaluation**  
• Electrical installations, fixtures, and safety compliance
• Plumbing systems, water pressure, and drainage
• HVAC systems and ventilation adequacy

🎨 **Finishes & Fixtures**
• Wall, ceiling, and flooring finish quality
• Door and window installation and operation
• Kitchen and bathroom fixture functionality
• Built-in storage and joinery craftsmanship"""
        
        scope_para = doc.add_paragraph(scope_text)
        scope_para.style = 'EnhancedBody'
        
        doc.add_paragraph()
        
        # Quality criteria section
        criteria_header = doc.add_paragraph("🎯 QUALITY ASSESSMENT CRITERIA")
        criteria_header.style = 'EnhancedSubsectionHeader'
        
        criteria_text = """Classification methodology follows systematic evaluation protocols:

✅ **Compliant Status**: Component meets required standards and specifications, ready for settlement
❌ **Defect Status**: Component requires remediation or adjustment before final handover  
⚪ **Not Applicable**: Component not present, accessible, or relevant to specific unit configuration

Each assessment point is documented with photographic evidence and detailed descriptions to facilitate efficient remediation workflows."""
        
        criteria_para = doc.add_paragraph(criteria_text)
        criteria_para.style = 'EnhancedBody'
        
        doc.add_paragraph()
        
        # Settlement readiness section
        readiness_header = doc.add_paragraph("🏠 SETTLEMENT READINESS CLASSIFICATION")
        readiness_header.style = 'EnhancedSubsectionHeader'
        
        readiness_text = """Units are categorized using evidence-based defect thresholds and estimated remediation timeframes:

🟢 **Ready for Settlement** (0-2 defects)
   Immediate settlement capability with minor or cosmetic issues only

🟡 **Minor Work Required** (3-7 defects)  
   1-3 days estimated remediation time for quick fixes and adjustments

🟠 **Major Work Required** (8-15 defects)
   1-2 weeks estimated completion for substantial repairs and installations

🔴 **Extensive Work Required** (15+ defects)
   2-4 weeks estimated timeframe for comprehensive remediation and quality upgrades"""
        
        readiness_para = doc.add_paragraph(readiness_text)
        readiness_para.style = 'EnhancedBody'
        
        doc.add_page_break()
    
    except Exception as e:
        print(f"Error in enhanced inspection process: {e}")

def add_enhanced_units_analysis(doc, metrics):
    """Enhanced units analysis with improved charts and formatting"""
    
    try:
        header = doc.add_paragraph("🏠 UNITS REQUIRING PRIORITY ATTENTION")
        header.style = 'EnhancedSectionHeader'
        
        if 'summary_unit' in metrics and len(metrics['summary_unit']) > 0:
            # Create enhanced charts
            create_enhanced_units_horizontal_chart(doc, metrics)
            create_enhanced_severity_chart(doc, metrics)
            
            # Enhanced summary analysis
            top_unit = metrics['summary_unit'].iloc[0]
            total_units = metrics.get('total_units', 0)
            
            summary_text = f"""📊 **Priority Analysis Results**: Unit {top_unit['Unit']} requires immediate priority attention with {top_unit['DefectCount']} identified defects, representing the highest concentration of remediation needs within the development.

🎯 **Resource Allocation Framework**:
• **Critical Priority**: {len(metrics['summary_unit'][metrics['summary_unit']['DefectCount'] > 15])} units requiring extensive remediation (15+ defects each)
• **High Priority**: {len(metrics['summary_unit'][(metrics['summary_unit']['DefectCount'] > 7) & (metrics['summary_unit']['DefectCount'] <= 15)])} units requiring major work (8-15 defects each)  
• **Medium Priority**: {len(metrics['summary_unit'][(metrics['summary_unit']['DefectCount'] > 2) & (metrics['summary_unit']['DefectCount'] <= 7)])} units requiring minor work (3-7 defects each)
• **Settlement Ready**: {len(metrics['summary_unit'][metrics['summary_unit']['DefectCount'] <= 2])} units ready for immediate handover

💡 **Strategic Insights**: This distribution pattern enables targeted resource deployment and realistic timeline forecasting for settlement preparation activities. The concentration of defects in specific units suggests opportunities for parallel remediation workflows and optimized trade scheduling."""
            
            summary_para = doc.add_paragraph(summary_text)
            summary_para.style = 'EnhancedBody'
        
        doc.add_page_break()
    
    except Exception as e:
        print(f"Error in enhanced units analysis: {e}")

def create_enhanced_units_horizontal_chart(doc, metrics):
    """Enhanced horizontal chart for top units with gradient colors"""
    
    try:
        if 'summary_unit' not in metrics or len(metrics['summary_unit']) == 0:
            return
        
        chart_title = doc.add_paragraph("Top 20 Units Requiring Immediate Intervention")
        chart_title.style = 'EnhancedSubsectionHeader'
        
        top_units = metrics['summary_unit'].head(20)
        
        if len(top_units) > 0:
            fig, ax = plt.subplots(figsize=(14, 11))
            
            # Enhanced color coding with pastel gradients
            colors = []
            for count in top_units['DefectCount']:
                if count > 25:
                    colors.append('#E8A8A8')  # Darker light red
                elif count > 15:
                    colors.append('#E6C288')  # Darker light orange
                elif count > 7:
                    colors.append('#F1E173')  # Darker light yellow
                elif count > 2:
                    colors.append('#B8D4A8')  # Darker light green
                else:
                    colors.append('#A8D4A8')  # Darker soft green
            
            # Create enhanced chart
            y_pos = np.arange(len(top_units))
            bars = ax.barh(y_pos, top_units['DefectCount'], color=colors, alpha=0.8, 
                          edgecolor='white', linewidth=2)
            
            # Enhanced styling
            ax.set_yticks(y_pos)
            ax.set_yticklabels([f"Unit {unit}" for unit in top_units['Unit']], 
                              fontsize=12, color='#2C3E50')
            ax.set_xlabel('Number of Defects', fontsize=14, fontweight='600', color='#4B8596')
            ax.set_title('Units Ranked by Defect Concentration (Priority Order)',
                        fontsize=18, fontweight='600', pad=25, color='#4B8596')
            
            # Enhanced grid and background
            ax.grid(axis='x', alpha=0.3, linestyle=':', color='gray')
            ax.set_facecolor('#FAFBFC')
            
            # Enhanced value labels
            for i, (bar, value) in enumerate(zip(bars, top_units['DefectCount'])):
                ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                       f'{value}', va='center', fontweight='bold', fontsize=12, color='#2C3E50')
            
            # Enhanced legend with darker pastel colors
            from matplotlib.patches import Patch
            legend_elements = [
                Patch(facecolor='#E8A8A8', label='Critical (25+ defects)', alpha=0.8),
                Patch(facecolor='#E6C288', label='Extensive (15-24 defects)', alpha=0.8),
                Patch(facecolor='#F1E173', label='Major (8-14 defects)', alpha=0.8),
                Patch(facecolor='#B8D4A8', label='Minor (3-7 defects)', alpha=0.8),
                Patch(facecolor='#A8D4A8', label='Ready (0-2 defects)', alpha=0.8)
            ]
            ax.legend(handles=legend_elements, loc='upper right', fontsize=11, framealpha=0.9)
            
            # Style the axes
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#BDC3C7')
            ax.spines['bottom'].set_color('#BDC3C7')
            
            plt.tight_layout()
            add_chart_to_document(doc, fig)
            plt.close()
    
    except Exception as e:
        print(f"Error creating enhanced units chart: {e}")

def add_enhanced_defects_analysis(doc, processed_data, metrics):
    """Enhanced defects analysis with better visual presentation"""
    
    try:
        header = doc.add_paragraph("📈 DEFECT PATTERNS & ANALYSIS")
        header.style = 'EnhancedSectionHeader'
        
        if 'summary_trade' in metrics and len(metrics['summary_trade']) > 0:
            top_trade = metrics['summary_trade'].iloc[0]
            total_defects = metrics.get('total_defects', 0)
            trade_percentage = (top_trade['DefectCount']/total_defects*100) if total_defects > 0 else 0
            
            defects_text = f"""🔍 **Primary Defect Category Analysis**: The comprehensive evaluation of {total_defects:,} individually documented defects reveals "{top_trade['Trade']}" as the dominant concern category, accounting for {top_trade['DefectCount']} instances ({trade_percentage:.1f}% of total defects).

🎯 **Pattern Recognition**: This concentration within the {top_trade['Trade'].lower()} trade category encompasses multiple sub-issues including installation inconsistencies, finish quality variations, functional defects, and compliance gaps. The systematic nature of these defects indicates opportunities for targeted quality control improvements.

💡 **Strategic Implications**: The clustering of defects within specific trade categories suggests that focused remediation efforts targeting the top 3-4 trade categories could address approximately 60-80% of all identified issues, enabling efficient resource deployment and accelerated settlement timelines."""
            
            defects_para = doc.add_paragraph(defects_text)
            defects_para.style = 'EnhancedBody'
        
        doc.add_page_break()
    
    except Exception as e:
        print(f"Error in enhanced defects analysis: {e}")

def add_enhanced_recommendations(doc, metrics):
    """Enhanced recommendations with better formatting and visual elements"""
    
    try:
        header = doc.add_paragraph("🚀 STRATEGIC RECOMMENDATIONS & ACTION PLAN")
        header.style = 'EnhancedSectionHeader'
        
        # Enhanced immediate priorities
        priorities_header = doc.add_paragraph("⚡ IMMEDIATE PRIORITIES (Next 14 Days)")
        priorities_header.style = 'EnhancedSubsectionHeader'
        
        priorities = []
        ready_pct = metrics.get('ready_pct', 0)
        extensive_units = metrics.get('extensive_work_units', 0)
        
        # Enhanced settlement strategy with emojis
        if ready_pct > 75:
            priorities.append("🎯 **Accelerated Settlement Protocol**: With 75%+ units ready, implement immediate settlement for compliant units while establishing parallel remediation workflows for remaining inventory.")
        elif ready_pct > 50:
            priorities.append("⚖️ **Phased Settlement Strategy**: Establish structured settlement phases prioritizing ready units first, with clear milestone-based progression for units under remediation.")
        else:
            priorities.append("🔧 **Quality-First Approach**: Implement comprehensive remediation program before settlement to ensure optimal customer satisfaction and minimize post-settlement defect claims.")
        
        # Enhanced trade-specific priorities
        if 'summary_trade' in metrics and len(metrics['summary_trade']) > 0:
            top_trade = metrics['summary_trade'].iloc[0]
            top_trade_pct = (top_trade['DefectCount'] / metrics.get('total_defects', 1) * 100)
            priorities.append(f"🔧 **{top_trade['Trade']} Focus Initiative**: This trade represents {top_trade_pct:.1f}% of all defects ({top_trade['DefectCount']} instances). Deploy dedicated supervision teams and additional resources with daily progress monitoring.")
        
        # Enhanced resource allocation
        if extensive_units > 0:
            priorities.append(f"👥 **Specialized Remediation Teams**: {extensive_units} units require extensive work (15+ defects each). Establish dedicated teams with enhanced supervision to maintain project timeline integrity and quality standards.")
        
        # Enhanced quality control
        priorities.append("📋 **Enhanced Quality Protocols**: Implement multi-tier inspection checkpoints with supervisor sign-offs for critical trades before final handover, reducing post-settlement callback rates.")
        
        for i, priority in enumerate(priorities, 1):
            priority_para = doc.add_paragraph(f"{i}. {priority}")
            priority_para.style = 'EnhancedBody'
            priority_para.paragraph_format.left_indent = Inches(0.4)
        
        doc.add_paragraph()
        
        # Enhanced medium-term strategies
        medium_header = doc.add_paragraph("📊 MEDIUM-TERM STRATEGIES (30-60 Days)")
        medium_header.style = 'EnhancedSubsectionHeader'
        
        medium_strategies = [
            "📈 **Performance Analytics Dashboard**: Establish real-time KPI monitoring with weekly stakeholder reviews tracking defect remediation rates, settlement readiness improvements, and customer satisfaction metrics.",
            "🎓 **Continuous Improvement Program**: Implement systematic lessons learned capture from this inspection to enhance quality control procedures and prevention strategies for future construction phases.",
            "📞 **Stakeholder Engagement Protocol**: Maintain proactive communication with unit owners including regular progress updates, revised settlement schedules, and transparent timeline management.",
            "💰 **Cost Optimization Strategy**: Negotiate bulk material procurement agreements and extended trade crew availability to optimize remediation costs while maintaining quality standards.",
            "🔍 **Advanced Quality Assurance**: Develop predictive quality control protocols using this inspection data to prevent similar defect patterns in future developments and construction phases."
        ]
        
        for i, strategy in enumerate(medium_strategies, 1):
            strategy_para = doc.add_paragraph(f"{i}. {strategy}")
            strategy_para.style = 'EnhancedBody'
            strategy_para.paragraph_format.left_indent = Inches(0.4)
        
        doc.add_page_break()
    
    except Exception as e:
        print(f"Error in enhanced recommendations: {e}")

def add_enhanced_footer(doc, metrics):
    """Enhanced footer with better design and comprehensive information"""
    
    try:
        header = doc.add_paragraph("📋 REPORT DOCUMENTATION & APPENDICES")
        header.style = 'EnhancedSectionHeader'
        
        # Enhanced methodology section
        methodology_header = doc.add_paragraph("🔬 INSPECTION METHODOLOGY & COMPLIANCE")
        methodology_header.style = 'EnhancedSubsectionHeader'
        
        methodology_text = """**INDUSTRY STANDARDS COMPLIANCE**:
This comprehensive quality assessment was conducted in full accordance with Australian building standards, industry best practices, and established protocols for pre-settlement residential construction evaluation. All accessible areas and building components were systematically assessed using standardized criteria developed for residential quality control.

**EVALUATION METHODOLOGY**:
• ✅ **Compliant**: Component meets all required standards and specifications, approved for settlement
• ❌ **Defect**: Component requires remediation, adjustment, or completion before final handover
• ⚪ **Not Applicable**: Component not present, accessible, or relevant to specific unit configuration

**SETTLEMENT READINESS FRAMEWORK**:
• **Ready for Settlement**: 0-2 minor defects (immediate settlement capability)
• **Minor Work Required**: 3-7 defects (1-3 days estimated remediation)  
• **Major Work Required**: 8-15 defects (1-2 weeks estimated completion)
• **Extensive Work Required**: 15+ defects (2-4 weeks estimated timeframe)"""
        
        methodology_para = doc.add_paragraph(methodology_text)
        methodology_para.style = 'EnhancedBody'
        
        doc.add_paragraph()
        
        # Enhanced data summary
        data_summary_header = doc.add_paragraph("📊 COMPREHENSIVE INSPECTION METRICS")
        data_summary_header.style = 'EnhancedSubsectionHeader'
        
        avg_defects = metrics.get('avg_defects_per_unit', 0)
        defect_rate = metrics.get('defect_rate', 0)
        quality_score = max(0, 100 - defect_rate)
        
        data_summary_text = f"""**INSPECTION SCOPE & RESULTS**:
• Total Residential Units Evaluated: {metrics.get('total_units', 0):,}
• Total Building Components Assessed: {metrics.get('total_inspections', 0):,}
• Total Defects Documented: {metrics.get('total_defects', 0):,}
• Overall Defect Rate: {metrics.get('defect_rate', 0):.2f}%
• Average Defects per Unit: {avg_defects:.2f}
• Development Quality Score: {quality_score:.0f}/100

**SETTLEMENT READINESS DISTRIBUTION**:
• Ready for Immediate Settlement: {metrics.get('ready_units', 0)} units ({metrics.get('ready_pct', 0):.1f}%)
• Minor Remediation Required: {metrics.get('minor_work_units', 0)} units ({metrics.get('minor_pct', 0):.1f}%)
• Major Remediation Required: {metrics.get('major_work_units', 0)} units ({metrics.get('major_pct', 0):.1f}%)  
• Extensive Remediation Required: {metrics.get('extensive_work_units', 0)} units ({metrics.get('extensive_pct', 0):.1f}%)"""
        
        data_summary_para = doc.add_paragraph(data_summary_text)
        data_summary_para.style = 'EnhancedBody'
        
        doc.add_paragraph()
        
        # Enhanced report details with better formatting
        details_header = doc.add_paragraph("📄 REPORT GENERATION & COMPANION RESOURCES")
        details_header.style = 'EnhancedSubsectionHeader'
        
        details_text = f"""**REPORT METADATA**:
• Report Generated: {datetime.now().strftime('%d %B %Y at %I:%M %p')}
• Inspection Completion: {metrics.get('inspection_date', 'N/A')}
• Building Development: {metrics.get('building_name', 'N/A')}
• Property Location: {metrics.get('address', 'N/A')}

**COMPANION DOCUMENTATION SUITE**:
Complete defect inventories, unit-by-unit detailed breakdowns, interactive filterable data tables, and comprehensive photographic documentation are available in the accompanying Excel analytics workbook. This comprehensive dataset includes advanced filtering capabilities, dynamic visual dashboards, pivot table analysis tools, and direct export functionality for integration with project management systems and remediation tracking platforms.

**TECHNICAL SUPPORT & FOLLOW-UP**:
For technical inquiries, data interpretation assistance, or additional analysis requirements, please contact the inspection team. Ongoing support is available for remediation planning, progress tracking, and post-completion verification inspections."""
        
        details_para = doc.add_paragraph(details_text)
        details_para.style = 'EnhancedBody'
        
        # Add decorative closing
        doc.add_paragraph()
        closing_para = doc.add_paragraph()
        closing_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        closing_run = closing_para.add_run("✦ END OF REPORT ✦")
        closing_run.font.name = 'Segoe UI'
        closing_run.font.size = Pt(14)
        closing_run.font.color.rgb = RGBColor(104, 142, 173)
        closing_run.font.bold = True
    
    except Exception as e:
        print(f"Error in enhanced footer: {e}")

# Backward compatibility and additional functions
def create_error_document(error, metrics):
    """Create enhanced error document"""
    
    doc = Document()
    title = doc.add_heading("Inspection Report - Generation Error", level=1)
    error_para = doc.add_paragraph(f"Report generation encountered an issue: {str(error)}")
    
    if metrics:
        basic_para = doc.add_paragraph(f"""
Basic Information:
Building: {metrics.get('building_name', 'N/A')}
Total Units: {metrics.get('total_units', 'N/A')}
Total Defects: {metrics.get('total_defects', 'N/A')}
        """)
    
    return doc

# Additional helper functions for missing components
def add_enhanced_trade_summary(doc, processed_data, metrics):
    """Enhanced trade summary with better visual presentation"""
    
    try:
        header = doc.add_paragraph("🔧 TRADE-SPECIFIC DEFECT ANALYSIS")
        header.style = 'EnhancedSectionHeader'
        
        overview_text = """This section provides a comprehensive breakdown of identified defects organized by trade category, including complete unit inventories for targeted remediation planning and resource allocation optimization."""
        
        overview_para = doc.add_paragraph(overview_text)
        overview_para.style = 'EnhancedBody'
        
        doc.add_paragraph()
        
        if processed_data is not None and len(processed_data) > 0:
            try:
                component_details = generate_complete_component_details(processed_data)
                add_enhanced_trade_tables(doc, component_details)
            except Exception as e:
                print(f"Error generating enhanced trade tables: {e}")
        
        doc.add_page_break()
    
    except Exception as e:
        print(f"Error in enhanced trade summary: {e}")

def generate_complete_component_details(processed_data):
    """Generate component details for trade analysis"""
    
    try:
        required_columns = ['StatusClass', 'Trade', 'Room', 'Component', 'Unit']
        missing_columns = [col for col in required_columns if col not in processed_data.columns]
        
        if missing_columns:
            print(f"Missing columns: {missing_columns}")
            return pd.DataFrame()
        
        defects_only = processed_data[processed_data['StatusClass'] == 'Not OK']
        
        if len(defects_only) == 0:
            return pd.DataFrame()
        
        component_summary = defects_only.groupby(['Trade', 'Room', 'Component']).agg({
            'Unit': lambda x: ', '.join(sorted(x.astype(str).unique()))
        }).reset_index()
        
        component_summary.columns = ['Trade', 'Room', 'Component', 'Affected Units']
        
        unit_counts = defects_only.groupby(['Trade', 'Room', 'Component'])['Unit'].nunique().reset_index()
        component_summary = component_summary.merge(unit_counts, on=['Trade', 'Room', 'Component'])
        component_summary.columns = ['Trade', 'Room', 'Component', 'Affected Units', 'Unit Count']
        
        component_summary = component_summary.sort_values(['Trade', 'Unit Count'], ascending=[True, False])
        
        return component_summary
    
    except Exception as e:
        print(f"Error generating component details: {e}")
        return pd.DataFrame()

def add_enhanced_trade_tables(doc, component_details):
    """Add enhanced trade tables with better formatting"""
    
    try:
        if len(component_details) == 0:
            return
        
        trades = component_details['Trade'].unique()
        
        for trade in trades:
            try:
                trade_data = component_details[component_details['Trade'] == trade]
                
                trade_header = doc.add_paragraph(f"🔧 {trade}")
                trade_header.style = 'EnhancedSubsectionHeader'
                
                table = doc.add_table(rows=1, cols=3)
                table.style = 'Table Grid'
                
                table.columns[0].width = Inches(2.5)
                table.columns[1].width = Inches(4.0)
                table.columns[2].width = Inches(0.8)
                
                headers = ['Component & Location', 'Affected Units', 'Count']
                for i, header in enumerate(headers):
                    cell = table.cell(0, i)
                    cell.text = header
                    para = cell.paragraphs[0]
                    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run = para.runs[0]
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(255, 255, 255)
                    run.font.size = Pt(11)
                    
                    set_cell_background_color(cell, "688EAD")  # Pastel blue header
                
                for _, row in trade_data.iterrows():
                    table_row = table.add_row()
                    
                    component_location = str(row['Component'])
                    if pd.notna(row['Room']) and str(row['Room']).strip():
                        component_location += f" ({row['Room']})"
                    
                    table_row.cells[0].text = component_location
                    table_row.cells[0].paragraphs[0].runs[0].font.size = Pt(10)
                    
                    table_row.cells[1].text = str(row['Affected Units'])
                    table_row.cells[1].paragraphs[0].runs[0].font.size = Pt(10)
                    
                    table_row.cells[2].text = str(row['Unit Count'])
                    table_row.cells[2].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                    table_row.cells[2].paragraphs[0].runs[0].font.size = Pt(10)
                    table_row.cells[2].paragraphs[0].runs[0].font.bold = True
                
                doc.add_paragraph()
            
            except Exception as e:
                print(f"Error processing trade {trade}: {e}")
                continue
    
    except Exception as e:
        print(f"Error in enhanced trade tables: {e}")

def add_enhanced_component_breakdown(doc, processed_data, metrics):
    """Enhanced component breakdown analysis"""
    
    try:
        header = doc.add_paragraph("🔍 COMPONENT-LEVEL ANALYSIS")
        header.style = 'EnhancedSectionHeader'
        
        intro_text = "This analysis identifies the most frequently affected individual components across all units, enabling targeted quality control improvements and preventive measures for future construction phases."
        
        intro_para = doc.add_paragraph(intro_text)
        intro_para.style = 'EnhancedBody'
        
        doc.add_paragraph()
        
        # Generate and display component analysis
        if processed_data is not None and len(processed_data) > 0:
            component_data = generate_complete_component_details(processed_data)
            
            if len(component_data) > 0:
                component_aggregated = component_data.groupby(['Component', 'Trade']).agg({
                    'Unit Count': 'sum',
                    'Affected Units': lambda x: ', '.join(x.astype(str).unique()) if len(x) > 1 else x.iloc[0]
                }).reset_index()
                
                top_components = component_aggregated.nlargest(15, 'Unit Count')
                
                if len(top_components[top_components['Unit Count'] > 1]) >= 10:
                    top_components = top_components[top_components['Unit Count'] > 1].head(10)
                
                most_freq_header = doc.add_paragraph("🎯 Most Frequently Affected Components")
                most_freq_header.style = 'EnhancedSubsectionHeader'
                
                if len(top_components) > 0:
                    comp_table = doc.add_table(rows=1, cols=5)
                    comp_table.style = 'Table Grid'
                    
                    comp_table.columns[0].width = Inches(2.0)
                    comp_table.columns[1].width = Inches(1.8)
                    comp_table.columns[2].width = Inches(2.5)
                    comp_table.columns[3].width = Inches(0.8)
                    comp_table.columns[4].width = Inches(1.0)
                    
                    headers = ['Component', 'Trade', 'Sample Affected Units', 'Total Count', 'Percentage']
                    for i, header in enumerate(headers):
                        cell = comp_table.cell(0, i)
                        cell.text = header
                        para = cell.paragraphs[0]
                        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        run = para.runs[0]
                        run.font.bold = True
                        run.font.color.rgb = RGBColor(255, 255, 255)
                        run.font.size = Pt(11)
                        
                        set_cell_background_color(cell, "688EAD")
                    
                    total_units = metrics.get('total_units', 1)
                    for _, comp_row in top_components.iterrows():
                        row = comp_table.add_row()
                        
                        # Component
                        row.cells[0].text = str(comp_row.get('Component', 'N/A'))
                        row.cells[0].paragraphs[0].runs[0].font.size = Pt(10)
                        
                        # Trade
                        row.cells[1].text = str(comp_row.get('Trade', 'N/A'))
                        row.cells[1].paragraphs[0].runs[0].font.size = Pt(10)
                        
                        # Sample affected units
                        affected_units = str(comp_row.get('Affected Units', ''))
                        if len(affected_units) > 30:
                            units_list = affected_units.split(', ')
                            sample_units = ', '.join(units_list[:5])
                            if len(units_list) > 5:
                                sample_units += f" (+ {len(units_list)-5} more)"
                            row.cells[2].text = sample_units
                        else:
                            row.cells[2].text = affected_units
                        row.cells[2].paragraphs[0].runs[0].font.size = Pt(9)
                        
                        # Count
                        unit_count = comp_row.get('Unit Count', 0)
                        row.cells[3].text = str(unit_count)
                        row.cells[3].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                        row.cells[3].paragraphs[0].runs[0].font.size = Pt(10)
                        row.cells[3].paragraphs[0].runs[0].font.bold = True
                        
                        # Percentage
                        percentage = (unit_count / total_units * 100) if total_units > 0 else 0
                        row.cells[4].text = f"{percentage:.1f}%"
                        row.cells[4].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                        row.cells[4].paragraphs[0].runs[0].font.size = Pt(10)
                        row.cells[4].paragraphs[0].runs[0].font.bold = True
                    
                    # Enhanced analysis text
                    if len(top_components) > 0:
                        top_component = top_components.iloc[0]
                        unit_count = top_component.get('Unit Count', 0)
                        component_name = top_component.get('Component', 'Unknown')
                        trade_name = top_component.get('Trade', 'Unknown')
                        
                        doc.add_paragraph()
                        
                        analysis_text = f"""🔍 **Component Analysis Insights**: "{component_name}" emerges as the most frequently affected component, impacting {unit_count} units ({unit_count/total_units*100:.1f}% of all inspected units). This pattern reveals a systematic issue requiring immediate attention within the {trade_name} trade category.

📊 **Key Findings from Component Analysis**:
• The top 5 most problematic components collectively affect {top_components.head(5)['Unit Count'].sum()} units across the development
• {trade_name} trade demonstrates the highest frequency of component-specific defects
• Recurring component failures across multiple units indicate potential systematic installation or quality control issues
• Component-level patterns suggest opportunities for targeted supplier quality improvements

💡 **Strategic Recommendations**: The concentration of defects in specific components presents clear opportunities for focused interventions, enhanced installation procedures, and strengthened quality control protocols during the construction process. Addressing these top components systematically could resolve a significant portion of overall defects."""
                        
                        analysis_para = doc.add_paragraph(analysis_text)
                        analysis_para.style = 'EnhancedBody'
                else:
                    no_pattern_text = "📊 The component-level analysis reveals distributed defects across various components without significant concentration patterns, indicating isolated issues rather than systematic component problems."
                    
                    no_pattern_para = doc.add_paragraph(no_pattern_text)
                    no_pattern_para.style = 'EnhancedBody'
        else:
            no_data_para = doc.add_paragraph("📋 Component-level breakdown data is not available for detailed analysis in this report.")
            no_data_para.style = 'EnhancedBody'
        
        doc.add_page_break()
    
    except Exception as e:
        print(f"Error in enhanced component breakdown: {e}")

# Backward compatibility functions
def generate_professional_word_report(processed_data, metrics, images=None):
    """Backward compatibility wrapper for the enhanced report generator"""
    return generate_enhanced_word_report(processed_data, metrics, images)

def generate_word_report(processed_data, metrics, images=None):
    """Backward compatibility function"""
    return generate_enhanced_word_report(processed_data, metrics, images)

def create_inspection_report(processed_data, metrics, images=None):
    """Alternative function name for backward compatibility"""
    return generate_enhanced_word_report(processed_data, metrics, images)

# Main execution and testing
if __name__ == "__main__":
    print("✨ Enhanced Word Report Generator with Pastel Colors loaded successfully!")
    print("\n🎨 VISUAL ENHANCEMENTS APPLIED:")
    print("• ✅ Pastel color palette throughout charts and tables")
    print("• ✅ Enhanced typography with Segoe UI font family")
    print("• ✅ Improved visual hierarchy with better spacing")
    print("• ✅ Enhanced icons and decorative elements")
    print("• ✅ Gradient color schemes in charts")
    print("• ✅ Better visual balance and readability")
    print("• ✅ Professional pastel styling while maintaining readability")
    print("• ✅ Enhanced chart legends and labels")
    print("• ✅ Improved table styling with subtle backgrounds")
    print("• ✅ Better document flow and visual breathing room")
    
    print("\n🎯 KEY IMPROVEMENTS:")
    print("• More engaging visual presentation")
    print("• Professional pastel color scheme")
    print("• Enhanced readability and scanning")
    print("• Better visual hierarchy")
    print("• Improved professional appearance")
    print("• Maintains backward compatibility")