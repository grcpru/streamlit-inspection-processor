"""
Professional Excel Report Generator for Inspection Reports
This module generates professional Excel documents matching the Argyle Square format
"""

import pandas as pd
from datetime import datetime
import pytz
from io import BytesIO
import xlsxwriter


def generate_professional_excel_report(final_df, metrics):
    """
    Generate a professional Excel report matching the Argyle Square format
    
    Args:
        final_df: Processed inspection DataFrame
        metrics: Dictionary containing calculated metrics
        
    Returns:
        BytesIO: Excel file buffer
    """
    
    # Create BytesIO buffer
    excel_buffer = BytesIO()
    
    # Create workbook with xlsxwriter for better formatting
    workbook = xlsxwriter.Workbook(excel_buffer, {'nan_inf_to_errors': True})
    
    # Define comprehensive formats matching the professional style
    title_format = workbook.add_format({
        'bold': True,
        'font_size': 18,
        'bg_color': '#4CAF50',
        'font_color': 'white',
        'align': 'center',
        'valign': 'vcenter',
        'border': 2,
        'border_color': '#2E7D32'
    })
    
    building_header = workbook.add_format({
        'bold': True,
        'font_size': 14,
        'bg_color': '#2196F3',
        'font_color': 'white',
        'align': 'center',
        'valign': 'vcenter',
        'border': 1
    })
    
    section_header = workbook.add_format({
        'bold': True,
        'font_size': 12,
        'bg_color': '#FF9800',
        'font_color': 'white',
        'align': 'center',
        'valign': 'vcenter',
        'border': 1
    })
    
    label_format = workbook.add_format({
        'bold': True,
        'font_size': 11,
        'bg_color': '#F5F5F5',
        'border': 1,
        'align': 'left',
        'valign': 'vcenter'
    })
    
    data_format = workbook.add_format({
        'font_size': 11,
        'border': 1,
        'align': 'right',
        'valign': 'vcenter'
    })
    
    # Settlement readiness formats with color coding
    ready_format = workbook.add_format({
        'font_size': 11,
        'border': 1,
        'align': 'right',
        'valign': 'vcenter',
        'bg_color': '#C8E6C9',
        'font_color': '#2E7D32'
    })
    
    minor_format = workbook.add_format({
        'font_size': 11,
        'border': 1,
        'align': 'right',
        'valign': 'vcenter',
        'bg_color': '#FFF3C4',
        'font_color': '#F57F17'
    })
    
    major_format = workbook.add_format({
        'font_size': 11,
        'border': 1,
        'align': 'right',
        'valign': 'vcenter',
        'bg_color': '#FFCDD2',
        'font_color': '#C62828'
    })
    
    extensive_format = workbook.add_format({
        'font_size': 11,
        'border': 1,
        'align': 'right',
        'valign': 'vcenter',
        'bg_color': '#F8BBD9',
        'font_color': '#AD1457'
    })
    
    # Data table header format
    table_header = workbook.add_format({
        'bold': True,
        'font_size': 10,
        'bg_color': '#37474F',
        'font_color': 'white',
        'align': 'center',
        'valign': 'vcenter',
        'border': 1,
        'text_wrap': True
    })
    
    # Data cell format
    cell_format = workbook.add_format({
        'font_size': 10,
        'border': 1,
        'align': 'left',
        'valign': 'vcenter'
    })
    
    # Alternating row format
    alt_row_format = workbook.add_format({
        'font_size': 10,
        'border': 1,
        'align': 'left',
        'valign': 'vcenter',
        'bg_color': '#F8F9FA'
    })
    
    footer_format = workbook.add_format({
        'font_size': 9,
        'italic': True,
        'align': 'center',
        'font_color': '#666666'
    })
    
    # ===== EXECUTIVE DASHBOARD SHEET =====
    worksheet = workbook.add_worksheet("📊 Executive Dashboard")
    worksheet.set_column('A:A', 35)
    worksheet.set_column('B:B', 45)
    
    current_row = 0
    
    # Main Title
    worksheet.merge_range(f'A{current_row + 1}:B{current_row + 1}', 
                         f'🏢 {metrics["building_name"].upper()} - INSPECTION REPORT', title_format)
    worksheet.set_row(current_row, 30)
    current_row += 2
    
    # Building Information Section
    worksheet.merge_range(f'A{current_row + 1}:B{current_row + 1}', 
                         '🏢 BUILDING INFORMATION', building_header)
    worksheet.set_row(current_row, 25)
    current_row += 2
    
    building_data = [
        ('Building Name', metrics['building_name']),
        ('Address', metrics['address']),
        ('Inspection Date', metrics['inspection_date']),
        ('Total Units Inspected', f"{metrics['total_units']:,}"),
        ('Unit Types', metrics['unit_types_str'])
    ]
    
    for label, value in building_data:
        worksheet.write(current_row, 0, label, label_format)
        worksheet.write(current_row, 1, value, data_format)
        current_row += 1
    
    current_row += 1
    
    # Inspection Summary Section
    worksheet.merge_range(f'A{current_row + 1}:B{current_row + 1}', 
                         '📋 INSPECTION SUMMARY', section_header)
    worksheet.set_row(current_row, 25)
    current_row += 2
    
    inspection_data = [
        ('Total Inspection Points', f"{metrics['total_inspections']:,}"),
        ('Total Defects Found', f"{metrics['total_defects']:,}"),
        ('Overall Defect Rate', f"{metrics['defect_rate']:.2f}%"),
        ('Average Defects per Unit', f"{metrics['avg_defects_per_unit']:.1f}")
    ]
    
    for label, value in inspection_data:
        worksheet.write(current_row, 0, label, label_format)
        worksheet.write(current_row, 1, value, data_format)
        current_row += 1
    
    current_row += 1
    
    # Settlement Readiness Section
    worksheet.merge_range(f'A{current_row + 1}:B{current_row + 1}', 
                         '🏠 SETTLEMENT READINESS ANALYSIS', section_header)
    worksheet.set_row(current_row, 25)
    current_row += 2
    
    readiness_data = [
        ('✅ Ready for Settlement (0-2 defects)', 
         f"{metrics['ready_units']} units ({metrics['ready_pct']:.1f}%)", ready_format),
        ('⚠️ Minor Work Required (3-7 defects)', 
         f"{metrics['minor_work_units']} units ({metrics['minor_pct']:.1f}%)", minor_format),
        ('🔧 Major Work Required (8-15 defects)', 
         f"{metrics['major_work_units']} units ({metrics['major_pct']:.1f}%)", major_format),
        ('🚧 Extensive Work Required (15+ defects)', 
         f"{metrics['extensive_work_units']} units ({metrics['extensive_pct']:.1f}%)", extensive_format)
    ]
    
    for label, value, cell_format_type in readiness_data:
        worksheet.write(current_row, 0, label, label_format)
        worksheet.write(current_row, 1, value, cell_format_type)
        current_row += 1
    
    current_row += 1
    
    # Top Problem Trades Section
    worksheet.merge_range(f'A{current_row + 1}:B{current_row + 1}', 
                         '⚠️ TOP PROBLEM TRADES', section_header)
    worksheet.set_row(current_row, 25)
    current_row += 2
    
    if len(metrics['summary_trade']) > 0:
        top_trades = metrics['summary_trade'].head(10)
        
        for idx, (_, row) in enumerate(top_trades.iterrows(), 1):
            trade_label = f"{idx}. {row['Trade']}"
            defect_count = f"{row['DefectCount']} defects"
            worksheet.write(current_row, 0, trade_label, label_format)
            worksheet.write(current_row, 1, defect_count, data_format)
            current_row += 1
    else:
        worksheet.write(current_row, 0, "No defects found", label_format)
        worksheet.write(current_row, 1, "All trades passed inspection", data_format)
        current_row += 1
    
    current_row += 2
    
    # Footer
    melbourne_tz = pytz.timezone('Australia/Melbourne')
    melbourne_time = datetime.now(melbourne_tz)
    report_time = melbourne_time.strftime('%d/%m/%Y at %I:%M %p AEDT')
    
    worksheet.merge_range(f'A{current_row + 1}:B{current_row + 1}', 
                         f'Report generated on {report_time} | Professional Inspection Report Processor v2.0', 
                         footer_format)
    
    # ===== RAW INSPECTION DATA SHEET =====
    create_data_sheet(workbook, final_df, "📋 All Inspections", table_header, cell_format, alt_row_format)
    
    # ===== DEFECTS ONLY SHEET =====
    if len(metrics['summary_trade']) > 0:
        defects_only = final_df[final_df['StatusClass'] == 'Not OK']
        create_data_sheet(workbook, defects_only, "🔍 Defects Only", table_header, cell_format, alt_row_format)
    
    # ===== SETTLEMENT READINESS SHEET =====
    create_settlement_sheet(workbook, metrics, table_header, cell_format, ready_format, minor_format, major_format, extensive_format)
    
    # ===== TRADE SUMMARY SHEET =====
    if len(metrics['summary_trade']) > 0:
        create_data_sheet(workbook, metrics['summary_trade'], "🔧 Trade Summary", table_header, cell_format, alt_row_format)
    
    # ===== UNIT SUMMARY SHEET =====
    if len(metrics['summary_unit']) > 0:
        create_data_sheet(workbook, metrics['summary_unit'], "🏠 Unit Summary", table_header, cell_format, alt_row_format)
    
    # ===== ROOM SUMMARY SHEET =====
    if len(metrics['summary_room']) > 0:
        create_data_sheet(workbook, metrics['summary_room'], "🚪 Room Summary", table_header, cell_format, alt_row_format)
    
    # ===== COMPONENT DETAILS SHEET =====
    if len(metrics['component_details_summary']) > 0:
        create_data_sheet(workbook, metrics['component_details_summary'], "🔍 Component Details", table_header, cell_format, alt_row_format)
    
    # ===== METADATA SHEET =====
    create_metadata_sheet(workbook, metrics, table_header, cell_format)
    
    # Close workbook and return buffer
    workbook.close()
    excel_buffer.seek(0)
    return excel_buffer


