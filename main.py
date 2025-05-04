import os
import cohere
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
load_dotenv()

cohere_key = os.environ.get('key2')
co = cohere.ClientV2(cohere_key)

API_KEY = os.environ.get('key')
MAX_CLAIMS = 3
print("API_KEY loaded:", API_KEY)
  

def fetch_claims(query):
    try:
        service = build("factchecktools", "v1alpha1", developerKey=API_KEY)
        request = service.claims().search(query=query)
        return request.execute()
    except HttpError as err:
        print(f"❌ Google Fact Check API error: {err}")
    except Exception as e:
        print(f"⚠️ Unexpected error: {e}")
    return None

def cohere_response(user_input):
    google_fact = fetch_claims(user_input)
    if google_fact:
        response = co.chat(
            model="command-r-plus",
            messages=[{"role": "user", "content": f"Based on {google_fact}, evaluate the truth of {user_input} on a scale of 1-10 and explain why. Three sentences max. Make sure to include a source and link"}],
        )
        return response
    response = co.chat(
        model="command-r-plus",
        messages=[{"role": "user", "content":f"Evaluate the truth of {user_input} based on your knowledge on a scale of 1-10 and explain YOUR RATING. If you can't confidently answer, respond :Unable to verify this claim. "}],
    )
    return response
def extract_text_manually(response):
    response_str = str(response)
    try:
        start = response_str.index("text='") + len("text='")
        end = response_str.index("')", start)
        return response_str[start:end]
    except ValueError as e:
        print(f"❌ Could not parse text from response: {e}")
        return None

def main():
    user_query = input("Enter a query to fact-check: ").strip()
    if not user_query:
        print("⚠️ You must enter a query!")
        return

    print(f"🔍 Querying for: “{user_query}”")
    response = cohere_response(user_query)
    result = extract_text_manually(response)

    if result:
        print(result)
    else:
        print("❌ No usable text extracted.")


if __name__ == "__main__":
    main()
