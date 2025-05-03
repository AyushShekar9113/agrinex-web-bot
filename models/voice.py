from fastapi import WebSocket
from pymongo import MongoClient
from .farmer import register_farmer, farmers_collection
# from farmer import register_farmer,farmers_collection
import speech_recognition as sr
import re  
from word2number import w2n
import time
import requests
import urllib.parse
from datetime import datetime, timezone
import pytz
import json
import os
import threading
from googletrans import Translator
import asyncio
from gtts import gTTS
import pygame
import sys
import io
import tempfile

# GROQ_API_KEY = "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"
# GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Initialize MongoDB Connection
client = MongoClient("mongodb://localhost:27017/")  
db = client["agrinex"]
sub_districts_collection = db["villages"]  # ✅ Correct collection
sales_collection = db["sales"]
help_requests_collection = db["help_requests"]
emergency_collection = db["emergency_requests"]
# Initialize Text-to-Speech (TTS)
# engine = pyttsx3.init()
# engine.setProperty("rate", 150)
# Set your local timezone (e.g., Asia/Kolkata)
local_tz = pytz.timezone("Asia/Kolkata")
# Get current time in local timezone
local_time = datetime.now(local_tz)
# Store the timestamp in ISO format with timezone offset
# timestamp = local_time.isoformat()
OFFLINE_STORAGE = "offline_sales.json"

# Initialize pygame for playing audio
# pygame.mixer.init()

# async def speak(text, lang='kn'):
#     print(f"Agrinex ({lang}): {text}")
#     try:
#         tts = gTTS(text=text, lang=lang)
#         with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
#             temp_path = fp.name
#             tts.save(temp_path)
#         pygame.mixer.init()
#         pygame.mixer.music.load(temp_path)
#         pygame.mixer.music.play()
#         while pygame.mixer.music.get_busy():
#             await asyncio.sleep(0.3)
#         pygame.mixer.music.unload()
#         os.remove(temp_path)
#     except Exception as e:
#         print(f"❌ TTS error: {e}")
# Local audio directory
AUDIO_DIR = "audio"


class WebSocketPrinter(io.TextIOBase):
    def __init__(self, websocket, original_stdout):
        self.websocket = websocket
        self.original_stdout = original_stdout  # Keep the original terminal stdout

    def write(self, message: str):
        if message.strip():  # Avoid sending empty newlines
            import asyncio
            asyncio.create_task(self.websocket.send_text(message))
        
        # Also print normally to terminal
        self.original_stdout.write(message)
        self.original_stdout.flush()

    def flush(self):
        self.original_stdout.flush()


# Ensure the audio directory exists
if not os.path.exists(AUDIO_DIR):
    os.makedirs(AUDIO_DIR)

def process_message_and_generate_audio(message: str):  
    # Example of processing the message - integrate your AI model here
    ai_response = f"AI response to: {message}"  # Replace with your actual logic
    
    # Generate the speech from the AI response using gTTS
    audio_file_name = f"response_{uuid.uuid4()}.mp3"
    audio_file_path = os.path.join(AUDIO_DIR, audio_file_name)  # Save in an 'audio' directory

    # Create the audio file
    tts = gTTS(ai_response, lang='en')
    tts.save(audio_file_path)

    # Return the response text and the name of the audio file (to use in URL)
    return ai_response, audio_file_name

# Initialize pygame for local audio playback
# pygame.mixer.init()

# This flag determines if the environment is local or deployed
IS_LOCAL = True  # Set to True for local, False for cloud deployment

async def speak(websocket,text, lang='kn'):
    print(f"Agrinex ({lang}): {text}")

    try:
        if IS_LOCAL:
            # Local TTS with Pygame
            print("Using local TTS with Pygame")

            # Create temporary audio file from gTTS
            tts = gTTS(text=text, lang=lang)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                temp_path = fp.name
                tts.save(temp_path)

            # Load and play audio using Pygame
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()

            # Wait until the audio finishes
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.3)
            
            # Clean up the temporary file after playing
            pygame.mixer.music.unload()
            os.remove(temp_path)
        
        else:
            # Cloud TTS with gTTS (when deployed)
            # Cloud TTS for web deployment
            print("Using cloud TTS with gTTS")

            filename = f"response_{int(asyncio.get_event_loop().time()*1000)}.mp3"
            audio_path = os.path.join(AUDIO_DIR, filename)
            tts = gTTS(text=text, lang=lang)
            tts.save(audio_path)
            # Construct the public URL path to the audio file
# Determine base URL dynamically
            BASE_URL = "http://127.0.0.1:8000" if IS_LOCAL else "https://your-app-name.onrender.com"
# Create the dynamic audio URL
            audio_url = f"{BASE_URL}/static/audio/{filename}"
            print(f"Audio URL: {audio_url}")
# Send URL to frontend via WebSocket
            await websocket.send(json.dumps({"audio_url": audio_url}))        
    except Exception as e:
        print(f"❌ TTS error: {e}")

# # Example function to upload to cloud storage (AWS S3, Google Cloud Storage, etc.)
# def save_to_cloud_storage(text, lang):
#     try:
#         # Placeholder for cloud storage logic (AWS S3, GCS, etc.)
#         # For instance, upload the file to S3 and get the URL
#         audio_file_name = f"response_{uuid.uuid4()}.mp3"
#         tts = gTTS(text=text, lang=lang)
        
#         # Example: Uploading to cloud (This part is pseudo-code, replace with actual logic)
#         cloud_file_url = f"https://example-cloud-storage.com/{audio_file_name}"
        
