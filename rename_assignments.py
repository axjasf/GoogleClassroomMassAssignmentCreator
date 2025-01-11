from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pandas as pd
import pickle
import os
import base64

# Configuration
ENCODED_COURSE_ID = "NzA3ODgxMzE3NTE2"  # Your encoded course ID
PREFIX = "[BD] "
CSV_FILE = "bd_structure.csv"  # Your CSV file with assignments

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