from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pandas as pd
import os.path
import pickle
from datetime import datetime
import pytz
import base64

# Configuration Constants
COURSE_ID = "NzMzOTIwNTcyMzA2"  # Your Google Classroom course ID
TIMEZONE = "America/Los_Angeles"  # Your timezone
CSV_FILE = "bd_structure.csv"  # Your CSV file name

# Google Classroom API Scopes
SCOPES = [
    'https://www.googleapis.com/auth/classroom.courses',
    'https://www.googleapis.com/auth/classroom.coursework.students',
    'https://www.googleapis.com/auth/classroom.topics'
]


def get_credentials():
    """Gets valid user credentials from storage."""
    print("Starting authentication process...")
    creds = None
    if os.path.exists('token.pickle'):
        print("Found existing token.pickle file")
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        print("Need to get new credentials...")
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired credentials")
            creds.refresh(Request())
        else:
            print("\nOpening browser for authentication...")
            if not os.path.exists('credentials.json'):
                print("Error: credentials.json not found!")
                print("Please download your OAuth credentials")
                print("and save them as 'credentials.json' in this directory.")
                exit(1)
            
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            
            # Try different ports if one is busy
            ports = [8080, 8090, 8000, 0]  # 0 means random available port
            for port in ports:
                try:
                    print(f"Trying port {port}...")
                    creds = flow.run_local_server(
                        port=port,
                        prompt='consent',
                        success_message='Authentication complete!'
                    )
                    print(f"Authentication successful on port {port}!")
                    break
                except OSError:
                    if port == ports[-1]:  # Last port in the list
                        raise
                    print(f"Port {port} is busy, trying another...")
                    continue

        print("Saving credentials to token.pickle")
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return creds


def create_or_get_topic(service, course_id, topic_name):
    """Creates a topic if it doesn't exist, or gets the existing topic ID."""
    try:
        # List existing topics
        topics = service.courses().topics().list(courseId=course_id).execute()

        # Check if topic already exists
        for topic in topics.get('topic', []):
            if topic['name'] == topic_name:
                topic_id = topic['topicId']
                print(f"Topic URL: https://classroom.google.com/w/{course_id}/tc/{topic_id}")
                return topic_id

        # Create new topic if it doesn't exist
        topic = {
            'name': topic_name
        }
        created_topic = service.courses().topics().create(
            courseId=course_id,
            body=topic
        ).execute()
        topic_id = created_topic['topicId']
        print(f"Created new topic. URL: https://classroom.google.com/w/{course_id}/tc/{topic_id}")
        return topic_id
    except Exception as e:
        print(f"Error with topic '{topic_name}': {str(e)}")
        return None


def parse_date(date_str):
    """Parses date string in the format M/D/YYYY to datetime object."""
    try:
        return datetime.strptime(date_str, '%m/%d/%Y')
    except ValueError:
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            raise ValueError(f"Unsupported date format: {date_str}")


def decode_course_id(encoded_id):
    """Decode the base64 course ID to its numeric form."""
    try:
        # Pad the base64 string if needed
        padding_needed = len(encoded_id) % 4
        if padding_needed:
            encoded_id += '=' * (4 - padding_needed)
        
        # Decode base64 to bytes, then to string, then to integer
        decoded_bytes = base64.b64decode(encoded_id)
        decoded_str = decoded_bytes.decode('utf-8')
        return decoded_str
    except Exception as e:
        print(f"Error decoding course ID: {str(e)}")
        return encoded_id


def create_assignments(encoded_course_id, csv_file, timezone_str='UTC'):
    """Creates assignments in Google Classroom from a CSV file."""
    # Decode the course ID
    course_id = decode_course_id(encoded_course_id)
    print(f"Using decoded course ID: {course_id}")
    
    # Read the CSV file
    df = pd.read_csv(csv_file)
    
    # Create the Classroom API service
    creds = get_credentials()
    service = build('classroom', 'v1', credentials=creds)
    
    # Verify course access
    try:
        course = service.courses().get(id=course_id).execute()
        print(f"Successfully accessed course: {course.get('name', 'Unknown')}")
    except Exception as e:
        print(f"Error accessing course: {str(e)}")
        return
    
    # Get timezone
    tz = pytz.timezone(timezone_str)
    
    # Process each row in the CSV
    for _, row in df.iterrows():
        # Skip rows with N/A or — in DueDate
        if row['DueDate'] in ['N/A', '—'] or row['ScheduledDate'] in ['N/A', '—']:
            print(f"Skipping {row['Title']} as it has N/A dates")
            continue
            
        # Skip rows with — in Points
        if row['Points'] in ['—', 'N/A']:
            print(f"Skipping {row['Title']} as it has no points")
            continue

        # Get or create topic based on Group
        topic_id = create_or_get_topic(service, course_id, row['Group'])
        
        try:
            # Convert date strings to datetime objects
            due_date = parse_date(row['DueDate'])
            schedule_date = parse_date(row['ScheduledDate'])
            
            # Set times: due at 23:59, scheduled at 00:01
            due_date = due_date.replace(hour=23, minute=59)
            schedule_date = schedule_date.replace(hour=0, minute=1)
            
            # Localize the dates
            due_date = tz.localize(due_date)
            schedule_date = tz.localize(schedule_date)
            
            # Prepare the assignment
            assignment = {
                'title': row['Title'],
                'maxPoints': int(row['Points']),
                'workType': 'ASSIGNMENT',
                'state': ('DRAFT' if schedule_date > datetime.now(tz)
                          else 'PUBLISHED'),
                'dueDate': {
                    'year': due_date.year,
                    'month': due_date.month,
                    'day': due_date.day,
                },
                'dueTime': {
                    'hours': due_date.hour,
                    'minutes': due_date.minute,
                }
            }
            
            # Add topic if available
            if topic_id:
                assignment['topicId'] = topic_id
            
            # Add scheduledTime if the assignment should be published later
            if schedule_date > datetime.now(tz):
                assignment['scheduledTime'] = schedule_date.isoformat()
            
            assignment = service.courses().courseWork().create(
                courseId=course_id,
                body=assignment
            ).execute()
            print(f"Assignment created: {row['Title']}")
        except Exception as e:
            print(f"Error creating assignment '{row['Title']}': {str(e)}")


def main():
    print(f"\nUsing course ID: {COURSE_ID}")
    print(f"Using timezone: {TIMEZONE}")
    print("Starting assignment creation...\n")
    
    create_assignments(COURSE_ID, CSV_FILE, TIMEZONE)


if __name__ == '__main__':
    main()