#         # Normally you'd upload the file here and get the URL
#         print(f"Audio saved to cloud: {cloud_file_url}")
        
#         return cloud_file_url  # Return cloud URL
#     except Exception as e:
#         print(f"❌ Cloud storage error: {e}")
#         return None
# # Set the SDL_AUDIODRIVER to "dummy" for environments without audio hardware
# os.environ["SDL_AUDIODRIVER"] = "dummy"

# async def speak(text, lang='kn'):
#     if not text.strip():
#         print("⚠️ Skipping empty text for TTS.")
#         return

#     print(f"Agrinex ({lang}): {text}")
#     try:
#         # Generate speech from text using gTTS
#         tts = gTTS(text=text, lang=lang)
        
#         # Save the speech to a temporary MP3 file
#         with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
#             temp_path = fp.name
#             tts.save(temp_path)

#         # Debugging: Check if the file was created
#         if os.path.exists(temp_path):
#             print(f"Temporary MP3 file created at {temp_path}")
#         else:
#             print("❌ Failed to create the temporary MP3 file.")
#             return

#         # Initialize pygame mixer for audio playback
#         pygame.mixer.init()
#         print("Pygame mixer initialized successfully.")

#         # Load the MP3 file and play it
#         pygame.mixer.music.load(temp_path)
#         print("MP3 file loaded into pygame mixer.")
#         pygame.mixer.music.play()

#         # Wait until the music finishes playing
#         while pygame.mixer.music.get_busy():
#             await asyncio.sleep(0.3)

#     except Exception as e:
#         print(f"❌ TTS error: {e}")
#     finally:
#         # Ensure pygame mixer is properly quit after use
#         pygame.mixer.quit()

#         # Clean up the temporary MP3 file
#         if os.path.exists(temp_path):
#             os.remove(temp_path)
#             print(f"Temporary MP3 file removed: {temp_path}")


import httpx

async def send_output(message: str,text):
    print(f"Output: {message}")
    try:
        response = httpx.post("http://127.0.0.1:8000/send-output/", json={"output": text})
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to send output to frontend: {e}")       

async def recognize_speech():
    """Recognize speech input from the microphone with error handling."""
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            print("\nListening...")
            time.sleep(0.5)
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(source, timeout=15, phrase_time_limit=20)
        
        text = recognizer.recognize_google(audio)
        print("Recognized:", text)
        return text.strip()
    except sr.UnknownValueError:
        await speak("I couldn't understand. Please repeat.")
        return None
    except sr.RequestError:
        await speak("Speech recognition service is down.")
        return None
    except OSError as e:
        await speak(f"Microphone error: {e}")
        return None
misheard_numbers = {
    "tree": "three",
    "to": "two",
    "for": "four",
    "ate": "eight"
}

async def recognize_dtmf():
    """
    Placeholder function for DTMF input (keypad). In a real-world app, 
    this would capture digits pressed by the user on their phone keypad.
    """
    await speak("Please press a number on your keypad now.", lang='en')
    # Simulated fallback — replace this with actual DTMF handler
    try:
        user_input = input("Simulated DTMF (Enter a number): ")
        return user_input.strip()
    except Exception as e:
        print(f"[DTMF Error] {e}")
        return ""

translator = Translator()
async def translate_text(text, target_lang):
    translator = Translator()
    try:
        translated = await translator.translate(text, target_lang)  # ✅ await directly
        return translated.text
    except Exception as e:
        print(f"Translation error: {e}")
        return text
# Assuming this function exists to send messages to WebSocket
async def send_message_to_websocket(message: str):
    # Send to all active WebSocket connections
    for connection in connections:
        await connection.send_text(message)

async def speak_translated(websocket: WebSocket,text, language="en"):
    """Smart multilingual TTS with number support for Kannada."""

    def localize_numbers(txt, lang):
        if lang == "kn":
            number_map = {
                "0": "೦", "1": "೧", "2": "೨", "3": "೩", "4": "೪",
                "5": "೫", "6": "೬", "7": "೭", "8": "೮", "9": "೯"
            }
            return ''.join(number_map.get(c, c) for c in txt)
        return txt

    # Translate your message
    translated = await translate_text(text, language)

    # Localize numbers if needed
    if language == "kn":
        translated = localize_numbers(translated, language)
    await send_message_to_websocket(f"Agent: {translated}")
    # Call the TTS
    await websocket.send_text(translated)
    print(f"Translated message: {translated}")
    await speak(websocket,translated,lang=language)
    await send_output(text,translated)

