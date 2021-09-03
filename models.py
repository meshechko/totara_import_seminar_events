import os
import shutil
from flask import session
from werkzeug.utils import secure_filename
from pathlib import Path
import zipfile
import tarfile
import magic
import xmltodict
import json
import csv
import uuid
from dateutil import rrule, parser, relativedelta
from dateutil.rrule import rrulestr
from datetime import datetime
import os.path
from os import path
import time
import string
import random

import db
# CONFIG data

#done
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads/')
DEFAULT_SEMINAR_FOLDER = UPLOAD_FOLDER + '/seminar/'
DEFAULT_FACETOFACE_XML = DEFAULT_SEMINAR_FOLDER + '/activities/facetoface_14350/facetoface.xml'

#done
def getSeminarFolder(userID):
    return UPLOAD_FOLDER + userID + "/seminar/"

# done
def getUserFolder(userID):
    return UPLOAD_FOLDER + userID

# ROOMS upload

#done
def createFolder(folder):
    Path(folder).mkdir(parents=True, exist_ok=True)


def saveToJsonFile(list, file_name):
    userFolder = getUserFolder(session["userID"])
    if os.path.isdir(userFolder) == False: # done
        createFolder(userFolder) #done
    with open(os.path.join(userFolder, file_name+".json"), 'w') as file:
        toJson = json.dumps(list)
        file.write(toJson)


def getFromJsonFile(file_name):
    list = []
    userFile = getUserFolder(session["userID"])+"/"+file_name+".json"

    if path.exists(userFile):
        list = open(userFile, "rb").read()
        list = json.loads(list)
    else:
        folder = "default/"
        if 'pin' in session:
            folder = "default/" + session['pin'] + '/'

        list = open((UPLOAD_FOLDER + folder + file_name+".json"), "rb").read()
        list = json.loads(list)
    return list

# BACKUP upload


#TODO how to move this into the controller or add this code into the route (it will make route code much longer)?
def unzip_backup(file, folder):

    # check if diectory alreay exist and overwrite its content
    if os.path.exists(folder):
        shutil.rmtree(folder)

    filename = secure_filename(file.filename) #get uploaded file name
    #TODO how to avoid creating folder here as its created in @app.before_request
    Path(folder).mkdir(parents=True, exist_ok=True) # create seminar folder
    
    file.save(os.path.join(folder, filename)) # upload file in to user folder

    mbz_filepath = folder+filename

    fileinfo = magic.from_file(mbz_filepath)

    #check if file is zip or gzip and unzip it into the user seminar folder, otherwise don't unzip as .mbz is zip type file
    if 'Zip archive data' in fileinfo:
        with zipfile.ZipFile(mbz_filepath, 'r') as myzip:
            myzip.extractall(folder)

    elif 'gzip compressed data' in fileinfo:
        tar = tarfile.open(mbz_filepath)
        tar.extractall(path=folder)
        tar.close()

    else:
        return False

    os.remove(mbz_filepath) # delete .mbz after unzipping 

    return True


def getf2fxml():
    userActivitiesFolder = getSeminarFolder(session["userID"])+"activities/"
    if path.exists(userActivitiesFolder) == False:
        if 'pin' in session:
            userActivitiesFolder = UPLOAD_FOLDER + "default/" + session['pin'] + '/seminar/activities/'
        else:
            userActivitiesFolder = UPLOAD_FOLDER + "default/seminar/activities/"

    subfolders = [f.path for f in os.scandir(
        userActivitiesFolder) if f.is_dir()]
    for folder in list(subfolders):
        if "facetoface" in folder:
            return folder+"/facetoface.xml"


def saveToF2fXml(data):
     with open(getf2fxml(), "w") as f:
         f.write(data)
         return True


GENERATED_ZIP_BACKUP_FILE_NAME = "backup-totara-activity-facetoface.mbz"


