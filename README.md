# Google Classroom Mass Assignment Creator

A Python script to bulk create assignments in Google Classroom from a CSV file. This tool helps teachers quickly set up multiple assignments with scheduled publish dates and due dates.

## Features

- Bulk create assignments from CSV file
- Schedule publish dates for assignments
- Set due dates and points
- Organize assignments into topics
- Support for timezone configuration
- Handles base64-encoded course IDs

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

## Configuration

Edit the constants at the top of `script.py`:
```python
# Configuration Constants
COURSE_ID = "YOUR_COURSE_ID"  # Your Google Classroom course ID
TIMEZONE = "America/Los_Angeles"  # Your timezone
CSV_FILE = "bd_structure.csv"  # Your CSV file name
```

## CSV Format

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

## Usage

1. Update the configuration constants in `script.py`
2. Run the script:
   ```bash
   python script.py
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

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](https://choosealicense.com/licenses/mit/) 