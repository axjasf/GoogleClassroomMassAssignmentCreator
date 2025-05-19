from flask import Flask, render_template, redirect, url_for, flash, request, \
    session
from functools import wraps
import google_classroom_service as gcs
import json
import os
import pickle  # For storing credentials in session after OAuth

app = Flask(__name__)
# Important: Set a strong secret key for session management in a real app
app.secret_key = 'your secret key'

CONFIG_FILE_PATH = 'schedule_config.json'
DAYS_OF_WEEK = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
    "Sunday"
]


def load_schedule_config():
    """Loads schedule configuration from JSON file."""
    if os.path.exists(CONFIG_FILE_PATH):
        try:
            with open(CONFIG_FILE_PATH, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            flash(
                "Error: schedule_config.json is corrupted. Please re-save.",
                "error"
            )
            return {}  # Return empty dict if corrupted
    return {}


def save_schedule_config(config_data):
    """Saves schedule configuration to JSON file."""
    try:
        with open(CONFIG_FILE_PATH, 'w') as f:
            json.dump(config_data, f, indent=4)
        flash("Schedule configuration saved successfully!", "success")
    except Exception as e:
        flash(f"Error saving schedule configuration: {str(e)}", "error")


@app.route('/login')
def login():
    flow = gcs.get_flow()
    flow.redirect_uri = url_for('oauth2callback', _external=True)
    authorization_url, state = flow.authorization_url(
        access_type='offline',  # Get a refresh token
        include_granted_scopes='true'
    )
    session['oauth_state'] = state
    return redirect(authorization_url)


@app.route('/oauth2callback')
def oauth2callback():
    # state = session.pop('oauth_state', None)
    # Security check: Ensure state matches (omitted for brevity)
    # if not state or state != request.args.get('state'):
    #     flash('Invalid OAuth state.', 'error')
    #     return redirect(url_for('index'))

    flow = gcs.get_flow()
    # The redirect URI used to exchange the authorization code must be the
    # same URI that was used to request the authorization code.
    flow.redirect_uri = url_for('oauth2callback', _external=True)

    try:
        authorization_response = request.url
        flow.fetch_token(authorization_response=authorization_response)
    except Exception as e:
        flash(f'Error fetching OAuth token: {str(e)}', 'error')
        print(f"OAuth token fetch error: {e}")
        return redirect(url_for('index'))

    credentials = flow.credentials
    session['credentials'] = pickle.dumps(credentials)
    with open(gcs.TOKEN_PICKLE_PATH, 'wb') as token_file:
        pickle.dump(credentials, token_file)
    
    flash('Authentication successful!', 'success')
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.pop('credentials', None)
    if os.path.exists(gcs.TOKEN_PICKLE_PATH):
        try:
            os.remove(gcs.TOKEN_PICKLE_PATH)
        except Exception as e:
            print(f"Error removing token.pickle: {e}")
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not gcs.get_credentials_from_session_or_pickle():
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
@login_required
def index():
    try:
        courses = gcs.list_courses()
        if courses is None:
            flash(
                "Error: Could not retrieve courses. "
                "Check console for details.",
                "error"
            )
            courses = []
        elif not courses:
            flash(
                "No active Google Classroom courses found or no access.",
                "info"
            )
        return render_template('index.html', courses=courses)
    except FileNotFoundError as e:
        # Display FileNotFoundError (e.g. credentials.json missing)
        flash(str(e), "error")
        return render_template('index.html', courses=[])
    except Exception as e:
        # Catch any other unexpected errors during service call
        msg = f"An unexpected error occurred: {str(e)}. Check console."
        flash(msg, "error")
        print(f"Error in index route: {e}")  # Log to console
        return render_template('index.html', courses=[])


@app.route('/course/<course_id>')
@login_required
def view_course(course_id):
    try:
        assignments = gcs.list_course_work(course_id)
        course_name = "Selected Course"  # Default course name

        if assignments is None:
            flash_msg = (
                f"Error: Could not retrieve assignments for course "
                f"{course_id}. Check console."
            )
            flash(flash_msg, "error")
            assignments = []
        elif not assignments:
            flash("No assignments found for this course.", "info")

        all_courses = gcs.list_courses()
        if all_courses:
            for c in all_courses:
                if c['id'] == course_id:
                    course_name = c.get('name', course_id)
                    break

        return render_template(
            'view_course.html',
            assignments=assignments,
            course_id=course_id,
            course_name=course_name
        )
    except Exception as e:
        msg = (
            f"An unexpected error occurred while loading course details: "
            f"{str(e)}. Check console."
        )
        flash(msg, "error")
        print(f"Error in view_course route for {course_id}: {e}")
        return redirect(url_for('index'))


@app.route('/schedule-config', methods=['GET', 'POST'])
@login_required
def schedule_config_route():
    if request.method == 'POST':
        try:
            school_year_start = request.form.get('school_year_start')
            school_year_end = request.form.get('school_year_end')

            course_schedules = []
            courses_from_api = gcs.list_courses()

            if courses_from_api:
                for course in courses_from_api:
                    course_id = course['id']
                    form_field_name = f'course_days_{course_id}'
                    if form_field_name in request.form:
                        selected_days = request.form.getlist(form_field_name)
                        if selected_days:
                            course_schedules.append({
                                "course_id": course_id,
                                "course_name": course.get(
                                    'name', 'Unknown Course'
                                ),
                                "days": selected_days
                            })

            config_data = {
                "school_year_start": school_year_start,
                "school_year_end": school_year_end,
                "course_schedules": course_schedules
            }
            save_schedule_config(config_data)
            return redirect(url_for('schedule_config_route'))
        except Exception as e:
            flash(
                f"Error processing schedule configuration: {str(e)}",
                "error"
            )
            print(f"Error in schedule_config_route (POST): {e}")

    current_config = load_schedule_config()
    available_courses = gcs.list_courses()

    if available_courses is None:
        flash(
            "Could not load courses from Google Classroom. "
            "Cannot configure schedule.",
            "error"
        )
        available_courses = []

    return render_template(
        'schedule_config.html',
        config=current_config,
        courses=available_courses,
        days_of_week=DAYS_OF_WEEK
    )


@app.route(
    '/course/<course_id>/assignment/<assignment_id>/edit',
    methods=['GET', 'POST']
)
@login_required
def edit_assignment_route(course_id, assignment_id):
    if request.method == 'POST':
        try:
            original_assignment = gcs.get_course_work_item(
                course_id, assignment_id
            )
            if not original_assignment:
                flash("Error: Original assignment not found. Cannot update.",
                      "error")
                return redirect(url_for('view_course', course_id=course_id))

            new_title = request.form.get('title')
            original_title = original_assignment.get('title')

            if new_title is not None and new_title != original_title:
                assignment_body = {
                    'title': new_title
                }
                update_mask = 'title'
                
                gcs.update_course_work(
                    course_id, assignment_id, assignment_body, update_mask
                )
                flash('Assignment title updated successfully!', 'success')
                return redirect(url_for('view_course', course_id=course_id))
            elif new_title == original_title:
                flash("No change in title detected.", "info")
                return redirect(url_for('edit_assignment_route',
                                        course_id=course_id,
                                        assignment_id=assignment_id))
            else:  # new_title is None
                flash("Title cannot be empty.", "error")
                return redirect(url_for('edit_assignment_route',
                                        course_id=course_id,
                                        assignment_id=assignment_id))

        except Exception as e:
            msg = f"Error updating assignment: {str(e)}"
            flash(msg, "error")
            print(f"Error in edit_assignment_route (POST): {e}")
            # Redirect back to the edit page on error
            return redirect(url_for('edit_assignment_route',
                                    course_id=course_id,
                                    assignment_id=assignment_id))

    # GET request:
    try:
        assignment = gcs.get_course_work_item(course_id, assignment_id)
        course_name = "Selected Course"
        all_courses = gcs.list_courses()
        if all_courses:
            for c in all_courses:
                if c['id'] == course_id:
                    course_name = c.get('name', course_id)
                    break

        if not assignment:
            flash('Assignment not found or error fetching details.', 'error')
            return redirect(url_for('view_course', course_id=course_id))

        return render_template('edit_assignment.html',
                               assignment=assignment,
                               course_id=course_id,
                               assignment_id=assignment_id,
                               course_name=course_name)
    except Exception as e:
        msg = f"Error loading assignment for editing: {str(e)}"
        flash(msg, "error")
        print(f"Error in edit_assignment_route (GET): {e}")
        return redirect(url_for('view_course', course_id=course_id))


@app.route(
    '/course/<course_id>/assignments/bulk-edit',
    methods=['GET', 'POST']
)
@login_required
def bulk_edit_assignments_route(course_id):
    course_name = "Selected Course"
    actual_course_name_obj = gcs.get_course_name(course_id)
    if actual_course_name_obj:
        course_name = actual_course_name_obj

    original_assignments_dict = {}
    current_assignments = gcs.list_course_work(course_id)
    if current_assignments:
        for assign in current_assignments:
            original_assignments_dict[assign['id']] = assign
    else:  # Handle case where there are no assignments
        current_assignments = []

    if request.method == 'POST':
        updated_count = 0
        error_count = 0
        error_messages = []

        # Prefixes are applied client-side by JS into title fields.
        # Backend works with the state of title fields as submitted.

        selected_assignment_ids = request.form.getlist('selected_assignments')

        if not selected_assignment_ids:
            flash("No assignments were selected for update.", "info")
            return redirect(url_for('bulk_edit_assignments_route',
                                    course_id=course_id))

        # Iterate only through selected and known assignments
        for assign_id in selected_assignment_ids:
            if assign_id not in original_assignments_dict:
                error_msg = f"Skipped unknown assignment ID: {assign_id}"
                error_messages.append(error_msg)
                error_count += 1
                continue  # Should not happen if form is from our GET

            original_assignment = original_assignments_dict[assign_id]
            update_mask_fields = []
            assignment_body = {}

            # Title: Get from form (potentially modified by JS/user)
            submitted_title = request.form.get(f'title_{assign_id}')

            if submitted_title is not None and \
               submitted_title != original_assignment.get('title'):
                assignment_body['title'] = submitted_title
                update_mask_fields.append('title')
            elif submitted_title is not None:  # Title submitted, even if same
                assignment_body['title'] = submitted_title

            # --- Due Date logic (only for selected assignments) ---
            new_due_date_str = request.form.get(f'due_date_{assign_id}')
            original_due_date_obj = original_assignment.get('dueDate')
            original_due_date_str = ""
            if original_due_date_obj and all(
                original_due_date_obj.get(k) for k in ['year', 'month', 'day']
            ):
                original_due_date_str = (
                    f"{original_due_date_obj['year']}-"
                    f"{original_due_date_obj['month']:02d}-"
                    f"{original_due_date_obj['day']:02d}")

            if new_due_date_str is not None and \
               new_due_date_str != original_due_date_str:
                if new_due_date_str:
                    year, month, day = map(int, new_due_date_str.split('-'))
                    due_payload = {"year": year, "month": month, "day": day}
                    assignment_body['dueDate'] = due_payload
                    update_mask_fields.append('dueDate')
                else:  # Empty string means clear due date
                    assignment_body['dueDate'] = None
                    update_mask_fields.append('dueDate')
            elif (new_due_date_str is not None and
                  'dueDate' not in update_mask_fields and
                  original_due_date_obj):
                # Submitted, no change, not in mask: add original to body
                if 'dueDate' not in assignment_body:
                    assignment_body['dueDate'] = original_due_date_obj

            # --- Max Points logic (only for selected assignments) ---
            new_max_points_str = request.form.get(f'max_points_{assign_id}')
            original_max_points = original_assignment.get('maxPoints')
            new_max_points = None
            title_for_err = original_assignment.get('title', 'Unknown Assign.')

            if new_max_points_str is not None:  # Field was present in form
                if new_max_points_str.strip():
                    try:
                        new_max_points = int(new_max_points_str)
                    except ValueError:
                        error_count += 1
                        error_messages.append(f"Invalid points for '{title_for_err}'.")
                        continue
                else:  # Empty string submitted, means clear points
                    new_max_points = None

            max_points_changed_or_cleared = False
            if new_max_points_str is not None:
                # If the field was submitted at all
                if new_max_points != original_max_points:
                    max_points_changed_or_cleared = True

            if max_points_changed_or_cleared:
                assignment_body['maxPoints'] = new_max_points
                update_mask_fields.append('maxPoints')
            elif (new_max_points_str is not None and
                  new_max_points_str.strip() and
                  'maxPoints' not in update_mask_fields):
                # Submitted, valid, no change, not in mask: add to body
                if 'maxPoints' not in assignment_body:
                    assignment_body['maxPoints'] = new_max_points

            if update_mask_fields:
                # Ensure title is in body if update is happening
                if 'title' not in assignment_body and submitted_title is not None:
                    assignment_body['title'] = submitted_title
                elif ('title' not in assignment_body and
                      original_assignment.get('title')):
                    # Fallback if title field somehow missing but was original
                    assignment_body['title'] = original_assignment.get('title')

                update_mask = ','.join(sorted(list(set(update_mask_fields))))
                try:
                    gcs.update_course_work(course_id, assign_id,
                                           assignment_body, update_mask)
                    updated_count += 1
                except Exception as e:
                    error_count += 1
                    error_messages.append(f"Updating '{title_for_err}': {e}")

        if updated_count > 0:
            flash(f"{updated_count} selected assignment(s) updated.", "success")
        if error_count > 0:
            details = '; '.join(error_messages)
            flash_msg = f"{error_count} selected assignment(s) failed to update. " \
                        f"Details: {details}"
            flash(flash_msg, "error")
        if not updated_count and not error_count and selected_assignment_ids:
            flash("No changes detected for selected assignments.", "info")

        return redirect(url_for('bulk_edit_assignments_route',
                                course_id=course_id))

    # GET request
    return render_template(
        'bulk_edit_assignments.html',
        assignments=current_assignments,
        course_id=course_id,
        course_name=course_name
    )


@app.route('/course/<course_id>/create-assignment', methods=['GET', 'POST'])
@login_required
def create_assignment_route(course_id):
    course_name = gcs.get_course_name(course_id)  # Helper to get course name
    if not course_name:
        flash("Error: Course not found.", "error")
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            title = request.form.get('title')
            description = request.form.get('description')
            # Due date/points omitted for simplicity in this test

            if not title:
                flash("Title is required to create an assignment.", "error")
                return render_template('create_assignment.html',
                                       course_id=course_id,
                                       course_name=course_name)
            
            assignment_body = {
                'title': title,
                'description': description if description else "",
                'workType': 'ASSIGNMENT'  # Explicitly set workType
            }

            created_assignment = gcs.create_new_assignment(
                course_id, assignment_body
            )
            if created_assignment:
                success_msg = (f"Assignment "
                               f"'{created_assignment.get('title')}' created!")
                flash(success_msg, "success")
                return redirect(url_for('view_course', course_id=course_id))
            else:
                flash("Failed to create assignment. Check server logs.",
                      "error")
        
        except Exception as e:
            flash(f"Error creating assignment: {str(e)}", "error")
            print(f"Error in create_assignment_route (POST): {e}")
        
        # Pass back submitted values on error
        return render_template(
            'create_assignment.html',
            course_id=course_id,
            course_name=course_name,
            title=request.form.get('title'),
            description=request.form.get('description')
        )

    # GET request
    return render_template('create_assignment.html',
                           course_id=course_id,
                           course_name=course_name)


if __name__ == '__main__':
    app.run(debug=True) 