def create_data_sheet(workbook, data_df, sheet_name, header_format, cell_format, alt_row_format):
    """Create a data sheet with professional formatting"""
    
    worksheet = workbook.add_worksheet(sheet_name)
    
    # Auto-adjust column widths
    for col_num, column in enumerate(data_df.columns):
        max_length = max(
            data_df[column].astype(str).map(len).max(),
            len(str(column))
        )
        worksheet.set_column(col_num, col_num, min(max_length + 2, 50))
    
    # Write headers
    for col_num, value in enumerate(data_df.columns):
        worksheet.write(0, col_num, value, header_format)
    
    # Write data with alternating row colors
    for row_num, (_, row) in enumerate(data_df.iterrows(), 1):
        for col_num, value in enumerate(row):
            if row_num % 2 == 0:
                worksheet.write(row_num, col_num, value, alt_row_format)
            else:
                worksheet.write(row_num, col_num, value, cell_format)


def create_settlement_sheet(workbook, metrics, header_format, cell_format, ready_format, minor_format, major_format, extensive_format):
    """Create settlement readiness analysis sheet"""
    
    worksheet = workbook.add_worksheet("🏠 Settlement Readiness")
    worksheet.set_column('A:A', 25)
    worksheet.set_column('B:B', 15)
    worksheet.set_column('C:C', 15)
    worksheet.set_column('D:D', 20)
    
    # Headers
    headers = ['Category', 'Units', 'Percentage', 'Criteria']
    for col_num, header in enumerate(headers):
        worksheet.write(0, col_num, header, header_format)
    
    # Data with color coding
    settlement_data = [
        ('✅ Ready for Settlement', metrics['ready_units'], f"{metrics['ready_pct']:.1f}%", '0-2 defects', ready_format),
        ('⚠️ Minor Work Required', metrics['minor_work_units'], f"{metrics['minor_pct']:.1f}%", '3-7 defects', minor_format),
        ('🔧 Major Work Required', metrics['major_work_units'], f"{metrics['major_pct']:.1f}%", '8-15 defects', major_format),
        ('🚧 Extensive Work Required', metrics['extensive_work_units'], f"{metrics['extensive_pct']:.1f}%", '15+ defects', extensive_format)
    ]
    
    for row_num, (category, units, percentage, criteria, format_type) in enumerate(settlement_data, 1):
        worksheet.write(row_num, 0, category, format_type)
        worksheet.write(row_num, 1, units, format_type)
        worksheet.write(row_num, 2, percentage, format_type)
        worksheet.write(row_num, 3, criteria, format_type)


