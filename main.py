# main.py
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from typing import Literal
from langgraph.types import Command
from agents.CalendarCheckerAgent import calendar_checker_agent
from agents.EventSchedulerAgent import event_scheduler_agent
from agents.EventModifierAgent import event_modifier_agent
from agents.EventRemoverAgent import event_remover_agent
from config import llm  # Import the shared llm from config.py
import datetime
import json

class State(TypedDict):
    next: str
    message_list : list

# # Creating the Agent Nodes

def calendar_checker_agent_node(state: State) -> Command[Literal['chatbot']]:

    #print("QUERY GOING TO calendar_checker_agent",state["message_list"][-1])
    result = calendar_checker_agent(str(state["message_list"][-1]))

    new_lst = state["message_list"]+ [("ai", "calendar_checker_agent : " + result)]

    return Command(goto='chatbot', update={"next":"chatbot","message_list":new_lst})

def event_scheduler_agent_node(state: State) -> Command[Literal['chatbot']]:

    #print("QUERY GOING TO event_scheduler_agent",state["message_list"][-1])
    result = event_scheduler_agent(str(state["message_list"][-1]))

    new_lst = state["message_list"]+ [("ai", "event_scheduler_agent : " + result)]

    return Command(goto='chatbot', update={"next":"chatbot","message_list":new_lst})

def event_remover_agent_node(state: State) -> Command[Literal['chatbot']]:

    #print("QUERY GOING TO CALENDAR AGENT",state["message_list"][-1])
    result = event_remover_agent(str(state["message_list"][-1]))

    new_lst = state["message_list"]+ [("ai", "event_remover_agent : " + result)]

    return Command(goto='chatbot', update={"next":"chatbot","message_list":new_lst})

def event_modifier_agent_node(state: State) -> Command[Literal['chatbot']]:

    #print("QUERY GOING TO event_modifier_agent",state["message_list"][-1])
    result = event_modifier_agent(str(state["message_list"][-1]))

    new_lst = state["message_list"]+ [("ai", "event_modifier_agent : " + result)]

    return Command(goto='chatbot', update={"next":"chatbot","message_list":new_lst})
"""
def calendar_node(state: State) -> Command[Literal['chatbot']]:

    #print("QUERY GOING TO CALENDAR AGENT",state["message_list"][-1])
    result = calendar_agent(str(state["message_list"][-1]))

    new_lst = state["message_list"]+ [("ai", "calendar_agent : " + result)]

    return Command(goto='chatbot', update={"next":"chatbot","message_list":new_lst})
"""

# # Human Input

def user_node(state: State) -> Command[Literal['chatbot']]:

    #query = state['message_list'][-1].content

    user_input = input("user: ")

    new_lst = state["message_list"]+ [("user", user_input)]
    
    if user_input == "exit":
        return Command(goto=END,update={"next": END,"message_list": new_lst})  

    return Command(goto='chatbot', update={"message_list":new_lst})

    #return


## Chatbot

current_date_time = datetime.datetime.now().strftime("%A, %B %d, %Y, %I:%M %p")

chatbot_prompt = f"""You are the Supervisor Agent for an AI Calendar Assistant system.

Current date and time: {current_date_time}.

Your Responsibilities:
- Talk to the user to fully understand their request.
- Collect **all required information** before sending a task to any agent.
- Send tasks to the correct agent with complete and clear information.
- Collect responses from agents and decide the next action.

Agents you can use:
- calendar_checker_agent: To check calendar events.
- event_scheduler_agent: To add new events (REQUIRES: event title, date, and time).
- event_remover_agent: To delete events.(Should Provide the event Id.)
- event_modifier_agent: To modify/edit/update events.
- user: If you need more information.

Important Rules:
1. Greet the user and ask what they want to do.
2. If user request is unclear or missing information, ask follow-up questions (one at a time) until you have everything needed.
3. Only send a task to another agent once you have **all required information**.
4. Be friendly, clear, and simple. Ask **one question at a time**.
5. Always format your reply in JSON:
   - `next`: agent to call (`calendar_checker_agent`, `event_scheduler_agent`, `event_editor_agent`, `user`, or `FINISH`)
   - `messages`: Message content (talk to the user or explain to the agent what task to do).

**EXTRA REMINDERS:**
- For scheduling an event: you must collect **event title**, **date**, and **time**.
- For deleting: you must collect **event_ID**.
- For editing : you must collect **event title** and **what exactly to edit**.
- If something is unclear, always ask the user first instead of guessing.

Example JSON message when enough info is collected:
```json

  "next": "event_scheduler_agent",
  "messages": "Schedule an event titled 'Team Meeting' on 2025-05-01 at 10:00 AM."


"""

class Router(TypedDict):
    """Worker to route to next."""

    next: Literal['calendar_checker_agent','user','event_scheduler_agent','event_remover_agent','event_modifier_agent','FINISH']
    messages:str

