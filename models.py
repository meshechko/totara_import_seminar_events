import os
import shutil
from flask import session
from werkzeug.utils import secure_filename
from pathlib import Path
import zipfile
import tarfile
import magic
import json
from dateutil.rrule import rrulestr
from datetime import datetime
import os.path
from os import path
import time
import db

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads/')
DEFAULT_SEMINAR_FOLDER = UPLOAD_FOLDER + 'default/seminar/'
DEFAULT_FACETOFACE_XML = DEFAULT_SEMINAR_FOLDER + 'activities/facetoface_14350/facetoface.xml'
GENERATED_ZIP_BACKUP_FILE_NAME = "backup-totara-activity-facetoface.mbz"


class Room:
    def __init__(self, room_id, name, description, timecreated, capacity, location, building, allowconflicts, user_id, id='',isDefault=0):
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

    def to_dict(self):
        room = {
                "@id": self.room_id,
                "name": self.name,
                "description": self.description,
                "capacity": self.capacity,
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
                                        "field_data": self.building,
                                        "paramdatavalue": "$@NULL@$",
                                    },
                                    {
                                        "@id": "",
                                        "field_name": "location",
                                        "field_type": "location",
                                        "field_data": '{"address":"' + self.location + '","size":"medium","view":"map","display":"address","zoom":12,"location":{"latitude":"0","longitude":"0"}}',
                                        "paramdatavalue": "$@NULL@$",
                                    },
                                ]
                            },
            }
        return room


class CustomField:
    def __init__(self, field_id, field_name, field_type, field_data, user_id='', isDefault='', id='', paramdatavalue='$@NULL@$'):
        self.id = id
        self.field_id = field_id
        self.field_name = field_name
        self.field_type = field_type
        self.field_data = field_data
        self.paramdatavalue = paramdatavalue
        self.isDefault = isDefault
        self.user_id = user_id

    def to_dict(self):
        field = {
                '@id': self.field_id,
                'field_name': self.field_name,
                'field_type': self.field_type,
                'field_data': self.field_data,
                'paramdatavalue': self.paramdatavalue,
                }
        return field


class Session:
    def __init__(self, timestart, timefinish, room, assets = None, id = '', sessiontimezone = '99'):
        self.id =id
        self.sessiontimezone=sessiontimezone
        self.timestart = timestart
        self.timefinish = timefinish
        self.assets = assets
        self.room = room

    def to_dict(self):
        date = {
                '@id': self.id,
                'sessiontimezone': self.sessiontimezone,  
                'timestart': str(self.timestart),
                'timefinish': str(self.timefinish),
                'assets': self.assets,
                }

        if self.room:
            date['room'] = self.room.to_dict()

        return date