async def select_language(websocket: WebSocket):
    sys.stdout = WebSocketPrinter(websocket, sys.stdout)

    await speak(websocket,"Welcome to AgriNex! Please choose your language.", lang='en')
    await speak(websocket,"Press 1 for Kannada, Press 2 for English, Press 3 for Hindi,4 for Telugu.", lang='en')

    user_choice = await recognize_speech()

    if not user_choice:
        return await select_language(websocket)

    user_choice = user_choice.lower().strip()
    print(f"[DEBUG] User language choice: '{user_choice}'")
    language = "en"
    instruction = "Please say or press the number in English, only then your language will be used for your understanding. For example, say 'number one' or press 1 on your keypad."

    if any(kw in user_choice for kw in ["1", "one", "number one", "kannada"]):
        print("[DEBUG] Kannada selected")
        language= "kn"
        instruction = "ದಯವಿಟ್ಟು ಸಂಖ್ಯೆಯನ್ನು ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ ಹೇಳಿ ಅಥವಾ ಕೀಪ್ಯಾಡ್‌ನಲ್ಲಿ ಒತ್ತಿ. ನಂತರ ನಿಮಗೆ ಅರ್ಥವಾಗುವ ಭಾಷೆಯಲ್ಲಿ ಸ್ಪಷ್ಟತೆ ಒದಗಿಸಲಾಗುತ್ತದೆ. ಉದಾಹರಣೆಗೆ 'number one' ಎಂದು ಹೇಳಿ ಅಥವಾ 1 ಒತ್ತಿ."
    
    elif any(kw in user_choice for kw in ["2", "two", "number two", "english"]):
        print("[DEBUG] English selected")
        language= "en"
        instruction = "Please say or press the number in English, only then your language will be used for your understanding. For example, say 'number one' or press 1 on your keypad."
    elif any(kw in user_choice for kw in ["3", "three", "number three", "hindi", "hindhi"]):
        print("[DEBUG] Hindi selected")
        language= "hi"
        instruction = "कृपया नंबर को अंग्रेज़ी में बोलें या कीपैड पर दबाएं, तभी आपकी भाषा में जवाब मिलेगा ताकि आपको समझ में आए। उदाहरण: 'number one' कहें या 1 दबाएं।"
    elif any(kw in user_choice for kw in ["4", "four", "number four", "telugu", "thelugu"]):
        print("[DEBUG] telugu selected")
        language= "te"
        instruction = "దయచేసి సంఖ్యను ఇంగ్లీష్‌లో చెప్పండి లేదా కీప్యాడ్ నొక్కండి. ఉదాహరణకు 'number one' అని చెప్పండి లేదా 1 నొక్కండి."
    else:
        await speak("I couldn't understand. Please say 1 for Kannada, 2 for English, or 3 for Hindi.", lang='en')
        return await select_language(websocket)
    await speak(websocket,instruction, lang=language)
    return language 
async def agri_nex_main_flow(websocket,language):
    """Main flow of AgriNex based on selected language."""
    await speak_translated(websocket,"AgriNex: Welcome to AgriNex!", language)
    await speak_translated(websocket,"Number 1: Register.", language)
    await speak_translated(websocket,"Number 2: If you are registered, provide your phone number.", language)

    user_choice = await recognize_speech()
    if not user_choice:
        await speak_translated(websocket,"I couldn't understand. Please try again.", language)
        return await agri_nex_main_flow(websocket,language)

    user_choice = user_choice.lower()

    if "one" in user_choice or "1" in user_choice:
        await speak_translated(websocket,"You've selected register. Please proceed with your registration.", language)
        # TODO: registration flow
    elif "two" in user_choice or "2" in user_choice:
        await speak_translated(websocket,"You've selected to provide your phone number.", language)
        # TODO: phone number flow
    else:
        await speak_translated(websocket,"Invalid choice, please try again.", language)
        return await agri_nex_main_flow(websocket,language)

def correct_number_text(text):
    """Fixes common speech misinterpretations for numbers."""
    return misheard_numbers.get(text, text)

def validate_phone(text):
    digits = re.sub(r'\D', '', text)
    print(f"[DEBUG] Extracted digits: {digits}")
    if len(digits) == 10:
        return digits
    elif len(digits) > 10:
        return digits[-10:]  # Take last 10 digits
    return None

def extract_number(text):
    """Extracts a number from spoken text (supports both digits and number words)."""
    if text is None:
        return None  # ✅ Handle None input properly

    number_words = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
    }
    text = text.lower().strip()
    print(f"Extracting number from: {text}") 
    # Check for direct number words
    for word, num in number_words.items():
        if word in text.lower():
            return num

    # Check for digit-based numbers
    numbers = re.findall(r'\d+', text)
    if numbers:
        return int(numbers[0])  # Convert first found number to int
    # Try converting words to numbers
    try:
        return w2n.word_to_num(text)  # Convert words to numbers
    except ValueError:
        return None  # No valid number found
    return None  # If no number found

async def list_sub_districts(district):
    """Fetch and list unique sub-districts for a given district."""
    print(f"Searching for district: {district}")  # Debugging

    query = {"District": {"$regex": f"^{district}$", "$options": "i"}}
    records = sub_districts_collection.find(query, {"Sub-District": 1, "_id": 0})  

    sub_district_list = list(set(record.get("Sub-District") for record in records if "Sub-District" in record))

    print("Fetched sub-districts:", sub_district_list)  # ✅ Debugging statement

    if not sub_district_list:
        print("Debug: No sub-districts found in MongoDB.")  # Debugging
        await speak("No sub-districts found for this district.")
        return None

    for idx, sub in enumerate(sub_district_list, 1):
        await speak(f"{idx}. {sub}")
    
    return sub_district_list
async def get_first_letter_from_speech():
    """Recognizes speech and extracts the first letter (capitalized)."""
    while True:
        await speak("Please say the name of your village.")
        response =await recognize_speech()

        if response:
            first_letter = response.strip()[0].upper()  # Get first letter & capitalize
            if first_letter.isalpha():
                await speak(f"You selected '{first_letter}'. Searching for villages...")
                return first_letter
        await speak("Invalid input. Please say a village name.")

