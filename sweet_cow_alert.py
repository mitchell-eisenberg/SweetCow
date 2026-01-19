import requests
from bs4 import BeautifulSoup
import json
import os

URL = "https://sweetcow.com/stanley-marketplace/"
CONFIG_FILE = "watched_flavors.json"

def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def scrape_flavors():
    resp = requests.get(URL, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    
    flavors = []
    for h3 in soup.select("h3"):
        name = h3.get_text(strip=True)
        # Filter out non-flavor headings
        if name and name not in ["#SWEETCOWICECREAM", "WELCOME!"]:
            flavors.append(name)
    return flavors

def check_matches(flavors, watched):
    """Check if any current flavors match watched keywords."""
    matches = []
    for watch in watched:
        # match_all: ALL terms must be present in the flavor name
        if "match_all" in watch:
            for flavor in flavors:
                flavor_lower = flavor.lower()
                if all(term.lower() in flavor_lower for term in watch["match_all"]):
                    matches.append({
                        "wanted": watch["name"],
                        "found": flavor
                    })
        # keywords: ANY keyword can match
        elif "keywords" in watch:
            for keyword in watch["keywords"]:
                for flavor in flavors:
                    if keyword.lower() in flavor.lower():
                        matches.append({
                            "wanted": watch["name"],
                            "found": flavor
                        })
                        break
    # Dedupe by wanted flavor name
    seen = set()
    unique = []
    for m in matches:
        if m["wanted"] not in seen:
            seen.add(m["wanted"])
            unique.append(m)
    return unique

def send_notification(matches, ntfy_topic):
    """Send push notification via ntfy.sh."""
    if not matches:
        return
    
    flavor_list = "\n".join(f"• {m['wanted']} (found: {m['found']})" for m in matches)
    message = f"Sweet Cow Alert! 🍦\n\n{flavor_list}\n\nStanley Marketplace has your flavor(s)!"
    
    requests.post(
        f"https://ntfy.sh/{ntfy_topic}",
        data=message.encode("utf-8"),
        headers={
            "Title": "Sweet Cow Flavor Alert",
            "Priority": "high",
            "Tags": "ice_cream"
        }
    )
    print(f"Notification sent to ntfy.sh/{ntfy_topic}")

def main():
    config = load_config()
    ntfy_topic = os.environ.get("NTFY_TOPIC", config.get("ntfy_topic", "sweetcow-stanley-mpe"))
    
    print(f"Scraping {URL}...")
    flavors = scrape_flavors()
    print(f"Found {len(flavors)} flavors: {flavors}")
    
    matches = check_matches(flavors, config["watched"])
    
    if matches:
        print(f"Matches found: {matches}")
        send_notification(matches, ntfy_topic)
    else:
        print("No matches today.")

if __name__ == "__main__":
    main()