def create_metadata_sheet(workbook, metrics, header_format, cell_format):
    """Create report metadata sheet"""
    
    worksheet = workbook.add_worksheet("📄 Report Metadata")
    worksheet.set_column('A:A', 25)
    worksheet.set_column('B:B', 40)
    
    melbourne_tz = pytz.timezone('Australia/Melbourne')
    melbourne_time = datetime.now(melbourne_tz)
    
    metadata = [
        ('Report Generated', melbourne_time.strftime('%Y-%m-%d %H:%M:%S AEDT')),
        ('Report Version', '2.0 Professional'),
        ('Building Name', metrics['building_name']),
        ('Total Units', str(metrics['total_units'])),
        ('Total Defects', str(metrics['total_defects'])),
        ('Data Source', 'iAuditor CSV Export'),
        ('Processing Engine', 'Professional Inspection Report Processor'),
        ('Charts Included', 'Yes'),
        ('Raw Data Included', 'Yes')
    ]
    
    # Headers
    worksheet.write(0, 0, 'Property', header_format)
    worksheet.write(0, 1, 'Value', header_format)
    
    # Data
    for row_num, (prop, value) in enumerate(metadata, 1):
        worksheet.write(row_num, 0, prop, cell_format)
        worksheet.write(row_num, 1, value, cell_format)


