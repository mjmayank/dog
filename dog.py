import requests
import base64
import openai
import json
from datetime import datetime
import time

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
                            "text": """Analyze this indoor pet camera image and provide a JSON response with the following information:

1. Dog presence and location
2. Dog's activity/behavior (Don't confuse the lamby plush toy with the dog. The dog is apricot colored)
3. Any safety concerns or signs of distress. Pay special attention to items left on the coffee table that should not normally be there. Glasses of water are okay.
4. Cleanliness or safety issues such as dangerous items or foods in reach (messes, food on table, spilled food/water, scattered toys)
5. Overall assessment

Format as JSON with fields: dog_present, location, activity, safety_concerns, cleanliness_issues, overall_assessment, timestamp"""
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
            if result.get('safety_concerns'):
                print(f"\n🚨 SAFETY ALERT: {result['safety_concerns']}")
            
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
