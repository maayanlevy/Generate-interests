import json
import os
import csv
import boto3
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List
import pydantic

# Constants
PYDANTIC_V2 = pydantic.VERSION.startswith("2.")
S3_BUCKET_NAME = 'travelogueit-code'
S3_FILE_NAME = 'interests.csv'

# Initialize S3 client
s3_client = boto3.client('s3')

# Load interests from S3 CSV file
def load_interests_from_s3(bucket_name, file_name):
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=file_name)
        content = response['Body'].read().decode('utf-8').splitlines()
        reader = csv.reader(content)
        return [row[0] for row in reader if row]  # Assuming interests are in the first column
    except Exception as e:
        raise ValueError(f"Error loading interests from S3: {e}")

INTERESTS = load_interests_from_s3(S3_BUCKET_NAME, S3_FILE_NAME)

# Pydantic models for structured output
class Interest(BaseModel):
    main_interest: str
    sub_interests: List[str]

class PlaceInterests(BaseModel):
    interests: List[Interest] = Field(..., min_items=1)

def validate_json(json_data, model):
    if PYDANTIC_V2:
        return model.model_validate_json(json_data)
    else:
        return model.parse_raw(json_data)

# Function to generate interests using OpenAI API
def generate_interests(place_details, openai_api_key):
    prompt = f"""
    Based on the following place details, generate a list of interests and sub-interests that match this location. 
    Choose only from the provided list of interests.

    Place Details:
    Name: {place_details.get('name', 'N/A')}
    Address: {place_details.get('formatted_address', 'N/A')}
    Types: {', '.join(place_details.get('types', []))}
    Description: {place_details.get('editorial_summary', {}).get('overview', 'N/A')}

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
    Ensure that you include only interests from the provided list.
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

    try:
        parsed_json = json.loads(content)
        return validate_json(json.dumps(parsed_json), PlaceInterests)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON returned by API: {e}")
    except pydantic.ValidationError as e:
        raise ValueError(f"API response doesn't match expected structure: {e}")

# Lambda handler
def lambda_handler(event, context):
    place_details = event.get("place_details")
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    
    if not place_details or not openai_api_key:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing required parameters"})
        }
    
    try:
        interests = generate_interests(place_details, openai_api_key)
        return {
            "statusCode": 200,
            "body": interests.json()
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
