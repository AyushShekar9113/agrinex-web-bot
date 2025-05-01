from datetime import datetime
from pymongo import MongoClient
import pytz

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")  # Update with your MongoDB URI if needed
db = client["agrinex"]  # Database name
farmers_collection = db["farmers"]  # Collection name

def generate_farmer_id(phone):
    """Generates a unique farmer ID using the last 4 digits of the phone number."""
    return f"F{phone[-4:]}"

def register_farmer(name, phone, district, sub_district, village):
    """Registers a new farmer with location details and returns their unique ID."""
    existing_farmer = farmers_collection.find_one({"phone": phone})
    
    if existing_farmer:
        return existing_farmer["farmer_id"]  # Farmer already registered
    
    farmer_id = generate_farmer_id(phone)
    new_farmer = {
        "farmer_id": farmer_id,
        "name": name,
        "phone": phone,
        "district": district,
        "sub_district": sub_district,
        "village": village,
        "registered_on": datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S"),
    }
    
    farmers_collection.insert_one(new_farmer)  # Insert into MongoDB
    return farmer_id



# from pymongo import MongoClient

# client = MongoClient("mongodb://localhost:27017/")
# db = client["agrinex"]  # Replace with your DB name
# collection = db["villages"]  # Replace with your collection name

# # villages = collection.find({"sub_district": "Dengaikote"}, {"_id": 0, "village_name": 1})

# # for village in villages:
# #     print(village)  # Ensure output is displayed

# print(db.villages.find_({"District": "Kodagu"}))  # ✅ Correct method name

# from pymongo import MongoClient

# client = MongoClient("mongodb://localhost:27017/")  # Adjust if needed
# db = client["agrinex"]  # Ensure this matches your DB name
# collection = db["villages"]  # Ensure this matches your collection name

# query = {"District": "Kodagu"}
# records = list(collection.find(query))

# if records:
#     print("Records found:", records)
# else:
#     print("No records found for Kodagu")

