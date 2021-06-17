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


@app.route('/create-events')
def create_events():
    checkUserSession()
    rooms = models.getRooms()
    rec = models.Recurrence()
    rec.xmlData = models.readXml()
    sessions = rec.getSessions()
    custom_fields = rec.getCustomFields()
    

    print(sessions)
    return render_template('event.html', rooms=rooms, sessions=sessions, custom_fields=custom_fields)


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

