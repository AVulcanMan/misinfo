import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

api_key = "AIzaSyBR9F-7xOy_LGT7oxygq6hZq0zu6NHFgzQ"

MAX_CLAIMS = 3

def build_table_row(claim):
    review = claim.get("claimReview", [{}])[0]
    publisher = review.get("publisher", {}).get("name", "Unknown Source")
    rating = review.get("textualRating", "No Rating")
    url = review.get("url", "#")
    claim_text = claim.get("text", "No claim text found")
    
    return f"| _{claim_text}_ | **{rating}** | [{publisher}]({url}) |"

def build_message(response):
    if "claims" in response and response["claims"]:
        print("\nAttempting to curate up to 3 relevant fact-checked claims:\n")
        print("| Claim | Rating | Source |")
        print("|:-|:-|:-|")
        for i, claim in enumerate(response["claims"][:MAX_CLAIMS]):
            print(build_table_row(claim))
    else:
        print("\n❌ No fact-checked claims found for that query.")

def main():
    user_query = input("Enter a query to fact-check: ").strip()
    if not user_query:
        print("⚠️ You must enter a query!")
        return

    try:
        service = build("factchecktools", "v1alpha1", developerKey=api_key)
        request = service.claims().search(query=user_query)
        response = request.execute()
        build_message(response)
    except HttpError as err:
        print(f"Google Fact Check API error: {err}")

if __name__ == "__main__":
    main()
