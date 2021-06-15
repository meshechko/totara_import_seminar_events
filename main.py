from flask import Flask, render_template, redirect, url_for, request, session, flash
import models
from forms import UploadBackup, UploadRooms
import random
import string


app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'



def checkUserSession():
    if 'userID' not in session:
        letters = string.ascii_lowercase
        randomString = ''.join(random.choice(letters) for i in range(10))
        session['userID'] = randomString


@app.route('/create-events', methods=['POST', 'GET'])
def upload_route_summary():
    checkUserSession()
    rooms = models.getRooms()
    
    return render_template('event.html', rooms=rooms)


@app.route('/', methods=['POST', 'GET'])
def uploadRooms():
    checkUserSession()
    form = UploadRooms()
    
    if request.method == 'POST' and form.validate():
        CSV = form.file.data
        rooms_list = models.covertCsvToList(CSV)
        if models.validateCsvHeaders(rooms_list):
            models.saveRooms(rooms_list)
            flash(
                f'Successfully upladed {len(models.getRooms())} rooms', 'success')
        else:
            flash('Please upload CSV that contains the following headers: \n id, name, description, capacity, location, building, published', 'danger')
    return render_template('form.html', form=form)


@app.route('/upload-backup', methods=['POST', 'GET'])
def uploadBackup():
    checkUserSession()
    form = UploadBackup()
    
    if request.method == 'POST' and form.validate():
        file = form.file.data
        if models.validateBackup(file):
            models.uploadBackup(file)
            if models.unzipBackup(file):
                flash(
                    f'Backup file uploaded', 'success')
            else:
                flash(f'Incorrect backup', 'danger')
        else:
            flash('The uploaded file doesn’t have Seminar activity. Click here to learn how to generate the seminar activity backup.')
    return render_template('backup.html', form=form)

