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
# CONFIG data

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads/')


def getSeminarFolder(userID):
    return UPLOAD_FOLDER + userID + "/seminar/"


def getUserFolder(userID):
    return UPLOAD_FOLDER + userID

# COMMON


def fileAllowed(filename, allowedExtension):
    if Path(filename).suffix == allowedExtension:
        return True

# ROOMS upload


requiredHeaders = ['id', 'name', 'description',
                   'capacity', 'location', 'building', 'published']


def createFolder(folder):
    Path(folder).mkdir(parents=True, exist_ok=True)


def covertCsvToList(file):
    decoded_file = file.read().decode('utf-8').splitlines()
    reader = csv.DictReader(decoded_file)
    return list(reader)


def validateCsvHeaders(rooms_list):
    roomsFileHeaders = list(rooms_list[0].keys())
    difference = [i for i in requiredHeaders +
                  roomsFileHeaders if i not in requiredHeaders or i not in roomsFileHeaders]
    if len(difference) == 0:
        return True


def getRooms():
    rooms = []
    userFile = getUserFolder(session["userID"])+"/rooms.json"

    if path.exists(userFile):
        rooms = open(userFile, "rb").read()
        rooms = json.loads(rooms)
    else:
        rooms = open((UPLOAD_FOLDER + "default/rooms.json"), "rb").read()
        rooms = json.loads(rooms)
    return rooms


def saveRooms(rooms_list):
    userFolder = getUserFolder(session["userID"])
    if os.path.isdir(userFolder) == False:
        createFolder(userFolder)
    with open(os.path.join(userFolder, "rooms.json"), 'w') as file:
        toJson = json.dumps(rooms_list)
        file.write(toJson)


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
        userActivitiesFolder = UPLOAD_FOLDER + "default/seminar/activities/"
    subfolders = [f.path for f in os.scandir(
        userActivitiesFolder) if f.is_dir()]
    for folder in list(subfolders):
        if "facetoface" in folder:
            return folder+"/facetoface.xml"


def readXml(xml_attribs=True):
    with open(getf2fxml(), "rb") as f:
        # my_dictionary = xmltodict.parse(f, xml_attribs=xml_attribs)
        return xmltodict.parse(f, dict_constructor=dict)


# RECURRANCE

# "DTSTART:20210902T090000 RRULE:FREQ=WEEKLY;COUNT=5;INTERVAL=10;UNTIL=20230102T090000"


def generate_recurring_sessions(custom_fields_data, details, timestart, timefinish, room, capacity, datestart, datefinish, frequency, occurrence_number, days_of_week, interval, allow_overbook, allow_cancellations, cancellation_cutoff_number, cancellation_cutoff_timeunit, min_capacity, send_capacity_email, send_capacity_email_cutoff_number, send_capacity_email_cutoff_timeunit, normal_cost):
    recurance_data = []

    sessions = []
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
    
    for date in dates:
        start = f"{ str(date.date()) } { timestart }"
        start = int(datetime.strptime(start, '%Y-%m-%d %H:%M').timestamp())
        finish = f"{ str(date.date()) } { timefinish }"
        finish = int(datetime.strptime(finish, '%Y-%m-%d %H:%M').timestamp())

        if not all_custom_fields:
            all_custom_fields = None
        
        session = {
            # 'id':
            'capacity': capacity,
            'allowoverbook': allow_overbook,
            # 'waitlisteveryone': 
            'details': details,
            'normalcost': normal_cost,
            "discountcost": "0", # this value is from event settings. so set it to 0 by default so far
            'allowcancellations': allow_cancellations,
            'cancellationcutoff': str(int(cancellation_cutoff_number) * int(cancellation_cutoff_timeunit)),
            "timecreated": str(int(time.time())),
            "timemodified": str(int(time.time())),
            "usermodified": "", # dont know user, leave blank
            "selfapproval": "0", # this value is from event settings. Check what will happen if after loading backup to Totara change this value in settings in Totara, will it affect generated backup and session created in Totara?
            'mincapacity': min_capacity,
            'cutoff':str(int(send_capacity_email_cutoff_number) * int(send_capacity_email_cutoff_timeunit)),
            'room': room, 
            'sendcapacityemail': send_capacity_email,
            'registrationtimestart': "0", # this value is from event settings. so set it to 0 by default so far
            'registrationtimefinish': "0", # this value is from event settings. so set it to 0 by default so far
            'cancelledstatus': "0",
            'session_roles': None, # TODO add value from backup uploaded by the user in the fufure
            'custom_fields': all_custom_fields,
            'sessioncancel_fields': None, # TODO add value from backup uploaded by the user in the fufure
            'signups': None, # TODO add value from backup uploaded by the user in the fufure
            "sessions_dates":{
                        "sessions_date": {
                            "@id": "",
                            "sessiontimezone": "99",
                            "timestart": "1633633200", #TODO convert exisitng values to UNIX
                            "timefinish": "1633662000",
                            "assets": None,
                        }
            },
            'date': date,
            'timestart': timestart,
            'timefinish': timefinish,
        }
        sessions.append(session)
    return sessions


