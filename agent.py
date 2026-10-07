import os
import time
import json
import requests
import urllib.parse
from groq import Groq
from dotenv import load_dotenv
import re

# 1. Environment Variables Load Karein
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX = os.getenv("GOOGLE_CX")

# Groq Client Initialize Karein
client = Groq(api_key=GROQ_API_KEY)

# Duplicate rokne ke liye file
SEEN_FILE = "seen_posts.txt"

def load_seen_posts():
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f)

def save_seen_post(post_id):
    with open(SEEN_FILE, "a", encoding="utf-8") as f:
        f.write(post_id + "\n")

# 2. Reddit se Data Nikalna (RSS Method - 100% Free & No Auth)
def get_reddit_leads():
    print("🔍 Reddit se leads dhoondh raha hoon (Multi-Subreddit RSS Method)...")
    subreddits = ['EntrepreneurRideAlong', 'marketing', 'socialmedia', 'sales', 'Coachify']
    all_leads = []
    
    for sub in subreddits:
        print(f"   -> Checking r/{sub}...")
        reddit_rss = f"https://www.reddit.com/r/{sub}/new.rss"
        encoded_rss_url = urllib.parse.quote(reddit_rss, safe='')
        api_url = f"https://api.rss2json.com/v1/api.json?rss_url={encoded_rss_url}"
        
        try:
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    for item in data["items"][:5]:
                        post_id = item["link"].split("/")[-2] 
                        clean_text = re.sub('<[^<]+?>', '', item.get("description", ""))
                        all_leads.append({
                            "id": post_id,
                            "title": item["title"],
                            "text": clean_text[:800],
                            "url": item["link"],
                            "author": item.get("author", "Unknown")
                        })
        except Exception as e:
            print(f"   ⚠️ r/{sub} se data nahi mila: {e}")
            
    print(f"✅ Total {len(all_leads)} posts mili AI ke liye.")
    return all_leads

# 3. Google se Data Nikalna
def get_google_leads():
    print("🔍 Google se 'Hiring Setter' Leads dhoondh raha hoon...")
    query = 'hiring appointment setter OR looking for closer OR need setter OR hiring remote sales'
    api_key = os.getenv("GOOGLE_API_KEY")
    cx = os.getenv("GOOGLE_CX")
    url = f"https://www.googleapis.com/customsearch/v1?q={query}&key={api_key}&cx={cx}&num=10"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        leads = []
        if "items" in data:
            for item in data["items"]:
                leads.append({
                    "id": item["link"], 
                    "title": item.get("title", "No Title"),
                    "text": item.get("snippet", "")[:800], 
                    "url": item["link"],
                    "author": "Google Search"
                })
        print(f"✅ Google se {len(leads)} leads mili.")
        return leads
    except Exception as e:
        print(f"❌ Google Search error: {e}")
        return []

# 4. AI Brain (Groq se filtering)
def evaluate_lead_with_ai(lead):
    prompt = f"""
You are an expert job qualifier for an "Appointment Setter" looking for commission-based work.

Analyze this post:
Title: "{lead['title']}"
Description: "{lead['text']}"

Your Task:
1. Is this post looking for an "Appointment Setter", "High Ticket Closer", "Sales Rep", or "DM Setter"?
2. REJECT if it is: A full-time corporate job, requires 3+ years experience, requires upfront payment, or is unrelated to sales.
3. ACCEPT if it is: Commission-based, remote, for a coach/agency/consultant, or mentions "uncapped commission".
4. Give a score 1-10.
5. Write a short, punchy pitch in English.

Pitch Instructions:
- Sound confident and hungry.
- Mention you are ready to start immediately and work on commission.
- Keep it under 3 sentences.

Respond ONLY in JSON format:
{{
  "isRelevant": true,
  "score": 8,
  "pitch": "Hey! Saw you're looking for a setter. I'm hungry, experienced in DMs, and ready to book calls for you on a commission basis. Let's chat!"
}}
"""
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        result = json.loads(completion.choices[0].message.content)
        return result
    except Exception as e:
        print(f"❌ AI Evaluation error: {e}")
        return {"isRelevant": False, "score": 0, "pitch": "AI Error"}

# 5. Discord Par Message Bhejna
def send_to_discord(lead, ai_result):
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    message = {
        "content": f"** NEW HOT LEAD DETECTED! **\n\n"
                   f" **Platform:** {lead.get('author', 'Unknown')}\n"
                   f"📝 **Title:** {lead['title']}\n"
                   f"🔗 **Link:** {lead['url']}\n\n"
                   f"🤖 **AI Score:** {ai_result.get('score', 0)}/10\n\n"
                   f"💬 **AI Drafted Pitch:**\n_{ai_result.get('pitch', 'No pitch')}_\n\n"
                   f"**Action:** Copy pitch, click link, and apply! "
    }
    try:
        response = requests.post(webhook_url, json=message, timeout=10)
        if response.status_code == 204:
            print(f"✅ Discord par bhej diya: {lead['title'][:30]}...")
        else:
            print(f"⚠️ Discord API Error: {response.text}")
    except Exception as e:
        print(f"❌ Discord connection error: {e}")

# 6. Main Execution Loop
def main():
    print("🚀 Multi-Platform Hunting Agent Started...")
    seen_posts = load_seen_posts()
    
    # --- Discord TEST ---
    print("\n--- Discord Test ---")
    test_lead = {
        "id": "test_123",
        "title": "TEST: Hiring Appointment Setter Needed!",
        "text": "Looking for a hungry setter to join my team.",
        "url": "https://test.com",
        "author": "Test User"
    }
    test_ai_result = {"isRelevant": True, "score": 10, "pitch": "Hi! I'm ready to start immediately."}
    send_to_discord(test_lead, test_ai_result)
    print("✅ Discord par TEST message bhej diya gaya hai. Apna Discord check karein!")
    # ---------------------
    
    print("\n--- Reddit Search ---")
    reddit_leads = get_reddit_leads()
    
    print("\n--- Google Search ---")
    google_leads = get_google_leads()
    
    all_leads = (reddit_leads or []) + (google_leads or [])
    
    if not all_leads:
        print("⚠️ Koi nayi leads nahi milin (Reddit/Google se).")
        return

    hot_leads_count = 0
    print("\n--- AI Evaluating Leads ---")
    
    for lead in all_leads:
        if lead["id"] in seen_posts:
            continue
            
        print(f"🧠 AI evaluate kar raha hai: {lead['title'][:40]}...")
        ai_result = evaluate_lead_with_ai(lead)
        
        # Safety check
        if ai_result is None:
            ai_result = {"isRelevant": False, "score": 0, "pitch": ""}
            
        print(f"    📊 Score: {ai_result.get('score', 0)}")
        
        if ai_result.get("isRelevant") and ai_result.get("score", 0) >= 4:
            send_to_discord(lead, ai_result)
            save_seen_post(lead["id"])
            hot_leads_count += 1
            
    print(f"\n🎉 Hunt Complete! {hot_leads_count} new hot leads bheji gayin.")

if __name__ == "__main__":
    main()