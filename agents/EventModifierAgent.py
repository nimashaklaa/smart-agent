# agents/calendar.py
"""
def calendar_agent():
    return "User's given dates are available."
"""
import os
import datetime
import pytz
import json
import dateparser
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

from config import llm  # Import the shared llm instance

def event_modifier_agent(query):

    # Google Calendar API Authentication
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    default_path = "./google_credentials/"
    SERVICE_ACCOUNT_FILE = default_path + "credentials.json"  # Ensure this file is uploaded

    def authenticate_google_calendar():
        creds = None
        if os.path.exists(default_path+"token.json"):
            creds = Credentials.from_authorized_user_file(default_path+"token.json", SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    SERVICE_ACCOUNT_FILE, SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open(default_path+"token.json", "w") as token:
                token.write(creds.to_json())
        return build('calendar', 'v3', credentials=creds)

    service = authenticate_google_calendar()

    def format_date_time(time_str):

        target_timezone='Asia/Colombo'

        # Parse the naive datetime string
        naive_dt = datetime.datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S")
        
        # Localize to the target timezone
        timezone = pytz.timezone(target_timezone)
        localized_dt = timezone.localize(naive_dt)
        
        return {'dateTime': localized_dt.isoformat(),'timeZone': target_timezone}

    @tool
    def update_event(event_id,title,start,end):
        """Update a Google Calendar event title or start end times or all of them."""

        event = service.events().get(calendarId='primary', eventId=event_id).execute()

        if title:
            event['summary'] = title
        
        if start:
            event['start'] = format_date_time(start)

        if end:
            event['end'] = format_date_time(end)     

        #print("Title",title)
        #print("START TIME" , event["start"])
        #print("END TIME", event["end"])
        
        updated_event = service.events().update(calendarId='primary', eventId=event['id'], body=event).execute()

        return updated_event   

    tools = [update_event]

    prompt = f"""You are a calendar assistant designed to modify, edit, or update the user's Google Calendar events. You work under a supervisor chatbot who communicates with the user.

    Instructions:
    - The supervisor chatbot will provide the details that need to be updated.
    - Then, use the `update_event` tool to update the event accordingly.
    - 

    Your primary role is to assist in editing calendar events.
    """


    calendar_agent = create_react_agent(model=llm,tools=tools,prompt=prompt)

    for step in calendar_agent.stream({"messages": [("human", query)]}):
        for key, value in step.items():
            print(key)
            if key == "agent":
                print(value["messages"])
                continue
            print(value)
        print("---------------")
    """
    for step in calendar_agent.stream({"messages": [("human", query)]}):
        continue
    """
    #print("Last Message: ",step["messages"][-1].content)
    return step["messages"][-1].content
           