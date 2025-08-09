import streamlit as st
from office365.sharepoint.client_context import ClientContext
from office365.runtime.auth.client_credential import ClientCredential
import pandas as pd
from io import BytesIO
import os

def get_sharepoint_context(site_url, client_id, client_secret, tenant_id):
    """Create SharePoint client context"""
    try:
        credentials = ClientCredential(client_id, client_secret)
        ctx = ClientContext(site_url).with_credentials(credentials)
        
        # Test connection
        web = ctx.web.get().execute_query()
        return ctx, web.title
    except Exception as e:
        st.error(f"SharePoint authentication failed: {str(e)}")
        return None, None

def download_mapping_file(site_url, client_id, client_secret, tenant_id):
    """Download MasterTradeMapping.csv from SharePoint"""
    try:
        ctx, site_title = get_sharepoint_context(site_url, client_id, client_secret, tenant_id)
        if ctx is None:
            return None
        
        # Construct file path
        site_path = site_url.split('/sites/')[1] if '/sites/' in site_url else ''
        file_url = f"/sites/{site_path}/InspectionFiles/MasterTradeMapping.csv"
        
        # Download file
        file_obj = ctx.web.get_file_by_server_relative_url(file_url)
        
        # Create a BytesIO object to store the file content
        file_content = BytesIO()
        file_obj.download(file_content).execute_query()
        
        # Read as CSV
        file_content.seek(0)
        trade_mapping = pd.read_csv(file_content)
        
        st.success(f"✅ Downloaded mapping file from SharePoint ({len(trade_mapping)} rows)")
        return trade_mapping
        
    except Exception as e:
        st.warning(f"Could not download mapping from SharePoint: {str(e)}")
        return None

def upload_files_to_sharepoint(excel_buffer, csv_content, original_filename, building_name, 
                              site_url, client_id, client_secret, tenant_id):
    """Upload processed files to SharePoint libraries"""
    try:
        ctx, site_title = get_sharepoint_context(site_url, client_id, client_secret, tenant_id)
        if ctx is None:
            return False
        
        # Upload original CSV to InspectionUploads
        uploads_folder = ctx.web.lists.get_by_title("InspectionUploads").root_folder
        uploads_folder.upload_file(original_filename, csv_content).execute_query()
        
        # Upload Excel report to InspectionReports
        from datetime import datetime
        excel_filename = f"{building_name.replace(' ', '_')}_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        reports_folder = ctx.web.lists.get_by_title("InspectionReports").root_folder
        excel_buffer.seek(0)
        reports_folder.upload_file(excel_filename, excel_buffer.getvalue()).execute_query()
        
        st.success(f"✅ Files uploaded to SharePoint successfully!")
        st.info(f"📊 Excel report: {excel_filename}")
        st.info(f"📄 Original CSV: {original_filename}")
        
        return True
        
    except Exception as e:
        st.error(f"❌ SharePoint upload failed: {str(e)}")
        return False

def update_file_status(original_filename, building_name, status, site_url, client_id, client_secret, tenant_id):
    """Update processing status of uploaded file"""
    try:
        ctx, site_title = get_sharepoint_context(site_url, client_id, client_secret, tenant_id)
        if ctx is None:
            return False
        
        # Find the file in InspectionUploads
        uploads_list = ctx.web.lists.get_by_title("InspectionUploads")
        items = uploads_list.items.filter(f"Name eq '{original_filename}'").get().execute_query()
        
        if len(items) > 0:
            item = items[0]
            item.set_property("ProcessingStatus", status)
            item.set_property("BuildingName", building_name)
            if status == "Completed":
                item.set_property("ReportGenerated", True)
            item.update()
            ctx.execute_query()
            
            return True
    except Exception as e:
        st.warning(f"Could not update file status: {str(e)}")
        return False
