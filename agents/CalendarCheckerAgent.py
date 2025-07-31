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

def calendar_checker_agent(query):

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

    # Functions to check availability in Google Calendar
    def format_to_iso(date_str, time_of_day="start"):

        parsed_date = dateparser.parse(date_str)
        
        if parsed_date is None:
            raise ValueError(f"Invalid date string: {date_str}")
        
        # Set the timezone to Sri Lankan time (Asia/Colombo)
        sri_lanka_tz = pytz.timezone("Asia/Colombo")

        if time_of_day == "start":
            formatted_date = parsed_date.replace(hour=0, minute=0, second=0, tzinfo=sri_lanka_tz)
        else:
            formatted_date = parsed_date.replace(hour=23, minute=59, second=59, tzinfo=sri_lanka_tz)

        return formatted_date.strftime("%Y-%m-%dT%H:%M:%SZ")

    @tool
    def check_availability(start_date, end_date):
        """Check user's availability based on Google Calendar events for given travel dates.
        If the user doesn't specify a year, default to the year 2025."""
        
        start_iso = format_to_iso(start_date, "start")
        end_iso =  format_to_iso(end_date, "end")
  
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_iso,
            timeMax=end_iso,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get("items", [])
        if not events:
            return "No events during the given time period."
        return events

    tools = [check_availability]

    prompt = f"""You are a calendar checker assistant designed to Check Availability.You work under a supervisor chatbot who communicate with a user.:

    - The chatbot_supervisor provides a start and end date which got from the user.  
    - Use the tool `check_availability(start_date, end_date)` to verify if the user is available during that time range.
    - If you need more details ask from the chatbot.  
    - When you provide the chatbot events also provide event IDs.

    Your role is to Check user Availability.And Today is {today_date}.
    """

    calendar_agent = create_react_agent(model=llm,tools=tools,prompt=prompt)

    """for step in calendar_agent.stream({"messages": [("human", query)]}):
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
           