from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pandas as pd
import os.path
import pickle
import base64
from datetime import datetime
import pytz


# Configuration Constants
ENCODED_COURSE_ID = "682514164930"  # Math course
TIMEZONE = "America/Los_Angeles"  # Your timezone
CSV_FILE = "quiz_structure.csv"  # Your CSV file name


# Google Classroom API Scopes
SCOPES = [
    'https://www.googleapis.com/auth/classroom.courses',
    'https://www.googleapis.com/auth/classroom.coursework.students',
    'https://www.googleapis.com/auth/classroom.topics'
]


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


def decode_course_id(encoded_id):
    """Decode the base64 course ID to its numeric form."""
    try:
        padding_needed = len(encoded_id) % 4
        if padding_needed:
            encoded_id += '=' * (4 - padding_needed)
        
        decoded_bytes = base64.b64decode(encoded_id)
        decoded_str = decoded_bytes.decode('utf-8')
        return decoded_str
    except Exception as e:
        print(f"Error decoding course ID: {str(e)}")
        return encoded_id


def create_or_get_topic(service, course_id, topic_name):
    """Creates a topic if it doesn't exist, or gets the existing topic ID."""
    try:
        topics = service.courses().topics().list(courseId=course_id).execute()
        
        for topic in topics.get('topic', []):
            if topic['name'] == topic_name:
                return topic['topicId']

        topic = {'name': topic_name}
        created_topic = service.courses().topics().create(
            courseId=course_id,
            body=topic
        ).execute()
        return created_topic['topicId']
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


def create_quiz(service, course_id, title, description, points, due_date,
               topic_id=None, materials=None):
    """Creates a quiz in Google Classroom."""
    try:
        quiz = {
            'title': title,
            'description': description,
            'maxPoints': points,
            'workType': 'QUIZ',
            'state': 'DRAFT',
            'dueDate': {
                'year': due_date.year,
                'month': due_date.month,
                'day': due_date.day,
            },
            'dueTime': {
                'hours': 23,
                'minutes': 59,
            }
        }

        if topic_id:
            quiz['topicId'] = topic_id

        if materials:
            quiz['materials'] = materials

        created_quiz = service.courses().courseWork().create(
            courseId=course_id,
            body=quiz
        ).execute()

        print(f"Created quiz: {title}")
        return created_quiz
    except Exception as e:
        print(f"Error creating quiz '{title}': {str(e)}")
        return None


def create_quizzes(encoded_course_id, csv_file, timezone_str='UTC'):
    """Creates quizzes in Google Classroom from a CSV file."""
    course_id = decode_course_id(encoded_course_id)
    print(f"Using decoded course ID: {course_id}")
    
    df = pd.read_csv(csv_file)
    
    creds = get_credentials()
    service = build('classroom', 'v1', credentials=creds)
    
    try:
        course = service.courses().get(id=course_id).execute()
        print(f"Successfully accessed course: {course.get('name', 'Unknown')}")
    except Exception as e:
        print(f"Error accessing course: {str(e)}")
        return
    
    for _, row in df.iterrows():
        if row['DueDate'] in ['N/A', '—']:
            print(f"Skipping {row['Title']} as it has N/A dates")
            continue
            
        if row['Points'] in ['—', 'N/A']:
            print(f"Skipping {row['Title']} as it has no points")
            continue

        topic_id = create_or_get_topic(service, course_id, row['Group'])
        
        try:
            due_date = parse_date(row['DueDate'])
            materials = []
            
            if 'FormURL' in row and pd.notna(row['FormURL']):
                materials.append({
                    'form': {
                        'formUrl': row['FormURL'],
                        'title': row['Title'],
                        'thumbnailUrl': None
                    }
                })

            create_quiz(
                service=service,
                course_id=course_id,
                title=row['Title'],
                description=row.get('Description', ''),
                points=int(row['Points']),
                due_date=due_date,
                topic_id=topic_id,
                materials=materials if materials else None
            )
        except Exception as e:
            print(f"Error creating quiz '{row['Title']}': {str(e)}")


def main():
    print(f"\nUsing course ID: {ENCODED_COURSE_ID}")
    print(f"Using timezone: {TIMEZONE}")
    print("Starting quiz creation...\n")
    
    create_quizzes(ENCODED_COURSE_ID, CSV_FILE, TIMEZONE)


if __name__ == '__main__':
    main() 