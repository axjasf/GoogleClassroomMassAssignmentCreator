from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pandas as pd
import pickle
import os
import base64
import sys

# Configuration
ENCODED_COURSE_ID = "NzA3ODgxMzE3NTE2"  # Your encoded course ID
PREFIX = "[BD] "
CSV_FILE = "bd_structure.csv"  # Your CSV file with assignments

# Test Mode - If enabled, will attempt to rename a specific assignment
TEST_MODE = True  # Set to True to test permissions
TEST_COURSE_ID = "682514164930"  # Change to a course ID you want to test with
TEST_ASSIGNMENT_TITLE = "Kapitel 7.1 - 7.4 - Kongruenz und Dreiecke"  # Change to an existing assignment title

# Google Classroom API Scopes
SCOPES = [
    'https://www.googleapis.com/auth/classroom.courses',
    'https://www.googleapis.com/auth/classroom.coursework.students'
]


def decode_course_id(encoded_id):
    """Decode the base64 course ID to its numeric form."""
    try:
        # Pad the base64 string if needed
        padding_needed = len(encoded_id) % 4
        if padding_needed:
            encoded_id += '=' * (4 - padding_needed)
        
        # Decode base64 to bytes, then to string
        decoded_bytes = base64.b64decode(encoded_id)
        decoded_str = decoded_bytes.decode('utf-8')
        return decoded_str
    except Exception as e:
        print(f"Error decoding course ID: {str(e)}")
        return encoded_id


def get_credentials():
    """Gets valid user credentials from storage."""
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return creds


def main():
    # Test Mode - directly try to rename a specific assignment
    if TEST_MODE:
        print("\n*** TEST MODE ENABLED ***")
        print(f"Attempting to rename assignment: {TEST_ASSIGNMENT_TITLE}")
        print(f"In course ID: {TEST_COURSE_ID}")
        
        # Get credentials and create service
        creds = get_credentials()
        service = build('classroom', 'v1', credentials=creds)
        
        # Verify course access
        try:
            course = service.courses().get(id=TEST_COURSE_ID).execute()
            print(f"Found course: {course.get('name', 'Unknown')}")
        except Exception as e:
            print(f"Error accessing course: {str(e)}")
            return
        
        # Get all coursework
        try:
            coursework = service.courses().courseWork().list(
                courseId=TEST_COURSE_ID,
                courseWorkStates=['PUBLISHED', 'DRAFT']
            ).execute()
            assignments = coursework.get('courseWork', [])
            print(f"\nFound {len(assignments)} assignments in classroom.")
        except Exception as e:
            print(f"Error listing assignments: {str(e)}")
            return
        
        if not assignments:
            print("No assignments found in the course.")
            return
        
        # Find the specific assignment
        target_assignment = None
        for assignment in assignments:
            if assignment['title'] == TEST_ASSIGNMENT_TITLE:
                target_assignment = assignment
                break
        
        if not target_assignment:
            print(f"ERROR: Assignment '{TEST_ASSIGNMENT_TITLE}' not found!")
            return
        
        # Try to rename the assignment
        try:
            new_title = f"TEST_PREFIX_{TEST_ASSIGNMENT_TITLE}"
            update = {
                'title': new_title
            }
            
            print(f"Attempting to rename: {TEST_ASSIGNMENT_TITLE} -> {new_title}")
            
            service.courses().courseWork().patch(
                courseId=TEST_COURSE_ID,
                id=target_assignment['id'],
                updateMask='title',
                body=update
            ).execute()
            
            print(f"SUCCESS! Renamed: {TEST_ASSIGNMENT_TITLE} -> {new_title}")
            
            # Restore the original name
            print(f"Restoring original name...")
            update = {
                'title': TEST_ASSIGNMENT_TITLE
            }
            
            service.courses().courseWork().patch(
                courseId=TEST_COURSE_ID,
                id=target_assignment['id'],
                updateMask='title',
                body=update
            ).execute()
            
            print(f"Restored original name: {new_title} -> {TEST_ASSIGNMENT_TITLE}")
            
            print("\nTEST SUCCESSFUL: This script has permission to modify assignments!")
            return
            
        except Exception as e:
            print(f"ERROR in test rename: {str(e)}")
            print("\nTEST FAILED: This script does NOT have permission to modify assignments.")
            return
    
    # Regular mode - process CSV file
    # Read CSV to get list of titles to rename
    df = pd.read_csv(CSV_FILE)
    csv_titles = set(df['Title'].dropna().tolist())
    print(f"\nFound {len(csv_titles)} titles in CSV file:")
    for title in sorted(csv_titles):
        print(f"CSV: {title}")
    
    # Decode course ID
    course_id = decode_course_id(ENCODED_COURSE_ID)
    print(f"\nUsing course ID: {course_id}")
    
    # Get credentials and create service
    creds = get_credentials()
    service = build('classroom', 'v1', credentials=creds)
    
    # Verify course access
    try:
        course = service.courses().get(id=course_id).execute()
        print(f"Found course: {course.get('name', 'Unknown')}")
    except Exception as e:
        print(f"Error accessing course: {str(e)}")
        return
    
    # Get all coursework
    try:
        # Get both published and draft assignments
        coursework = service.courses().courseWork().list(
            courseId=course_id,
            courseWorkStates=['PUBLISHED', 'DRAFT']
        ).execute()
        assignments = coursework.get('courseWork', [])
        print(f"\nFound {len(assignments)} assignments in classroom:")
        for assignment in assignments:
            state = assignment.get('state', 'UNKNOWN')
            print(f"Classroom: {assignment['title']} ({state})")
    except Exception as e:
        print(f"Error listing assignments: {str(e)}")
        return
    
    if not assignments:
        print("No assignments found in the course.")
        return
    
    print("\nStarting renaming process:")
    # Update each assignment that matches CSV titles
    for assignment in assignments:
        current_title = assignment['title']
        
        # Skip if already has prefix
        if current_title.startswith(PREFIX):
            print(f"Skipping (already has prefix): {current_title}")
            continue
            
        # Skip if not in CSV
        if current_title not in csv_titles:
            print(f"Skipping (not in CSV): {current_title}")
            continue
            
        # Create new title
        new_title = f"{PREFIX}{current_title}"
        
        # Update the assignment
        try:
            update = {
                'title': new_title
            }
            
            service.courses().courseWork().patch(
                courseId=course_id,
                id=assignment['id'],
                updateMask='title',
                body=update
            ).execute()
            
            print(f"Renamed: {current_title} -> {new_title}")
            
        except Exception as e:
            print(f"Error updating {current_title}: {str(e)}")


if __name__ == '__main__':
    main()
    print("\nDone! All matching assignments have been renamed.") 