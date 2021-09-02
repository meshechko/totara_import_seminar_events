from pathlib import Path
from flask import Flask, render_template, redirect, url_for, request, session, flash, send_file, g
import models
from forms import UploadBackup, UploadRooms, CreateEventForm, TimeZoneForm
from datetime import datetime
import xmltodict
import os
import shutil
import time
from werkzeug.utils import secure_filename
import csv
import random
import string

app = Flask(__name__)
app.secret_key = b'_5#y2L"Fjkmnrkj'


#FILTERS

@app.template_filter('time_format')
def datetime_format(value, format="%H:%M"):
    proper_date = datetime.fromtimestamp(int(value))
    return proper_date.strftime(format)

@app.template_filter('date_format')
def datetime_format(value, format="%A, %d %B %Y"):
    proper_date = datetime.fromtimestamp(int(value))
    return proper_date.strftime(format)


# ROUTES

myapp = models.Controller()
user = None

@app.route('/')
def index():
    return render_template('index.html')

@app.before_request
def before_request():
    if 'userID' not in session: # check if its a returning user

        # generate random user id that consists of 10 characters
        letters = string.ascii_lowercase
        random_string = ''.join(random.choice(letters) for i in range(10))

        session['userID'] = random_string # create session for a new user
        myapp.new_user(user_id=session['userID']) # initiat user and add user to database
    
    g.user = myapp.get_user_details(session['userID']) # assign user to global app scope context

    # assign user set timezone to server
    os.environ["TZ"] = g.user.timezone 
    time.tzset()


@app.route('/create-recurring-events', methods=['GET', 'POST'])
def create_recurring_events(pin=None):

    form = CreateEventForm()
    timezone_form = TimeZoneForm()
    rooms = g.user.rooms
    custom_fields = g.user.custom_fields
    form.rooms.choices = [(room.id, room.name) for room in rooms]
    max_generated_events = 1000
    recurrence_type = request.args.get('recurrence_type')
    if request.method == 'POST' and form.validate_on_submit() and g.user.timezone:
        for field in custom_fields:
            try:
                field["field_data"] = request.form[field['field_name']]
            except:
                pass
                  
        details = form.details.data
        timestart = form.timestart.data.strftime("%H:%M")
        timefinish = form.timefinish.data.strftime("%H:%M")
        room_id = form.rooms.data
            
        capacity = form.capacity.data

        #recurrence
        datestart = form.datestart.data.strftime("%Y%m%d")
        datefinish = form.datefinish.data.strftime("%Y%m%d")
        
        frequency = form.frequency.data
        if form.occurrence_number:
            occurrence_number = form.occurrence_number.data
        
        interval = form.interval.data
        allow_overbook = form.allow_overbook.data

        allow_cancellations = form.allow_cancellations.data
        cancellation_cutoff_number = form.cancellation_cutoff_number.data
        cancellation_cutoff_timeunit = form.cancellation_cutoff_timeunit.data
        min_capacity = form.min_capacity.data
        send_capacity_email = form.send_capacity_email.data
        send_capacity_email_cutoff_number = form.send_capacity_email_cutoff_number.data
        send_capacity_email_cutoff_timeunit = form.send_capacity_email_cutoff_timeunit.data
        normal_cost = form.normal_cost.data
        # session["timezone"] = form.timezone.data
        
        recurring_dates = ""
        if recurrence_type == "manual":
            recurring_dates = models.strDatesToDatetimeList(form.manual_dates.data)
            session["recurrence_type"] = "manual"
        else:
            days_of_week = ""
            if form.days_of_week:
                days_of_week = request.form.getlist('days_of_week')

            # recurring_dates = models.generateRecurringDates(
            #     datestart=datestart, 
            #     datefinish=datefinish, 
            #     frequency=frequency, 
            #     occurrence_number=occurrence_number, 
            #     days_of_week=days_of_week, 
            #     interval=interval)

            recurrence = models.Recurrence(
                datestart=datestart, 
                datefinish=datefinish, 
                frequency=frequency, 
                occurrence_number=occurrence_number[0], 
                days_of_week=days_of_week, 
                interval=interval
            )

            recurring_dates = recurrence.dates

            # print(recurrence.dates)

        if (len(recurring_dates) + models.countGeneratedEvents()) <= max_generated_events:
            
            
            generated_session = models.generate_recurring_sessions(
                custom_fields_data=custom_fields, 
                details=details, 
                timestart=timestart, 
                timefinish=timefinish, 
                room_id=room_id, 
                capacity=capacity, 
                recurring_dates=recurring_dates,
                allow_overbook=allow_overbook, 
                allow_cancellations=allow_cancellations, 
                cancellation_cutoff_number=cancellation_cutoff_number, 
                cancellation_cutoff_timeunit=cancellation_cutoff_timeunit, 
                min_capacity=min_capacity, 
                send_capacity_email=send_capacity_email, 
                send_capacity_email_cutoff_number=send_capacity_email_cutoff_number,
                send_capacity_email_cutoff_timeunit=send_capacity_email_cutoff_timeunit,
                normal_cost=normal_cost)

            sessions = models.getFromJsonFile("sessions")

            if len(generated_session) > 0:
                sessions.append(generated_session)
                flash(f'<span class="btn btn-link p-0 align-baseline" data-tableid="recurrence-{ (len(sessions) -1) }" onclick="scrollSmoothTo(this.getAttribute(\'data-tableid\'));">{ len(recurring_dates) } events</span> have been successfully generated.', 'success')
            
            models.saveToJsonFile(sessions, "sessions")
            
            return redirect(url_for('create_recurring_events', recurrence_type=request.args.get('recurrence_type')))
        else:
            flash(f'You have requested to many events. Maximum number of events you can create is { max_generated_events }.', 'danger')
            return redirect(url_for('create_recurring_events'))
    else:
        session_sets = []
        session_sets = models.getFromJsonFile("sessions")
    
    return render_template('create-recurring-events.html', form=form, rooms=rooms, session_sets=session_sets, custom_fields={"custom_field":custom_fields}, timezone=os.environ["TZ"], timezone_form = timezone_form, recurrence_type=recurrence_type)