def zipGeneratedSessions():
    base_dir = getSeminarFolder(session["userID"])
    userFolder = getUserFolder(session["userID"])+"/"
    with zipfile.ZipFile(userFolder + GENERATED_ZIP_BACKUP_FILE_NAME, "w",
                     compression=zipfile.ZIP_DEFLATED) as zf:
        base_path = os.path.normpath(base_dir)
        for dirpath, dirnames, filenames in os.walk(base_dir):
            for name in sorted(dirnames):
                path = os.path.normpath(os.path.join(dirpath, name))
                zf.write(path, os.path.relpath(path, base_path))
            for name in filenames:
                path = os.path.normpath(os.path.join(dirpath, name))
                if os.path.isfile(path):
                    zf.write(path, os.path.relpath(path, base_path))
    # urllib.request.urlretrieve(urlparse(str(userFolder + GENERATED_ZIP_BACKUP_FILE_NAME)))


def readXml(xml_attribs=True):
    with open(getf2fxml(), "rb") as f:
        # my_dictionary = xmltodict.parse(f, xml_attribs=xml_attribs)
        return xmltodict.parse(f, dict_constructor=dict)


# RECURRANCE

# "DTSTART:20210902T090000 RRULE:FREQ=WEEKLY;COUNT=5;INTERVAL=10;UNTIL=20230102T090000"

def generate_recurring_sessions(recurring_dates, custom_fields_data, details, timestart, timefinish, room_id, capacity,  allow_overbook, allow_cancellations, cancellation_cutoff_number, cancellation_cutoff_timeunit, min_capacity, send_capacity_email, send_capacity_email_cutoff_number, send_capacity_email_cutoff_timeunit, normal_cost):


    sessions = []
    
    if room_id != None:
        room = next((item for item in getFromJsonFile("rooms") if item['id'] == room_id), None)
        room = {
                "@id": room["id"],
                "name": room["name"],
                "description": room["description"],
                "capacity": room["capacity"],
                "allowconflicts": "0",
                "custom": "0",
                "hidden": "0",
                "usercreated": "$@NULL@$",
                "usermodified": "$@NULL@$",
                            "timecreated": "",
                            "timemodified": "",
                            "room_fields": {
                                "room_field": [
                                    {
                                        "@id": "",
                                        "field_name": "building",
                                        "field_type": "text",
                                        "field_data": room["building"],
                                        "paramdatavalue": "$@NULL@$",
                                    },
                                    {
                                        "@id": "",
                                        "field_name": "location",
                                        "field_type": "location",
                                        "field_data": '{"address":"' + room["location"] + '","size":"medium","view":"map","display":"address","zoom":12,"location":{"latitude":"0","longitude":"0"}}',
                                        "paramdatavalue": "$@NULL@$",
                                    },
                                ]
                            },
            }
    else:
        room = None

    all_custom_fields = []
    for custom_field in custom_fields_data:
        field_dict = {
                '@id': '',
                'field_name': custom_field.field_name,
                'field_type': custom_field.field_type,
                'field_data': custom_field.field_data,
                'paramdatavalue': custom_field.paramdatavalue,
            }
        
        all_custom_fields.append(field_dict)

    for date in recurring_dates:
        start = f"{ str(date.date()) } { timestart }"
        start = int(datetime.strptime(start, '%Y-%m-%d %H:%M').timestamp())
        finish = f"{ str(date.date()) } { timefinish }"
        finish = int(datetime.strptime(finish, '%Y-%m-%d %H:%M').timestamp())

        if not all_custom_fields:
            all_custom_fields = None

        session = {
            '@id': "",
            'capacity': str(capacity),
            'allowoverbook': str(int(allow_overbook)),
            'waitlisteveryone': "0",
            'details': details,
            'normalcost': str(normal_cost),
            "discountcost": "0",  # this value is from event settings. so set it to 0 by default so far
            'allowcancellations': allow_cancellations,
            'cancellationcutoff': str(int(cancellation_cutoff_number) * int(cancellation_cutoff_timeunit)),
            "timecreated": str(int(time.time())),
            "timemodified": str(int(time.time())),
            "usermodified": "",  # dont know user, leave blank
            "selfapproval": "0",  # this value is from event settings. Check what will happen if after loading backup to Totara change this value in settings in Totara, will it affect generated backup and session created in Totara?
            'mincapacity': str(min_capacity),
            'cutoff': str(int(send_capacity_email_cutoff_number) * int(send_capacity_email_cutoff_timeunit)),
            'sendcapacityemail': str(int(send_capacity_email)),
            # this value is from event settings. so set it to 0 by default so far
            'registrationtimestart': "0",
            # this value is from event settings. so set it to 0 by default so far
            'registrationtimefinish': "0",
            'cancelledstatus': "0",
            'session_roles': None,  # TODO add value from backup uploaded by the user in the fufure
            'custom_fields': {
                "custom_field": all_custom_fields
                },
            # TODO add value from backup uploaded by the user in the fufure
            'sessioncancel_fields': None,
            'signups': None,  
            "sessions_dates": {
                "sessions_date": {
                    "@id": "",
                    "sessiontimezone": "99",  # TODO do we need timezone or Totara add it automatically?
                    "timestart": str(start),
                    "timefinish": str(finish),
                    "assets": None,
                }
            }
        }
        if room:
            session["sessions_dates"]["sessions_date"]["room"] = room

        sessions.append(session)
    return sessions

