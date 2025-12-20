#!/usr/bin/env python3
import os
from dotenv import load_dotenv
load_dotenv()
from notion_client import Client

NOTION_TOKEN = os.getenv('NOTION_TOKEN')
NOTION_DB_ID = os.getenv('NOTION_DB_ID')
print(f"Token present: {bool(NOTION_TOKEN)}")
print(f"DB ID: {NOTION_DB_ID}")

if NOTION_TOKEN:
    notion = Client(auth=NOTION_TOKEN)
    print("Client created")
    # Try to list databases to see if connection works
    try:
        # Check if databases has query
        print("Databases attributes:", dir(notion.databases))
        print("Has query?", hasattr(notion.databases, 'query'))
        # Try to call query
        response = notion.databases.query(database_id=NOTION_DB_ID, filter={})
        print("Query succeeded")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
else:
    print("No token")