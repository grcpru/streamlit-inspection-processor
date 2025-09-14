#!/usr/bin/env python3
"""
Database Diagnostic Tool
Checks data consistency between inspector and builder interfaces
"""

import sqlite3
import pandas as pd
from datetime import datetime

def diagnose_data_discrepancy():
    """Comprehensive database diagnostic for data discrepancy issues"""
    
    print("=" * 80)
    print("DATABASE DIAGNOSTIC TOOL")
    print("Analyzing data discrepancy between Inspector and Builder interfaces")
    print("=" * 80)
    print()
    
    try:
        conn = sqlite3.connect("inspection_system.db")
        
        # 1. Check all tables and their record counts
        print("1. TABLE OVERVIEW")
        print("-" * 40)
        
        tables_to_check = [
            'processed_inspections',
            'inspection_items', 
            'inspection_defects',
            'enhanced_defects'
        ]
        
        for table in tables_to_check:
            try:
                cursor = conn.cursor()
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"{table}: {count:,} records")
                
                # Check if table has building_name or related field
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [col[1] for col in cursor.fetchall()]
                relevant_cols = [col for col in columns if 'building' in col.lower() or 'inspection_id' in col.lower()]
                if relevant_cols:
                    print(f"  Relevant columns: {', '.join(relevant_cols)}")
                
            except Exception as e:
                print(f"{table}: NOT FOUND or ERROR ({e})")
        
        print()
        
        # 2. Check Argyle Square data specifically
        print("2. ARGYLE SQUARE DATA ANALYSIS")
        print("-" * 40)
        
        # From processed_inspections
        cursor.execute("""
            SELECT id, building_name, total_units, processed_at
            FROM processed_inspections 
            WHERE building_name LIKE '%Argyle%' AND is_active = 1
        """)
        argyle_inspections = cursor.fetchall()
        
        print(f"Active inspections for Argyle Square: {len(argyle_inspections)}")
        for insp in argyle_inspections:
            print(f"  ID: {insp[0]}, Name: {insp[1]}, Units: {insp[2]}, Date: {insp[3]}")
        
        if not argyle_inspections:
            print("  ERROR: No Argyle Square inspections found!")
            return
        
        inspection_id = argyle_inspections[0][0]  # Use first active inspection
        
        print()
        
        # 3. Compare data sources for same inspection
        print("3. DATA SOURCE COMPARISON (Same Building)")
        print("-" * 40)
        
        # Check inspection_items (if exists)
        try:
            cursor.execute("""
                SELECT unit_number, status_class, COUNT(*) as count
                FROM inspection_items 
                WHERE inspection_id = ?
                GROUP BY unit_number, status_class
                ORDER BY unit_number
            """, (inspection_id,))
            
            items_data = cursor.fetchall()
            if items_data:
                print("From inspection_items (COMPLETE DATA):")
                current_unit = None
                unit_summary = {}
                
                for row in items_data:
                    unit, status, count = row
                    if unit not in unit_summary:
                        unit_summary[unit] = {'OK': 0, 'Not OK': 0, 'Blank': 0}
                    unit_summary[unit][status] = count
                
                # Show first 10 units
                for i, (unit, counts) in enumerate(sorted(unit_summary.items())[:10]):
                    defect_count = counts.get('Not OK', 0)
                    total_items = sum(counts.values())
                    print(f"  Unit {unit}: {defect_count} defects out of {total_items} total items")
                    
                if len(unit_summary) > 10:
                    print(f"  ... and {len(unit_summary) - 10} more units")
                    
                print(f"Total units in inspection_items: {len(unit_summary)}")
                print(f"Total defects in inspection_items: {sum(counts.get('Not OK', 0) for counts in unit_summary.values())}")
            else:
                print("inspection_items: NO DATA FOUND")
                
        except Exception as e:
            print(f"inspection_items: TABLE NOT FOUND ({e})")
        
        print()
        
        # Check inspection_defects
        try:
            cursor.execute("""
                SELECT unit_number, COUNT(*) as defect_count
                FROM inspection_defects 
                WHERE inspection_id = ?
                GROUP BY unit_number
                ORDER BY unit_number
            """, (inspection_id,))
            
            defects_data = cursor.fetchall()
            if defects_data:
                print("From inspection_defects (LEGACY DEFECTS):")
                for unit, count in defects_data[:10]:  # Show first 10
                    print(f"  Unit {unit}: {count} defects")
                if len(defects_data) > 10:
                    print(f"  ... and {len(defects_data) - 10} more units")
                print(f"Total units in inspection_defects: {len(defects_data)}")
                print(f"Total defects in inspection_defects: {sum(row[1] for row in defects_data)}")
            else:
                print("inspection_defects: NO DATA FOR THIS INSPECTION")
                
        except Exception as e:
            print(f"inspection_defects: ERROR ({e})")
        
        print()
        
        # Check enhanced_defects
        try:
            cursor.execute("""
                SELECT ed.unit_number, COUNT(*) as defect_count
                FROM enhanced_defects ed
                WHERE ed.inspection_id = ?
                GROUP BY ed.unit_number
                ORDER BY ed.unit_number
            """, (inspection_id,))
            
            enhanced_data = cursor.fetchall()
            if enhanced_data:
                print("From enhanced_defects (BUILDER INTERFACE):")
                for unit, count in enhanced_data[:10]:  # Show first 10
                    print(f"  Unit {unit}: {count} defects")
                if len(enhanced_data) > 10:
                    print(f"  ... and {len(enhanced_data) - 10} more units")
                print(f"Total units in enhanced_defects: {len(enhanced_data)}")
                print(f"Total defects in enhanced_defects: {sum(row[1] for row in enhanced_data)}")
            else:
                print("enhanced_defects: NO DATA FOR THIS INSPECTION")
                
        except Exception as e:
            print(f"enhanced_defects: ERROR ({e})")
        
        print()
        
        # 4. Direct comparison for specific units
        print("4. UNIT-BY-UNIT COMPARISON")
        print("-" * 40)
        
        # Compare Unit G05 specifically (from your screenshot)
        test_units = ['G05', '602', '401']  # Units from your Excel data
        
        for unit in test_units:
            print(f"\nUnit {unit} Analysis:")
            
            # From inspection_items
            try:
                cursor.execute("""
                    SELECT status_class, COUNT(*) 
                    FROM inspection_items 
                    WHERE inspection_id = ? AND unit_number = ?
                    GROUP BY status_class
                """, (inspection_id, unit))
                
                items_status = dict(cursor.fetchall())
                defects_from_items = items_status.get('Not OK', 0)
                total_items = sum(items_status.values())
                print(f"  inspection_items: {defects_from_items} defects out of {total_items} total items")
                
            except:
                print(f"  inspection_items: No data")
            
            # From inspection_defects
            try:
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM inspection_defects 
                    WHERE inspection_id = ? AND unit_number = ?
                """, (inspection_id, unit))
                
                defects_legacy = cursor.fetchone()[0]
                print(f"  inspection_defects: {defects_legacy} defects")
                
            except:
                print(f"  inspection_defects: No data")
            
            # From enhanced_defects
            try:
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM enhanced_defects 
                    WHERE inspection_id = ? AND unit_number = ?
                """, (inspection_id, unit))
                
                defects_enhanced = cursor.fetchone()[0]
                print(f"  enhanced_defects: {defects_enhanced} defects")
                
            except:
                print(f"  enhanced_defects: No data")
        
        print()
        
        # 5. Check for data integrity issues
        print("5. DATA INTEGRITY CHECK")
        print("-" * 40)
        
        # Check for orphaned records
        try:
            cursor.execute("""
                SELECT COUNT(*) 
                FROM enhanced_defects ed
                LEFT JOIN processed_inspections pi ON ed.inspection_id = pi.id
                WHERE pi.id IS NULL
            """)
            orphaned = cursor.fetchone()[0]
            if orphaned > 0:
                print(f"WARNING: {orphaned} orphaned records in enhanced_defects")
            else:
                print("No orphaned records found")
                
        except Exception as e:
            print(f"Orphan check failed: {e}")
        
        # Check for duplicate records
        try:
            cursor.execute("""
                SELECT unit_number, room, component, COUNT(*) as dupes
                FROM enhanced_defects 
                WHERE inspection_id = ?
                GROUP BY unit_number, room, component
                HAVING COUNT(*) > 1
                ORDER BY dupes DESC
                LIMIT 5
            """, (inspection_id,))
            
            duplicates = cursor.fetchall()
            if duplicates:
                print("Potential duplicate defects found:")
                for dup in duplicates:
                    print(f"  Unit {dup[0]} - {dup[1]} - {dup[2]}: {dup[3]} copies")
            else:
                print("No duplicate defects found")
                
        except Exception as e:
            print(f"Duplicate check failed: {e}")
        
        print()
        
        # 6. Migration status check
        print("6. MIGRATION STATUS")
        print("-" * 40)
        
        try:
            # Check if enhanced_defects were populated
            cursor.execute("SELECT MIN(created_at), MAX(created_at), COUNT(*) FROM enhanced_defects")
            migration_info = cursor.fetchone()
            
            if migration_info[2] > 0:
                print(f"Enhanced defects table has {migration_info[2]:,} records")
                print(f"Date range: {migration_info[0]} to {migration_info[1]}")
                
                # Check status distribution
                cursor.execute("""
                    SELECT status, COUNT(*) 
                    FROM enhanced_defects 
                    GROUP BY status
                    ORDER BY COUNT(*) DESC
                """)
                status_dist = cursor.fetchall()
                print("Status distribution:")
                for status, count in status_dist:
                    print(f"  {status}: {count:,}")
            else:
                print("Enhanced defects table is EMPTY - migration may have failed")
                
        except Exception as e:
            print(f"Migration status check failed: {e}")
        
        conn.close()
        
        print()
        print("=" * 80)
        print("DIAGNOSTIC COMPLETE")
        print("=" * 80)
        
        # 7. Recommendations
        print("\nRECOMMENDations:")
        print("1. Check which table your Excel report uses as source")
        print("2. If enhanced_defects is empty or incomplete, run migration again")
        print("3. Verify that both interfaces query the same inspection_id")
        print("4. Consider re-generating enhanced_defects from inspection_items if available")
        
    except Exception as e:
        print(f"DIAGNOSTIC FAILED: {e}")
        import traceback
        traceback.print_exc()

