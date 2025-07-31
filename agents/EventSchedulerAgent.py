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

    # Function to check for conflicts before scheduling
    @tool
    def check_calendar_conflicts(event_details: str) -> str:
        """Check for conflicts in Google Calendar before scheduling. Provide event details as a dictionary with keys: 
        'summary' (title), 'start_time' (ISO 8601 format), 'end_time' (ISO 8601 format).
        Returns information about any conflicting events or confirms availability."""
        
        # Ensure event_details is a dictionary
        if isinstance(event_details, str):
            try:
                event_details = json.loads(event_details.replace("'", '"'))
            except json.JSONDecodeError:
                return "❌ Error: Provided event details are not in valid JSON format."

        # Extract details safely from dictionary
        summary = event_details.get("summary", "No Title")
        start_time = event_details.get("start_time")
        end_time = event_details.get("end_time")

        if not start_time or not end_time:
            return "❌ Error: Missing 'start_time' or 'end_time'."

        # Convert time to Google Calendar's format
        start_dt = datetime.datetime.fromisoformat(start_time)
        end_dt = datetime.datetime.fromisoformat(end_time)

        # Check for conflicts
        try:
            # Get events in the time range - use timezone-aware datetime
            timezone = pytz.timezone("Asia/Colombo")
            start_dt_tz = start_dt.replace(tzinfo=timezone)
            end_dt_tz = end_dt.replace(tzinfo=timezone)
            
            events_result = service.events().list(
                calendarId='primary',
                timeMin=start_dt_tz.isoformat(),
                timeMax=end_dt_tz.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            if not events:
                return f"✅ No conflicts found! You are available for '{summary}' from {start_dt.strftime('%B %d, %Y at %I:%M %p')} to {end_dt.strftime('%I:%M %p')}."
            
            # Format conflicting events
            conflicts = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                event_summary = event.get('summary', 'No Title')
                conflicts.append(f"- {event_summary} ({start} to {end})")
            
            conflict_list = "\n".join(conflicts)
            return f"❌ Conflicts found! You have the following events during this time:\n{conflict_list}\n\nPlease choose a different time for '{summary}'."
            
        except Exception as e:
            return f"❌ Error checking conflicts: {str(e)}"

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


    tools = [check_calendar_conflicts, create_calendar_event]

    prompt = f"""You are an assistant designed to schedule events in Google Calendar. You work under a supervisor chatbot who communicates with a user.
 
    **CRITICAL WORKFLOW - YOU MUST FOLLOW THIS EXACTLY:**
    1. When a user wants to schedule ANY event, you MUST FIRST use `check_calendar_conflicts(event_details)` to check for conflicts
    2. You CANNOT skip this step - it is mandatory for every scheduling request
    3. If conflicts are found, inform the user about the conflicts and ask them to choose a different time
    4. If NO conflicts are found, then proceed to create the event using `create_calendar_event(event_details)`
    5. Always return the event_id when an event is successfully created
    
    **IMPORTANT RULES:**
    - NEVER use `create_calendar_event` without first using `check_calendar_conflicts`
    - ALWAYS check for conflicts before scheduling
    - If there are conflicts, clearly explain what conflicts exist and suggest alternative times
    - If no conflicts, proceed with scheduling and provide the event details
    - Always be helpful and provide clear information about availability or conflicts
    
    **Example workflow:**
    1. User says: "schedule meeting with John tomorrow at 2 PM"
    2. You MUST first call: `check_calendar_conflicts(event_details)` 
    3. If conflicts found: Tell user about conflicts
    4. If no conflicts: Call `create_calendar_event(event_details)`
    
    Your role is to schedule events safely. Today is {today_date}.
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
    
    # Handle different step formats
    if "messages" in step:
        return step["messages"][-1].content
    elif "agent" in step and "messages" in step["agent"]:
        return step["agent"]["messages"][-1].content
    elif "output" in step:
        return step["output"]
    elif "payload" in step and "result" in step["payload"]:
        # Handle the new format with payload.result
        result = step["payload"]["result"]
        if isinstance(result, list) and len(result) > 0:
            # Extract the message content from the result
            for item in result:
                if isinstance(item, tuple) and len(item) == 2 and item[0] == "messages":
                    messages = item[1]
                    if messages and hasattr(messages[-1], 'content'):
                        return messages[-1].content
        return str(step)
    else:
        # Fallback: return the step itself as string
        return str(step)
           