import streamlit as st
import requests
import json
import csv
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List
import pydantic

# Check Pydantic version
PYDANTIC_V2 = pydantic.VERSION.startswith("2.")

# Constants
GOOGLE_PLACE_DETAILS_URL = 'https://maps.googleapis.com/maps/api/place/details/json'

# Load interests from the CSV file
@st.cache_data
def load_interests_from_csv(file_path):
    with open(file_path, 'r') as f:
        reader = csv.reader(f)
        return [row[0] for row in reader if row]  # Assuming interests are in the first column

INTERESTS = load_interests_from_csv('interests.csv')

# Pydantic model for structured output
class Interest(BaseModel):
    main_interest: str
    sub_interests: List[str]

class PlaceInterests(BaseModel):
    interests: List[Interest] = Field(..., min_items=1)

# Function to get JSON schema
def get_json_schema(model):
    if PYDANTIC_V2:
        return model.model_json_schema()
    else:
        return model.schema()

# Function to validate JSON
def validate_json(json_data, model):
    if PYDANTIC_V2:
        return model.model_validate_json(json_data)
    else:
        return model.parse_raw(json_data)

# Function to get place details from Google Places API
def get_place_details(place_id, google_api_key):
    params = {
        'place_id': place_id,
        'fields': 'name,formatted_address,types,editorial_summary',
        'key': google_api_key
    }
    response = requests.get(GOOGLE_PLACE_DETAILS_URL, params=params)
    return response.json()

# Function to generate interests using OpenAI API
def generate_interests(place_details, openai_api_key):
    prompt = f"""
    Based on the following place details, generate a list of interests and sub-interests that match this location. 
    Choose only from the provided list of interests.

    Place Details:
    Name: {place_details['result'].get('name', 'N/A')}
    Address: {place_details['result'].get('formatted_address', 'N/A')}
    Types: {', '.join(place_details['result'].get('types', []))}
    Description: {place_details['result'].get('editorial_summary', {}).get('overview', 'N/A')}

    Provided list of interests:
    {', '.join(INTERESTS)}

    Generate the response in a structured JSON format with the following structure:
    {{
        "interests": [
            {{
                "main_interest": "Interest Category",
                "sub_interests": ["Sub-interest 1", "Sub-interest 2", ...]
            }},
            ...
        ]
    }}
    Ensure that you include at least one interest in the list.
    """

    client = OpenAI(api_key=openai_api_key)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that generates structured data about place interests."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    st.write("Debug - API Response:", content)  # Debug output

    try:
        parsed_json = json.loads(content)
        return validate_json(json.dumps(parsed_json), PlaceInterests)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON returned by API: {e}")
    except pydantic.ValidationError as e:
        raise ValueError(f"API response doesn't match expected structure: {e}")

# Streamlit app
st.title("Place Interests Generator")

# Input for Google Place ID
place_id = st.text_input("Enter Google Place ID:")

# Input for Google API Key
google_api_key = st.text_input("Enter Google API Key:", type="password")

# Input for OpenAI API Key
openai_api_key = st.text_input("Enter OpenAI API Key:", type="password")

if st.button("Generate Interests"):
    if place_id and google_api_key and openai_api_key:
        # Get place details
        place_details = get_place_details(place_id, google_api_key)
        
        if place_details['status'] == 'OK':
            st.subheader("Place Details:")
            st.write(f"Name: {place_details['result'].get('name', 'N/A')}")
            st.write(f"Address: {place_details['result'].get('formatted_address', 'N/A')}")
            st.write(f"Types: {', '.join(place_details['result'].get('types', []))}")
            st.write(f"Description: {place_details['result'].get('editorial_summary', {}).get('overview', 'N/A')}")

            # Generate interests
            try:
                interests = generate_interests(place_details, openai_api_key)
                
                st.subheader("Generated Interests:")
                for interest in interests.interests:
                    st.write(f"- {interest.main_interest}")
                    for sub_interest in interest.sub_interests:
                        st.write(f"  - {sub_interest}")
            except Exception as e:
                st.error(f"Error generating interests: {str(e)}")
        else:
            st.error(f"Error fetching place details: {place_details['status']}")
    else:
        st.warning("Please enter Google Place ID, Google API Key, and OpenAI API Key.")

# Instructions
st.markdown("""
## How to use:
1. Ensure you have all required packages installed. You can do this by running:
   ```
   pip install -r requirements.txt
   ```
2. Enter a valid Google Place ID. You can find Place IDs using the [Google Places API Place ID Finder](https://developers.google.com/maps/documentation/places/web-service/place-id).
3. Enter your Google API Key.
4. Enter your OpenAI API Key.
5. Click "Generate Interests" to fetch place details and generate matching interests.

Note: Make sure you have the necessary API keys and permissions to use Google Places API and OpenAI API.

## Files in this project:
- `app.py`: The main Streamlit application file.
- `interests.csv`: CSV file containing the list of interests.
- `requirements.txt`: List of Python packages required to run this application.
""")