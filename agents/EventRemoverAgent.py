# agents/calendar.py

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

def event_remover_agent(query):

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

    @tool
    def delete_event(event_id):
        """Delete Google Calendar events for given travel dates."""
        
        service.events().delete(calendarId='primary', eventId=event_id).execute()

    tools = [delete_event]

    prompt = f"""You are a calendar assistant designed to delete/remove the user's google calendar events. You can do two types of requests.You work under a supervisor chatbot who communicate with a user.:

    - The chatbot_supervisor provides an event_Id.  
    - Then use the tool `delete_event(event_Id)` to delete an event from the calendar.  
    - If you need more details ask from the chatbot.like event_ID not provided.  


    Your role is to remove calendar events.
    """

    calendar_agent = create_react_agent(model=llm,tools=tools,prompt=prompt)

    """for step in calendar_agent.stream({"messages": [("human", query)]}):
        for key, value in step.items():
            print(key)
            if key == "agent":
                print(value["messages"])
                continue
            print(value)
        print("---------------")"""
    for step in calendar_agent.stream({"messages": [("human", query)]}):
        continue
    #print("Last Message: ",step["messages"][-1].content)
    
    # Handle different step formats
    if "messages" in step:
        return step["messages"][-1].content
    elif "agent" in step and "messages" in step["agent"]:
        return step["agent"]["messages"][-1].content
    elif "output" in step:
        return step["output"]
    else:
        # Fallback: return the step itself as string
        return str(step)
           