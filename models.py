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
    if "facetoface" in file.filename:
        return True

def uploadBackup(file):
    seminarFolder = getSeminarFolder(session["userID"])
    if os.path.exists(seminarFolder):
        shutil.rmtree(seminarFolder)
    
    filename = secure_filename(file.filename)
    Path(seminarFolder).mkdir(parents=True, exist_ok=True)
    file.save(os.path.join(seminarFolder, filename))
        

def unzipBackup(file):
    seminarFolder = getSeminarFolder(session["userID"])
    mbz_filepath = seminarFolder+file.filename
    fileinfo = magic.from_file(mbz_filepath)
    fullpath_to_unzip_dir = seminarFolder

    if 'Zip archive data' in fileinfo:
        with zipfile.ZipFile(mbz_filepath, 'r') as myzip:
            myzip.extractall(fullpath_to_unzip_dir)
    elif 'gzip compressed data' in fileinfo:
        tar = tarfile.open(mbz_filepath)
        tar.extractall(path=fullpath_to_unzip_dir)
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


def convert_xml_to_dictionary(xml_attribs=True):
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