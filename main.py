import os
import cohere
import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
import re
import json
import praw
import pandas as pd
import requests

# Load API keys
load_dotenv()
if not st.secrets:
    from dotenv import load_dotenv
    load_dotenv()
    API_KEY = os.getenv("key")
    cohere_key = os.getenv("key2")
else:
    API_KEY = st.secrets["key"]
    cohere_key = st.secrets["key2"]
se_user = st.secrets["se_user"]
se_secret = st.secrets["se_secret"]

# Initialize Cohere client
co = cohere.ClientV2(cohere_key)
# Initialize Reddit
reddit = praw.Reddit(
    client_id=st.secrets["reddit_id"],
    client_secret= st.secrets["reddit_secret"],
    user_agent=st.secrets["reddit_agent"],
)
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
            messages=[{"role": "user", "content": f"Based on {google_fact}, evaluate the truth of '{user_input}' on a scale of 1-10 and explain why. Three sentences max. Make sure to include the google fact check links.ALWAYS begin your answer with a Rating: (score)/10."}]
        )
    else:
        response = co.chat(
            model="command-r-plus",
            messages=[{"role": "user", "content": f"Evaluate the truth of '{user_input}' based on your knowledge on a scale of 1-10 and explain YOUR RATING.  ALWAYS begin your answer with a Rating: (score)/10."}]
        )
    print(response)
    return response
reddit_icon_url = "https://th.bing.com/th/id/OIP.khATfz1EKTtDrzIWUsmvLwHaHa?rs=1&pid=ImgDetMain"

def get_reddit_comments(claim, subreddits=["conservative", "conspiracy"], limit=20):
    """Fetch Reddit comments from given subreddits that partially match the claim from the past year."""
    comments_data = []
    search_query = claim  # partial match search
    claim_words = [word.lower() for word in re.findall(r'\w+', claim)]

    for sub in subreddits:
        subreddit = reddit.subreddit(sub)
        for submission in subreddit.search(search_query, sort="hot", limit=limit):
            submission.comments.replace_more(limit=0)
            for comment in submission.comments[:20]:
                comment_text = comment.body.lower()
                match_count = sum(word in comment_text for word in claim_words)
                if match_count >= 2:
                    comments_data.append({
                        "subreddit": sub,
                        "post_title": submission.title,
                        "comment": comment.body,
                        "score": comment.score,
                        "permalink": f"https://reddit.com{comment.permalink}"
                    })
    return comments_data


# Extract Cohere response text
def extract_text_manually(response):
    response_str = str(response)
    try:
        match = re.search(r'text=(["\'])(.*?)\1', response_str, re.DOTALL)
        if match:
            raw_text = match.group(2)
            cleaned_text = raw_text.replace('\\n', ' ').replace('\n', ' ').strip()
            cleaned_text = re.sub(r"Rating:\s*\d{1,2}/10\s*", "", cleaned_text, count=1, flags=re.IGNORECASE)
            return cleaned_text
        else:
            raise ValueError("Pattern not found")
    except ValueError as e:
        st.error(f"❌ Could not parse text from response: {e}")
        return None

def extract_rating(response):
    response_str = str(response)
    match = re.search(r'Rating:\s*(\d{1,2})/10', response_str)
    if match:
        rating = int(match.group(1))
        return rating
    else:
        print("❌ Could not find rating in response")
        return None

def interpret_rating(rating):
    if rating <= 2:
        return "❌ False"
    elif rating <= 4:
        return "⚠️ Most Likely False"
    elif rating <= 6:
        return "❓ Mixed: Both True and False"
    elif rating <= 8:
        return "✅ Likely True"
    else:
        return "✅ True"

# Initialize history
if "history" not in st.session_state:
    st.session_state.history = []

# Streamlit UI with navigation
st.sidebar.title("🕵️‍♂️ AI-Powered Fact Checker 🕵️‍♂️")
page = st.sidebar.radio("Go to", ["Fact Checker", "Past Claims"])

if page == "Fact Checker":
    st.title("🕵️‍♂️ AI-Powered Fact Checker 🕵️‍♂️")
    user_query = st.text_input("Enter a claim to fact-check:", "")

    if st.button("Check Fact"):
        if not user_query.strip():
            st.warning("⚠️ You must enter a query!")
        else:
            st.info(f"🔍 Checking claim: “{user_query}”")
            response = cohere_response(user_query)
            rating = extract_rating(response)
            result = extract_text_manually(response)

            if result and rating is not None:
                interpretation = interpret_rating(rating)
                st.success("✅ Fact-Check Result:")
                st.subheader("🧠 Truth Rating")
                st.progress(rating / 10)
                st.markdown(f"## 🧾 Interpretation: {interpretation}")
                st.markdown(f"**Score: {rating}/10**")
                cleaned_result = re.sub(r'https?://\S+', '', result).strip()
                st.write(cleaned_result)

                urls = re.findall(r'https?://\S+', result)
                if urls:
                    st.markdown("**Sources:**")
                    for url in urls:
                        st.markdown(f"- [{url}]({url})")

                st.session_state.history.append({
                    "claim": user_query,
                    "rating": rating,
                    "interpretation": interpretation,
                    "result": result
                })

                # 🧵 Reddit Comments
                st.divider()
                st.markdown(
    f"""
    <h3>
        <img src="{reddit_icon_url}" width="30" style="vertical-align:middle; margin-right:8px;">
        <span style="vertical-align:middle;">Reddit Reactions</span>
    </h3>
    """,
    unsafe_allow_html=True
)
                reddit_comments = get_reddit_comments(user_query)
                if reddit_comments:
                    for entry in reddit_comments:
                        st.markdown(f"**Post:** {entry['post_title']}")
                        st.markdown(f"🔗 [View comment]({entry['permalink']}) — 👍 {entry['score']}")
                        st.write(entry['comment'])
                        st.markdown("---")
                else:
                    st.info("No relevant Reddit comments found.")
            else:
                st.error("❌ No usable text extracted.")
                st.write(cohere_response(user_query))

elif page == "Past Claims":
    st.title("📜 Past Fact-Checks")
    if st.session_state.history:
        st.markdown("### 🔎 Search Past Claims")
        search_term = st.text_input("Search claims:", key="search")
        for entry in reversed(st.session_state.history):
            if search_term.lower() in entry["claim"].lower():
                st.markdown(f"### 📝 {entry['claim']}")
                st.markdown(f"**Rating:** {entry['rating']}/10 — {entry['interpretation']}")
                cleaned_result = re.sub(r'https?://\S+', '', entry['result']).strip()
                st.markdown(f"**Result:** {cleaned_result}")
                urls = re.findall(r'https?://\S+', entry['result'])
                if urls:
                    st.markdown("**Sources:**")
                    for url in urls:
                        st.markdown(f"- [{url}]({url})")
                st.markdown("---")

        st.download_button(
            label="📥 Download History",
            data=json.dumps(st.session_state.history, indent=2),
            file_name="fact_check_history.json",
            mime="application/json"
        )

        if st.button("🧹 Clear History"):
            st.session_state.history.clear()
            st.success("History cleared!")
    else:
        st.info("No past fact-checks available.")