def export_raw_data_comparison():
    """Export raw data for manual comparison"""
    
    try:
        conn = sqlite3.connect("inspection_system.db")
        
        # Get Argyle Square inspection ID
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM processed_inspections 
            WHERE building_name LIKE '%Argyle%' AND is_active = 1
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        if not result:
            print("No Argyle Square inspection found")
            return
        
        inspection_id = result[0]
        
        # Export data from each table
        tables_data = {}
        
        # From inspection_items
        try:
            df_items = pd.read_sql_query("""
                SELECT unit_number, unit_type, room, component, trade, status_class, urgency
                FROM inspection_items 
                WHERE inspection_id = ?
                ORDER BY unit_number, room, component
            """, conn, params=[inspection_id])
            
            tables_data['inspection_items'] = df_items
            df_items.to_csv('argyle_inspection_items.csv', index=False)
            print(f"Exported inspection_items data: {len(df_items)} records -> argyle_inspection_items.csv")
            
        except Exception as e:
            print(f"Could not export inspection_items: {e}")
        
        # From inspection_defects  
        try:
            df_defects = pd.read_sql_query("""
                SELECT unit_number, unit_type, room, component, trade, urgency, status, created_at
                FROM inspection_defects 
                WHERE inspection_id = ?
                ORDER BY unit_number, room, component
            """, conn, params=[inspection_id])
            
            tables_data['inspection_defects'] = df_defects
            df_defects.to_csv('argyle_inspection_defects.csv', index=False)
            print(f"Exported inspection_defects data: {len(df_defects)} records -> argyle_inspection_defects.csv")
            
        except Exception as e:
            print(f"Could not export inspection_defects: {e}")
        
        # From enhanced_defects
        try:
            df_enhanced = pd.read_sql_query("""
                SELECT unit_number, unit_type, room, component, trade, urgency, status, created_at
                FROM enhanced_defects 
                WHERE inspection_id = ?
                ORDER BY unit_number, room, component
            """, conn, params=[inspection_id])
            
            tables_data['enhanced_defects'] = df_enhanced
            df_enhanced.to_csv('argyle_enhanced_defects.csv', index=False)
            print(f"Exported enhanced_defects data: {len(df_enhanced)} records -> argyle_enhanced_defects.csv")
            
        except Exception as e:
            print(f"Could not export enhanced_defects: {e}")
        
        # Create summary comparison
        if tables_data:
            summary_data = []
            
            # Get all unique units
            all_units = set()
            for df in tables_data.values():
                if 'unit_number' in df.columns:
                    all_units.update(df['unit_number'].unique())
            
            for unit in sorted(all_units):
                row = {'unit': unit}
                
                for table_name, df in tables_data.items():
                    if table_name == 'inspection_items':
                        # Count Not OK items
                        defect_count = len(df[(df['unit_number'] == unit) & (df['status_class'] == 'Not OK')])
                        total_count = len(df[df['unit_number'] == unit])
                        row[f'{table_name}_defects'] = defect_count
                        row[f'{table_name}_total'] = total_count
                    else:
                        # Count all records (they're all defects)
                        defect_count = len(df[df['unit_number'] == unit])
                        row[f'{table_name}_defects'] = defect_count
                
                summary_data.append(row)
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_csv('argyle_comparison_summary.csv', index=False)
            print(f"Created comparison summary -> argyle_comparison_summary.csv")
        
        conn.close()
        
    except Exception as e:
        print(f"Export failed: {e}")

if __name__ == "__main__":
    print("Choose diagnostic option:")
    print("1. Run full diagnostic")
    print("2. Export raw data for comparison")
    print("3. Both")
    
    choice = input("Enter choice (1/2/3): ").strip()
    
    if choice in ['1', '3']:
        diagnose_data_discrepancy()
    
    if choice in ['2', '3']:
        print("\n" + "="*50)
        export_raw_data_comparison()