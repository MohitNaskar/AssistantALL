import os
from livekit import api
from flask import Flask, request
from dotenv import load_dotenv
from flask_cors import CORS
import uuid

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route("/getToken")
def get_token():
    name = request.args.get("name", "my name")
    room = request.args.get("room", None)
    
    if not room:
        room = "room-support"  # Use a fixed room name
    
    print(f"📍 User '{name}' joining room '{room}'")
    
    # Create user token
    token = api.AccessToken(
        os.getenv("LIVEKIT_API_KEY"), 
        os.getenv("LIVEKIT_API_SECRET")
    ).with_identity(name).with_name(name).with_grants(
        api.VideoGrants(room_join=True, room=room)
    )
    
    return token.to_jwt()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)