from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os  # Added os for environment variable
import os.path
import pickle
from flask import session, url_for, request as flask_request

# For local development only, to allow HTTP for oauthlib.
# In production, you MUST use HTTPS and not set this.
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Google Classroom API Scopes
SCOPES = [
    'https://www.googleapis.com/auth/classroom.courses',
    'https://www.googleapis.com/auth/classroom.coursework.students'
]

TOKEN_PICKLE_PATH = 'token.pickle'
CREDENTIALS_PATH = 'credentials.json'


def get_flow():
    """Creates and returns an OAuth Flow object."""
    try:
        flow = Flow.from_client_secrets_file(
            CREDENTIALS_PATH,
            scopes=SCOPES
        )
        return flow
    except FileNotFoundError:
        msg = f"ERROR: '{CREDENTIALS_PATH}' not found. " \
              f"Please ensure it is in the project root."
        print(msg)
        raise
    except Exception as e:
        print(f"Error creating OAuth flow: {e}")
        raise


def get_credentials_from_session_or_pickle():
    """Tries to get credentials from Flask session or token.pickle."""
    creds = None
    if 'credentials' in session:
        creds_dict = session['credentials']
        try:
            creds = pickle.loads(creds_dict)
        except TypeError:
            from google.oauth2.credentials import Credentials
            try:
                creds = Credentials(**creds_dict)
            except Exception as e:
                print(f"Error loading credentials from session dict: {e}")
                session.pop('credentials', None)

    if creds and creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                session['credentials'] = pickle.dumps(creds)
                with open(TOKEN_PICKLE_PATH, 'wb') as token_file:
                    pickle.dump(creds, token_file)
            except Exception as e:
                print(f"Error refreshing token from session/pickle: {e}")
                session.pop('credentials', None)
                if os.path.exists(TOKEN_PICKLE_PATH):
                    os.remove(TOKEN_PICKLE_PATH)
                creds = None
        return creds

    # If not in session or not valid, try token.pickle
    if os.path.exists(TOKEN_PICKLE_PATH):
        with open(TOKEN_PICKLE_PATH, 'rb') as token_file:
            creds = pickle.load(token_file)
        if creds and creds.valid:
            if creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    # Save refreshed token
                    with open(TOKEN_PICKLE_PATH, 'wb') as token_file_save:
                        pickle.dump(creds, token_file_save)
                    session['credentials'] = pickle.dumps(creds)  # Update session
                except Exception as e:
                    print(f"Error refreshing token from pickle: {e}")
                    if os.path.exists(TOKEN_PICKLE_PATH):
                        os.remove(TOKEN_PICKLE_PATH)  # Remove invalid pickle
                    creds = None
            return creds
        elif creds and not creds.valid:  # Pickle exists, creds invalid, no refresh
            if os.path.exists(TOKEN_PICKLE_PATH):
                os.remove(TOKEN_PICKLE_PATH)
            creds = None
            
    return None  # No valid credentials found


def get_classroom_service():
    """Builds and returns a Google Classroom API service object."""
    creds = get_credentials_from_session_or_pickle()
    if not creds:
        print("DEBUG: No valid creds in get_classroom_service. "
              "App should redirect to login.")
        return None
    service = build('classroom', 'v1', credentials=creds)
    return service


def list_courses():
    """Lists all courses accessible by the user."""
    service = get_classroom_service()
    courses = []
    page_token = None
    try:
        while True:
            response = service.courses().list(
                pageToken=page_token, courseStates=['ACTIVE']).execute()
            courses.extend(response.get('courses', []))
            page_token = response.get('nextPageToken', None)
            if not page_token:
                break
    except Exception as e:
        print(f"An error occurred while listing courses: {e}")
        return None
    return courses


def list_course_work(course_id):
    """Lists all coursework for a given course."""
    service = get_classroom_service()
    coursework_list = []
    page_token = None
    try:
        while True:
            response = service.courses().courseWork().list(
                courseId=course_id,
                pageToken=page_token,
                courseWorkStates=['PUBLISHED', 'DRAFT']  # Include drafts
            ).execute()
            coursework_list.extend(response.get('courseWork', []))
            page_token = response.get('nextPageToken', None)
            if not page_token:
                break
    except Exception as e:
        msg = (f"An error occurred while listing coursework for course "
               f"{course_id}: {e}")
        print(msg)
        return None
    return coursework_list


def get_course_work_item(course_id, assignment_id):
    """Gets a specific coursework item (assignment)."""
    service = get_classroom_service()
    try:
        assignment = service.courses().courseWork().get(
            courseId=course_id,
            id=assignment_id
        ).execute()
        return assignment
    except Exception as e:
        print(f"Error fetching assignment {assignment_id} for course "
              f"{course_id}: {e}")
        return None


def update_course_work(course_id, assignment_id, assignment_body, update_mask):
    """Updates an existing coursework item (assignment)."""
    service = get_classroom_service()
    try:
        updated_assignment = service.courses().courseWork().patch(
            courseId=course_id,
            id=assignment_id,
            updateMask=update_mask,  # Fields to update, comma-separated
            body=assignment_body
        ).execute()
        print(f"Assignment {assignment_id} updated successfully.")
        return updated_assignment
    except Exception as e:
        # It's useful to print the error here for server logs
        error_message = (
            f"Error updating assignment {assignment_id} for course "
            f"{course_id}: {e}"
        )
        print(error_message)
        # Re-raise the exception so the route can catch it and flash a message
        raise


def get_course_name(course_id):
    """Helper function to get the name of a course by its ID."""
    service = get_classroom_service()
    try:
        course = service.courses().get(id=course_id).execute()
        return course.get('name')
    except Exception as e:
        print(f"Error fetching course name for ID {course_id}: {e}")
        return None


def create_new_assignment(course_id, assignment_body):
    """Creates a new assignment (courseWork) in a specific course."""
    service = get_classroom_service()
    try:
        # Ensure workType is set, defaulting to ASSIGNMENT if not present
        if 'workType' not in assignment_body:
            assignment_body['workType'] = 'ASSIGNMENT'
        
        created_assignment = service.courses().courseWork().create(
            courseId=course_id,
            body=assignment_body
        ).execute()
        print(f"Assignment '{created_assignment.get('title')}' created.")
        return created_assignment
    except Exception as e:
        print(f"An error occurred while creating assignment: {e}")
        # Re-raise to be caught by the route for flashing message
        raise


if __name__ == '__main__':
    # Example usage (for testing this module directly)
    print("Attempting to list courses...")
    available_courses = list_courses()
    if available_courses:
        print(f"Found {len(available_courses)} courses:")
        for course in available_courses:
            print(f"- {course.get('name')} (ID: {course.get('id')})")

            # Test listing coursework for the first course found
            if course.get('id'):
                print(
                    f"  Attempting to list assignments for "
                    f"'{course.get('name')}'..."
                )
                assignments = list_course_work(course.get('id'))
                if assignments:
                    print(f"  Found {len(assignments)} assignments:")
                    for assignment in assignments:
                        print(
                            f"    - {assignment.get('title')} "
                            f"(State: {assignment.get('state')})"
                        )
                elif assignments is None:
                    print("    Error listing assignments for this course.")
                else:
                    print("    No assignments found for this course.")
                break  # Only test for the first course to keep output brief
    elif available_courses is None:
        print("Error trying to list courses.")
    else:
        print(
            "No courses found or user does not have access "
            "to any active courses."
        ) 