# #DELETE this function
# def strDatesToDatetimeList(dates):
#     if isinstance(dates, str):
#         dates = dates.replace(' ','').split(",")
#         dates = sorted([datetime.strptime(date, '%d/%m/%Y') for date in dates])
#         return dates



def count_generated_events():
    all_sessions = sum(getFromJsonFile("sessions"),[])
    return len(all_sessions)


def copyDefaultToUserFolder():
    seminarFolder = getSeminarFolder(session["userID"])
    if path.exists(seminarFolder) == False:
        shutil.copytree(UPLOAD_FOLDER + "default/seminar/", seminarFolder)
    elif len(os.listdir(seminarFolder) ) == 0:
        shutil.rmtree(seminarFolder)
        shutil.copytree(UPLOAD_FOLDER + "default/seminar/", seminarFolder)
        
    return True


def appendEventsToXml():
    facetoface_dict = readXml()
    generated_sessions = sum(getFromJsonFile("sessions"),[])# sum is required to merge multiple sets of generated events into one set to ensure each session is properly printed in <sessions> xml tag
    try:
        facetoface_dict["activity"]["facetoface"]["sessions"]["session"] =  generated_sessions
    except:
        facetoface_dict["activity"]["facetoface"]["sessions"] = {"session": generated_sessions}
    return facetoface_dict

class Room:
    def __init__(self, room_id, name, description, timecreated, capacity, location, building, allowconflicts, user_id, isDefault=0, id=''):
        self.id = id
        self.room_id = room_id
        self.name = name
        self.description = description
        self.timecreated = timecreated
        self.capacity = capacity
        self.location = location
        self.building = building
        self.allowconflicts = allowconflicts
        self.isDefault = isDefault
        self.user_id = user_id

    def get_room(self):
        room = {
                "@id": self.room.id,
                "name": self.room.name,
                "description": self.room.description,
                "capacity": self.room.capacity,
                "allowconflicts": "0",
                "custom": "0",
                "hidden": "0",
                "usercreated": "$@NULL@$",
                "usermodified": "$@NULL@$",
                            "timecreated": "",
                            "timemodified": "",
                            "room_fields": {
                                "room_field": [
                                    {
                                        "@id": "",
                                        "field_name": "building",
                                        "field_type": "text",
                                        "field_data": self.room.building,
                                        "paramdatavalue": "$@NULL@$",
                                    },
                                    {
                                        "@id": "",
                                        "field_name": "location",
                                        "field_type": "location",
                                        "field_data": '{"address":"' + self.room.location + '","size":"medium","view":"map","display":"address","zoom":12,"location":{"latitude":"0","longitude":"0"}}',
                                        "paramdatavalue": "$@NULL@$",
                                    },
                                ]
                            },
            }
        return room