class Event:
    def __init__(self, id, capacity, allowoverbook, details, normalcost, allowcancellations, cancellationcutoff, timecreated, timemodified, mincapacity, cutoff, sendcapacityemail, usermodified, selfapproval, waitlisteveryone, discountcost, registrationtimestart, registrationtimefinish,cancelledstatus):
        self.id=id
        self.capacity = capacity
        self.allowoverbook = allowoverbook
        self.waitlisteveryone = waitlisteveryone
        self.details=details
        self.normalcost = normalcost
        self.discountcost = discountcost
        self.allowcancellations = allowcancellations
        self.cancellationcutoff = cancellationcutoff 
        self.timecreated = timecreated
        self.timemodified = timemodified
        self.usermodified = usermodified
        self.selfapproval = selfapproval
        self.mincapacity = mincapacity
        self.cutoff = cutoff 
        self.sendcapacityemail = sendcapacityemail
        self.registrationtimestart = registrationtimestart
        self.registrationtimefinish = registrationtimefinish
        self.cancelledstatus = cancelledstatus
        self.__custom_fields = []
        self.__sessions_dates = []

    def add_custom_field(self, field):
        if len(self.__custom_fields) == 0:
            self.__custom_fields = field.to_dict()

        elif isinstance(self.__custom_fields, dict):
            first_field = self.__custom_fields
            self.__custom_fields = []
            self.__custom_fields.append(first_field)
            self.__custom_fields.append(field.to_dict())

        else:
            self.__custom_fields.append(field.to_dict())
        
    
    @property
    def custom_fields(self):
        return self.__custom_fields

    def add_session(self, session):
        if len(self.__sessions_dates) == 0: # TODO try if xmlparser can recognise a list with a single dict?
            self.__sessions_dates = session.to_dict()

        elif isinstance(self.__sessions_dates, dict):
            first_session = self.__sessions_dates
            self.__sessions_dates = []
            self.__sessions_dates.append(first_session)
            self.__sessions_dates.append(session)

        else:
            self.__sessions_dates.append(session.to_dict())


    def to_dict(self):
        event = {
            '@id': "",
            'capacity': str(self.capacity),
            'allowoverbook': str(int(self.allowoverbook)),
            'waitlisteveryone': '0',
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
            'session_roles': None,  
            'custom_fields': None,
            'sessioncancel_fields': None,
            'signups': None,  
            "sessions_dates": {
                "sessions_date": self.__sessions_dates
            }
        }
        
        if len(self.__custom_fields) > 0:
            event['custom_fields'] = {'custom_field': self.__custom_fields}

        return event


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
        self.__event_sets = []
        self.__root_folder = UPLOAD_FOLDER + self.id + '/'
        self.__events_file = self.root_folder + "events.json"
        self.__rooms = []
        self.__custom_fields = []
        self.update_lastlogin()

    def get_sets_data(self):
        sets = self.event_sets
        new_sets = []
        for set in sets:
            set_data = []
            for event in set:
                
                custom_fields_data = []
                custom_fields_wrapper = event['custom_fields']
                if custom_fields_wrapper:
                    custom_fields = custom_fields_wrapper['custom_field']
                    if custom_fields:
                        if isinstance(custom_fields, list): 
                            for field in custom_fields:
                                custom_fields_data.append(f"{field['field_name']} : {field['field_data']}")
                        else:
                            custom_fields_data.append(f"{custom_fields['field_name']} : {custom_fields['field_data']}")
                
                try:
                    room =  event['sessions_dates']['sessions_date']['room']['name']
                except:
                    room = ''

                event = {  
                'index' :  set.index(event),
                'custom_fields': "<br>". join(custom_fields_data),
                'capacity' : event['capacity'],
                'details' : event['details'],
                'date' : datetime.fromtimestamp(int(event['sessions_dates']['sessions_date']['timestart'])).strftime('%A, %d %B %Y'),
                'time' : datetime.fromtimestamp(int(event['sessions_dates']['sessions_date']['timestart'])).strftime('%H:%M') + ' - ' + datetime.fromtimestamp(int(event['sessions_dates']['sessions_date']['timefinish'])).strftime('%H:%M'),
                'room' : room,
                }
                set_data.append(event)

            new_data = {
                'index' : sets.index(set),
                'data' : set_data
            }
            new_sets.append(new_data)
        return new_sets
    #TODO is this a right way to do? Tried to ave just in a session but looks like g.user creates a new object on every page so data is not transered between pages. Is there a way to transfer object between routes?

    @property
    def events_file(self):
        return self.__events_file

    @property
    def event_sets(self):
        file_name = self.root_folder+"events.json"
        if path.exists(file_name):
            data = open(file_name, "rb").read()
            self.__event_sets = json.loads(data)
        else:
            self.__event_sets = []
        
        return self.__event_sets

    @event_sets.setter
    def event_sets(self, value):

        Path(self.root_folder).mkdir(parents=True, exist_ok=True)

        file_name = self.events_file            
        with open(file_name, 'w') as file:
            toJson = json.dumps(value)
            file.write(toJson)

    def count_events(self):
        return len(sum(self.event_sets,[]))
    
    def get_all_events(self):
        return sum(self.event_sets,[])
    
    def count_event_sets(self):
        # print('self.__event_sets')
        # print(self.__event_sets)
        # print('self.event_sets')
        # print(self.event_sets)
        return len(self.__event_sets) #TODO why self.__event_sets shows 1 when first event added but is use self.event_sets shows 0?

    @property
    def root_folder(self):
        return self.__root_folder

    @root_folder.setter
    def root_folder(self, value):
        self.__root_folder = value

    @property
    def seminar_folder(self):
        return self.root_folder + 'seminar/'

    @property
    def activity_folder(self):
        return self.seminar_folder + 'activities/'

    @property
    def facetoface_xml(self):
        subfolders = [f.path for f in os.scandir(self.activity_folder) if f.is_dir()]
        for folder in list(subfolders):
            if "facetoface" in folder:
                return folder+ '/' + 'facetoface.xml'

    @property
    def timezone(self):
        user_data = db.get_user(id=self.id)
        timezone = user_data['timezone']
        self.__timezone = timezone
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
                            id = room['id'],
                            room_id = room['room_id'],
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

