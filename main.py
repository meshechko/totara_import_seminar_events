from flask import Flask, render_template, redirect, url_for, request, session, flash, send_file
import models
from forms import UploadBackup, UploadRooms, CreateEventForm
import random
import string
from datetime import datetime
import xmltodict
import json
import os
import shutil

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xe7c]'


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

@app.route('/')
def index():
    checkUserSession()
    return render_template('index.html')

def checkUserSession():
    if 'userID' not in session:
        letters = string.ascii_lowercase
        randomString = ''.join(random.choice(letters) for i in range(10))
        session['userID'] = randomString
        seminarFolder = models.getSeminarFolder(session["userID"])
        models.createFolder(seminarFolder)


@app.route('/create-recurring-events', methods=['GET', 'POST'])
def create_recurring_events():
    checkUserSession()
    form = CreateEventForm()
    rooms = models.getFromJsonFile("rooms")
    custom_fields = models.getCustomFieldsFromXML(models.readXml())
    form.rooms.choices = [(room["id"], room["name"]) for room in models.getFromJsonFile("rooms")]
    max_generated_events = 1000
    if request.method == 'POST' and form.validate_on_submit():
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
        days_of_week = ""
        if form.days_of_week:
            days_of_week = request.form.getlist('days_of_week')
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

        recurring_dates = models.generateRecurringDates(
            datestart=datestart, 
            datefinish=datefinish, 
            frequency=frequency, 
            occurrence_number=occurrence_number, 
            days_of_week=days_of_week, 
            interval=interval)

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
            
            return redirect(url_for('create_recurring_events'))
        else:
            flash(f'You have requested to many events. Maximum number of events you can create is { max_generated_events }.', 'danger')
            return redirect(url_for('create_recurring_events'))
    else:
        session_sets = []
        session_sets = models.getFromJsonFile("sessions")
    return render_template('create-recurring-events.html', form=form, rooms=rooms, session_sets=session_sets, custom_fields=custom_fields)

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

@app.route('/add-rooms', methods=['POST', 'GET'])
def add_rooms():
    checkUserSession()
    form = UploadRooms()
    required_headings = ', '.join(models.requiredHeaders)
    if request.method == 'POST' and form.validate():
        CSV = form.file.data
        rooms_list = models.covertCsvToList(CSV)
        if models.validateCsvHeaders(rooms_list):
            models.saveToJsonFile(rooms_list, "rooms")
            flash(f'Successfully upladed {len(models.getFromJsonFile("rooms"))} rooms', 'success')
        else:
            flash(f'Please upload CSV that contains the following headers: \n { required_headings }', 'danger')
        return redirect(url_for('add_rooms'))
    return render_template('add-rooms.html', form=form, required_headings=required_headings)


@app.route('/upload-backup', methods=['POST', 'GET'])
def upload_backup():
    checkUserSession()
    form = UploadBackup()
    
    if request.method == 'POST':
        file = form.file.data
        if models.validateBackup(file):
            if models.unzipBackup(file):
                #TODO think if its necessary to import exisitng backup or it will just complicate things. Maybe this app should b used for creatin new sessions only rather than modifying exisitng ones.
                facetoface_dict = models.readXml()
                backup_sessions = models.getSessionsFromXML(facetoface_dict)
                if len(backup_sessions) > 0:
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
        seminarFolder = models.getSeminarFolder(session["userID"])
        shutil.rmtree(seminarFolder)
    return redirect(url_for('create_recurring_events'))

@app.route('/delete-rooms', methods=['POST'])
def delete_rooms():
    if request.method == 'POST':
        os.remove(models.getUserFolder(session["userID"])+'/rooms.json')
    return redirect(url_for('create_recurring_events'))

@app.route('/clear-all', methods=['POST'])
def clear_all():
    if request.method == 'POST':
        session.pop("userID", None)
    return redirect(url_for('create_recurring_events'))
