from pathlib import Path
from flask import Flask, render_template, redirect, url_for, request, session, flash, send_file, g, jsonify
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
from os import path

app = Flask(__name__)
app.secret_key = b'_5#y2L"ojiKnrkj'

myapp = models.Controller()

#FILTERS
@app.template_filter('time_format')
def datetime_format(value, format="%H:%M"):
    proper_date = datetime.fromtimestamp(int(value))
    return proper_date.strftime(format)


@app.template_filter('date_format')
def datetime_format(value, format="%A, %d %B %Y"):
    proper_date = datetime.fromtimestamp(int(value))
    return proper_date.strftime(format)


@app.template_filter('to_list')
def to_list(value):
    if isinstance(value, list) == False:
        value = [value]
    return value


@app.before_request
def before_request():
    if 'userID' not in session: # check if its a returning user
        # generate random user id that consists of 10 characters
        letters = string.ascii_lowercase
        random_string = ''.join(random.choice(letters) for i in range(10))

        session['userID'] = random_string # create session for a new user

        myapp.new_user(user_id=session['userID']) # initiat user and add user to database
    
    g.user = myapp.get_user_details(session['userID']) # assign user to global app scope context

   
    #TODO how to use the same user object across all requests/pages? At the moment it creates a new object for every request. Hence, it makes it impossible to store data in user properties, e.g. I have created events.json to temporary store events that user generated. If there's a way to have only one user object then I thought would be better to store generated events in user property rather than .json file.
    
    # assign user set timezone to server
    os.environ["TZ"] = g.user.timezone 
    time.tzset()


@app.route('/')
def index():

    return render_template('index.html')


@app.route('/create-recurring-events', methods=['GET', 'POST'])
def create_recurring_events():
    form = CreateEventForm()
    timezone_form = TimeZoneForm()
    
    user_custom_fields = g.user.custom_fields # get custom fields user has in adabase

    rooms = g.user.rooms # get rooms user has in database
    form.rooms.choices = [(room.id, room.name) for room in rooms] #loadrooms id and name form dtabase

    max_generated_events = 1000 # max number of events user can create (including the ones in the uploaded backup file)

    recurrence_type = request.args.get('recurrence_type') # type of recurrence either selected dates from calendar or recurrence patterns

    if request.method == 'POST' and form.validate_on_submit() and g.user.timezone:
        
        form_custom_fields = []

        i = 0
        for field in user_custom_fields: #loop through all custom fields in a form and append values to form_custom_fields  that will then transfer data to the Event object
            form_custom_fields.append(field)
            form_custom_fields[i].field_data = request.form[field.field_name]
            i += 1

        recurrence = models.Recurrence()

        if recurrence_type == "manual": #if user selected some specific dates in the calendar
            dates = form.manual_dates.data.replace(' ','').split(",")
            recurrence.dates = sorted([datetime.strptime(date, '%d/%m/%Y') for date in dates])

            session["recurrence_type"] = "manual" #use session to show manual calendar rather than recurring form after page is refreshed

        else: #if user selected recurrence pattern e.g. every Tuesday
            occurrence_number = ''
            if form.occurrence_number:
                occurrence_number = form.occurrence_number.data

            days_of_week = ''
            if form.days_of_week:
                days_of_week = request.form.getlist('days_of_week')

            recurrence.datestart=form.datestart.data.strftime("%Y%m%d") #TODO what is the best way to convert here or within Recurrence class
            recurrence.datefinish=form.datefinish.data.strftime("%Y%m%d")
            recurrence.frequency=form.frequency.data
            recurrence.occurrence_number=occurrence_number
            recurrence.days_of_week=days_of_week
            recurrence.interval=form.interval.data

        if (recurrence.count() + g.user.count_events()) <= max_generated_events: 

            generated_events = myapp.generate_recurring_events(
                user = g.user,
                custom_fields=form_custom_fields, 
                details=form.details.data,
                timestart=form.timestart.data.strftime("%H:%M"), 
                timefinish=form.timefinish.data.strftime("%H:%M"), 
                room_id=form.rooms.data, 
                capacity=form.capacity.data, 
                recurring_dates=recurrence.dates,
                allow_overbook=form.allow_overbook.data, 
                allow_cancellations=form.allow_cancellations.data, 
                cancellation_cutoff_number=form.cancellation_cutoff_number.data, 
                cancellation_cutoff_timeunit=form.cancellation_cutoff_timeunit.data, 
                min_capacity=form.min_capacity.data, 
                send_capacity_email=form.send_capacity_email.data, 
                send_capacity_email_cutoff_number=form.send_capacity_email_cutoff_number.data,
                send_capacity_email_cutoff_timeunit=form.send_capacity_email_cutoff_timeunit.data,
                normal_cost=form.normal_cost.data)
            
            user_events = g.user.event_sets
            
            if len(generated_events) > 0:
                user_events.append(generated_events)
                flash(f'<span class="btn btn-link p-0 align-baseline" data-tableid="recurrence-{ g.user.count_event_sets() - 1 }" onclick="scrollSmoothTo(this.getAttribute(\'data-tableid\'));">{ recurrence.count() } events</span> have been successfully generated.', 'success')
            
            g.user.event_sets = user_events
            
            return redirect(url_for('create_recurring_events', recurrence_type=request.args.get('recurrence_type')))
        else:
            flash(f'You have requested to many events. Maximum number of events you can create is { max_generated_events }.', 'danger')
            return redirect(url_for('create_recurring_events'))

    return render_template('create-recurring-events.html', form=form, rooms=rooms, session_sets=g.user.get_sets_data(), custom_fields={"custom_field":user_custom_fields}, timezone=os.environ["TZ"], timezone_form = timezone_form, recurrence_type=recurrence_type)


