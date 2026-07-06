# loading the future annotations to allow for postponed evaluation of type annotations
from __future__ import annotations

import asyncio
import json
import os
from collections import defaultdict
from typing import Any, Dict, List

import httpx
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
)
from livekit.agents.worker import AgentServer
from livekit.plugins.google.realtime import RealtimeModel
from livekit.agents import RoomInputOptions

from api import (
    get_news,
    google_search,
    store_user_data,
    summarize_conversation,
)
from promts import INSTRUCTIONS

load_dotenv()

#creating an entrypoint function that will be called when the agent is started
async def entrypoint(ctx: JobContext):
    print("Job received, connecting to room...")
    await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)
    print("Connected to room, waiting for participants...")
    participant =await ctx.wait_for_participant()
    print(f"Participant joined: {participant.identity}")
    
    #loading the RealtimeModel with the specified parameters
    voice_model = RealtimeModel(
        model="gemini-3.1-flash-live-preview",
        api_key=os.getenv("GOOGLE_API_KEY"),
        instructions=INSTRUCTIONS,
        voice="Aoede",
        temperature=0.7,        
    )
    
    #creating an AgentSession with the loaded model and starting it with the specified tools
    session = AgentSession(llm=voice_model)

    #starting the session with the specified room and agent configuration
    await session.start(
        
        room=ctx.room,
        agent=Agent(
            instructions=INSTRUCTIONS,
            tools=[
                store_user_data,
                summarize_conversation,
                google_search,
                get_news,
            ],
        ),
    )
    
    print("greetings sent")

# Add this at module level (outside any function)
from livekit.agents.worker import AgentServer


server = AgentServer.from_server_options(
    WorkerOptions(
        entrypoint_fnc=entrypoint,
    )
)

# Run the server if this script is executed directly
if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))