async def list_villages_by_first_letter(sub_district):
    """Fetch villages for a given sub-district and filter by first letter."""
    sub_district = sub_district.strip()  # Remove any extra spaces
    query = {"Sub-District": sub_district}    
    # Fetch all villages under the given sub-district
    cursor = sub_districts_collection.find(query, {"Village": 1, "_id": 0})
    # Extract village names from documents
    villages = [doc["Village"] for doc in cursor]

    print("Debug: Retrieved villages data ->", villages)  # ✅ Debugging

    if not villages:
        await speak("No villages found for this sub-district.")
        return None

    first_letter = (await get_first_letter_from_speech()).upper()
    filtered_villages = [v for v in villages if v.upper().startswith(first_letter)]

    if not filtered_villages:
        await speak(f"No villages found starting with '{first_letter}'.")
        return None
    formatted_villages = "\n".join([f"{i+1}. {v}" for i, v in enumerate(filtered_villages)])
    # speak(f"Villages starting with {first_letter}: " + ", ".join(filtered_villages))
    await speak(f"Villages starting with {first_letter} are as follows: \n{formatted_villages}")
    return filtered_villages

async def get_valid_input(prompt):
    """Continuously asks for input until a valid response is received."""
    while True:
        await speak(prompt)
        response =await recognize_speech()
        if response:
            return response
        
def check_internet():
    """Check if there is an active internet connection."""
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except requests.ConnectionError:
        return False

def store_offline(data):
    """Store failed transactions locally for retry."""
    try:
        with open(OFFLINE_STORAGE, "a") as file:
            json.dump(data, file)
            file.write("\n")  # Store each entry on a new line
    except Exception as e:
        print(f"Error storing offline: {e}")

def retry_offline_sales():
    """Retry sending stored offline sales when internet is back."""
    while True:
        if check_internet():
            try:
                if not os.path.exists(OFFLINE_STORAGE):
                    time.sleep(300)  # Wait and retry after 5 minutes
                    continue                  
                with open(OFFLINE_STORAGE, "r") as file:
                    lines = file.readlines()
                with open(OFFLINE_STORAGE, "w") as file:  # Clear file after reading
                    pass                  
                for line in lines:
                    data = json.loads(line)
                    sales_collection.insert_one(data)
                    print("✅ Offline sale uploaded successfully!")
            except FileNotFoundError:
                pass  
        time.sleep(300)  # Retry every 5 minutes

def start_offline_sync():
    """Start the offline sync as a background thread."""
    thread = threading.Thread(target=retry_offline_sales, daemon=True)
    thread.start()

async def register_farmer_voice(websocket,language):
    """Handles voice-based farmer registration with retry logic."""
    await speak_translated(websocket,"Welcome to AgriNex. Please say your name.",language )
    name = await recognize_speech()
    if not name:
        await speak_translated(websocket,"I couldn't hear your name. Please try again later.",language)
        return None
    while True:
        await speak_translated(websocket,f"Hello {name}, please say your 10-digit phone number slowly.",language)
        phone =await recognize_speech()
        phone = validate_phone(phone)
        if not phone:
            await speak_translated(websocket,"Invalid phone number. Please try again.",language)
            continue  # Ask again

        # ✅ Check if phone number already exists in the database
        existing_farmer = farmers_collection.find_one({"phone": phone})
        if existing_farmer:
            await speak_translated(websocket,"This phone number is already registered. Please use a different number.",language)
            continue  # Ask for a different number
        break

    district =await get_valid_input("Which district are you from?")
    sub_district_list = await list_sub_districts(district)

    if sub_district_list:
        # **Ask user to select a number for sub-district**
        while True:
            await speak_translated(websocket,"Please say the number of your sub-district.",language)
            user_choice = await recognize_speech()
            choice_index = extract_number(user_choice)  # ✅ Extracts number only

            if choice_index and 1 <= choice_index <= len(sub_district_list):
                selected_sub_district = sub_district_list[choice_index - 1]
                await speak_translated(websocket,f"You selected {selected_sub_district}.",language)
                break  
            
            await speak_translated(websocket,"Invalid choice. Please say a number from the list.")

        # **Now Ask for Village Selection**
        village_list =await list_villages_by_first_letter(selected_sub_district)

        if village_list:
            await speak_translated(websocket,"Please say the number of your village from the list.",language)
            while True:
                village_choice =await recognize_speech()
                village_index = extract_number(village_choice)

                if village_index and 1 <= village_index <= len(village_list):
                    selected_village = village_list[village_index - 1]
                    await speak_translated(websocket,f"You selected {selected_village}.",language)
                    break

                await speak_translated(websocket,"Invalid choice. Please say a number from the list.",language)
        else:
            selected_village = "Unknown"  # In case no village selection happens

        # **Register the farmer with selected sub-district & village**
        farmer_id = register_farmer(name, phone, district, selected_sub_district, selected_village)
        await speak_translated(websocket,f"Registration successful! Your farmer ID is {farmer_id}.",language)
        print(f"Farmer Registered: {name} - {phone} - {district}, {selected_sub_district}, {selected_village} - ID: {farmer_id}")
        return phone
    await speak_translated(websocket,"Registration failed due to incorrect sub-district selection. Please contact support.",language)
    return None

