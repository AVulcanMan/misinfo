import os
import cohere
import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# Load API keys
load_dotenv()
if not st.secrets:
    from dotenv import load_dotenv
    load_dotenv()
    API_KEY = os.getenv("key")
    cohere_key = os.getenv("key2")
else:
    # For Streamlit Cloud
    API_KEY = st.secrets["key"]
    cohere_key = st.secrets["key2"]

# Initialize Cohere client
co = cohere.ClientV2(cohere_key)

# Fetch Google Fact Check claims
def fetch_claims(query):
    try:
        service = build("factchecktools", "v1alpha1", developerKey=API_KEY)
        request = service.claims().search(query=query)
        return request.execute()
    except HttpError as err:
        st.error(f"❌ Google Fact Check API error: {err}")
    except Exception as e:
        st.error(f"⚠️ Unexpected error: {e}")
    return None

# Generate response using Cohere
def cohere_response(user_input):
    google_fact = fetch_claims(user_input)
    if google_fact:
        response = co.chat(
            model="command-r-plus",
            messages=[{"role": "user", "content": f"Based on {google_fact}, evaluate the truth of '{user_input}' on a scale of 1-10 and explain why. Three sentences max. Make sure to include a source and link.ALWAYS being your answer with a Rating: (score)/10."}]
        )
    else:
        response = co.chat(
            model="command-r-plus",
            messages=[{"role": "user", "content": f"Evaluate the truth of '{user_input}' based on your knowledge on a scale of 1-10 and explain YOUR RATING. Explain how confident you are in your answer. ALWAYS being your answer with a Rating: (score)/10."}]
        )
    print(response)
    return response

# Extract Cohere response text
def extract_text_manually(response):
    response_str = str(response)
    try:
        start = response_str.index("text='") + len("text='")
        end = response_str.index("')", start)
        raw_text = response_str[start:end]
        cleaned_text = raw_text.replace('\\n', ' ').replace('\n', ' ').strip()
        return cleaned_text
    except ValueError as e:
        st.error(f"❌ Could not parse text from response: {e}")
        return None
def extract_rating(response):
    response_str = str(response)
    start = response_str.index("Rating:") + len("Rating:")
    end = response_str.index("/", start)
    text_rating = response_str[start:end]
    rating = int(text_rating)
    return rating
# Streamlit UI
st.title("🕵️‍♂️ AI-Powered Fact Checker")
user_query = st.text_input("Enter a claim to fact-check:", "")

if st.button("Check Fact"):
    if not user_query.strip():
        st.warning("⚠️ You must enter a query!")
    else:
        st.info(f"🔍 Checking claim: “{user_query}”")
        response = cohere_response(user_query)
        rating = extract_rating(response)
        result = extract_text_manually(response)
        if result and rating:
            st.success("✅ Fact-Check Result:")
            st.subheader("🧠 Truth Rating")
            st.progress(rating / 10)
            st.caption(f"Score: {rating}/10")
            st.write(result)
        else:
            st.error("❌ No usable text extracted.")
