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
        return Ture

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

recurance_data = []

start = "20210902"
frequency = "WEEKLY"
days = []
inteval = "10"
end = "20220102"

if frequency:
  recurance_data.append("FREQ="+frequency)
  
if len(days) > 0:
  recurance_data.append("BYDAY="+','.join(days))

if inteval:
  recurance_data.append("INTERVAL="+inteval)
  
if end:
  recurance_data.append("UNTIL="+end)
  
recurrance_data_string = f"DTSTART:{start} RRULE:{ ';'.join(recurance_data[0:]) }"

events = list(rrulestr(recurrance_data_string))

for event in events:
    print(event.strftime("%m/%d/%Y"))
    
class Recurrence:
    def __init__(self):
        self.xmlData = {}
        self.generatedEvents = {}
    
    def getCustomFieldsFromXml(self):
        list_of_custom_fiels = []
        return list_of_custom_fiels
        
    def getEvents(self):
        list_of_events = []
        return list_of_events
    
    #TODO is this method required or just internal statement would work
    def setEvents(self):
        self.xmlData["add_path_to_events_dict_or_list"] = self.generatedEvents
        return True
        


        
