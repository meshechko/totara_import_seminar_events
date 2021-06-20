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

from dateutil import rrule, parser, relativedelta
from dateutil.rrule import rrulestr
from datetime import datetime

#CONFIG data

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

requiredHeaders = ['id', 'name', 'description', 'capacity', 'location', 'building', 'published']

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
    userFolder = getUserFolder(session["userID"])
    rooms = open(userFolder+"/rooms.json", "rb").read()
    return json.loads(rooms)

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
    
    #TODO check why this one is not under ELSE?
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
    seminarFolder = getSeminarFolder(session["userID"])
    subfolders = [ f.path for f in os.scandir(seminarFolder+"activities/") if f.is_dir() ]
    for folder in list(subfolders):
        if "facetoface" in folder:
            return folder+"/facetoface.xml"


def readXml(xml_attribs=True):
    with open(getf2fxml(), "rb") as f:
        # my_dictionary = xmltodict.parse(f, xml_attribs=xml_attribs)
        return xmltodict.parse(f, dict_constructor=dict)


# RECURRANCE

# "DTSTART:20210902T090000 RRULE:FREQ=WEEKLY;COUNT=5;INTERVAL=10;UNTIL=20230102T090000"


    

def generate_events(custom_fiels_data, details, timestart, timefinish, room, capacity, datestart, datefinish, frequency, occurance_number, days_of_week, interval):
    recurance_data = []
    generated_events = []
    if frequency:
        recurance_data.append("FREQ="+frequency)

    if days_of_week:
        recurance_data.append(f"BYDAY={ ','.join(days_of_week) }")

    if interval:
        recurance_data.append(f"INTERVAL={ interval }")
    
    if datefinish:
        recurance_data.append(f"UNTIL={ datefinish }")

    if occurance_number and frequency == "MONTHLY":
        recurance_data.append(f"BYSETPOS={ occurance_number }")
    
    recurrance_data_string = f"DTSTART:{ datestart } RRULE:{ ';'.join(recurance_data[0:]) }"
    # print(recurrance_data_string)
    dates = list(rrulestr(recurrance_data_string))


    for date in dates:
        start = f"{ str(date.date()) } { timestart }"
        start = int(datetime.strptime(start, '%Y-%m-%d %H:%M').timestamp())
        finish = f"{ str(date.date()) } { timefinish }"
        finish = int(datetime.strptime(finish, '%Y-%m-%d %H:%M').timestamp())
        
        #TODO adjust custom fields
        # field = {
            #     "@id": "6892",
            #     "field_name": "Presenter",
            #     "field_type": "text",
            #     "field_data": "James Smith",
            #     "paramdatavalue": "$@NULL@$",
            # }

        generated_events.append({"@id": "",
                "capacity": capacity,
                "allowoverbook": "0",
                "waitlisteveryone": "0",
                "details": details,
                "normalcost": "0",
                "discountcost": "0",
                "allowcancellations": "1",
                "cancellationcutoff": "0",
                "timecreated": "1615156305",
                "timemodified": "1623841147",
                "usermodified": "19239",
                "selfapproval": "0",
                "mincapacity": "0",
                "cutoff": "0",
                "sendcapacityemail": "0",
                "registrationtimestart": "0",
                "registrationtimefinish": "0",
                "cancelledstatus": "0",
                "session_roles": None,
                "custom_fields": {
                    "custom_field": custom_fiels_data
                },
                "sessioncancel_fields": None,
                "signups": None,
                "sessions_dates": {
                    "sessions_date": {
                        "@id": "",
                        "sessiontimezone": "99",
                        "timestart": start,
                        "timefinish": finish,
                        "room": {
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
                        },
                        "assets": None,
                    }
                    }
       })

    return generated_events

class Recurrence:
    def __init__(self):
        self.xmlData = {}
        self.generatedSessions = {}
    
    def getCustomFields(self):
        list_of_custom_fiels = self.xmlData["activity"]["facetoface"]["sessions"]["session"][0]["custom_fields"]["custom_field"]
        return list_of_custom_fiels
        
    def getSessions(self):
        list_of_sessions = self.xmlData["activity"]["facetoface"]["sessions"]["session"]
        return list_of_sessions
    
    #TODO is this method required or just internal statement would work
    def setSessions(self):
        self.xmlData["activity"]["facetoface"]["sessions"]["session"] = self.generatedSessions
        return True
        


        