#TODO - Is it helpful somehow to have Recurrence as class or just e method in the controller?
class Recurrence:
    def __init__(self, datestart='', datefinish='',frequency='', occurrence_number='', days_of_week='', interval=''):
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
        if len(recurrence_data) > 0:
            self.__dates = list(rrulestr(recurrance_data_string))

        return self.__dates


    @dates.setter
    def dates(self, value):
        self.__dates = value

    def count(self):
        return len(self.__dates)

#TODO does this controller make any sense? Essentially it is just a bunch of helper functions?
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


    def generate_recurring_events(
        self,
        user, 
        recurring_dates, 
        custom_fields, 
        details, 
        timestart, 
        timefinish, 
        room_id, 
        capacity,  
        allow_overbook, 
        allow_cancellations, 
        cancellation_cutoff_number, 
        cancellation_cutoff_timeunit, 
        min_capacity, 
        send_capacity_email, 
        send_capacity_email_cutoff_number, 
        send_capacity_email_cutoff_timeunit, 
        normal_cost):

        events = []
        
        if room_id != None:
            selected_room = next((item for item in user.rooms if item.room_id == room_id), None)
        else:
            selected_room = None


        for date in recurring_dates:
            event = Event(
                        id = '',
                        capacity = str(capacity),
                        allowoverbook = str(int(allow_overbook)),
                        details = details,
                        normalcost = str(normal_cost),
                        allowcancellations = allow_cancellations,
                        cancellationcutoff = str(int(cancellation_cutoff_number) * int(cancellation_cutoff_timeunit)),
                        timecreated = str(int(time.time())),
                        timemodified = str(int(time.time())),
                        mincapacity = str(min_capacity),
                        cutoff = str(int(send_capacity_email_cutoff_number) * int(send_capacity_email_cutoff_timeunit)),
                        sendcapacityemail = str(int(send_capacity_email)),
                        # TODO add the below values to the form if needed later on
                        usermodified = '', 
                        selfapproval = '0',
                        waitlisteveryone = '0',
                        discountcost = '0',
                        registrationtimestart = '0',
                        registrationtimefinish = '0',
                        cancelledstatus = '0'
                    )   

            
            if len(custom_fields) > 0:
                for field in custom_fields:
                    event.add_custom_field(field)

            start = f'{ str(date.date()) } { timestart }'
            start = int(datetime.strptime(start, '%Y-%m-%d %H:%M').timestamp())
            finish = f'{ str(date.date()) } { timefinish }'
            finish = int(datetime.strptime(finish, '%Y-%m-%d %H:%M').timestamp())

            session = Session(
                timestart = start, 
                timefinish = finish, 
                room = selected_room
            )
            event.add_session(session)
      
            events.append(event.to_dict())
        return events


    def unzip_backup(self, file, folder):

        # check if diectory alreay exist and overwrite its content
        if os.path.exists(folder):
            shutil.rmtree(folder)

        filename = secure_filename(file.filename) #get uploaded file name

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


    def zip_backup(self, root_folder, seminar_folder):
        with zipfile.ZipFile(root_folder + GENERATED_ZIP_BACKUP_FILE_NAME, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            base_path = os.path.normpath(seminar_folder)
            for dirpath, dirnames, filenames in os.walk(seminar_folder):
                for name in sorted(dirnames):
                    path = os.path.normpath(os.path.join(dirpath, name))
                    zf.write(path, os.path.relpath(path, base_path))
                for name in filenames:
                    path = os.path.normpath(os.path.join(dirpath, name))
                    if os.path.isfile(path):
                        zf.write(path, os.path.relpath(path, base_path))
        # urllib.request.urlretrieve(urlparse(str(userFolder + GENERATED_ZIP_BACKUP_FILE_NAME)))