def generate_filename(building_name, report_type="Excel"):
    """
    Generate professional filename with building name first
    
    Args:
        building_name: Name of the building
        report_type: Type of report (Excel or Word)
        
    Returns:
        str: Formatted filename
    """
    
    # Clean building name for filename
    clean_building_name = "".join(c for c in building_name if c.isalnum() or c in (' ', '-', '_')).strip()
    clean_building_name = clean_building_name.replace(' ', '_')
    
    # Get Melbourne timezone timestamp
    melbourne_tz = pytz.timezone('Australia/Melbourne')
    timestamp = datetime.now(melbourne_tz).strftime("%Y%m%d_%H%M%S")
    
    # Format: BuildingName_Inspection_Report_Excel_YYYYMMDD_HHMMSS
    filename = f"{clean_building_name}_Inspection_Report_{report_type}_{timestamp}"
    
    return filename


# Test function
def test_excel_generator():
    """Test function to verify Excel generator is working"""
    try:
        # Create sample data for testing
        sample_data = pd.DataFrame({
            'Unit': ['Unit_1', 'Unit_2'],
            'UnitType': ['Apartment', 'Apartment'],
            'Room': ['Bathroom', 'Kitchen'],
            'Component': ['Toilet', 'Sink'],
            'StatusClass': ['OK', 'Not OK'],
            'Trade': ['Plumbing', 'Plumbing']
        })
        
        sample_metrics = {
            'building_name': 'Test Building',
            'address': 'Test Address',
            'inspection_date': '2025-01-01',
            'unit_types_str': 'Apartment',
            'total_units': 2,
            'total_inspections': 2,
            'total_defects': 1,
            'defect_rate': 50.0,
            'avg_defects_per_unit': 0.5,
            'ready_units': 1,
            'minor_work_units': 1,
            'major_work_units': 0,
            'extensive_work_units': 0,
            'ready_pct': 50.0,
            'minor_pct': 50.0,
            'major_pct': 0.0,
            'extensive_pct': 0.0,
            'summary_trade': pd.DataFrame({'Trade': ['Plumbing'], 'DefectCount': [1]}),
            'summary_unit': pd.DataFrame({'Unit': ['Unit_2'], 'DefectCount': [1]}),
            'summary_room': pd.DataFrame({'Room': ['Kitchen'], 'DefectCount': [1]}),
            'component_details_summary': pd.DataFrame({
                'Trade': ['Plumbing'],
                'Room': ['Kitchen'],
                'Component': ['Sink'],
                'Units with Defects': ['Unit_2']
            })
        }
        
        # Generate Excel
        excel_buffer = generate_professional_excel_report(sample_data, sample_metrics)
        
        # Test filename generation
        filename = generate_filename("Test Building", "Excel")
        
        return True, f"Excel generator test successful. Filename: {filename}.xlsx"
        
    except Exception as e:
        return False, f"Excel generator test failed: {str(e)}"


if __name__ == "__main__":
    # Run test when module is executed directly
    success, message = test_excel_generator()
    print(f"Test Result: {message}")