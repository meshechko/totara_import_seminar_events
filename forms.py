from flask_wtf import FlaskForm
from wtforms import SubmitField, TextAreaField, DateTimeField, IntegerField, SelectField, SelectMultipleField, BooleanField, RadioField, validators, widgets
from wtforms.fields import html5 as h5fields
from wtforms.widgets import html5 as h5widgets
from flask_wtf.file import FileField, FileAllowed, FileRequired
from datetime import datetime, time

from wtforms.widgets.core import CheckboxInput

class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

class UploadRooms(FlaskForm):
    file = FileField("Upload CSV", validators=[
        FileRequired(), FileAllowed(['csv'], 'You can upload CSV only')])
    submit = SubmitField('Upload')


class UploadBackup(FlaskForm):
    file = FileField("Upload Totara Seminar activity backup", validators=[
        FileRequired()])
    submit = SubmitField('Upload')
    
class CreateEventForm(FlaskForm):
    details = TextAreaField(u'Details', render_kw={"class": "form-control"})
    timestart = DateTimeField(u'Start time', [validators.required()], format='%H:%M', render_kw={"class": "form-control time flatpickr-input active"}, default=time(12))
    timefinish = DateTimeField(u'Finish time', [validators.required()], format='%H:%M', render_kw={"class": "form-control time flatpickr-input active"}, default=time(12))
    capacity = IntegerField(u'Maximum bookings', [validators.required()], widget=h5widgets.NumberInput(min=0, max=1000, step=1), render_kw={"class": "form-control"}, default="10")

    rooms = SelectField(u'Rooms', [validators.required()], render_kw={"class": "form-select"})

    # registration_datestart = DateTimeField(u'Date', format='%d/%m/%Y', render_kw={"class": "form-control time flatpickr-input active"}, default=time(12))
    # registration_timestart = DateTimeField(u'Time', format='%H:%M', render_kw={"class": "form-control time flatpickr-input active"}, default=time(12))
    # enable_registration_start = CheckboxInput("Enable Sign-up open date and time")

    # registration_datefinish = DateTimeField(u'Date', format='%d/%m/%Y', render_kw={"class": "form-control time flatpickr-input active"}, default=time(12))
    # registration_timefinish = DateTimeField(u'Time', format='%H:%M', render_kw={"class": "form-control time flatpickr-input active"}, default=time(12))
    # enable_registration_finish = CheckboxInput("Enable Sign-up closes date and time")

    allow_overbook = BooleanField("Enable waitlist")

    allow_cancellations = RadioField('Enable waitlist', choices=[("1",'At any time'),("0",'Never'),("2",'Until specified period')], default="1")
    cancellation_cutoff_number = IntegerField(u'Time', widget=h5widgets.NumberInput(min=0, max=1000, step=1), render_kw={"class": "form-control", 'disabled':''}, default=0)
    cancellation_cutoff_timeunit = SelectField(u'Time unit', choices=[(604800, 'weeks'), (86400, 'days'), (3600, 'hours'), (60, 'minutes'), (1, 'seconds')], default=3600, render_kw={"class": "form-select", 'disabled':''})

    min_capacity = IntegerField(u'Minimum bookings ', widget=h5widgets.NumberInput(min=0, max=1000, step=1), render_kw={"class": "form-control"}, default=0)

    send_capacity_email = BooleanField("Notify about minimum bookings")
    send_capacity_email_cutoff_number = IntegerField(u'Time', widget=h5widgets.NumberInput(min=0, max=1000, step=1), render_kw={"class": "form-control", 'disabled':''}, default=0)
    send_capacity_email_cutoff_timeunit = SelectField(u'Time unit', choices=[(604800, 'weeks'), (86400, 'days'), (3600, 'hours'), (60, 'minutes'), (1, 'seconds')], default=3600, render_kw={"class": "form-select", 'disabled':''})

    normal_cost =IntegerField(u'Normal cost', widget=h5widgets.NumberInput(min=0, max=1000, step=1), render_kw={"class": "form-control"}, default=0)


    datestart = DateTimeField(u'Start', [validators.required()], format='%d/%m/%Y', render_kw={"class": "form-control cal flatpickr-input active", "readonly":"readonly"}, default=datetime.today)
    datefinish = DateTimeField(u'End by', [validators.required()], format='%d/%m/%Y', render_kw={"class": "form-control cal flatpickr-input active", "readonly":"readonly"}, default=datetime.today)
    frequency = SelectField(u'Frequency', choices=[('WEEKLY', 'Weekly'), ('MONTHLY', 'Monthly')], default='WEEKLY', render_kw={"class": "form-select"})
    interval = IntegerField(u'of every', [validators.required()], widget=h5widgets.NumberInput(min=0, max=50, step=1), render_kw={"class": "form-control d-inline"}, default=1)
    days_of_week = MultiCheckboxField('', choices=[('MO', 'Monday'), ('TU', 'Tuesday'), ('WE', 'Wednesday'), ('TH', 'Thursday'), ('FR', 'Friday'), ('SA', 'Saturday'), ('SU', 'Sunday')], render_kw={'class': "form-check-input"})
    occurrence_number = SelectField(u'The', choices=[(1, 'First'), (2, 'Second'), (3, 'Third'), (4, 'Fourth'), (-1, 'Last')], default=1, render_kw={"class": "form-select"})