async def handle_farmer_interaction(websocket,phone_number, language,skip_phone_prompt=False):
    """Retrieve farmer details and guide them through options."""
    while True:
        if not skip_phone_prompt or not phone_number:
            await speak_translated(websocket,"Please say your 10-digit phone number slowly and clearly.", language)
            await asyncio.sleep(1.5)
            phone_raw = await recognize_speech()
            phone = validate_phone(phone_raw)
        else:
            phone = phone_number  # use existing number

        if phone:
            farmer = farmers_collection.find_one({"phone": phone})
            if farmer:
                name = farmer.get("name", "Farmer")
                farmer_id = farmer.get("farmer_id", "Unknown")

                await speak_translated(websocket,f"Welcome back, {name}! Your farmer ID is {farmer_id}.", language)
                await speak_translated(websocket,"What would you like to do today? Choose from the following options:", language)

                options = {
                    "1": "Weather update",
                    "2": "Live price",
                    "3": "Sell the commodities",
                    "4": "Request assistance",
                    "5": "emergency_requests",
                    "6": "Chat with Agrinex AI Agent"
                }

                for key, value in options.items():
                    await speak_translated(websocket,f"{key}. {value}", language)

                await speak_translated(websocket,"Please say the number of your choice.", language)

                while True:
                    user_choice = await recognize_speech()

                    if not user_choice:
                        await speak_translated(websocket,"I couldn't understand. Please try again.", language)
                        continue

                    user_choice = user_choice.lower().strip()

                    if "one" in user_choice or "1" in user_choice:
                        user_choice = "1"
                    elif "two" in user_choice or "2" in user_choice:
                        user_choice = "2"
                    elif "three" in user_choice or "3" in user_choice:
                        user_choice = "3"
                    elif "four" in user_choice or "4" in user_choice:
                        user_choice = "4"
                    elif "five" in user_choice or "5" in user_choice:
                        user_choice = "5"
                    elif "six" in user_choice or "6" in user_choice:
                        user_choice = "6"

                    if user_choice in options:
                        await speak_translated(websocket,f"You selected {options[user_choice]}.", language)
                        if user_choice == "1":
                            await fetch_and_speak_weather(websocket,farmer, language)
                        elif user_choice == "2":
                            await fetch_and_speak_live_price(websocket,farmer, language)
                        elif user_choice == "3":
                            await sell_commodities(websocket,farmer, language)
                        elif user_choice == "4":
                            await request_help(websocket,farmer, language)
                        elif user_choice =="5":
                            await emergency_alert_number_menu(websocket,farmer,farmer_id, language)
                        elif user_choice == "6":
                            await speak_translated(websocket,"Starting Agrinex AI Assistant. Speak naturally in your language.", language)
                            await bulletproof_voice_menu(websocket,language)

                        await return_or_exit(websocket,language, phone)
                        return phone, farmer
                    else:
                        await speak_translated(websocket,"I couldn't understand. Please say a valid number.", language)
            else:
                await speak_translated(websocket,"You are not registered. Say 'register' to create an account or provide another number.", language)
                response = await recognize_speech()

                if response and "register" in response.lower():
                    await register_farmer_voice(websocket,language)
                    return

                continue
        else:
            await speak_translated(websocket,"Invalid phone number. Please try again.", language)

# OpenCage API Key
OPENCAGE_API_KEY = "a17810d210b242b1ba948b470bad8af6"

def get_coordinates(village):
    """Fetch latitude and longitude for a given village using OpenCage API."""
    encoded_place = urllib.parse.quote(village)
    url = f"https://api.opencagedata.com/geocode/v1/json?q={encoded_place}&key={OPENCAGE_API_KEY}"    
    try:
        response = requests.get(url)
        data = response.json()        
        if data["results"]:
            lat = data["results"][0]["geometry"]["lat"]
            lon = data["results"][0]["geometry"]["lng"]
            return lat, lon
        else:
            return None, None
    except Exception as e:
        return None, None

def get_live_price(crop_name):
    """Mock function to get live crop price."""
    crop_prices = {"wheat": 1800, "rice": 2100, "sugarcane": 3000}
    return crop_prices.get(crop_name.lower(), None)

async def fetch_and_speak_weather(websocket,farmer, language):
    village = farmer.get("village", "Unknown")
    if village == "Unknown":
        await speak_translated(websocket,"We don’t have your village details. Please update them first.", language)
        return

    lat, lon = get_coordinates(village)
    if lat is None or lon is None:
        await speak_translated(websocket,f"Sorry, I couldn't find the location for {village}.", language)
        return
    await speak_translated(websocket,f"Fetching live weather updates for {village}...", language)
    url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat}&lon={lon}"
    headers = {"User-Agent": "AgriNexBot/1.0"}

    try:
        response = requests.get(url, headers=headers)
        data = response.json()

        if "properties" in data:
            timeseries = data["properties"]["timeseries"]
            today = datetime.utcnow().date()
            rain_chances = []
            temp_now = None
            weather_desc = None
            feels_like = None
            wind_speed = 0
            # 1. Extract current weather, feels-like, and wind
            for item in timeseries:
                timestamp = item["time"]
                dt = datetime.fromisoformat(timestamp[:-1])

                if dt.date() != today:
                    continue

                if temp_now is None:
                    details = item["data"]["instant"]["details"]
                    temp_now = details.get("air_temperature")
                    feels_like = details.get("air_temperature")  # Placeholder (real feels-like not available here)
                    wind_speed = details.get("wind_speed", 0)
                    weather_desc = item["data"].get("next_1_hours", {}).get("summary", {}).get("symbol_code", "")

                details = item["data"].get("next_1_hours", {}).get("details", {})
                rain_prob = details.get("probability_of_precipitation")
                if rain_prob is None:
                    rain_mm = details.get("precipitation_amount")
                    if rain_mm is not None:
                        if rain_mm == 0:
                            rain_prob = 0
                        elif rain_mm < 0.5:
                            rain_prob = 20
                        elif rain_mm < 2:
                            rain_prob = 50
                        else:
                            rain_prob = 80

                if rain_prob is not None:
                    rain_chances.append(rain_prob)

            if temp_now is not None:
                await speak_translated(websocket,f"The current temperature in {village} is {temp_now}°C.", language)

            # Feels-like note
            if feels_like is not None and abs(feels_like - temp_now) >= 2:
                await speak_translated(websocket,f"It feels like {feels_like}°C.", language)

            # Wind warning
            if wind_speed >= 20:
                await speak_translated(websocket,"Strong winds expected today. Please avoid spraying or working in open fields.", language)

            if weather_desc:
                await speak_translated(websocket,f"The weather is {weather_desc.replace('_', ' ')}.", language)

            if rain_chances:
                avg_rain_chance = sum(rain_chances) / len(rain_chances)
                await speak_translated(websocket,f"The average chance of rain today is {round(avg_rain_chance)}%.", language)

                # 4. Suggest actions based on rain
                if avg_rain_chance >= 60:
                    await speak_translated(websocket,"There is a high chance of rain today. Please avoid pesticide spraying.", language)
                elif avg_rain_chance <= 20:
                    await speak_translated(websocket,"It’s a dry day. A good time to water your crops.", language)
            else:
                await speak_translated(websocket,"Rain probability data for the day is not available.", language)

            # 3. Breakdown for the next 12 hours
            await speak_translated(websocket,"Here’s the rain forecast for today:", language)

            breakdown = {
                "Morning": (6, 12),
                "Afternoon": (12, 16),
                "Evening": (16, 20),
                "Night": (20, 24)
            }
            now = datetime.utcnow()
            for period, (start_hour, end_hour) in breakdown.items():
                chance = None
                for item in timeseries:
                    dt = datetime.fromisoformat(item["time"][:-1])
                    if dt.date() == today and start_hour <= dt.hour < end_hour:
                        rain_mm = item["data"].get("next_1_hours", {}).get("details", {}).get("precipitation_amount", 0)
                        if rain_mm is not None:
                            if rain_mm == 0:
                                chance = "no"
                            elif rain_mm < 0.5:
                                chance = "low"
                            elif rain_mm < 2:
                                chance = "moderate"
                            else:
                                chance = "high"
                            break
                if chance:
                    await speak_translated(websocket,f"{period}: {chance} chance of rain.", language)

        else:
            await speak_translated(websocket,"Weather data is not available right now.", language)

    except Exception as e:
        await speak_translated(websocket,"I couldn't fetch the weather data at the moment.", language)

