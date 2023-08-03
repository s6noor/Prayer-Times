# Author: Sidrah Noor
# This code is the property of Sidrah Noor.
import requests
import os
import json
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = ['https://www.googleapis.com/auth/calendar']
ADDRESS = '<Insert address>' #insert address for the location for which you require prayer times
YEAR = '2021'
MONTH = '03'
CALENDAR_NAME = "Prayer"
TIMEZONE = "America/New_York" #to-do - automate the change between daylight savings versus not. Also, Timezone must follow IANA

class Prayer():
    def __init__(self, api_output, name, alternative_name=None):
        self.api = api_output
        self.name = name
        if alternative_name is not None: self.aname = alternative_name
        else: self.aname = None
        self.times = list()
        self.dates = list()
        self.events = [0]

    def get_dateTime(self, instance):
        date = f"{instance['date']['gregorian']['year']}-0{instance['date']['gregorian']['month']['number']}-{instance['date']['gregorian']['day']}"

        if self.aname is None:
            time = instance['timings'][self.name].replace(' (EST)','').replace(' (EDT)','')
        else:
            time = instance['timings'][self.aname].replace(' (EST)','').replace(' (EDT)','')

        endtime = datetime.strptime(time, '%H:%M')
        timechange = timedelta(seconds=60)
        endtime = endtime + timechange
        endtime = f'{date}T{endtime.time()}'
        return((f"{date}T{time}:00", endtime))

    def get_calendar_event_batch(self):
        for each_day in self.api['data']:
            self.events.append({
                'summary': self.name,
                'start': {
                    'dateTime': self.get_dateTime(each_day)[0],
                    'timeZone': TIMEZONE
                },
                'end': {
                    'dateTime': self.get_dateTime(each_day)[1],
                    'timeZone': TIMEZONE
                }
            })
        
        return self.events[1:]


# extract the prayer times
def get_prayer_times():

    # See https://aladhan.com/prayer-times-api#GetCalendarByAddress for information on using the api
    response = requests.get(f'http://api.aladhan.com/v1/calendarByAddress?address={ADDRESS}&month={MONTH}&year={YEAR}&method=2')
    #print(response.json())

    all_info = response.json()

    Fajr = Prayer(all_info, 'Fajr')
    #Sunrise = Prayer(all_info, 'Sunrise')
    Dhuhr = Prayer(all_info, 'Dhuhr')
    Asr = Prayer(all_info, 'Asr')
    Magrib = Prayer(all_info, 'Magrib', alternative_name='Maghrib')
    Isha = Prayer(all_info, 'Isha')

    prayers = [Fajr.get_calendar_event_batch(), 
                #Sunrise.get_calendar_event_batch(), 
                Dhuhr.get_calendar_event_batch(), 
                Asr.get_calendar_event_batch(), 
                Magrib.get_calendar_event_batch(), 
                Isha.get_calendar_event_batch()]

    return prayers


def add_events(calendar_service, all_event_parameters, calendar_id= 'primary'):
    for prayer in all_event_parameters:
        for item in prayer:
            #print(item)
            event = calendar_service.events().insert(calendarId= calendar_id, body=item).execute()
    print(f'{event} has been added successfully!')

def create_new_calendar(calendar_service):
    #this creates a calendar called Prayer in the specified time zone
    calendar = {
        "summary": CALENDAR_NAME,
        'timeZone': TIMEZONE
    }
    try:
        created_calendar = calendar_service.calendars().insert(body=calendar).execute()
        return created_calendar['id']
    except:
        print("An error occured") #ideally you want to print the exact nature of the error using googleapi for http error. Future to-do

#Source: ChatGPT; doing some error handling here to make sure that new calendars are only created if one doesnt already exist.
def find_calendar_by_name(service, target_name):
    page_token = None
    while True:
        calendar_list = service.calendarList().list(pageToken=page_token).execute()
        for calendar in calendar_list.get('items', []):
            if calendar['summary'] == target_name:
                print(f'Found existing calendar with calendarId: {calendar["id"]}')
                return calendar['id']
        page_token = calendar_list.get('nextPageToken')
        if not page_token:
            break
    return None

def main():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)
    # Check if the calendar already exists
    prayer_calendar_id = find_calendar_by_name(service, CALENDAR_NAME)
    if not prayer_calendar_id:
        # If the calendar doesn't exist, create a new one
        prayer_calendar_id = create_new_calendar(service)
    add_events(service, get_prayer_times(), prayer_calendar_id)

main()
