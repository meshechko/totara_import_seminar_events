from flask import Flask, render_template, redirect, url_for, request, session, flash
import models
from forms import UploadBackup, UploadRooms, CreateEventForm
import random
import string
from datetime import datetime
import dicttoxml
import xmltodict

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]a/'


#FILTERS

@app.template_filter('time_format')
def datetime_format(value, format="%H:%M"):
    proper_date = datetime.fromtimestamp(int(value))
    return proper_date.strftime(format)

@app.template_filter('date_format')
def datetime_format(value, format="%d/%m/%y"):
    proper_date = datetime.fromtimestamp(int(value))
    return proper_date.strftime(format)


# ROUTES

@app.route('/')
def index():
    return render_template('index.html')

def checkUserSession():
    if 'userID' not in session:
        letters = string.ascii_lowercase
        randomString = ''.join(random.choice(letters) for i in range(10))
        session['userID'] = randomString



@app.route('/create-recurring-events', methods=['GET', 'POST'])
def create_recurring_events():
    checkUserSession()
    form = CreateEventForm()
    rooms = models.getRooms()
    #https://gis.stackexchange.com/questions/202978/converting-xml-dict-xml-using-python
    # out = xmltodict.unparse(models.readXml(), pretty=True)
    # print(out)
    if len(rooms) > 0:
        form.rooms.choices = [(room["id"], room["name"]) for room in models.getRooms()]
    
    custom_fields = models.getCustomFields(models.readXml())

    session_sets = []
    if 'sessions' in session:
        session_sets = session['sessions']
    else:
        session['sessions'] = []
    return render_template('create-recurring-events.html', form=form, rooms=rooms, session_sets=session_sets, custom_fields=custom_fields)



@app.route('/generate-events', methods=['POST'])
def generate_events():
    form = CreateEventForm()
    if request.method == 'POST':
        list_of_custom_fields = models.getCustomFields(models.readXml())
        custom_fields_data = []
        for field in list_of_custom_fields:
            if field["field_type"] == "text":
                new_field = {
                    "@id": "",
                    "field_name": field['field_name'],
                    "field_type": "text",
                    "field_data": request.form[field['field_name']],
                    "paramdatavalue": "$@NULL@$",
                }
                custom_fields_data.append(new_field)
        # custom_fields = ""
        # if "custom_fields" in request.form:
        #     custom_fields = request.form.getlist('custom_fields')

        details = form.details.data
        timestart = form.timestart.data.strftime("%H:%M")
        timefinish = form.timefinish.data.strftime("%H:%M")
        room = ""
        if form.rooms:
            room = form.rooms.data
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

        allow_cancellations = int(form.allow_cancellations.data)
        cancellation_cutoff_number = form.cancellation_cutoff_number.data
        cancellation_cutoff_timeunit = int(form.cancellation_cutoff_timeunit.data)
        min_capacity = form.min_capacity.data
        send_capacity_email = form.send_capacity_email.data
        send_capacity_email_cutoff_number = form.send_capacity_email_cutoff_number.data
        send_capacity_email_cutoff_timeunit = int(form.send_capacity_email_cutoff_timeunit.data)
        normal_cost = form.normal_cost.data

        generated_session = models.generate_recurring_sessions(custom_fields_data=custom_fields_data, details=details, timestart=timestart, timefinish=timefinish, room=room, capacity=capacity, datestart=datestart, datefinish=datefinish, frequency=frequency, occurrence_number=occurrence_number, days_of_week=days_of_week, interval=interval, allow_overbook=allow_overbook, allow_cancellations=allow_cancellations, cancellation_cutoff_number=cancellation_cutoff_number, cancellation_cutoff_timeunit=cancellation_cutoff_timeunit, min_capacity=min_capacity, send_capacity_email=send_capacity_email, send_capacity_email_cutoff_number=send_capacity_email_cutoff_number,send_capacity_email_cutoff_timeunit=send_capacity_email_cutoff_timeunit,normal_cost=normal_cost)
        
        sessions = session['sessions']
        if len(generated_session) > 0:
            sessions.append(generated_session)
        session['sessions'] = sessions
        return redirect(url_for('create_recurring_events'))
    return render_template('create-recurring-events.html')

@app.route('/delete-session', methods=['POST'])
def delete_session():
    if request.method == 'POST':
        sessions = session['sessions']
        set_index = int(request.form['session_set_index'])
        session_index = int(request.form['session_index'])
        if len(sessions[set_index]) == 1:
            del sessions[set_index]
        else:
            del sessions[set_index][session_index]
        session['sessions'] = sessions
        return redirect(url_for('create_recurring_events'))
    return render_template('create-recurring-events.html')

@app.route('/delete-sessions-set', methods=['POST'])
def delete_sessions_set():
    if request.method == 'POST':
        sessions = session['sessions']
        set_index = int(request.form['session_set_index'])
        del sessions[set_index]
        session['sessions'] = sessions
        return redirect(url_for('create_recurring_events'))
    return render_template('create-recurring-events.html')

@app.route('/upload-rooms', methods=['POST', 'GET'])
def upload_rooms():
    checkUserSession()
    form = UploadRooms()
    
    if request.method == 'POST' and form.validate():
        CSV = form.file.data
        rooms_list = models.covertCsvToList(CSV)
        if models.validateCsvHeaders(rooms_list):
            models.saveRooms(rooms_list)
            flash(f'Successfully upladed {len(models.getRooms())} rooms', 'success')
        else:
            flash('Please upload CSV that contains the following headers: \n id, name, description, capacity, allowconflicts, building, location', 'danger')
    return render_template('upload-rooms.html', form=form)


@app.route('/upload-backup', methods=['POST', 'GET'])
def upload_backup():
    checkUserSession()
    form = UploadBackup()
    
    if request.method == 'POST':
        file = form.file.data
        if models.validateBackup(file):
            if models.unzipBackup(file):
                flash(f'Backup file uploaded successfully', 'success')
            else:
                flash(f'Incorrect backup', 'danger')
        else:
            flash('Upload the correct Totara activity backup that ends with .mbz. Scroll down to see a guide how to create Seminar activity backup with custom fields.', 'danger')
    return render_template('upload-backup.html', form=form)