def chatbot_node(state:State) -> Command[Literal['calendar_checker_agent','user','event_scheduler_agent','event_remover_agent','event_modifier_agent','__end__']] :
    messages = [
        {"role": "system","content":chatbot_prompt}
    ] + state["message_list"]

    response = llm.with_structured_output(Router).invoke(messages)

    new_lst = state["message_list"] + [("ai", "chatbot_supervisor : " + response["messages"])]
    
    goto = response["next"]

    if goto == "FINISH":
        return Command(goto="user",update={"next": "user","message_list": new_lst})

    return Command(goto=goto,update={"next": goto,"message_list": new_lst})       

# Initialize the state graph

builder = StateGraph(State)
builder.add_edge(START, "chatbot")
builder.add_node("chatbot", chatbot_node)
builder.add_node("calendar_checker_agent", calendar_checker_agent_node)
builder.add_node("event_scheduler_agent", event_scheduler_agent_node)
builder.add_node("event_remover_agent", event_remover_agent_node)
builder.add_node("event_modifier_agent", event_modifier_agent_node)
builder.add_node("user", user_node)

# Compile the graph
graph = builder.compile()
"""
# Initial state for the conversation
initial_state = {
    "message_list": [("user", "Hi")],
}

# Start the graph stream to trigger the flow
for s in graph.stream(initial_state,subgraphs=True):
        
        #print(s)
        #message_data = s[1]  # Access the second element of the tuple
        #print(f"Next action: {message_data.get('next')}")
        #print(f"Message list: {message_data.get('message_list')}")
        #pprint.pprint(f"Last Message: {message_data.get('message_list')[-1]}")
        #print("\n----\n")
        
        for key, value in s[1].items():
            if key in ['chatbot', 'calendar_checker_agent','event_scheduler_agent','event_remover_agent','event_modifier_agent']:
                #print(value['messages'])
                print(key)
                print("next_node: " + value['next'])
                print("message: " + value['message_list'][-1][1])
        print("----")

"""
##########################################################################################################################################
######################################################    FastAPI Backend    #######################################################################
##########################################################################################################################################


from fastapi import FastAPI
from fastapi.responses import StreamingResponse,Response
from typing import AsyncIterator
from pydantic import BaseModel
import os
import json

# When the FastAPI app run for the first time remove the graph_state.json file 
if os.path.exists("graph_state.json"):
    os.remove("graph_state.json")

app = FastAPI()

class ChatInput(BaseModel):
    message: str

@app.post("/chat")
def chat(human_input:ChatInput):
    # Check if the file exists
    if os.path.exists("graph_state.json"):
        with open("graph_state.json", "r") as json_file:
            current_state = json.load(json_file)
    else:
        # If the file doesn't exist, create a new one with default values
        current_state = {
            "message_list": [("user", "Hi")],
        }
        with open("graph_state.json", "w") as json_file:
            json.dump(current_state, json_file)
    # with open("graph_state.json", "r") as json_file:
    #   current_state =  json.load(json_file)
    current_state["next"] = 'chatbot'
    current_state["message_list"].append(['user',human_input.message])   
    initial_state = current_state

    # Start the graph stream
    for s in graph.stream(initial_state,subgraphs=True,interrupt_before=["user"],stream_mode="values"):
        print(s[1])
        if "message_list" in s[1] and s[1]['message_list'][-1][0] == "ai":
            current_state["message_list"].append(["ai",s[1]['message_list'][-1][1]])
            with open("graph_state.json", "w") as json_file:
                json.dump(current_state, json_file, indent=4) 
            
            print("message: " + s[1]['message_list'][-1][1])
            print("next_node: " + s[1]["next"])
            print("----")
            print("\n")
            print(s[1]["next"] + "\n")        
    return current_state["message_list"]      

################################### chat streaming ###############################################

@app.post("/chat_stream")
async def chat_stream(human_input:ChatInput):
    # Check if the file exists
    #return {"reply": f"You said: {human_input.message}"}
    if os.path.exists("graph_state.json"):
        with open("graph_state.json", "r") as json_file:
            current_state = json.load(json_file)
    else:
        # If the file doesn't exist, create a new one with default values
        current_state = {
            "message_list": [("user", "Hi")],
        }
        with open("graph_state.json", "w") as json_file:
            json.dump(current_state, json_file)
    # with open("graph_state.json", "r") as json_file:
    #   current_state =  json.load(json_file)
    current_state["next"] = 'chatbot'
    current_state["message_list"].append(['user',human_input.message])   
    initial_state = current_state
    #return {"Message":"Hi from backend"} 

    # Start the graph stream

    async def message_stream() -> AsyncIterator[str]:
        for s in graph.stream(initial_state, subgraphs=True, interrupt_before=["user"], stream_mode="values"):
            if "message_list" in s[1] and s[1]['message_list'][-1][0] == "ai":
                current_state["message_list"].append(["ai",s[1]['message_list'][-1][1]])

                with open("graph_state.json", "w") as json_file:
                    json.dump(current_state, json_file, indent=4)

                print("message: " + s[1]['message_list'][-1][1])
                print("next_node: " + s[1].get("next", ""))
                print("----\n")
                
                yield s[1]['message_list'][-1][1] + "\n"

    return StreamingResponse(message_stream(), media_type="text/plain")


