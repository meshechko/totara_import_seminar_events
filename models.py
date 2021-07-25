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


requiredHeaders = ['id', 'name', 'description', 'timecreated',
                   'capacity', 'location', 'building', 'allowconflicts']


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

def saveToJsonFile(list, file_name):
    userFolder = getUserFolder(session["userID"])
    if os.path.isdir(userFolder) == False:
        createFolder(userFolder)
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
        list = open((UPLOAD_FOLDER + "default/"+file_name+".json"), "rb").read()
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
    print(recurrance_data_string)
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
        field_dict = {"custom_field":{
                '@id': '',
                'field_name': custom_field["field_name"],
                'field_type': custom_field["field_type"],
                'field_data': custom_field["field_data"],
                'paramdatavalue': '$@NULL@$',
            }
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
            'custom_fields': all_custom_fields,
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
        sessions = file["activity"]["facetoface"]["sessions"]
        # need to check if it is a lis or not because if there's only one event (session) then xmltodict makes it as a dict, if there are 2 and more then xmltodict makes it a list of dict's
        if isinstance(sessions, list):
            custom_fields = sessions[0]["custom_fields"]["custom_field"]
        else:
            custom_fields = sessions["session"]["custom_fields"]["custom_field"]
    except:
        custom_fields = []
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
    # print(f'len(os.listdir(seminarFolder) ) == 0: {len(os.listdir(seminarFolder) ) == 0}')
    if path.exists(seminarFolder) == False:
        shutil.copytree(UPLOAD_FOLDER + "default/seminar/", seminarFolder)
    elif len(os.listdir(seminarFolder) ) == 0:
        shutil.rmtree(seminarFolder)
        shutil.copytree(UPLOAD_FOLDER + "default/seminar/", seminarFolder)
        
    return True


def appendEventsToXml():
    facetoface_dict = readXml()
    #TODO currenty it doenst work if xml from backup doesnt have any events. Address this later
    facetoface_dict["activity"]["facetoface"]["sessions"]["session"] = sum(getFromJsonFile("sessions"),[]) # sum is required to merge multiple sets of generated events into one set to ensure each session is properly printed in <sessions> xml tag
    return facetoface_dict
