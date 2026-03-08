import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Read the MONGO_URI from the environment variables
MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable is not set. Please define it in your .env file.")

# Initialize the MongoDB client
client = MongoClient(MONGO_URI)

# Default to "ai_emergency_monitoring" if no database is defined in the URI
db = client.get_default_database(default="ai_emergency_monitoring")

def get_db():
    """Returns the database instance."""
    return db