def getCustomFieldsFromXML(file):
    custom_fields = []
    sessions = file["activity"]["facetoface"]["sessions"]
    try:
        # need to check if it is a lis or not because if there's only one event (session) then xmltodict makes it as a dict, if there are 2 and more then xmltodict makes it a list of dict's
        if isinstance(sessions, list): 
            custom_fields = sessions[0]["custom_fields"]["custom_field"]
        else:
            custom_fields = sessions["session"]["custom_fields"]["custom_field"]
    except:
        custom_fields = []
    return custom_fields


def copyDefaultToUserFolder():
    seminarFolder = getSeminarFolder(session["userID"])
    if path.exists(seminarFolder) == False:
        shutil.copytree(UPLOAD_FOLDER + "default/seminar/", seminarFolder)
    return True


def appendEventsToXml():
    facetoface_dict = readXml()
    if 'sessions' in session:
        facetoface_dict["activity"]["facetoface"]["sessions"] = session['sessions']
    return facetoface_dict


def convertGeneratedToXmlDict(session_data):
    room = ""
    if session_data["room"] != None:
        room = {
            "@id": "636",
            "name": None,
            "description": "<p>Marae for Tikanga Maori use only</p>",
            "capacity": "18",
            "allowconflicts": "0",
            "custom": "0",
            "hidden": "0",
            "usercreated": "$@NULL@$",
            "usermodified": "$@NULL@$",
                            "timecreated": "1478480518",
                            "timemodified": "1478480518",
                            "room_fields": {
                                "room_field": [
                                    {
                                        "@id": "582",
                                        "field_name": "building",
                                        "field_type": "text",
                                        "field_data": "Rehua Marae",
                                        "paramdatavalue": "$@NULL@$",
                                    },
                                    {
                                        "@id": "581",
                                        "field_name": "location",
                                        "field_type": "location",
                                        "field_data": '{"address":"79 Springfield Road, Edgeware","size":"medium","view":"map","display":"address","zoom":12,"location":{"latitude":"0","longitude":"0"}}',
                                        "paramdatavalue": "$@NULL@$",
                                    },
                                ]
                            },
        }

    session = {"@id": "",
               "capacity": session_data["capacity"],
               "allowoverbook": session_data["data"],
               "waitlisteveryone": session_data["allow_overbook"],
               "details": session_data["details"],
               "normalcost": session_data["normal_cost"],
               "discountcost": "0",
               "allowcancellations": session_data["allow_cancellations"],
               "cancellationcutoff": "ADD_DATA",
               "timecreated": "ADD_DATA-UNIXTIMESTAMP",
               "timemodified": "ADD_DATA-UNIXTIMESTAMP",
               "usermodified": "",
               "selfapproval": "0",
               "mincapacity": session_data["min_capacity"],
               "cutoff": "ADD_DATA",
               "sendcapacityemail": session_data["send_capacity_email"],
               "registrationtimestart": "0",
               "registrationtimefinish": "0",
               "cancelledstatus": "0",
               "session_roles": None,
               "custom_fields": {
                   "custom_field": session_data["custom_fields_data"]
               },
               "sessioncancel_fields": None,
               "signups": None,
               "sessions_dates": {
                   "sessions_date": {
                       "@id": "",
                       "sessiontimezone": "99",
                       "timestart": session_data["timestart"],
                       "timefinish": session_data["timefinish"],
                       "room": rooms,
                       "assets": None,
                   }
               }
               }

    return session