@app.route('/download', methods=['POST'])
def download():
    models.copyDefaultToUserFolder()
    # events = "Nothing is here"
    #sum(listoflists,[]) #TODO add this to merge list of lists for events
    events = xmltodict.unparse(models.appendEventsToXml(), pretty=True)
    if request.method == 'POST': #TODO add validation if user is trying to click download when there are no events generated (e.g. user deleted events in one browser tab and then goes to another tab and tries to download file with 0 events)
        if models.countGeneratedEvents() > 0:
            # events = models.appendEventsToXml()
            # events = xmltodict.unparse(models.appendEventsToXml(), pretty=True)
            models.saveToF2fXml(events)
            models.zipGeneratedSessions()
            userFolder = models.getUserFolder(session["userID"])+"/"
            return send_file(f"{userFolder}{models.GENERATED_ZIP_BACKUP_FILE_NAME}")
        else:
            flash(f"Ooops, looks like you don't have any events. Create some events first and try to downlad again.", 'danger')
            return redirect(url_for('create_recurring_events'))
    return render_template('download.html', events=events)

@app.route('/delete-session', methods=['POST'])
def delete_session():
    if request.method == 'POST':
        sessions = models.getFromJsonFile("sessions")
        set_index = int(request.form['session_set_index'])
        session_index = int(request.form['session_index'])
        if len(sessions[set_index]) == 1:
            del sessions[set_index]
        else:
            del sessions[set_index][session_index]
        models.saveToJsonFile(sessions, "sessions")
        return redirect(url_for('create_recurring_events'))
    return render_template('create-recurring-events.html')

@app.route('/delete-sessions-set', methods=['POST'])
def delete_sessions_set():
    if request.method == 'POST':
        sessions = models.getFromJsonFile("sessions")
        set_index = int(request.form['session_set_index'])
        del sessions[set_index]
        models.saveToJsonFile(sessions, "sessions")
        return redirect(url_for('create_recurring_events'))
    return render_template('create-recurring-events.html')

#DONE
@app.route('/add-rooms', methods=['POST', 'GET'])
def add_rooms():
    form = UploadRooms() #WTFroms for Uploading rooms
    required_headers = ['id', 'name', 'description', 'timecreated', 'capacity', 'location', 'building', 'allowconflicts'] # these are headers that must be uploaded

    required_headers_str = ', '.join(required_headers) # save them as string to display on the page

    if request.method == 'POST' and form.validate():
        CSV = form.file.data #get frle form the form

        decoded_file = CSV.read().decode('utf-8').splitlines() #read CSV
        reader = csv.DictReader(decoded_file)
        rooms = list(reader) # save CSV data to list

        csv_headers = list(rooms[0].keys()) # read headers form the uploaded CSV file
        difference = [i for i in required_headers + csv_headers if i not in required_headers or i not in csv_headers] # check if headers in the CSV file are any all matching to the required headers listed in required_headers

        if len(difference) == 0: # proceed with the code below if uploaded csv has same headers as the required ones

            g.user.delete_rooms() # delete and re-write user rooms in DB. 

            for room in rooms: #loop through all rooms from CVS and create Rooms object for each fo them
                room = models.Room(
                        room_id = room['id'],
                        name=room['name'],
                        description=room['description'],
                        timecreated=room['timecreated'],
                        capacity=room['capacity'],
                        location=room['location'],
                        building=room['building'],
                        allowconflicts=room['allowconflicts'],
                        user_id = g.user.id,
                        isDefault = 0
                    )
                g.user.add_room(room) # append these rooms to the User object and save in database

            flash(f'Successfully uploaded { len(g.user.rooms) } rooms', 'success')
            return redirect(url_for('add_rooms'))
        else:
            flash(f'Please upload CSV that contains the following headers: \n { required_headers_str }', 'danger')
    return render_template('add-rooms.html', form=form, required_headings=required_headers_str)