async def sell_commodities(websocket,farmer,language):
    """Handles selling commodities and stores data in a separate collection."""
    await speak_translated(websocket,f"{farmer.get('name', 'Farmer')}, please say the name of the commodity you want to sell.",language)
    commodity = await recognize_speech()

    if not commodity:
        await speak_translated(websocket,"I couldn't understand. Please try again.",language)
        return sell_commodities(farmer)  # Retry
    commodity = commodity.lower().strip()
    while True:
        await speak_translated(websocket,f"How many kilograms of {commodity} do you want to sell?",language)    
        quantity = (await recognize_speech()).strip()
        if quantity is None:
            await speak_translated(websocket,"I couldn't understand the quantity. Please try again.",language)
            continue  # Retry input

        quantity = quantity.strip()

        try:
            quantity = float(quantity)  # Convert to a number
            if quantity <= 0:
                await speak_translated(websocket,"Quantity must be greater than zero. Please try again.",language)
                continue  # Retry input
            break  # Exit loop if input is valid
        except ValueError:
            await speak_translated(websocket,"Invalid quantity. Please say a number.",language)
            continue  # Retry input # Retry
    # Get live price of the commodity

    while True:
        await speak_translated(websocket,f"At what price per kilogram do you want to sell {commodity}?",language)
        price = await recognize_speech()

        if not price:
            await speak_translated(websocket,"I couldn't understand. Please repeat.",language)
            continue  # Ask again

        match = re.search(r"\d+(\.\d+)?", price)  # Extract numeric value
        if match:
            price = float(match.group())  # Convert to float
            if price > 0:
                break  # Valid price, exit loop
            else:
                await speak_translated(websocket,"Price must be greater than zero. Please try again.",language)
        else:
            await speak_translated(websocket,"Invalid price format. Please say a numeric value.",language)

    # **Store the sale details in the separate 'sales' collection**
    sale_entry = {
        "farmer_id": farmer["farmer_id"],
        "name": farmer["name"],
        "phone": farmer["phone"],
        "village":farmer["village"],
        "commodity": commodity,
        "quantity_kg": quantity,
        "price_per_kg": price,
        "total_price": quantity * price,
        "timestamp": local_time.strftime("%Y-%m-%d %H:%M:%S")
    }
    if check_internet():
        sales_collection.insert_one(sale_entry)  # ✅ Insert into MongoDB
        await speak_translated(websocket,f"Your {quantity} kg of {commodity} has been listed for sale at {price} per kg.",language)
    else:
        store_offline(sale_entry)  # 🚫 Save offline if no internet
        await speak_translated(websocket,"Your sale has been saved offline and will be uploaded once the internet is back.",language)

    return True  # ✅ Success
start_offline_sync()

async def request_help(websocket,farmer_id, language):
    # Ask the farmer for issue type
    await speak_translated(websocket,"Please tell us the type of issue. For example: registration issue, product sale problem, or technical support.", language)
    issue_type = await get_valid_input(language)

    # Ask for a brief description
    await speak_translated(websocket,"Thank you. Please briefly describe your issue.", language)
    issue_description = await get_valid_input(language)

    # Ask for urgency level
    await speak_translated(websocket,"How urgent is this issue? Say: high, medium, or low.", language)
    urgency = await get_valid_input(language)

    # Save the help request in MongoDB
    save_help_request(
        farmer_id=farmer_id,
        issue_type=issue_type,
        description=issue_description,
        urgency=urgency
    )

    # Confirm to the farmer
    await speak_translated(websocket,"We have received your help request. Our support team will contact you soon.", language)

