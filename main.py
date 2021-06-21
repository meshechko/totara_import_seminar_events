from flask import Flask, render_template, redirect, url_for, request, session, flash
import models
from forms import UploadBackup, UploadRooms
import random
import string
from datetime import datetime

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'


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

def checkUserSession():
    if 'userID' not in session:
        letters = string.ascii_lowercase
        randomString = ''.join(random.choice(letters) for i in range(10))
        session['userID'] = randomString


@app.route('/create-events', methods=['GET', 'POST'])
def create_events():
    checkUserSession()
    rooms = models.getRooms()
    rec = models.Recurrence()
    rec.xmlData = models.readXml()
    sessions = rec.getSessions()
    custom_fields = rec.getCustomFields()

    if request.method == 'POST':
        custom_fields_data = []
        for field in custom_fields:
            if field["field_type"] == "text":
                new_field = {
                    "@id": "",
                    "field_name": field['field_name'],
                    "field_type": "text",
                    "field_data": request.form[field['field_name']],
                    "paramdatavalue": "$@NULL@$",
                }
                custom_fields_data.append(new_field)

        details = request.form['details']
        timestart = request.form['timestart']
        timefinish = request.form['timefinish']
        room = request.form['room']
        capacity = request.form['capacity']

        #recurrence
        datestart = datetime.strptime(request.form['datestart'], '%d/%m/%Y').strftime("%Y%m%d")
        datefinish = datetime.strptime(request.form['datefinish'], '%d/%m/%Y').strftime("%Y%m%d")
        frequency = request.form['frequency']
        occurance_number = request.form['occurance_number']
        days_of_week = request.form.getlist('days_of_week[]')
        interval = request.form['interval']
        
        generated_session = models.generate_events(custom_fields_data=custom_fields_data, details=details, timestart=timestart, timefinish=timefinish, room=room, capacity=capacity, datestart=datestart, datefinish=datefinish, frequency=frequency, occurance_number=occurance_number, days_of_week=days_of_week, interval=interval)
        rec.appendToTempGeneratedSessions(generated_session)
        session_sets = rec.getTempGeneratedSessions
    return render_template('event.html', rooms=rooms, session_sets=session_sets, custom_fields=custom_fields)


@app.route('/generate-events', methods=['GET', 'POST'])
def generate_events():
    if request.method == 'POST':
        return redirect(url_for('create_events'))
    return render_template('event.html')


@app.route('/', methods=['POST', 'GET'])
def uploadRooms():
    checkUserSession()
    form = UploadRooms()
    
    if request.method == 'POST' and form.validate():
        CSV = form.file.data
        rooms_list = models.covertCsvToList(CSV)
        if models.validateCsvHeaders(rooms_list):
            models.saveRooms(rooms_list)
            flash(f'Successfully upladed {len(models.getRooms())} rooms', 'success')
        else:
            flash('Please upload CSV that contains the following headers: \n id, name, description, capacity, location, building, published', 'danger')
    return render_template('form.html', form=form)


@app.route('/upload-backup', methods=['POST', 'GET'])
def uploadBackup():
    checkUserSession()
    form = UploadBackup()
    
    if request.method == 'POST':
        file = form.file.data
        if models.validateBackup(file):
            if models.unzipBackup(file):
                flash(f'Backup file uploaded', 'success')
            else:
                flash(f'Incorrect backup', 'danger')
        else:
            flash('Upload the correct Totara activity backup that ends with .mbz. Click here to learn how to generate the seminar activity backup.', 'danger')
    return render_template('backup.html', form=form)

