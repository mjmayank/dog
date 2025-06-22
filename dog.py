import requests
import base64
import openai
import json
from datetime import datetime
import time
from dotenv import load_dotenv
import os

load_dotenv()
# Configuration
CAMERA_URL = "http://localhost:5000/snapshot/pet-cam.jpg"
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Initialize OpenAI client
openai.api_key = OPENAI_API_KEY

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
- isViewObstructed: true if the coffee table is not in the frame or there is not a full unobstructed view of the top of the coffee table. Otherwise false.
- isDogPresent: true if the dog is present, otherwise false. (Don't confuse the lamby plush toy with the dog. The dog is apricot colored.)
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
                print(f"\n🧹 CLEANLINESS NOTICE: {result['cleanliness_issues']}")

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
    # For single analysis, run:
    main()

    # For continuous monitoring, uncomment this line:
    # continuous_monitoring(interval_minutes=5)
