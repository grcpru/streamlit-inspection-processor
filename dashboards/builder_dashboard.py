# =============================================================================
# UPDATED builder_dashboard.py
# =============================================================================

"""
Enhanced Builder Dashboard Module
Addresses requirements: Photo evidence and completion workflow
"""

class EnhancedBuilderDashboard:
    def __init__(self):
        self.user = self.get_current_user()
    
    def get_current_user(self):
        return {
            "username": st.session_state.get("username", ""),
            "name": st.session_state.get("user_name", "Builder"),
            "role": st.session_state.get("user_role", "builder")
        }
    
    def show(self):
        """Main builder dashboard with photo upload and completion workflow"""
        st.markdown(f"""
        <div class="main-header">
            <h1>Builder Workspace</h1>
            <p>Work Management with Photo Evidence</p>
            <div style="margin-top: 1rem; opacity: 0.9; font-size: 0.9em;">
                <span>Welcome back, <strong>{self.user['name']}</strong>!</span>
                <span style="margin-left: 2rem;">Role: <strong>Builder</strong></span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        self.show_work_assignments()
    
    def show_work_assignments(self):
        """Show work assignments with photo upload capability"""
        st.markdown("### Your Work Assignments")
        
        try:
            conn = sqlite3.connect("inspection_system.db")
            cursor = conn.cursor()
            
            # Check if enhanced tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='enhanced_defects'")
            has_enhanced_tables = cursor.fetchone() is not None
            
            if has_enhanced_tables:
                # Get assigned defects from enhanced table
                cursor.execute('''
                    SELECT ed.id, ed.unit_number, ed.room, ed.component, ed.trade, 
                           ed.urgency, ed.planned_completion, ed.status, pi.building_name
                    FROM enhanced_defects ed
                    JOIN processed_inspections pi ON ed.inspection_id = pi.id
                    WHERE pi.is_active = 1 AND ed.status IN ('open', 'assigned', 'in_progress')
                    ORDER BY 
                        CASE ed.urgency 
                            WHEN 'Urgent' THEN 1 
                            WHEN 'High Priority' THEN 2 
                            ELSE 3 
                        END,
                        ed.planned_completion
                ''')
                
                work_assignments = cursor.fetchall()
            else:
                # Fallback to legacy table
                cursor.execute('''
                    SELECT id, unit_number, room, component, trade, 
                           urgency, planned_completion, status, 'Building' as building_name
                    FROM inspection_defects
                    WHERE status IN ('open', 'assigned', 'in_progress')
                    ORDER BY 
                        CASE urgency 
                            WHEN 'Urgent' THEN 1 
                            WHEN 'High Priority' THEN 2 
                            ELSE 3 
                        END,
                        planned_completion
                ''')
                
                work_assignments = cursor.fetchall()
            
            if not work_assignments:
                st.success("No open work assignments! All defects are completed or approved.")
                conn.close()
                return
            
            # Summary metrics
            urgent_count = len([w for w in work_assignments if w[5] == 'Urgent'])
            high_priority_count = len([w for w in work_assignments if w[5] == 'High Priority'])
            normal_count = len(work_assignments) - urgent_count - high_priority_count
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Urgent", urgent_count)
            with col2:
                st.metric("High Priority", high_priority_count)
            with col3:
                st.metric("Normal", normal_count)
            
            st.markdown(f"**{len(work_assignments)} work items assigned to you:**")
            
            # Work items interface
            for work_data in work_assignments:
                defect_id = work_data[0]
                
                urgency_icon = "🚨" if work_data[5] == "Urgent" else "⚠️" if work_data[5] == "High Priority" else "🔧"
                
                with st.expander(f"{urgency_icon} Unit {work_data[1]} - {work_data[2]} - {work_data[3]} ({work_data[4]})", expanded=False):
                    
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown(f"""
                        **Building:** {work_data[8]}  
                        **Unit:** {work_data[1]}  
                        **Location:** {work_data[2]} - {work_data[3]}  
                        **Trade:** {work_data[4]}  
                        **Urgency:** {work_data[5]}  
                        **Due Date:** {work_data[6]}  
                        **Current Status:** {work_data[7].replace('_', ' ').title()}
                        """)
                    
                    with col2:
                        if has_enhanced_tables:
                            # Show existing photos
                            cursor.execute('''
                                SELECT id, photo_type, description, uploaded_at
                                FROM defect_photos 
                                WHERE defect_id = ?
                                ORDER BY uploaded_at DESC
                                LIMIT 3
                            ''', (defect_id,))
                            
                            photos = cursor.fetchall()
                            if photos:
                                st.markdown("**Photos:**")
                                for photo in photos:
                                    st.caption(f"{photo[1]}: {photo[2]}")
                            else:
                                st.info("No photos uploaded yet")
                    
                    # Action buttons
                    if has_enhanced_tables:
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if st.button(f"📸 Add Photo", key=f"photo_{defect_id}"):
                                self.show_photo_upload_interface(defect_id)
                        
                        with col2:
                            if work_data[7] != 'in_progress' and st.button(f"🔄 Start Work", key=f"start_{defect_id}"):
                                cursor.execute('''
                                    UPDATE enhanced_defects 
                                    SET status = 'in_progress' 
                                    WHERE id = ?
                                ''', (defect_id,))
                                conn.commit()
                                st.success("Work started!")
                                st.rerun()
                        
                        with col3:
                            if st.button(f"✅ Mark Complete", key=f"complete_{defect_id}", type="primary"):
                                self.show_completion_interface(defect_id)
                    else:
                        st.info("Enhanced photo and completion features not yet available. Contact your administrator.")
            
            conn.close()
            
        except Exception as e:
            st.error(f"Error loading work assignments: {e}")
    
    def show_photo_upload_interface(self, defect_id):
        """Interface for uploading photos"""
        st.markdown("#### Upload Photo Evidence")
        
        photo_type = st.selectbox(
            "Photo type:",
            options=['before', 'during', 'after', 'evidence'],
            help="Select the type of photo you're uploading"
        )
        
        description = st.text_input(
            "Photo description:",
            placeholder="Describe what this photo shows..."
        )
        
        uploaded_photo = st.file_uploader(
            "Choose photo file:",
            type=['png', 'jpg', 'jpeg'],
            help="Upload a clear photo showing the defect or work progress"
        )
        
        if uploaded_photo and st.button("Upload Photo"):
            if self.save_defect_photo(defect_id, uploaded_photo, photo_type, description):
                st.success("Photo uploaded successfully!")
                st.rerun()
            else:
                st.error("Failed to upload photo")
    
    def show_completion_interface(self, defect_id):
        """Interface for marking defects as complete"""
        st.markdown("#### Mark Defect as Complete")
        
        completion_notes = st.text_area(
            "Completion notes:",
            placeholder="Describe the work performed and any important details...",
            help="Provide details about how the defect was resolved"
        )
        
        st.markdown("**Upload completion photos:**")
        
        before_photo = st.file_uploader(
            "Before photo (if not already uploaded):",
            type=['png', 'jpg', 'jpeg'],
            key=f"before_{defect_id}"
        )
        
        after_photo = st.file_uploader(
            "After photo (required):",
            type=['png', 'jpg', 'jpeg'],
            key=f"after_{defect_id}"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Cancel", key=f"cancel_complete_{defect_id}"):
                st.rerun()
        
        with col2:
            if st.button("Submit for Approval", key=f"submit_complete_{defect_id}", type="primary"):
                if not after_photo:
                    st.error("After photo is required for completion")
                    return
                
                if not completion_notes.strip():
                    st.error("Completion notes are required")
                    return
                
                # Upload photos and mark complete
                photos_uploaded = True
                
                if before_photo:
                    if not self.save_defect_photo(defect_id, before_photo, 'before', "Before work photo"):
                        photos_uploaded = False
                
                if after_photo:
                    if not self.save_defect_photo(defect_id, after_photo, 'after', "After work completion"):
                        photos_uploaded = False
                
                if photos_uploaded:
                    # Mark as completed pending approval
                    try:
                        conn = sqlite3.connect("inspection_system.db")
                        cursor = conn.cursor()
                        
                        cursor.execute('''
                            UPDATE enhanced_defects 
                            SET status = 'completed_pending_approval', 
                                completed_by = ?, 
                                completed_at = ?, 
                                completion_notes = ?
                            WHERE id = ?
                        ''', (self.user['username'], datetime.now(), completion_notes, defect_id))
                        
                        conn.commit()
                        conn.close()
                        
                        st.success("Work submitted for approval! The property developer will review your completion.")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Failed to submit completion: {e}")
                else:
                    st.error("Failed to upload photos")
    
    def save_defect_photo(self, defect_id, photo_file, photo_type, description):
        """Save photo evidence for a defect"""
        try:
            from PIL import Image
            import io
            import uuid
            
            # Read and compress image
            image = Image.open(photo_file)
            
            # Resize if too large (max 1920x1080)
            if image.width > 1920 or image.height > 1080:
                image.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
            
            # Convert to JPEG and compress
            img_buffer = io.BytesIO()
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            image.save(img_buffer, format='JPEG', quality=85, optimize=True)
            img_data = img_buffer.getvalue()
            
            # Save to database
            conn = sqlite3.connect("inspection_system.db")
            cursor = conn.cursor()
            
            photo_id = str(uuid.uuid4())
            filename = f"{defect_id}_{photo_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            
            cursor.execute('''
                INSERT INTO defect_photos 
                (id, defect_id, photo_type, filename, photo_data, uploaded_by, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (photo_id, defect_id, photo_type, filename, img_data, self.user['username'], description))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            st.error(f"Error saving photo: {e}")
            return False

# Function to replace existing dashboard calls
def show_enhanced_property_developer_dashboard():
    dashboard = EnhancedDeveloperDashboard()
    dashboard.show()

def show_enhanced_builder_dashboard():
    dashboard = EnhancedBuilderDashboard()
    dashboard.show()