@app.route('/download', methods=['POST'])
def download():
    if path.exists(g.user.seminar_folder) == False: #if user has not uploaded a their backup - copy default backup to user folder so there're files to zip and download
        shutil.copytree(models.DEFAULT_SEMINAR_FOLDER, g.user.seminar_folder)
        
    with open(g.user.facetoface_xml, "rb") as f: #open facetoface.xml that user uploaded
        facetoface_dict = xmltodict.parse(f, dict_constructor=dict) #convert content of facetoface.xml to dict
    
    try: 
        facetoface_dict["activity"]["facetoface"]["sessions"]["session"] =  g.user.get_all_events()

    except: #if there are no events in the backup user has uploaded then append {"session": g.user.get_all_events()}
        facetoface_dict["activity"]["facetoface"]["sessions"] = {"session": g.user.get_all_events()}

    facetoface_xml = xmltodict.unparse(facetoface_dict, pretty=True) #convert generated events and the ones that were imported from user backup file (if any)

    if request.method == 'POST': 

        if g.user.count_events() > 0: # check if there are any events, otherwise no backup to zip and download without any events

            with open(g.user.facetoface_xml, "w") as f: #open file from user folder
                f.write(facetoface_xml)

            #zip user folder
            myapp.zip_backup(
                root_folder=g.user.root_folder,
                seminar_folder=g.user.seminar_folder
                )

            zip_file = os.path.join(g.user.root_folder, models.GENERATED_ZIP_BACKUP_FILE_NAME)
           
            # send file to the user
            return send_file(zip_file)
        else:
            flash(f"Ooops, looks like you don't have any events. Create some events first and try to downlad again.", 'danger')

    return redirect(url_for('create_recurring_events'))


@app.route('/delete-event', methods=['POST'])
def delete_event():
    events = g.user.event_sets

    set_index = int(request.form['session_set_index'])
    session_index = int(request.form['session_index'])

    if len(events[set_index]) == 1:
        del events[set_index]
    else:
        del events[set_index][session_index]
    
    g.user.event_sets = events

    table_data = g.user.get_sets_data()

    return jsonify({'data': render_template('event-sets.html', session_sets=table_data)})


