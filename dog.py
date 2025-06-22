import requests
import base64
import openai
import json
from datetime import datetime
import time
from dotenv import load_dotenv
import os
from twilio.rest import Client
import argparse

load_dotenv()
# Configuration
CAMERA_URL = "http://localhost:5000/snapshot/pet-cam.jpg"
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_FROM_NUMBER = os.getenv('TWILIO_FROM_NUMBER')
TWILIO_TO_NUMBER = os.getenv('TWILIO_TO_NUMBER')
TWILIO_SERVICE_SID = os.getenv('TWILIO_SERVICE_SID')

# Pushover Configuration
PUSHOVER_API_TOKEN = os.getenv('PUSHOVER_API_TOKEN')
PUSHOVER_USER_KEY = os.getenv('PUSHOVER_USER_KEY')

# Initialize OpenAI client
openai.api_key = OPENAI_API_KEY
# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN else None

def capture_image():
    """Capture image from the camera snapshot endpoint"""
    try:
        response = requests.get(CAMERA_URL, timeout=10)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        print(f"Error capturing image: {e}")
        return None

def encode_image_base64(image_data):
    """Convert image data to base64 string"""
    return base64.b64encode(image_data).decode('utf-8')

def send_text_alert(message):
    """Sends a text message via Twilio."""
    if not twilio_client or not TWILIO_TO_NUMBER or not TWILIO_FROM_NUMBER:
        print("Twilio credentials not fully set. Cannot send text alert.")
        print(f"Message: {message}")
        return

    try:
        message_body = f"Dog Cam Alert:\n\n{message}"

        message = twilio_client.messages.create(
            body=message_body, from_=TWILIO_FROM_NUMBER, to=TWILIO_TO_NUMBER
        )
        print(f"Sent text message SID: {message.sid}")
    except Exception as e:
        print(f"Error sending text message via Twilio: {e}")

def send_pushover_alert(message, title="Dog Cam Alert"):
    """Sends a notification via Pushover."""
    if not PUSHOVER_API_TOKEN or not PUSHOVER_USER_KEY:
        print("Pushover credentials not set. Cannot send notification.")
        print(f"Title: {title}")
        print(f"Message: {message}")
        return

    try:
        payload = {
            "token": PUSHOVER_API_TOKEN,
            "user": PUSHOVER_USER_KEY,
            "message": message,
            "title": title
        }
        response = requests.post("https://api.pushover.net/1/messages.json", data=payload, timeout=10)
        response.raise_for_status()
        print("Sent Pushover notification successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Error sending Pushover notification: {e}")

def analyze_image_with_gpt(image_data):
    """Send image to ChatGPT for analysis"""
    base64_image = encode_image_base64(image_data)

    try:
        response = openai.chat.completions.create(
            model="gpt-4o",  # Use gpt-4o for vision capabilities
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                """
Analyze this indoor pet camera image and provide a JSON response in the following format:

{
  isDanger: boolean,
  isViewObstructed: boolean,
  isDogPresent: boolean,
  dog_location: string,
  dog_activity: string,
  safety_concerns: string,
  cleanliness_issues: string,
  coffee_table_items: string,
  overall_assessment: string
}

Instructions for each field:
- isDanger: true if there are any safety concerns or signs of distress, otherwise false. Safety concerns include items and food left on the coffee table, sofa, or on the ground that could be dangerous to a dog. Glasses of water are fine but ANY food, food containers, or food wrappers are a danger. Chocolate and items containing chocolate are dangerous.
- isViewObstructed: true if there are large objects in the foreground or any part of the coffee table is blocked by furniture, objects, or people that prevent a clear view of the top surface — even partially. For example, if a chair, stool, or large object is blocking part of the table from the camera's point of view, mark this as true. If the entire top surface of the coffee table is clearly visible and unobstructed, mark it as false.
- isDogPresent: true if the dog is present, otherwise false. (Don't confuse the lamby plush toy with the dog. The dog is apricot/brown colored. The dog is not white)
- dog_location: Describe where the dog is in the room.
- dog_activity: Describe the dog's activity or behavior. (Don't confuse the lamby plush toy with the dog. The dog is apricot colored.)
- safety_concerns: List any safety concerns or signs of distress. Pay special attention to items left on the coffee table that should not normally be there. Glasses of water are okay.
- coffee_table_items: List any items on the coffee table that should not normally be there.
- overall_assessment: Provide an overall summary of what the dog is doing.

Return only the JSON object as your response.
                                """
                            )
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500,
            response_format={"type": "json_object"}
        )

        return response.choices[0].message.content

    except Exception as e:
        print(f"Error analyzing image with GPT: {e}")
        return None

def main():
    """Main function to capture and analyze image"""
    print(f"Starting pet camera analysis at {datetime.now()}")

    # Capture image
    print("Capturing image...")
    image_data = capture_image()

    if image_data is None:
        print("Failed to capture image. Exiting.")
        return

    print(f"Image captured successfully ({len(image_data)} bytes)")

    # Analyze with ChatGPT
    print("Analyzing with ChatGPT...")
    analysis = analyze_image_with_gpt(image_data)

    if analysis:
        try:
            # Parse JSON response
            result = json.loads(analysis)
            result['timestamp'] = datetime.now().isoformat()

            print("\n" + "="*50)
            print("ANALYSIS RESULTS:")
            print("="*50)
            print(json.dumps(result, indent=2))

            # Check for alerts
            if result.get('isDanger'):
                print(f"\n🚨 SAFETY ALERT: ")
            else:
                print(f"\nNO SAFETY ALERT: ")
            print(f" {result.get('safety_concerns', '')}")

            if result.get('cleanliness_issues'):
                print(f"🧹 CLEANLINESS NOTICE: {result['cleanliness_issues']}")

            # New logic to send text
            if result.get('isViewObstructed') or result.get('isDanger') or os.getenv('ENV') == 'dev':
                print("\nSending notification alert...")
                alert_message = json.dumps(result, indent=2)
                # send_text_alert(alert_message)
                send_pushover_alert(alert_message)

        except json.JSONDecodeError:
            print("Error parsing JSON response:")
            print(analysis)
    else:
        print("Failed to get analysis from ChatGPT")

def continuous_monitoring(interval_minutes=5):
    """Run continuous monitoring every X minutes"""
    print(f"Starting continuous monitoring (every {interval_minutes} minutes)")
    print("Press Ctrl+C to stop")

    try:
        while True:
            main()
            print(f"\nWaiting {interval_minutes} minutes until next check...")
            time.sleep(interval_minutes * 60)
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pet camera monitoring script.")
    parser.add_argument(
        "-i", "--interval",
        type=int,
        default=5,
        help="The interval in minutes for continuous monitoring. Default is 5."
    )
    args = parser.parse_args()

    if args.interval:
        continuous_monitoring(interval_minutes=args.interval)
    else:
        print("Running a single analysis.")
        main()
