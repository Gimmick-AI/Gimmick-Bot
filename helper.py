import settings
import requests
import json
import bardapi

logger = settings.logging.getLogger("bot")

def get_generated_text(prompt):
    # The API endpoint
    api_endpoint = settings.API_ENDPOINT
    
    # Prepare the payload and headers for the API request
    payload = {'prompt': prompt}
    headers = {'Content-Type': 'application/json'}

    try:
        # Send the request to the API with a timeout of 300 seconds
        response = requests.post(api_endpoint, headers=headers, json=payload, timeout=300)

        # Parse the JSON response
        data = json.loads(response.text)

        # Get the generated text from the response
        generated_text = data['output']

        return generated_text
    except Exception as e:
        logger.error(f"Failed to get response from API: {e}")
        return None

def split_response_into_messages(response):
    words = response.split()
    messages = []
    current_message = ""
    for word in words:
        if len(current_message) + len(word) + 1 <= 1900:  # Check if adding the word exceeds the character limit
            current_message += word + " "
        else:
            messages.append(current_message)
            current_message = word + " "
    messages.append(current_message)
    return messages

def get_ratio(x):
    if x == "1:1":
        height = 512
        width = 512
    elif x == "2:3":
        height = 768
        width = 512
    elif x == "3:2":
        height = 512
        width = 768
    elif x == "3:4":
        height = 680
        width = 512
    elif x == "4:3":
        height = 528
        width = 704
    elif x == "9:16":
        height = 904
        width = 512
    elif x == "16:9":
        height = 512
        width = 904
    else:
        height = 512
        width = 512
    return height, width