class CustomField:
    def __init__(self, field_id, field_name, field_type, field_data, paramdatavalue, user_id, isDefault, id=''):
        self.id = id
        self.field_id = field_id
        self.field_name = field_name
        self.field_type = field_type
        self.field_data = field_data
        self.paramdatavalue = paramdatavalue
        self.isDefault = isDefault
        self.user_id = user_id

    def get_field(self):
        field = {
                '@id': self.field_id,
                'field_name': self.field_name,
                'field_type': self.field_type,
                'field_data': self.field_data,
                'paramdatavalue': self.paramdatavalue,
                }
        return field

class Session:
    def __init__(self, id, sessiontimezone, timestart, timefinish, assets):
        self.id =id
        self.sessiontimezone=sessiontimezone
        self.timestart = timestart
        self.timefinish = timefinish
        self.assets = assets # make None if empty

    def __str__(self):
        date = {
                "@id": self.id,
                "sessiontimezone": self.timestart,  
                "timestart": str(self.timestart),
                "timefinish": str(self.timefinish),
                "assets": self.assets,
                }
        return date

class Event:
    def __init__(self, id, capacity, allowoverbook, details, normalcost, allowcancellations, cancellationcutoff, timecreated, timemodified, mincapacity, cutoff, sendcapacityemail, sessiontimezone, usermodified, selfapproval, waitlisteveryone, discountcost, registrationtimestart, registrationtimefinish,cancelledstatus):
        self.id=id
        self.capacity = capacity
        self.allowoverbook = allowoverbook
        self.waitlisteveryone = waitlisteveryone
        self.details=details
        self.normalcost = normalcost
        self.discountcost = discountcost
        self.allowcancellations = allowcancellations
        self.cancellationcutoff = cancellationcutoff # str(int(self.cancellation_cutoff_number) * int(self.cancellation_cutoff_timeunit))
        self.timecreated = timecreated
        self.timemodified = timemodified
        self.usermodified = usermodified
        self.selfapproval = selfapproval
        self.mincapacity = mincapacity
        self.cutoff = cutoff # str(int(self.send_capacity_email_cutoff_number) * int(self.send_capacity_email_cutoff_timeunit))
        self.sendcapacityemail = sendcapacityemail
        self.registrationtimestart = registrationtimestart
        self.registrationtimefinish = registrationtimefinish
        self.cancelledstatus = cancelledstatus
        self.session_roles = []
        self.custom_fields = []
        self.sessioncancel_fields = []
        self.signups = []
        self.sessiontimezone = sessiontimezone
        self.sessions_dates = []

    def add_custom_field(self, field):
        self.custom_fields.append(field)

    def get_event(self):

        if len(self.session_roles) == 0:
            session_roles = None
        if len(self.ssessioncancel_fieldsession_roles) == 0:
            sessioncancel_fields = None
        if len(self.signups) == 0:
            signups = None

        session = {
            '@id': "",
            'capacity': str(self.capacity),
            'allowoverbook': str(int(self.allowoverbook)),
            'waitlisteveryone': self.waitlisteveryone,
            'details': self.details,
            'normalcost': str(self.normalcost),
            "discountcost": self.discountcost,  # this value is from event settings. so set it to 0 by default so far
            'allowcancellations': self.allowcancellations,
            'cancellationcutoff': self.cancellationcutoff,
            "timecreated": str(int(time.time())),
            "timemodified": str(int(time.time())),
            "usermodified": self.usermodified,  # dont know user, leave blank
            "selfapproval": self.selfapproval,  # this value is from event settings. Check what will happen if after loading backup to Totara change this value in settings in Totara, will it affect generated backup and session created in Totara?
            'mincapacity': str(self.mincapacity),
            'cutoff': self.cutoff,
            'sendcapacityemail': str(int(self.sendcapacityemail)),
            # this value is from event settings. so set it to 0 by default so far
            'registrationtimestart': self.registrationtimestart,
            # this value is from event settings. so set it to 0 by default so far
            'registrationtimefinish': self.registrationtimefinish,
            'cancelledstatus': self.cancelledstatus,
            'session_roles': session_roles,  
            'custom_fields': {
                "custom_field": self.custom_fields
                },
            'sessioncancel_fields': sessioncancel_fields,
            'signups': signups,  
            "sessions_dates": {
                "sessions_date": self.sessions_dates
            }
        }
        return session

