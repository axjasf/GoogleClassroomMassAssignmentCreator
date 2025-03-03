# Google Classroom Assignment Management Tools

A collection of Python scripts to manage Google Classroom assignments, including bulk creation and mass renaming of assignments.

## Tools Included

1. **Mass Assignment Creator** (`script.py`)
   - Bulk create assignments from CSV file
   - Schedule publish dates for assignments
   - Set due dates and points
   - Organize assignments into topics

2. **Assignment Renamer** (`rename_assignments.py`)
   - Bulk rename assignments to add prefixes
   - Works with both published and draft assignments
   - Matches assignments based on CSV file titles
   - Preserves all other assignment properties

3. **Quiz Creator** (`create_quiz.py`)
   - Bulk create quizzes from CSV file
   - Link Google Forms to quizzes
   - Set due dates and points
   - Organize quizzes into topics

4. **Quiz Response Grader** (`grade_quiz_responses.py`)
   - Process Google Form quiz responses
   - Grade student self-assessments
   - Record scores in a Google Spreadsheet
   - Track submission timestamps

## Prerequisites

- Python 3.7+
- Google Classroom access
- OAuth 2.0 credentials from Google Cloud Console

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/axjasf/GoogleClassroomMassAssignmentCreator.git
   cd GoogleClassroomMassAssignmentCreator
   ```

2. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up Google Cloud Console:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project or select existing one
   - Enable Google Classroom API
   - Create OAuth 2.0 credentials (Desktop application)
   - Download and save as `credentials.json` in the project directory

## Mass Assignment Creator

### Configuration

Edit the constants at the top of `script.py`:
```python
# Configuration Constants
COURSE_ID = "YOUR_COURSE_ID"  # Your Google Classroom course ID
TIMEZONE = "America/Los_Angeles"  # Your timezone
CSV_FILE = "assignments.csv"  # Your CSV file name
```

### CSV Format for Assignment Creation

Create a CSV file with the following columns:
- `Group`: Topic name for organizing assignments
- `Title`: Assignment title
- `DueDate`: Due date in M/D/YYYY format
- `ScheduledDate`: Publish date in M/D/YYYY format
- `Points`: Maximum points (numeric)

Example:
```csv
Group,Title,DueDate,ScheduledDate,Points
Unit 1,Assignment 1,1/28/2025,1/18/2025,100
Unit 1,Quiz 1,1/29/2025,1/19/2025,50
```

## Assignment Renamer

### Configuration

Edit the constants at the top of `rename_assignments.py`:
```python
# Configuration
ENCODED_COURSE_ID = "YOUR_ENCODED_COURSE_ID"  # Your base64 encoded course ID
PREFIX = "[BD] "  # Prefix to add to assignments
CSV_FILE = "titles.csv"  # CSV file with assignment titles to match
```

### CSV Format for Renaming

Create a CSV file with a `Title` column containing the exact titles of assignments to be renamed:
```csv
Title
Assignment 1
Quiz 1
```

## Quiz Creator

### Configuration

Edit the constants at the top of `create_quiz.py`:
```python
# Configuration Constants
ENCODED_COURSE_ID = "YOUR_ENCODED_COURSE_ID"  # Your base64 encoded course ID
TIMEZONE = "America/Los_Angeles"  # Your timezone
CSV_FILE = "quiz_structure.csv"  # Your CSV file name
```

### CSV Format for Quiz Creation

Create a CSV file with the following columns:
- `Group`: Topic name for organizing quizzes
- `Title`: Quiz title
- `Description`: Quiz description/instructions
- `DueDate`: Due date in M/D/YYYY format
- `Points`: Maximum points (numeric)
- `FormURL`: URL of the linked Google Form (optional)

Example:
```csv
Group,Title,Description,DueDate,Points,FormURL
Grammar,Quiz 1,Basic Quiz,1/28/2025,50,https://forms.google.com/your-form-url
```

## Quiz Response Grader

### Configuration

Edit the constants at the top of `grade_quiz_responses.py`:
```python
# Configuration Constants
FORM_ID = 'YOUR_FORM_ID'  # Your Google Form ID
SPREADSHEET_ID = 'YOUR_SPREADSHEET_ID'  # Your response spreadsheet ID
```

### Required Google API Access
- Forms API (for reading responses)
- Sheets API (for recording grades)

### Setup Instructions
1. Create a Google Form for your quiz
2. Set up a response spreadsheet
3. Get the Form ID from the form URL
4. Get the Spreadsheet ID from the spreadsheet URL
5. Update the configuration constants

### Usage
```bash
python grade_quiz_responses.py
```

The script will:
1. Check for new form responses
2. Process the latest response
3. Calculate the total score
4. Record the timestamp and score in the spreadsheet

## Usage

1. Update the configuration constants in the desired script
2. Run the appropriate script:
   ```bash
   # For creating assignments
   python script.py
   
   # For renaming assignments
   python rename_assignments.py
   
   # For creating quizzes
   python create_quiz.py
   
   # For grading quiz responses
   python grade_quiz_responses.py
   ```

## Finding Your Course ID

1. Open your Google Classroom course
2. The course ID is in the URL:
   ```
   https://classroom.google.com/c/YOUR_COURSE_ID
   ```

## Notes

- Assignments with "N/A" or "—" for dates or points will be skipped
- Future-dated assignments are created as drafts
- All assignments are due at 23:59 on their due date
- All assignments are scheduled to publish at 00:01 on their scheduled date
- The renaming script will skip assignments that already have the specified prefix
- Quizzes are created as drafts and need to be reviewed before publishing
- Google Forms must be created separately before linking them to quizzes

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](https://choosealicense.com/licenses/mit/) 