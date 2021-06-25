from flask_wtf import FlaskForm
from wtforms import SubmitField, TextAreaField, DateTimeField, IntegerField, SelectField, validators
from wtforms.fields import html5 as h5fields
from wtforms.widgets import html5 as h5widgets
from flask_wtf.file import FileField, FileAllowed, FileRequired
from datetime import date


class UploadRooms(FlaskForm):
    file = FileField("Upload CSV", validators=[
        FileRequired(), FileAllowed(['csv'], 'You can upload CSV only')])
    submit = SubmitField('Upload')


class UploadBackup(FlaskForm):
    file = FileField("Upload Totara Seminar activity backup", validators=[
        FileRequired()])
    submit = SubmitField('Upload')

today = date.today()
today = today.strftime("%d/%m/%Y")
    
class CreateEventForm(FlaskForm):
    details = TextAreaField(u'Details', render_kw={"class": "form-control"})
    timestart = DateTimeField(u'Start time', [validators.required()], format='%H:%M', render_kw={"class": "form-control time flatpickr-input active"}, default="12:00")
    timefinish = DateTimeField(u'Finish time', [validators.required()], format='%H:%M', render_kw={"class": "form-control time flatpickr-input active"}, default="12:00")
    capacity = IntegerField(u'Maximum bookings', [validators.required()], widget=h5widgets.NumberInput(min=0, max=1000, step=1), render_kw={"class": "form-control"}, default="10")
    rooms = SelectField(u'Rooms', [validators.required()], render_kw={"class": "form-select"})

    datestart = DateTimeField(u'Start', [validators.required()], format='%d/%m/%Y', render_kw={"class": "form-control cal flatpickr-input active", "readonly":"readonly"}, default=today)
    datefinish = DateTimeField(u'End by', [validators.required()], format='%d/%m/%Y', render_kw={"class": "form-control cal flatpickr-input active", "readonly":"readonly"}, default=today)
    frequency = SelectField(u'Frequency', choices=[('WEEKLY', 'Weekly'), ('MONTHLY', 'Monthly')], default='WEEKLY', render_kw={"class": "form-select"})

    