def save_help_request(farmer_id, issue_type, description, urgency="medium"):
    help_request = {
        "farmer_id": farmer_id,
        "type": issue_type,
        "description": description,
        "urgency": urgency.lower(),
        "status": "pending",
        "timestamp": local_time.strftime("%Y-%m-%d %H:%M:%S")
    }
    help_requests_collection.insert_one(help_request)
    print(f"Help request saved: {help_request}")

import smtplib
from email.mime.text import MIMEText

async def emergency_alert_number_menu(websocket,farmer,farmer_id, language):
    # Speak the options to the user
    await speak_translated(websocket,"1. Flood or Rain Damage. 2. Wild Animal Attack. 3. Crop Theft. 4. Health Emergency. 5. Other Issue. Please say the number.", language)

    # Get the number from the user's voice
    response = await get_valid_input(language)
    number = extract_number_from_text(response)

    emergency_map = {
        1: "Flood or Rain Damage",
        2: "Wild Animal Attack",
        3: "Crop Theft",
        4: "Health Emergency",
        5: "Other Issue"
    }

    if number not in emergency_map:
        await speak_translated(websocket,"Invalid choice. Please try again.", language)
        return

    emergency_type = emergency_map[number]

    # Ask for a short voice description
    await speak_translated(websocket,"Please briefly describe your issue.", language)
    description = await get_valid_input(language)

    # Log to MongoDB
    from datetime import datetime
    incident_time = datetime.now()
    emergency_data = {
        "name": farmer["name"],
        "farmer_id": farmer["farmer_id"],
        "village": farmer["village"],
        "sub_district": farmer["sub_district"],
        "category": emergency_type,
        "description": description,
        "timestamp": incident_time,
        "status": "Reported"
    }
    emergency_collection.insert_one(emergency_data)
    # Confirm to the farmer
    await speak_translated(websocket,f"We have recorded your {emergency_type}. Help will be sent soon.", language)
    # Send alert to creator via email
    send_emergency_email(farmer, farmer_id,emergency_type, description, incident_time)

def extract_number_from_text(text):
    text = text.lower()
    words = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "1": 1, "2": 2, "3": 3, "4": 4, "5": 5
    }
    for word, num in words.items():
        if word in text:
            return num
    return None

from email.mime.text import MIMEText
import smtplib

def send_emergency_email(farmer, farmer_id, category, message, Time):
    sender = "ayushshekar045@gmail.com"
    receiver = [
        "deelakshadeekshith@gmail.com",
        "reddyadishesha015@gmail.com",
        "ayushgowda952@gmail.com",
        "lepakshaswamy60@gmail.com"
    ]
    
    subject = f"[Emergency Alert] {category} from Farmer {farmer.get('name')} (ID: {farmer_id})"

    body = f"""
🚨 Emergency Alert 🚨
Name: {farmer.get('name')}
Farmer ID: {farmer.get('farmer_id')}
Village: {farmer.get('village')}
Sub-District: {farmer.get('sub_district')}
Description: {message}
Time: {Time.strftime("%Y-%m-%d %H:%M:%S")}
    """

    msg = MIMEText(body)
    msg["From"] = sender
    msg["To"] = ", ".join(receiver)
    msg["Subject"] = subject

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.starttls()
            smtp.login(sender, "hhpu qvbz zfeu siqq")  # App password
            smtp.sendmail(sender, receiver, msg.as_string())
            print("✅ Emergency email sent successfully.")
    except Exception as e:
        print("❌ Email failed:", e)

async def return_or_exit(websocket,language, phone_number):
    await speak_translated(websocket,"Say 9 to return to the main menu or 0 to exit.", language)
    while True:
        response = await recognize_speech()
        number = extract_number(response)
        if response in ["exit", "quit", "stop", "number zero"]:
            await speak_translated(websocket,"Thank you for using AgriNex. Goodbye!", language)
            return  # Exit the function
        elif number == 9:
            await handle_farmer_interaction(websocket,phone_number, language,skip_phone_prompt=True)
            return
        elif number == 0:
            await speak_translated(websocket,"Thank you for using AgriNex. Goodbye!", language)
            return
        else:
            await speak_translated(websocket,"Invalid input. Please say 9 to return or 0 to exit.", language)

import uuid
# from fuzzywuzzy import fuzz

