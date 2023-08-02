import requests
import os
import json
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = ['https://www.googleapis.com/auth/calendar']
ADDRESS = '<Insert address>'
YEAR = '2021'
MONTH = '03'


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
                    'timeZone': 'EST'
                },
                'end': {
                    'dateTime': self.get_dateTime(each_day)[1],
                    'timeZone': 'EST'
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
    Sunrise = Prayer(all_info, 'Sunrise')
    Dhuhr = Prayer(all_info, 'Dhuhr')
    Asr = Prayer(all_info, 'Asr')
    Magrib = Prayer(all_info, 'Magrib', alternative_name='Maghrib')
    Isha = Prayer(all_info, 'Isha')

    prayers = [Fajr.get_calendar_event_batch(), 
                Sunrise.get_calendar_event_batch(), 
                Dhuhr.get_calendar_event_batch(), 
                Asr.get_calendar_event_batch(), 
                Magrib.get_calendar_event_batch(), 
                Isha.get_calendar_event_batch()]

    return prayers


def add_events(calendar_service, all_event_parameters):
    for prayer in all_event_parameters:
        for item in prayer:
            #print(item)
            event = calendar_service.events().insert(calendarId='primary', body=item).execute()
    print(f'{event} has been added successfully!')

def main():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
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

    add_events(service, get_prayer_times())

main()
