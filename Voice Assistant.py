from __future__ import print_function

import datetime
import pickle
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import platform
import os
import time
import playsound
import speech_recognition as sr
from gtts import gTTS
import pytz
import subprocess

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
MONTHS = ["january", "february", "march", "april", "may", "june","july", "august", "september","october", "november", "december"]
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DAY_EXTENSIONS = ["rd", "th", "st", "nd"]

def speak(text):
    tts = gTTS(text=text, lang="en")
    filename = "vox.mp3"
    tts.save(filename)
    playsound.playsound(filename)

def get_audio():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        audio = r.listen(source)
        said = ""

        try:
            said = r.recognize_google(audio)
            print(said)
        except Exception as e:
            print("Exception" + str(e))

    return said

def authenticate_googleCalendar():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
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

    return service

def get_events(day, service):
    # Call the Calendar API
    date = datetime.datetime.combine(day, datetime.datetime.min.time())
    end = datetime.datetime.combine(day, datetime.datetime.max.time())
    utc = pytz.UTC
    date = date.astimezone(utc)
    end = end.astimezone(utc)
    events_result = service.events().list(calendarId = 'primary', timeMin = date.isoformat(),
                                        timeMax = end.isoformat(), singleEvents = True,
                                        orderBy = 'startTime').execute()
    events = events_result.get('items', [])

    if not events:
        speak('No upcoming events found.')
    else:
        speak(f"You have {len(events)} events on this day.")

    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(start, event['summary'])

        start_time = str(start.split("T")[1].split("-")[0])  # get the hour the event starts
        if int(start_time.split(":")[0]) < 12:  # if the event is in the morning
            start_time = start_time + "am"
        else:
            # converting 24-hour time format to 12 hour + |we need to allow the minute aspect to be functional instead of only hour|
            start_time = str(int(start_time.split(":")[0]) - 12)
            start_time = start_time + "pm"

        speak(event["summary"] + " at " + start_time)


def get_date(text):
    text = text.lower()
    # The following code makes it so that the user can't just request a date that already passed
    # because it wouldn't make sense to make a request to get a past event.
    # Instead, it allows the current date the user is making the request as well as the days following it.
    today = datetime.date.today()

    if text.count("today") > 0:
        return today

    day = -1
    day_of_week = -1
    month = -1
    year = today.year

    # If the user does not make a request to get their tasks for the current day,
    # we iterate through this for loop to find out which date they are talking about.
    for word in text.split():
        if word in MONTHS:
            month = MONTHS.index(word) + 1
        elif word in DAYS:
            day_of_week = DAYS.index(word)

        #If the word is simply a digit, make the voice assistant interpret the digit as
        #date with one of the following extensions: "rd", "th", "st", "nd"
        elif word.isdigit():
            day = int(word)
        else:
            for ext in DAY_EXTENSIONS:
                found = word.find(ext)
                # SlICING BY INDEX
                if found > 0:
                    try:
                        day = int(word[:found])
                    except:
                        pass

    if month < today.month and month != -1:
        # if the month mentioned is before the current month, set the year to the next
        year += 1

    if month == -1 and day != -1:  # if we didn't find a month, but we have a day
        if day < today.day:
            month = today.month + 1
        else:
            month = today.month

    # if we only found a date of the week
    if month == -1 and day == -1 and day_of_week != -1:
        current_day_of_week = today.weekday()
        # Find the difference between the two dates
        dif = day_of_week - current_day_of_week
        # So that we can start fresh every new week/every Monday
        if dif < 0:
            dif += 7
            if text.count("next") >= 1:
                dif += 7

        return today + datetime.timedelta(dif)
    # if the user doesn't provide a date in a correct format, they will get something like -1/-1/-1
    # in order to resolve that we do:
    if day != -1:
        return datetime.date(month=month, day=day, year=year)

def note(file_name, text):
    full_path = os.path.abspath(file_name)

    # Write text to the file
    with open(full_path, 'w') as file:
        file.write(text)

    # Open the file based on the platform
    if os.path.exists(full_path):
        if platform.system() == "Darwin":  # macOS
            subprocess.Popen(["open", full_path])
        else:
            print("Unsupported operating system")
    else:
        print(f"File not found: {full_path}")

# Example usage
# note("Note.txt", "Jonathan is the goat")


SERVICE = authenticate_googleCalendar()
print("Start speaking")
text = get_audio().lower()


CALENDAR_STRS = ["what do i have", "do i have", "am i busy", "what is happening"
                 "do I have any plans on", "do I have plans on", "am I free", "when is"]

for phrase in CALENDAR_STRS:
    # Allow Vox to interpret all texts, typically with upper case letters like I and the beginning letter of words
    if phrase in text.lower():
        date = get_date(text)
        if date:
            get_events(date, SERVICE)
        else:
            speak("Please Try Again")


NOTE_STRS = ["make a note", "write this down", "remember this", "type this", "take a note"]

for phrase in NOTE_STRS:
    if phrase in text:
        speak("What would you like me to write down? ")
        write_down = get_audio().lower()
        note("Note.txt", write_down)  # Provide both file name and text
        speak("I've made a note of that.")