async def bulletproof_voice_menu(websocket,language):
    if language == "kn":
        instruction = "ದಯವಿಟ್ಟು ಸಂಖ್ಯೆಯನ್ನು ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ ಹೇಳಿ ಅಥವಾ ಕೀಪ್ಯಾಡ್‌ನಲ್ಲಿ ಒತ್ತಿ. ಉದಾಹರಣೆಗೆ 'number one' ಎಂದು ಹೇಳಿ ಅಥವಾ 1 ಒತ್ತಿ."
    elif language == "hi":
        instruction = "कृपया संख्या को अंग्रेज़ी में बोलें या कीपैड पर दबाएँ। जैसे 'number one' बोलें या 1 दबाएँ।"
    else:
        instruction = "Please say or press the number in English. For example, say 'number one' or press 1 on your keypad."
    await speak(instruction, lang=language)    
    prompt = """
    Say or press:
    1 - About Agrinex
    2 - How to Register
    3 - How to Sell
    4 - How to Buy
    5 - Is it Safe?
    9 - Go back
    0 - Exit
    """
    await speak_translated(websocket,prompt, language)

    response = await recognize_speech()
    if not response or not any(c.isdigit() for c in response):
        await speak_translated("I didn't catch that. You can also press the number on your keypad.", language)
        response = await recognize_speech()
        if not response or not any(c.isdigit() for c in response):
            response = await recognize_dtmf()

    if not response:
        await speak_translated(websocket,"Still didn't get that. Returning to main menu.", language)
        return await bulletproof_voice_menu(websocket,language)

    choice = ''.join(filter(str.isdigit, response.strip()))[:1]

    if choice == "1":
        await speak_translated(websocket,"Agrinex is a platform to help farmers connect directly with buyers. It's built to make farming more profitable and transparent.", language)
    elif choice == "2":
        await speak_translated(websocket,"Registration is easy. Just say your name, phone number, and district. You'll pick your sub-district, and village name based on first letter. Then you'll receive a unique farmer ID to login and track everything.", language)
    elif choice == "3":
        await speak_translated(websocket,"To sell, just say the product name, quantity, and your price. We'll list it and connect with interested buyers.", language)
    elif choice == "4":
        await speak_translated(websocket,"To buy, browse available products on our site or call and mention what you need. We'll connect you with sellers.", language)
    elif choice == "5":
        await speak_translated(websocket,"Yes, it's 100% safe. Agrinex verifies both buyers and sellers. All transactions are tracked.", language)
    elif choice == "9":
        return "back"
    elif choice == "0":
        await speak_translated(websocket,"Thank you for using Agrinex. Goodbye!", language)
        return "exit"
    else:
        await speak_translated(websocket,"Invalid choice. Please try again.", language)
    return await bulletproof_voice_menu(websocket,language)

def process_user_choice(farmer):
    """Capture the user's choice and execute the selected action."""
    while True:
        user_choice = recognize_speech()
        choice_index = extract_number(user_choice)
        if choice_index == 1:
            fetch_and_speak_weather(farmer)
        elif choice_index == 2:
            speak("Which crop's price do you want to check?")
            crop_name = recognize_speech()
            price = get_live_price(crop_name)
            if price:
                speak(f"The price of {crop_name} is ₹{price} per quintal.")
            else:
                speak("Sorry, I couldn't fetch the price right now.")
        elif choice_index == 3:
            speak("Processing...")
        elif choice_index == 4:
            speak("How can we assist you?")
        else:
            speak("Invalid choice. Please say a number from the list.")

connections = []
# Function to send printed messages to WebSocket
def websocket_print(websocket, message: str):
    # Send the message to all connected WebSocket clients
    for conn in connections:
        if conn != websocket:
            asyncio.create_task(conn.send_text(message))

class WebSocketPrinter(io.TextIOBase):
    def __init__(self, websocket, original_stdout):
        self.websocket = websocket
        self.original_stdout = original_stdout  # Keep the original terminal stdout

    def write(self, message: str):
        if message.strip():  # Avoid sending empty newlines
            import asyncio
            asyncio.create_task(self.websocket.send_text(message))
        
        # Also print normally to terminal
        self.original_stdout.write(message)
        self.original_stdout.flush()

    def flush(self):
        self.original_stdout.flush()

# **Main Loop**

async def main(websocket):
    print("Agent: Using local TTS with Pygame")
    sys.stdout = WebSocketPrinter(websocket, sys.stdout)
    # Language Selection
    language = await select_language(websocket)  # Choose language
    await speak_translated(websocket,"Welcome to AgriNex!", language)
    phone_number = None
    should_exit = False
    agent_response = "" 
    while not should_exit:
        if not phone_number:
            # Prompt user for registration or providing phone number
            await speak_translated(websocket,"Number 1: Register.", language)
            await speak_translated(websocket,"Number 2: If you are registered, provide your phone number.", language)

            user_input = await recognize_speech()

            if user_input:
                user_input = user_input.lower().strip()

                print(f"Recognized: {user_input}")  # Debugging step to see what was captured

                # Handle registration
                if user_input in ["register", "sign up", "number one", "one", "1", "number 1"]:
                    await speak_translated(websocket,"You chose to register.", language)
                    phone_number = await register_farmer_voice(websocket,language)

                    if phone_number:  # Registration successful
                        await handle_farmer_interaction(websocket,phone_number, language)
                        continue
                # Handle existing users
                elif user_input in ["number two", "two", "2", "number 2"]:
                    await speak_translated(websocket,"Please say your 10-digit phone number.", language)
                    phone_number, farmer = await handle_farmer_interaction(websocket,phone_number,language)
                    agent_response = f"Welcome back, Farmer {farmer.name}."
                    
                else:
                    await speak_translated(websocket,"Sorry, I didn't understand. Please say 'Number 1' to register or 'Number 2' to provide your phone number.", language)
                    agent_response = "Invalid input. Please say 'Number 1' or 'Number 2'."
                    continue  # Restart the loop if input is invalid

            if not phone_number:
                continue  # Restart if no valid phone number is obtained


        # **Chat Functionality**
        while True:
            user_input = await recognize_speech()
            if user_input:
                user_input = user_input.lower().strip()
                if user_input in ["exit", "quit", "stop"]:
                    await speak_translated(websocket,"Goodbye!", language)
                    should_exit = True  
                    break
                response = "I couldn't process your request. Please try again later."  # Placeholder response
                agent_response = response 
            await speak_translated(websocket,response, language)
        if should_exit:
            break
    return agent_response
if __name__ == "__main__": 
    os.environ["IS_LOCAL"] = "true"  # Set this as "false" in cloud environments

    print("Test Local Mode (Pygame):")
    speak("Hello, this is a local test!", 'en')

    print("\nTest Cloud Mode (gTTS):")
    os.environ["IS_LOCAL"] = "false"  # Switch to cloud
    speak("Hello, this is a cloud test!", 'en')
