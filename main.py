import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
load_dotenv()
# Replace with your own API key
API_KEY = os.environ.get('key')
MAX_CLAIMS = 3
print("API_KEY loaded:", API_KEY)
def build_table_row(claim):
    review = claim.get("claimReview", [{}])[0]
    publisher = review.get("publisher", {}).get("name", "Unknown Source")
    rating = review.get("textualRating", "No Rating")
    url = review.get("url", "#")
    claim_text = claim.get("text", "No claim text found")
    
    return f"| _{claim_text}_ | **{rating}** | [{publisher}]({url}) |"

def build_message(response, user_query):
    if "claims" in response and response["claims"]:
        print("\nAttempting to curate up to 3 relevant fact-checked claims:\n")
        print("| Claim | Rating | Source |")
        print("|:-|:-|:-|")

        curated_claims = []
        for i, claim in enumerate(response["claims"][:MAX_CLAIMS]):
            print(build_table_row(claim))
            curated_claims.append(claim)

        # --- Final Verdict Summary ---
        print("\n--- Final Verdict ---")
        most_relevant = curated_claims[0]
        review = most_relevant.get("claimReview", [{}])[0]
        print(f"🔎 Based on the most relevant claim:")
        print(f"- **Claim:** _{most_relevant.get('text', 'No claim text found')}_")
        print(f"- **Rating:** **{review.get('textualRating', 'No Rating')}**")
        print(f"- **Source:** [{review.get('publisher', {}).get('name', 'Unknown Source')}]({review.get('url', '#')})")
    else:
        print("\n❌ No fact-checked claims found for that query.")
        print(f"\n--- Final Verdict ---")
        print(f"No fact-checks found for the query: “{user_query}”. Consider consulting reputable sources manually.")

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

def main():
    user_query = input("Enter a query to fact-check: ").strip()
    if not user_query:
        print("⚠️ You must enter a query!")
        return

    print(f"🔍 Querying for: “{user_query}”")
    response = fetch_claims(user_query)
    if response:
        build_message(response, user_query)

if __name__ == "__main__":
    main()
