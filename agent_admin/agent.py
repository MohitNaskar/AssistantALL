# loading the future annotations to allow for postponed evaluation of type annotations
from __future__ import annotations

from flask import session
from promts import INSTRUCTIONS
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,llm,
    AgentSession,
    Agent
)

from livekit.plugins import google
from livekit.plugins.google.realtime import RealtimeModel
from dotenv import load_dotenv
import os
from livekit import rtc
from api import (
    get_contact_details_by_phone,
    list_all_contacts,
    store_user_data,
)

load_dotenv()


#creating an entrypoint function that will be called when the agent is started
async def entrypoint(ctx: JobContext):
    print("Job received, connecting to room...")
    await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)
    print("Connected to room, waiting for participants...")
    participant =await ctx.wait_for_participant(kind=rtc.ParticipantKind.PARTICIPANT_KIND_STANDARD)
    print(f"Participant joined: {participant.identity}")
    
    #loading the RealtimeModel with the specified parameters
    model = RealtimeModel(
        model="gemini-3.1-flash-live-preview",
        api_key=os.getenv("GOOGLE_API_KEY"),
        instructions=INSTRUCTIONS,
        voice="Aoede",
        temperature=0.7,        
    )
    
    #creating an AgentSession with the loaded model and starting it with the specified tools
    session = AgentSession(llm=model)

    #starting the session with the specified room and agent configuration
    await session.start(
        
        room=ctx.room,
        agent=Agent(
            instructions=INSTRUCTIONS,
            tools=[
                store_user_data,
                list_all_contacts,
                get_contact_details_by_phone,
            ],
        ),
    )
    
    print("greetings sent")

# Add this at module level (outside any function)
from livekit.agents.worker import AgentServer

server = AgentServer.from_server_options(
    WorkerOptions(
        entrypoint_fnc=entrypoint,
        agent_name="Gemini Agent",
    )
)

# Run the server if this script is executed directly
if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint,
                              agent_name="Gemini Agent"))