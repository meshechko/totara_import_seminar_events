from flask_wtf import FlaskForm
from wtforms import SubmitField
from flask_wtf.file import FileField, FileAllowed, FileRequired


class UploadRooms(FlaskForm):
    file = FileField("Upload CSV", validators=[
        FileRequired(), FileAllowed(['csv'], 'You can upload CSV only')])
    submit = SubmitField('Upload')


class UploadBackup(FlaskForm):
    file = FileField("Upload Totara Seminar activity backup", validators=[
        FileRequired(), FileAllowed(['mbz', 'zip'], 'Upload the correct Totara activity backup that ends with .mbz. Click here to learn how to generate the seminar activity backup.')])
    submit = SubmitField('Upload')