@app.route('/delete-events-set', methods=['POST'])
def _delete_events_set():
    events = g.user.event_sets
    set_index = int(request.form['session_set_index'])
    del events[set_index]
    g.user.event_sets = events
    table_data = g.user.get_sets_data()
    return jsonify({'data': render_template('event-sets.html', session_sets=table_data)})


@app.route('/add-rooms', methods=['POST', 'GET'])
def add_rooms():
    form = UploadRooms() 
    required_headers = ['id', 'name', 'description', 'timecreated', 'capacity', 'location', 'building', 'allowconflicts'] # these are headers that must be uploaded

    required_headers_str = ', '.join(required_headers) # save them as string to display on the page

    if request.method == 'POST' and form.validate():
        CSV = form.file.data #get frle form the form

        #TODO move to controller
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

            #TODO messages are return value from the method in Controller
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

            if myapp.unzip_backup(file=file, folder=g.user.seminar_folder): #check if uploaded file is correct archive and unzip it into user seminar folder

                facetoface_dict = {}

                with open(g.user.facetoface_xml, "rb") as f: #open facetoface.xml that user uploaded
                    facetoface_dict = xmltodict.parse(f, dict_constructor=dict) #convert content of facetoface.xml to dict

                try: #check if there any sessions in the uploaded file. Without TRY it will show error as the below path in a dict will not be accessible. That's why added TRY here
                    backup_sessions = facetoface_dict["activity"]["facetoface"]["sessions"]["session"]

                    # need to check if it is a lis or not because if there's only one event (session) then xmltodict makes it as a dict, if there are 2 and more then xmltodict makes it a list of dict's
                    if isinstance(backup_sessions, list) == False:
                        backup_sessions = [backup_sessions]
                except:
                    backup_sessions = []

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

                    try: #try to ead file, if it doesnt exist (means user hasn't uploaded any thing yet) create an empty list
                        sessions = g.user.event_sets
                    except:
                        sessions = []
                    sessions.insert(0, backup_sessions)

                    g.user.event_sets = sessions


                return jsonify(message='Backup file uploaded successfully')
            else:
                return jsonify(message='Incorrect backup'), 500
        else:
            return jsonify(message='Upload the correct Totara activity backup that ends with .mbz. Scroll down to see a guide on how to create a Seminar activity backup with custom fields.'), 500

    return render_template('upload-backup.html', form=form)


@app.route('/delete-backup', methods=['POST'])
def delete_backup():
    if request.method == 'POST':
        shutil.rmtree(g.user.seminar_folder)
        g.user.delete_custom_fields()
    return redirect(url_for('create_recurring_events'))


@app.route('/delete-rooms', methods=['POST'])
def delete_rooms():
    if request.method == 'POST':
        g.user.delete_rooms()
    return redirect(url_for('create_recurring_events'))


# TODO remove user generated events for loged in user and remove rooms, custom fields and all events for unauthenticated users
@app.route('/clear-all', methods=['POST'])
def clear_all():
    if request.method == 'POST':
        if g.user.email:
            file_to_rem = Path(g.user.events_file)
            file_to_rem.unlink(missing_ok=True)
        else:
            shutil.rmtree(g.user.root_folder)
            g.user.delete_custom_fields()
            g.user.delete_rooms()
    return redirect(url_for('create_recurring_events'))


@app.route('/save-timezone', methods=['POST'])
def save_timezone():
    form = TimeZoneForm()
    g.user.timezone = form.timezone.data
    return jsonify({'data': g.user.timezone})


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404
    

#TODO add login page and signup page
@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        userID = request.form["pin"]
        user = myapp.get_user_details(userID)
        if user:
            session['userID'] = user.id
            session['user_email'] = user.email
    return redirect(url_for('create_recurring_events'))


@app.route('/logout')
def logout():
    session.pop("userID", None)
    session.pop("user_email", None)
    return redirect(url_for('create_recurring_events'))

