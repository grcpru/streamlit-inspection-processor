# word_report_generator.py
# Professional Word Report Generator for Inspection Data
# Created to match Argyle Square report style

from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_PARAGRAPH_ALIGNMENT
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.shared import OxmlElement, qn
from docx.oxml.ns import nsdecls, parse_xml
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import pandas as pd
from datetime import datetime
import pytz

class InspectionWordReportGenerator:
    """
    Professional Word report generator for inspection data.
    Matches the style of professional inspection reports.
    """
    
    def __init__(self):
        self.doc = None
        self.melbourne_tz = pytz.timezone('Australia/Melbourne')
        
    def set_cell_background_color(self, cell, color):
        """Set background color for table cell"""
        try:
            shading_elm = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls('w'), color))
            cell._tc.get_or_add_tcPr().append(shading_elm)
        except Exception:
            pass

    def create_cover_page(self, metrics):
        """Create professional cover page matching Argyle Square style"""
        
        # Set document margins
        sections = self.doc.sections
        for section in sections:
            section.top_margin = Inches(0.8)
            section.bottom_margin = Inches(0.8)
            section.left_margin = Inches(1.2)
            section.right_margin = Inches(1.2)
        
        # Add vertical spacing for centering
        for _ in range(6):
            self.doc.add_paragraph()
        
        # Main title - exact match to sample
        title_lines = [
            'Pre Settlement Inspection Reporting',
            'and Analysis on Defects',
            'for Residential Units'
        ]
        
        for i, line in enumerate(title_lines):
            if i == 0:
                title = self.doc.add_heading(line, 0)
            else:
                title = self.doc.add_paragraph(line)
                title.alignment = WD_ALIGN_PARAGRAPH.CENTER
                title_run = title.runs[0]
                title_run.font.size = Pt(20)
                title_run.font.name = 'Arial'
                title_run.font.color.rgb = RGBColor(64, 64, 64)
        
        # Format main title
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_run = title.runs[0]
        title_run.font.size = Pt(24)
        title_run.font.name = 'Arial'
        title_run.font.color.rgb = RGBColor(64, 64, 64)
        title_run.font.bold = True
        
        # Add spacing
        for _ in range(4):
            self.doc.add_paragraph()
        
        # Date - matching sample format
        melbourne_time = datetime.now(self.melbourne_tz)
        date_para = self.doc.add_paragraph(f'Created {melbourne_time.strftime("%d %B %Y")}')
        date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        date_run = date_para.runs[0]
        date_run.font.size = Pt(16)
        date_run.font.name = 'Arial'
        date_run.font.color.rgb = RGBColor(64, 64, 64)
        
        # Add spacing
        for _ in range(4):
            self.doc.add_paragraph()
        
        # Building name - bold and prominent
        building_para = self.doc.add_paragraph()
        building_run = building_para.add_run(metrics['building_name'].upper())
        building_run.font.size = Pt(26)
        building_run.font.bold = True
        building_run.font.name = 'Arial'
        building_run.font.color.rgb = RGBColor(0, 0, 0)
        building_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Address - matching sample style
        address_para = self.doc.add_paragraph(metrics['address'].upper())
        address_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        address_run = address_para.runs[0]
        address_run.font.size = Pt(18)
        address_run.font.name = 'Arial'
        address_run.font.color.rgb = RGBColor(64, 64, 64)

    def create_summary_page(self, metrics):
        """Create comprehensive summary page"""
        self.doc.add_page_break()
        
        # Page header - matching sample
        header = self.doc.add_heading(f'{metrics["building_name"]} Pre-Settlement Inspection', level=1)
        header.add_run('\nSummary')
        header_run = header.runs[0]
        header_run.font.size = Pt(20)
        header_run.font.name = 'Arial'
        header_run.font.bold = True
        header_run.font.color.rgb = RGBColor(0, 0, 0)
        
        # Overview section
        overview_heading = self.doc.add_heading('Overview', level=2)
        overview_heading.runs[0].font.size = Pt(16)
        overview_heading.runs[0].font.color.rgb = RGBColor(0, 0, 0)
        
        # Overview text - matching sample content structure
        melbourne_time = datetime.now(self.melbourne_tz)
        overview_text = f"""This overview has been collected from the pre-settlement inspection checklists for various residential units within the {metrics['building_name']} development. This report was created {melbourne_time.strftime('%dth of %B %Y')}.

Each checklist details a room-by-room inspection of specific units conducted during the inspection period. The reports identify items indicating defects or issues, such as problems with cabinets, walls, doors, and flooring, etc, accompanied with corresponding analysis.

Furthermore, this comprehensive report includes detailed analysis and trade-specific breakdowns for ease of use by builders and project managers. An automated analysis of settlement readiness has been conducted based on defect counts per unit.

Key findings from this inspection include:"""
        
        overview_para = self.doc.add_paragraph(overview_text)
        overview_para.runs[0].font.size = Pt(11)
        overview_para.runs[0].font.name = 'Arial'
        
        # Key metrics in bullet format
        self.doc.add_paragraph()
        
        metrics_list = [
            f"Total units inspected: {metrics['total_units']:,}",
            f"Total inspection points evaluated: {metrics['total_inspections']:,}",
            f"Total defects identified: {metrics['total_defects']:,}",
            f"Overall defect rate: {metrics['defect_rate']:.2f}%",
            f"Average defects per unit: {metrics['avg_defects_per_unit']:.1f}"
        ]
        
        for metric in metrics_list:
            bullet_para = self.doc.add_paragraph(metric, style='List Bullet')
            bullet_para.runs[0].font.size = Pt(11)
            bullet_para.runs[0].font.name = 'Arial'
        
        self.doc.add_paragraph()
        
        # Settlement readiness section
        readiness_text = "Settlement readiness analysis shows:"
        readiness_para = self.doc.add_paragraph(readiness_text)
        readiness_para.runs[0].font.size = Pt(11)
        readiness_para.runs[0].font.name = 'Arial'
        readiness_para.runs[0].font.bold = True
        
        readiness_list = [
            f"Ready for settlement (0-2 defects): {metrics['ready_units']} units ({metrics['ready_pct']:.1f}%)",
            f"Minor work required (3-7 defects): {metrics['minor_work_units']} units ({metrics['minor_pct']:.1f}%)",
            f"Major work required (8-15 defects): {metrics['major_work_units']} units ({metrics['major_pct']:.1f}%)",
            f"Extensive work required (15+ defects): {metrics['extensive_work_units']} units ({metrics['extensive_pct']:.1f}%)"
        ]
        
        for readiness in readiness_list:
            bullet_para = self.doc.add_paragraph(readiness, style='List Bullet')
            bullet_para.runs[0].font.size = Pt(11)
            bullet_para.runs[0].font.name = 'Arial'

    def create_units_chart_page(self, metrics):
        """Create units with most defects chart page - matching sample exactly"""
        self.doc.add_page_break()
        
        # Header - exact match to sample
        header = self.doc.add_heading('Units with the Most Defects', level=1)
        header.runs[0].font.size = Pt(20)
        header.runs[0].font.name = 'Arial'
        header.runs[0].font.color.rgb = RGBColor(0, 0, 0)
        
        # Generate chart if data available
        if len(metrics['summary_unit']) > 0:
            chart_buffer = self.create_units_defects_chart(metrics['summary_unit'])
            if chart_buffer:
                self.doc.add_picture(chart_buffer, width=Inches(6.8))
                self.doc.add_paragraph()
        
        # Most common defect section - matching sample
        self.doc.add_paragraph()
        most_common_heading = self.doc.add_heading('Most Common Defect (by specific type)', level=2)
        most_common_heading.runs[0].font.size = Pt(16)
        most_common_heading.runs[0].font.color.rgb = RGBColor(0, 0, 0)
        
        if len(metrics['summary_trade']) > 0:
            top_trade = metrics['summary_trade'].iloc[0]
            most_common_text = f'Based on the count of individually noted items across the inspection reports, "{top_trade["Trade"]}" are the most frequently reported specific defect, identified across {metrics["total_units"]} different units.\n\nThis includes various issues, such as {top_trade["Trade"].lower()}-related problems that require attention before settlement.'
        else:
            most_common_text = "Analysis of defect patterns shows various issues across different trades requiring attention."
        
        most_common_para = self.doc.add_paragraph(most_common_text)
        most_common_para.runs[0].font.size = Pt(11)
        most_common_para.runs[0].font.name = 'Arial'

    def create_units_defects_chart(self, summary_unit_data):
        """Create horizontal bar chart matching sample style"""
        try:
            plt.style.use('default')
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Get top 6 units like in sample
            top_units = summary_unit_data.head(6)
            units = [f"Unit {unit}" for unit in top_units['Unit']]
            defects = top_units['DefectCount'].values
            
            # Colors matching sample - gradient from red to blue
            colors = ['#E74C3C', '#E67E22', '#F39C12', '#27AE60', '#3498DB', '#9B59B6']
            
            # Create horizontal bar chart
            bars = ax.barh(units, defects, color=colors[:len(units)], height=0.6)
            
            # Styling to match sample exactly
            ax.set_xlabel('Number of\nDefects', fontsize=12, fontweight='bold')
            ax.set_ylabel('Unit Number', fontsize=12, fontweight='bold')
            ax.set_title('')  # No title on chart itself
            
            # Add value labels on bars - matching sample position
            for bar, value in zip(bars, defects):
                ax.text(bar.get_width() + max(defects) * 0.02, 
                       bar.get_y() + bar.get_height()/2, 
                       str(value), ha='left', va='center', 
                       fontweight='bold', fontsize=12)
            
            # Clean styling like sample
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(axis='x', alpha=0.3, linestyle='-', linewidth=0.5)
            ax.set_axisbelow(True)
            
            # Adjust layout
            plt.tight_layout()
            
            # Save to buffer
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            buffer.seek(0)
            plt.close()
            
            return buffer
            
        except Exception as e:
            print(f"Chart generation error: {e}")
            return None

    def create_commonly_reported_defects_page(self, metrics):
        """Create commonly reported defects page - matching sample structure"""
        self.doc.add_page_break()
        
        # Header
        header = self.doc.add_heading('Commonly Reported Defects', level=1)
        header.runs[0].font.size = Pt(20)
        header.runs[0].font.name = 'Arial'
        
        # Introduction - matching sample
        intro_text = """The inspection reports across """ + metrics['building_name'] + """ have identified a range of reoccurring issues, both cosmetic and functional.

Below is a summary of the most frequently reported defect types."""
        
        intro_para = self.doc.add_paragraph(intro_text)
        intro_para.runs[0].font.size = Pt(11)
        intro_para.runs[0].font.name = 'Arial'
        
        self.doc.add_paragraph()
        
        # Trade descriptions based on actual data
        if len(metrics['trade_specific_summary']) > 0:
            trade_descriptions = {
                'Painting': 'Frequently noted across entry doors, walls, ceilings, and joinery. Common issues include incomplete or uneven paint coverage, drips, scuff marks, overpainting, and inconsistencies in finish. Paint defects were also observed on balcony surfaces and laundry hardware.',
                'Doors': 'Widespread across both apartment entry doors and internal rooms. Issues include alignment problems, faulty locks/latches, stoppers that are too short or missing, and paint or hardware damage. A few doors were missing entirely or unable to be installed due to sizing constraints.',
                'Windows': 'Reported defects include windows that do not close or lock properly, tight movement, missing seals, squeaks, and loose or poorly aligned handles. External cleaning was also required in some cases.',
                'Carpentry & Joinery': 'Issues with kitchen cabinets, wardrobes, and built-in furniture. Problems include misaligned or faulty cabinetry, missing shelves, doors that failed to stay closed, and poor finishing quality.',
                'Electrical': 'Power outlets (GPOs) in kitchens, laundries, and bedrooms were sometimes loose, not flush with walls, or incorrectly installed. Light fixtures were non-functional or poorly installed in bathrooms and bedrooms.',
                'Plumbing': 'Issues across kitchen sinks, laundry facilities, showers, and drainage systems. Problems include poor positioning, missing fixtures, gaps in benchtop sealing, and blocked drains due to building debris.',
                'Flooring - Tiles': 'Common in bathrooms, ensuites, balconies, and laundries. Problems include cracked, chipped, loose, or scratched tiles, poor grouting, and unfinished builder marks. Some tiles were not properly fixed to the substrate.',
                'Flooring - Carpets': 'Predominantly in bedrooms, issues include improper installation, rippling, visible seams, or water damage.',
                'Flooring - Timber': 'Flooring in living areas and corridors was identified for caulking issues, damage, or general substandard finish.',
                'Glass': 'Particularly on balconies, defects included sliding doors that dragged, didn\'t lock properly, or were misaligned. Scratches on glass panels were also common.'
            }
            
            # Create sections for top trades
            for _, trade_row in metrics['trade_specific_summary'].head(8).iterrows():
                trade_name = trade_row['Trade']
                
                # Trade heading
                trade_heading = self.doc.add_heading(trade_name, level=2)
                trade_heading.runs[0].font.size = Pt(14)
                trade_heading.runs[0].font.color.rgb = RGBColor(0, 0, 0)
                trade_heading.runs[0].font.bold = True
                
                # Description from template or custom
                base_description = trade_descriptions.get(trade_name, 
                    f'Various issues identified with {trade_name.lower()} components throughout the development.')
                
                # Add statistics
                stats_text = f' Total defects: {trade_row["Total_Defects"]}, affecting {trade_row["Units_Affected"]} units ({trade_row["Percentage_Units_Affected"]:.1f}% of total units).'
                
                full_description = base_description + stats_text
                
                desc_para = self.doc.add_paragraph(full_description)
                desc_para.runs[0].font.size = Pt(11)
                desc_para.runs[0].font.name = 'Arial'
                
                self.doc.add_paragraph()

    def create_defects_breakdown_chart_page(self, metrics):
        """Create defects breakdown chart - matching sample exactly"""
        self.doc.add_page_break()
        
        # Header
        header = self.doc.add_heading('Breakdown of Defects, by Type', level=1)
        header.runs[0].font.size = Pt(20)
        header.runs[0].font.name = 'Arial'
        
        # Introduction matching sample
        if len(metrics['summary_trade']) > 0:
            top_trade = metrics['summary_trade'].iloc[0]
            intro_text = f"""An overview below is provided of the different defect categories, highlighting the most common category as {top_trade['Trade']}, accounting for {top_trade['DefectCount']} of the total defect count."""
        else:
            intro_text = "An overview below is provided of the different defect categories."
        
        intro_para = self.doc.add_paragraph(intro_text)
        intro_para.runs[0].font.size = Pt(11)
        intro_para.runs[0].font.name = 'Arial'
        
        self.doc.add_paragraph()
        
        # Generate chart
        if len(metrics['summary_trade']) > 0:
            chart_buffer = self.create_trade_breakdown_chart(metrics['summary_trade'])
            if chart_buffer:
                self.doc.add_picture(chart_buffer, width=Inches(7.2))

    def create_trade_breakdown_chart(self, summary_trade_data):
        """Create horizontal bar chart for trade breakdown"""
        try:
            plt.style.use('default')
            fig, ax = plt.subplots(figsize=(12, 8))
            
            # Get data - limit to top 12 like sample
            trades_data = summary_trade_data.head(12)
            
            # Colors matching sample - varied palette
            colors = ['#FFB3BA', '#FFDFBA', '#FFFFBA', '#BAFFC9', '#BAE1FF', 
                     '#E1BAFF', '#FFBAF7', '#FFF2E6', '#E6F7E6', '#E6F7FF', 
                     '#F0E6FF', '#FFE6F2']
            
            # Create horizontal bars
            bars = ax.barh(trades_data['Trade'], trades_data['DefectCount'], 
                          color=colors[:len(trades_data)], height=0.7)
            
            # Add value labels on bars - matching sample style
            for bar, value in zip(bars, trades_data['DefectCount']):
                ax.text(bar.get_width() + max(trades_data['DefectCount']) * 0.01, 
                       bar.get_y() + bar.get_height()/2, 
                       str(value), ha='left', va='center', 
                       fontweight='bold', fontsize=11)
            
            # Styling to match sample
            ax.set_xlabel('Defect Total', fontsize=12, fontweight='bold')
            ax.set_ylabel('Work Type', fontsize=12, fontweight='bold')
            
            # Clean appearance like sample
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(axis='x', alpha=0.3, linestyle='-', linewidth=0.5)
            ax.set_axisbelow(True)
            
            plt.tight_layout()
            
            # Save to buffer
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
            buffer.seek(0)
            plt.close()
            
            return buffer
            
        except Exception as e:
            print(f"Trade breakdown chart error: {e}")
            return None

    def create_trade_summary_tables(self, metrics):
        """Create comprehensive trade summary tables - matching sample structure"""
        self.doc.add_page_break()
        
        # Header
        header = self.doc.add_heading('Trade Specific Defect Summary (Across All Units)', level=1)
        header.runs[0].font.size = Pt(20)
        header.runs[0].font.name = 'Arial'
        
        # Overview section
        overview_heading = self.doc.add_heading('Overview', level=2)
        overview_heading.runs[0].font.size = Pt(16)
        
        overview_text = """This section presents a consolidated list of identified defects, grouped by trade, along with the corresponding units where each issue was observed. Please note that while some units may have multiple occurrences, they are listed only once under each trade category for clarity."""
        
        overview_para = self.doc.add_paragraph(overview_text)
        overview_para.runs[0].font.size = Pt(11)
        overview_para.runs[0].font.name = 'Arial'
        
        self.doc.add_paragraph()
        
        # Create tables by trade - matching sample format
        if len(metrics['component_details_summary']) > 0:
            component_by_trade = metrics['component_details_summary'].groupby('Trade')
            
            for i, (trade_name, trade_group) in enumerate(component_by_trade):
                # Trade heading with color coding like sample
                trade_heading = self.doc.add_heading(trade_name, level=2)
                trade_heading.runs[0].font.size = Pt(14)
                trade_heading.runs[0].font.color.rgb = RGBColor(64, 64, 64)
                trade_heading.runs[0].font.bold = True
                
                # Create table matching sample layout
                num_rows = min(len(trade_group) + 1, 15)  # Limit to prevent overflow
                table = self.doc.add_table(rows=num_rows, cols=2)
                table.style = 'Table Grid'
                table.alignment = WD_TABLE_ALIGNMENT.LEFT
                
                # Set column widths
                table.columns[0].width = Inches(2.5)
                table.columns[1].width = Inches(4.5)
                
                # Headers - matching sample style
                headers = ['Defect Area', 'Units Affected']
                header_cells = table.rows[0].cells
                
                for j, header in enumerate(headers):
                    header_cells[j].text = header
                    # Format header cells
                    for paragraph in header_cells[j].paragraphs:
                        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        for run in paragraph.runs:
                            run.font.bold = True
                            run.font.size = Pt(11)
                            run.font.name = 'Arial'
                    
                    # Header background color matching sample
                    self.set_cell_background_color(header_cells[j], 'D3D3D3')
                
                # Add data rows
                for j, (_, row) in enumerate(trade_group.head(num_rows-1).iterrows(), 1):
                    data_cells = table.rows[j].cells
                    
                    # Combine Room and Component for defect area
                    defect_area = f"{row['Room']} {row['Component']}"
                    data_cells[0].text = defect_area
                    data_cells[1].text = str(row['Units with Defects'])
                    
                    # Format data cells
                    for cell in data_cells:
                        for paragraph in cell.paragraphs:
                            for run in paragraph.runs:
                                run.font.size = Pt(10)
                                run.font.name = 'Arial'
                
                self.doc.add_paragraph()
                
                # Page break after every 2 trades to match sample layout
                if i % 2 == 1 and i < len(component_by_trade) - 1:
                    self.doc.add_page_break()

    def generate_complete_report(self, final_df, metrics):
        """Generate the complete professional Word report"""
        
        # Initialize document
        self.doc = Document()
        
        # Create all sections
        self.create_cover_page(metrics)
        self.create_summary_page(metrics)
        self.create_units_chart_page(metrics)
        self.create_commonly_reported_defects_page(metrics)
        self.create_defects_breakdown_chart_page(metrics)
        self.create_trade_summary_tables(metrics)
        
        # Add contact/footer page
        self.doc.add_page_break()
        
        # Add significant spacing to push content to bottom
        for _ in range(25):
            self.doc.add_paragraph()
        
        # Contact information - matching sample style
        contact_para = self.doc.add_paragraph('Inspection Report Processor')
        contact_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        contact_para.runs[0].font.size = Pt(14)
        contact_para.runs[0].font.name = 'Arial'
        contact_para.runs[0].font.bold = True
        
        # Generation info
        melbourne_time = datetime.now(self.melbourne_tz)
        generated_para = self.doc.add_paragraph(f'Generated {melbourne_time.strftime("%d %B %Y at %I:%M %p AEDT")}')
        generated_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        generated_para.runs[0].font.size = Pt(12)
        generated_para.runs[0].font.name = 'Arial'
        
        return self.doc

# Convenience function for easy import
def generate_professional_word_report(final_df, metrics):
    """
    Generate a professional Word report matching industry standards.
    
    Args:
        final_df: DataFrame with processed inspection data
        metrics: Dictionary containing calculated metrics
        
    Returns:
        Document object ready for saving
    """
    generator = InspectionWordReportGenerator()
    return generator.generate_complete_report(final_df, metrics)

# Example usage function
def save_word_report_example(final_df, metrics, filename="inspection_report.docx"):
    """
    Example function showing how to generate and save a Word report.
    
    Args:
        final_df: Processed inspection DataFrame
        metrics: Calculated metrics dictionary
        filename: Output filename
    """
    
    # Generate the report
    doc = generate_professional_word_report(final_df, metrics)
    
    # Save to file
    doc.save(filename)
    print(f"Professional Word report saved as: {filename}")
    
    return doc

if __name__ == "__main__":
    # Example of how to use this module
    print("Word Report Generator Module")
    print("Import this module and use generate_professional_word_report()")
    print("Example: doc = generate_professional_word_report(final_df, metrics)")
