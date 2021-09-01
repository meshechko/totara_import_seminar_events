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

#done
def getSeminarFolder(userID):
    return UPLOAD_FOLDER + userID + "/seminar/"

# done
def getUserFolder(userID):
    return UPLOAD_FOLDER + userID

# COMMON


def fileAllowed(filename, allowedExtension):
    if Path(filename).suffix == allowedExtension:
        return True

# ROOMS upload


requiredHeaders = ['id', 'name', 'description', 'timecreated',
                   'capacity', 'location', 'building', 'allowconflicts']

#done
def createFolder(folder):
    Path(folder).mkdir(parents=True, exist_ok=True)

# #done
# def covertCsvToList(file):
#     decoded_file = file.read().decode('utf-8').splitlines()
#     reader = csv.DictReader(decoded_file)
#     return list(reader)

# #done
# def validateCsvHeaders(rooms_list):
#     roomsFileHeaders = list(rooms_list[0].keys())
#     difference = [i for i in requiredHeaders +
#                   roomsFileHeaders if i not in requiredHeaders or i not in roomsFileHeaders]
#     if len(difference) == 0:
#         return True


def saveToJsonFile(list, file_name):
    userFolder = getUserFolder(session["userID"])
    # if os.path.isdir(userFolder) == False: # done
    #     createFolder(userFolder) #done
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

def validateBackup(file):
    filename = secure_filename(file.filename)
    if "facetoface" in filename and fileAllowed(filename, ".mbz"):
        return True


def unzipBackup(file):
    seminarFolder = getSeminarFolder(session["userID"])

    # check if diectory alreay exist
    if os.path.exists(seminarFolder):
        shutil.rmtree(seminarFolder)

    # TODO check why this one is not under ELSE?
    filename = secure_filename(file.filename)
    createFolder(seminarFolder)

    # upload file in to user folder
    file.save(os.path.join(seminarFolder, filename))

    mbz_filepath = seminarFolder+filename
    fileinfo = magic.from_file(mbz_filepath)

    if 'Zip archive data' in fileinfo:
        with zipfile.ZipFile(mbz_filepath, 'r') as myzip:
            myzip.extractall(seminarFolder)
    elif 'gzip compressed data' in fileinfo:
        tar = tarfile.open(mbz_filepath)
        tar.extractall(path=seminarFolder)
        tar.close()
    else:
        return False
    os.remove(mbz_filepath)
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

def generateRecurringDates(datestart, datefinish,frequency, occurrence_number, days_of_week, interval):
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
                'field_name': custom_field["field_name"],
                'field_type': custom_field["field_type"],
                'field_data': custom_field["field_data"],
                'paramdatavalue': '$@NULL@$',
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


def strDatesToDatetimeList(dates):
    if isinstance(dates, str):
        dates = dates.replace(' ','').split(",")
        dates = sorted([datetime.strptime(date, '%d/%m/%Y') for date in dates])
        return dates

# import functools

# def haskey(d, path):
#     try:
#         functools.reduce(lambda x, y: x[y], path.split("."), d)
#         return True
#     except:
#         return False

#  from https://stackoverflow.com/a/65782539


def countGeneratedEvents():
    all_sessions = sum(getFromJsonFile("sessions"),[])
    return len(all_sessions)


def getCustomFieldsFromXML(file):
    custom_fields = []

    try:
        sessions = file["activity"]["facetoface"]["sessions"]["session"]
        # need to check if it is a lis or not because if there's only one event (session) then xmltodict makes it as a dict, if there are 2 and more then xmltodict makes it a list of dict's
        if isinstance(sessions, list):

            custom_fields = sessions[0]["custom_fields"]["custom_field"]
        else:

            custom_fields = sessions["custom_fields"]["custom_field"]
    except:
        custom_fields = []

    if isinstance(custom_fields, list) == False:
        custom_fields = [custom_fields]

    return custom_fields


def getSessionsFromXML(file):
    sessions = []
    try:
        sessions = file["activity"]["facetoface"]["sessions"]["session"]
        # need to check if it is a lis or not because if there's only one event (session) then xmltodict makes it as a dict, if there are 2 and more then xmltodict makes it a list of dict's
        if isinstance(sessions, list) == False:
            sessions = [sessions]
    except:
        sessions = []
    return sessions


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


class User:
    def __init__(self, id="", created=None, lastlogin=None, firstname=None, lastname=None, email=None, password=None, company=None, super_user_id=None, timezone=None, rooms = []):
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
        self.rooms = rooms
        self.update_lastlogin()


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
        return self.seminar_folder + '/activities/'

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
            room.id,
            room.name, 
            room.description, 
            room.capacity, 
            room.timecreated, 
            room.building, 
            room.location, 
            room.allowconflicts, 
            room.user_id, 
            room.isDefault)
        self.rooms.append(room)
    
    def delete_rooms(self):
        self.rooms = []
        db.delete_user_rooms(user_id=self.id)



class Room:
    def __init__(self, id, name, description, timecreated, capacity, location, building, allowconflicts, user_id, isDefault=0):
        self.id = id
        self.name = name
        self.description = description
        self.timecreated = timecreated
        self.capacity = capacity
        self.location = location
        self.building = building
        self.allowconflicts = allowconflicts
        self.isDefault = isDefault
        self.user_id = user_id


    def __str__(self):
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
                timezone=user_data['timezone'],
                rooms = db.get_user_rooms(user_id = user_data['id'])            
            )
            
        return user

    def create_user_id(self):
        letters = string.ascii_lowercase
        random_string = ''.join(random.choice(letters) for i in range(10))
        return random_string       

    