@app.route('/upload-backup', methods=['POST', 'GET'])
def upload_backup():
    form = UploadBackup()
    
    if request.method == 'POST':
        file = form.file.data
        filename = secure_filename(file.filename)
        if "facetoface" in filename and Path(filename).suffix == ".mbz":

            if models.unzipBackup(file):
                facetoface_dict = models.readXml()
                backup_sessions = models.getSessionsFromXML(facetoface_dict)
                if len(backup_sessions) > 0:
                    g.user.delete_custom_fields() #delete custom fields from the database and overwrite with new ones
                        
                    backup_custom_fields_wrapper = backup_sessions[0]["custom_fields"] # get <custom_fields></custom_fields> from xml

                    if backup_custom_fields_wrapper: #xmlparser returns None if there are zero fields inside <custom_fields></custom_fields> tag in xml

                        backup_custom_fields = backup_custom_fields_wrapper["custom_field"] # get the content of what's inside of <custom_fields></custom_fields>

                        if isinstance(backup_custom_fields, list) == False: # xmlparser returns a list if there are more than one custom field in <custom_fields></custom_fields>, otherwise it returns just one dictionary with custom field data (not a list).

                            backup_custom_fields = [backup_custom_fields] # convert dict to a list with one dictinoary as we need to loop through the list in the code below

                        for custom_field in backup_custom_fields:

                            field = models.CustomField(
                                field_id = custom_field['@id'], 
                                field_name = custom_field['field_name'], 
                                field_type = custom_field['field_type'], 
                                field_data = custom_field['field_data'], 
                                paramdatavalue = custom_field['paramdatavalue'],
                                isDefault = 0,
                                user_id = g.user.id
                            )

                            g.user.add_custom_field(field) # save custom fields from backup to database
                
                    sessions = models.getFromJsonFile("sessions")
                    sessions.insert(0, backup_sessions)
                    models.saveToJsonFile(sessions, "sessions")
             
                flash(f'Backup file uploaded successfully', 'success')
            else:
                flash(f'Incorrect backup', 'danger')
        else:
            flash('Upload the correct Totara activity backup that ends with .mbz. Scroll down to see a guide on how to create a Seminar activity backup with custom fields.', 'danger')
        return redirect(url_for('upload_backup'))
    xmldata = models.readXml()
    return render_template('upload-backup.html', form=form, xmldata=xmldata)


@app.route('/delete-backup', methods=['POST'])
def delete_backup():
    if request.method == 'POST':
        shutil.rmtree(g.user.root_folder)
        g.user.delete_custom_fields()
    return redirect(url_for('create_recurring_events'))

#DONE
@app.route('/delete-rooms', methods=['POST'])
def delete_rooms():
    if request.method == 'POST':
        g.user.delete_rooms()
    return redirect(url_for('create_recurring_events'))


# TODO remove user generated events for loged in user and remove rooms, custom fields and all events for unauthenticated users
@app.route('/clear-all', methods=['POST'])
def clear_all():
    if request.method == 'POST':
        session.pop("userID", None)
        # if session.get('pin') is None:
        #     session.pop("timezone", None)
    return redirect(url_for('create_recurring_events'))


@app.route('/save-timezone', methods=['POST'])
def save_timezone():
    form = TimeZoneForm()
    if request.method == 'POST':
       g.user.timezone = form.timezone.data
    return redirect(url_for('create_recurring_events'))

@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        userID = request.form["pin"]
        if userID == "healthlearn":
            session["pin"] = userID
    return redirect(url_for('create_recurring_events'))

@app.route('/logout')
def logout():
    session.pop("pin", None)
    return redirect(url_for('create_recurring_events'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404