#TODO - Is it helpful somehow to have Recurrence as class or just e method is fine?
class Recurrence:
    def __init__(self, datestart, datefinish,frequency, occurrence_number, days_of_week, interval):
        self.datestart = datestart
        self.datefinish = datefinish
        self.frequency = frequency
        self.occurrence_number = occurrence_number
        self.days_of_week = days_of_week
        self.interval = interval
        self.__dates = []

    @property
    def dates(self):

        recurrence_data = []

        if self.frequency == "WEEKLY":
            self.occurrence_number = ""

        days_of_week = [self.occurrence_number + day for day in self.days_of_week]

        if self.frequency:
            recurrence_data.append("FREQ="+self.frequency)

        if days_of_week:
            recurrence_data.append(f"BYDAY={ ','.join(days_of_week) }")

        if self.interval:
            recurrence_data.append(f"INTERVAL={ self.interval }")

        if self.datefinish:
            recurrence_data.append(f"UNTIL={ self.datefinish }")

        recurrance_data_string = f"DTSTART:{ self.datestart } RRULE:{ ';'.join(recurrence_data[0:]) }"

        self.__dates = list(rrulestr(recurrance_data_string))

        return self.__dates

#TODO how to move this into the controller or add this code into the route (it will make route code much longer)?
def generate_recurring_dates(datestart, datefinish,frequency, occurrence_number, days_of_week, interval):
    recurance_data = []
    # String builder - https://jakubroztocil.github.io/rrule/
    occurrence_number = occurrence_number
    if frequency == "WEEKLY":
        occurrence_number = ""

    days_of_week = [occurrence_number + day for day in days_of_week]


    if frequency:
        recurance_data.append("FREQ="+frequency)

    if days_of_week:
        recurance_data.append(f"BYDAY={ ','.join(days_of_week) }")

    if interval:
        recurance_data.append(f"INTERVAL={ interval }")

    if datefinish:
        recurance_data.append(f"UNTIL={ datefinish }")

    recurrance_data_string = f"DTSTART:{ datestart } RRULE:{ ';'.join(recurance_data[0:]) }"
    dates = list(rrulestr(recurrance_data_string))
    return dates



