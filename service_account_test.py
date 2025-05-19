from google.oauth2 import service_account
from googleapiclient.discovery import build

# Replace these with your actual values
COURSE_ID = '682514164930'  # The course ID you've been working with
ASSIGNMENT_ID = '779332849297'  # The assignment ID from previous tests
ASSIGNMENT_TITLE = 'Kapitel 7.1 - 7.4 - Kongruenz und Dreiecke'
USER_EMAIL = 'axel@perseveranceacademy.org'  # Your admin email

# The scopes needed for the API
SCOPES = [
    'https://www.googleapis.com/auth/classroom.courses',
    'https://www.googleapis.com/auth/classroom.coursework.students'
]

def main():
    try:
        # Load the service account credentials
        credentials = service_account.Credentials.from_service_account_file(
            'service-account.json', scopes=SCOPES)
        
        # Create delegated credentials for your user account
        delegated_credentials = credentials.with_subject(USER_EMAIL)
        
        # Create the Classroom API client
        service = build('classroom', 'v1', credentials=delegated_credentials)
        
        # Verify access to the course
        print(f"Verifying access to course {COURSE_ID}...")
        course = service.courses().get(id=COURSE_ID).execute()
        print(f"Successfully accessed course: {course.get('name')}")
        
        # Get the assignment to verify it exists
        print(f"Verifying assignment {ASSIGNMENT_ID}...")
        assignment = service.courses().courseWork().get(
            courseId=COURSE_ID, id=ASSIGNMENT_ID).execute()
        original_title = assignment.get('title')
        print(f"Found assignment: {original_title}")
        
        # Attempt to modify the assignment
        print(f"Attempting to rename assignment...")
        new_title = f"SA_TEST_{original_title}"
        
        update_body = {
            'title': new_title
        }
        
        updated = service.courses().courseWork().patch(
            courseId=COURSE_ID,
            id=ASSIGNMENT_ID,
            updateMask='title',
            body=update_body
        ).execute()
        
        print(f"SUCCESS! Assignment renamed to: {updated.get('title')}")
        
        # Restore the original title
        print(f"Restoring original title...")
        update_body = {
            'title': original_title
        }
        
        restored = service.courses().courseWork().patch(
            courseId=COURSE_ID,
            id=ASSIGNMENT_ID,
            updateMask='title',
            body=update_body
        ).execute()
        
        print(f"Successfully restored title to: {restored.get('title')}")
        print("\nSERVICE ACCOUNT TEST SUCCESSFUL!")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        print("\nSERVICE ACCOUNT TEST FAILED.")

if __name__ == '__main__':
    main() 