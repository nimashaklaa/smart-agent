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

def event_scheduler_agent(query):

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

    # Get Today's Date
    today_date = datetime.datetime.today().strftime("%B %d, %Y")

    # Function to add an event in Google Calendar
    @tool
    def create_calendar_event(event_details:str) -> str:

        """Creates an event in Google Calendar. Provide event details as a dictionary with keys: "
            "'summary' (title), 'description' (details), 'start_time' (ISO 8601 format), "
            "'end_time' (ISO 8601 format), and 'timezone' (e.g., 'UTC').
            If the user doesn't specify a year, default to the year 2025.
            """
        # Ensure event_details is a dictionary
        if isinstance(event_details, str):
            try:
                #print("Original JSON string:", event_details,type(event_details))  # Debug: Print the original JSON string
                event_details = json.loads(event_details.replace("'", '"'))
                #print("Converted dictionary:", event_details) 
            except json.JSONDecodeError:
                return "❌ Error, Provided event details are not in valid JSON format."

        # Extract details safely from dictionary
        summary = event_details.get("summary", "No Title")
        description = event_details.get("description", "No Description")
        start_time = event_details.get("start_time")
        end_time = event_details.get("end_time")
        timezone = "Asia/Colombo"

        if not start_time or not end_time:
            return "❌ Error: Missing 'start_time' or 'end_time'."

        #print(f"📅 Creating event: {summary} from {start_time} to {end_time} in {timezone}")

        # Convert time to Google Calendar's format
        start_dt = datetime.datetime.fromisoformat(event_details['start_time'])
        end_dt = datetime.datetime.fromisoformat(event_details['end_time'])

        event = {
            'summary': summary,
            #'location': '800 Howard St., San Francisco, CA 94103',
            'description': description,
            'start': {
                "dateTime": start_dt.isoformat(),
                "timeZone": timezone
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": timezone
            }
        }

        try:
            event_result = service.events().insert(calendarId="primary", body=event).execute()
            #print(event_result)
            event_link = event_result.get('htmlLink')
            #print('Event created:', event_link)
            event_id = event_result.get('id')
            return f"Event Created!\nEvent Link: {event_link}\nEvent ID: {event_id}"
            #return str(event_link)
        except Exception as e:
            #print(f"An error occurred: {e}")
            return str("Error")


    tools = [create_calendar_event]

    prompt = f"""You are an assistant designed to create_calendar_event.You work under a supervisor chatbot who communicate with a user.:
 
    - The chatbot_supervisor provides the event details which got from the user.
    - Then use the tool `create_calendar_event(event_details)` to add the event to the calendar. 
    - If you need more details ask from the chatbot.    
    - If an event was created always return the event_id.

    Your role is to schedule events.And Today is {today_date}.
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
    for step in calendar_agent.stream({"messages": [("human", query)]},stream_mode="debug"):
        continue
    print("Last Message: ",step["messages"][-1].content)
    
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
           