class User:
    def __init__(self, id="", created=None, lastlogin=None, firstname=None, lastname=None, email=None, password=None, company=None, super_user_id=None, timezone=None):
        self.id = id
        self.firstname = firstname
        self.lastname = lastname
        self.email = email
        self.password = password
        self.company = company
        self.super_user_id = super_user_id
        self.created = created
        self.lastlogin = lastlogin
        self.__timezone = timezone
        self.__root_folder = UPLOAD_FOLDER + self.id
        self.__rooms = []
        self.__custom_fields = []
        
        
        self.update_lastlogin()

    #TODO is this a right way to do? Tried to ave just in a session but looks like g.user creates a new object on every page so data is not transered between pages. Is there a way to transfer object between routes?
    @property
    def event_sets(self):
        file_name = self.root_folder+"/events.json"
        if path.exists(file_name):
            data = open(file_name, "rb").read()
            sessions = json.loads(data)
        else:
            sessions = []
        
        return sessions

    @event_sets.setter
    def event_sets(self, value):
        file_name = self.root_folder+ "/events.json"            
        with open(file_name, 'w') as file:
            toJson = json.dumps(value)
            file.write(toJson)

    @property
    def root_folder(self):
        return self.__root_folder

    @root_folder.setter
    def root_folder(self, value):
        self.__root_folder = value

    @property
    def seminar_folder(self):
        return self.root_folder + '/seminar/'

    @property
    def activity_folder(self):
        return self.seminar_folder + 'activities/'

    @property
    def facetoface_xml(self):
        subfolders = [f.path for f in os.scandir(self.activity_folder) if f.is_dir()]
        for folder in list(subfolders):
            if "facetoface" in folder:
                return folder+"/facetoface.xml"

    @property
    def timezone(self):
        return self.__timezone
    
    @timezone.setter
    def timezone(self, value):
        db.update_timezone(id=self.id, timezone=value)

    def update_lastlogin(self):
        db.update_lastlogin(self.id)

    def add_room(self, room):
        db.create_room(
            room_id=room.room_id,
            name=room.name, 
            description=room.description, 
            capacity=room.capacity, 
            timecreated=room.timecreated, 
            building=room.building, 
            location=room.location, 
            allowconflicts=room.allowconflicts, 
            user_id=room.user_id, 
            isDefault=room.isDefault
            )
    
    @property
    def rooms(self):
        rooms = db.get_user_rooms(user_id=self.id)
        for room in rooms:
            room_obj = Room(
                            room_id = room['id'],
                            name=room['name'],
                            description=room['description'],
                            timecreated=room['timecreated'],
                            capacity=room['capacity'],
                            location=room['location'],
                            building=room['building'],
                            allowconflicts=room['allowconflicts'],
                            user_id = self.id,
                            isDefault = 0
                        )
            self.__rooms.append(room_obj)
        return self.__rooms
    
    @rooms.setter
    def rooms(self, list):
        self.__rooms = list


    def delete_rooms(self):
        self.rooms = []
        db.delete_user_rooms(user_id=self.id)

    @property
    def custom_fields(self):
        custom_fields = db.get_user_custom_fields(user_id=self.id)
        for field in custom_fields:
            field_obj = CustomField(
                field_id = field['field_id'],
                field_name = field['name'],
                field_type= field['type'],
                field_data = field['data'],
                paramdatavalue= field['paramdatavalue'],
                user_id = field['user_id'],
                isDefault = field['isDefault']
             )
            self.__custom_fields.append(field_obj)
        return self.__custom_fields
    
    @custom_fields.setter
    def custom_fields(self, list):
        self.__custom_fields = list

    def add_custom_field(self, field):
        db.create_custom_field(
            field_id = field.field_id,
            name = field.field_name,
            type = field.field_type,
            data = field.field_data, 
            paramdatavalue = field.paramdatavalue,
            isDefault = field.isDefault,
            user_id = self.id
            )

    def delete_custom_fields(self):
        self.__custom_fields = []
        db.delete_user_custom_fields(user_id=self.id)

class Controller:
        
    def new_user(self, user_id, firstname="", lastname="", email="", password="",super_user_id="", company="", timezone="" ):
        db.create_user(
                id = user_id,
                firstname = firstname,
                lastname = lastname,
                email = email,
                password = password,
                super_user_id = super_user_id,
                company = company,
                created = int(time.time()),
                lastlogin = int(time.time()),
                timezone = timezone
            )

    def get_user_details(self, user_id):
        user_data = db.get_user(user_id)
        user = None
        if user_data:
            user = User(
                id = user_data['id'],
                firstname = user_data['firstname'],
                lastname = user_data['lastname'],
                email = user_data['email'],
                password = user_data['password'],
                super_user_id = user_data['super_user_id'],
                company = user_data['company'],
                created = user_data['created'],
                lastlogin = user_data['lastlogin'],
                timezone=user_data['timezone']
            )
            
        return user

    # def generate_events(self, ):
    #     recurrance = Recurrance(
    #         datestart, datefinish,frequency, occurrence_number, days_of_week, interval
    #     )


    

