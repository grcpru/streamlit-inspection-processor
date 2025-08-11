#!/usr/bin/env python3
"""
Debug script for Word report generation
Run this script to test if Word report generation works on your system
"""

import sys
import os
from io import BytesIO
import pandas as pd

def check_dependencies():
    """Check if all required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    missing_deps = []
    
    # Check python-docx
    try:
        import docx
        print("✅ python-docx is installed")
    except ImportError:
        missing_deps.append("python-docx")
        print("❌ python-docx is NOT installed")
    
    # Check pytz
    try:
        import pytz
        print("✅ pytz is installed")
    except ImportError:
        missing_deps.append("pytz")
        print("❌ pytz is NOT installed")
    
    # Check pandas
    try:
        import pandas
        print("✅ pandas is installed")
    except ImportError:
        missing_deps.append("pandas")
        print("❌ pandas is NOT installed")
    
    if missing_deps:
        print(f"\n❌ Missing dependencies: {', '.join(missing_deps)}")
        print("Install them with:")
        for dep in missing_deps:
            print(f"  pip install {dep}")
        return False
    
    print("✅ All dependencies are installed!")
    return True


def check_word_generator_file():
    """Check if word_report_generator.py exists and can be imported"""
    print("\n🔍 Checking word_report_generator.py...")
    
    # Check if file exists
    if not os.path.exists("word_report_generator.py"):
        print("❌ word_report_generator.py file not found in current directory")
        print("📁 Current directory:", os.getcwd())
        print("📋 Files in current directory:")
        for file in os.listdir("."):
            if file.endswith((".py", ".csv")):
                print(f"   - {file}")
        return False
    
    print("✅ word_report_generator.py file found")
    
    # Try to import
    try:
        from word_report_generator import generate_professional_word_report, test_word_generator
        print("✅ Successfully imported word_report_generator")
        
        # Run the built-in test
        success, message = test_word_generator()
        if success:
            print(f"✅ {message}")
            return True
        else:
            print(f"❌ {message}")
            return False
            
    except ImportError as e:
        print(f"❌ Failed to import word_report_generator: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing word generator: {e}")
        return False


def create_test_data():
    """Create sample test data for testing"""
    print("\n🔍 Creating test data...")
    
    # Sample final_df
    final_df = pd.DataFrame({
        'Unit': ['101', '102', '103', '104', '105'],
        'UnitType': ['2BR Apartment', '2BR Apartment', '3BR Apartment', '2BR Apartment', '3BR Apartment'],
        'Room': ['Kitchen Area', 'Bathroom', 'Living Room', 'Bedroom', 'Kitchen Area'],
        'Component': ['Kitchen Sink', 'Tiles', 'Walls', 'Carpets', 'Cabinets'],
        'StatusClass': ['Not OK', 'Not OK', 'OK', 'Not OK', 'Not OK'],
        'Trade': ['Plumbing', 'Flooring - Tiles', 'Painting', 'Flooring - Carpets', 'Carpentry & Joinery']
    })
    
    # Sample metrics
    metrics = {
        'building_name': 'Test Building Complex',
        'inspection_date': '2025-01-15',
        'address': '123 Test Street, Melbourne VIC 3000',
        'unit_types_str': '2BR Apartment, 3BR Apartment',
        'total_units': 5,
        'total_inspections': 25,
        'total_defects': 4,
        'defect_rate': 16.0,
        'avg_defects_per_unit': 0.8,
        'ready_units': 2,
        'minor_work_units': 3,
        'major_work_units': 0,
        'extensive_work_units': 0,
        'ready_pct': 40.0,
        'minor_pct': 60.0,
        'major_pct': 0.0,
        'extensive_pct': 0.0,
        'summary_trade': pd.DataFrame({
            'Trade': ['Plumbing', 'Flooring - Tiles', 'Carpentry & Joinery', 'Flooring - Carpets'],
            'DefectCount': [1, 1, 1, 1]
        }),
        'summary_unit': pd.DataFrame({
            'Unit': ['101', '102', '104', '105'],
            'DefectCount': [1, 1, 1, 1]
        }),
        'summary_room': pd.DataFrame({
            'Room': ['Kitchen Area', 'Bathroom', 'Bedroom'],
            'DefectCount': [2, 1, 1]
        }),
        'component_details_summary': pd.DataFrame({
            'Trade': ['Plumbing', 'Flooring - Tiles', 'Flooring - Carpets', 'Carpentry & Joinery'],
            'Room': ['Kitchen Area', 'Bathroom', 'Bedroom', 'Kitchen Area'],
            'Component': ['Kitchen Sink', 'Tiles', 'Carpets', 'Cabinets'],
            'Units with Defects': ['101', '102', '104', '105']
        })
    }
    
    print("✅ Test data created successfully")
    return final_df, metrics


def test_word_generation():
    """Test the actual Word document generation"""
    print("\n🔍 Testing Word document generation...")
    
    try:
        from word_report_generator import generate_professional_word_report
        
        # Create test data
        final_df, metrics = create_test_data()
        
        # Generate Word document
        print("📝 Generating Word document...")
        word_doc = generate_professional_word_report(final_df, metrics)
        
        # Try to save to BytesIO
        print("💾 Testing document save...")
        word_buffer = BytesIO()
        word_doc.save(word_buffer)
        word_buffer.seek(0)
        
        file_size = len(word_buffer.getvalue())
        print(f"✅ Word document generated successfully! Size: {file_size:,} bytes")
        
        # Optionally save to file for inspection
        test_filename = "test_inspection_report.docx"
        with open(test_filename, "wb") as f:
            f.write(word_buffer.getvalue())
        print(f"📄 Test document saved as: {test_filename}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error generating Word document: {e}")
        import traceback
        print("\n🔍 Full error traceback:")
        traceback.print_exc()
        return False


def main():
    """Run all diagnostic tests"""
    print("🚀 Word Report Generator Diagnostic Tool")
    print("=" * 50)
    
    all_passed = True
    
    # Check dependencies
    if not check_dependencies():
        all_passed = False
    
    # Check word generator file
    if not check_word_generator_file():
        all_passed = False
    
    # Test word generation if everything else passed
    if all_passed:
        if not test_word_generation():
            all_passed = False
    
    # Final summary
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Word report generation should work in your Streamlit app")
        print("\n📋 Next steps:")
        print("1. Make sure word_report_generator.py is in the same directory as your Streamlit app")
        print("2. Restart your Streamlit app")
        print("3. Try generating a Word report")
    else:
        print("❌ SOME TESTS FAILED!")
        print("🔧 Please fix the issues above before using Word reports in Streamlit")
        print("\n💡 Common fixes:")
        print("1. Install missing dependencies: pip install python-docx pytz")
        print("2. Make sure word_report_generator.py is in the correct location")
        print("3. Check file permissions")


if __name__ == "__main__":
    main()