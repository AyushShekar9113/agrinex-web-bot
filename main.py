import os
from typing import List
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from models import voice  # Your AI agent logic
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi import WebSocket,WebSocketDisconnect
import logging

app = FastAPI()
connections: List[WebSocket] = []
# Set up the Jinja2Templates for rendering HTML files from the templates folder
templates = Jinja2Templates(directory="templates")
# logging.basicConfig(level=logging.DEBUG)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://agrinex-web-bot-production.up.railway.app"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Serve static files like CSS, JS, and images from the "static" folder
app.mount("/static", StaticFiles(directory="static"), name="static")

# Endpoint to serve the index.html from the templates folder
@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    # Debugging line to check template loading
    print("Attempting to load the template")
    return templates.TemplateResponse("index.html", {"request": request})

# Endpoint to start the agent
@app.post("/start-agent/")
async def start_agent(background_tasks: BackgroundTasks):
    # Run AI agent in background
    # background_tasks.add_task(voice.main)
    # response_message = await voice.main()
    # print(f"Agent response: {response_message}")
    # Send back a response to the frontend
    return {"message": "Agent start requested. Please open WebSocket connection to proceed."}

# Endpoint to handle asking the agent
@app.post("/ask-agent/")
async def ask_agent(request: Request):
    data = await request.json()
    user_message = data.get("message")
    
    # Process the message and generate audio
    ai_response, audio_file_name = voice.process_message_and_generate_audio(user_message)
    
    # Construct the URL for the audio file
    audio_url = f"http://127.0.0.1:10000/audio/{audio_file_name}"

    
    return {"reply": ai_response, "audio_url": audio_url}

@app.post("/send-output/")
async def send_output_to_web(data: dict):
    output_text = data.get("output")
    for connection in connections:
        await connection.send_text(output_text)
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connections.append(websocket)
    
    # Set sys.stdout dynamically
    import sys
    from models.voice import WebSocketPrinter
    # Save real stdout
    original_stdout = sys.stdout
    # Redirect stdout
    sys.stdout = WebSocketPrinter(websocket, original_stdout)
    try:
        # Call your main agent logic here        
        import asyncio
        asyncio.create_task(voice.main(websocket))

        while True:
            await voice.speak_translated(websocket, "Welcome to AgriNex! Please choose your language.", "en")
            data = await websocket.receive_text()
            print(f"Received from client: {data}") 
    except WebSocketDisconnect:
        connections.remove(websocket)
        print("Client disconnected")
    finally:
        # Very important: restore terminal output when client disconnects
        sys.stdout = original_stdout
@app.get("/audio/{audio_file_name}")
async def get_audio(audio_file_name: str):
    audio_file_path = os.path.join("audio", audio_file_name)
    
    # Check if the file exists
    if not os.path.exists(audio_file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")

    # Return the audio file as a response
    return FileResponse(audio_file_path, media_type="audio/mp3")

# --- 1. For Exotel IVR Calls ---
# @app.post("/start-agent/")
# async def start_agent(background_tasks: BackgroundTasks):
#     # Run AI agent in background
#     background_tasks.add_task(voice.main)

#     # Send EXOML response to Exotel
#     exoml = """
#     <Response>
#         <Say>Welcome to AgriNex AI System. Please wait while we connect you.</Say>
#         <Connect>
#             <Room>farmer-support</Room>
#         </Connect>
#     </Response>
#     """
#     return Response(content=exoml.strip(), media_type="application/xml")
