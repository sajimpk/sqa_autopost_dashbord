from flask import Flask, render_template, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import os, json, random, requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import google.generativeai as genai
import requests

# Load environment variables
load_dotenv()
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")
AI_API_KEY = os.getenv("AI_API_KEY")

genai.configure(api_key=AI_API_KEY)
app = Flask(__name__)

POSTS_PER_DAY = 3
POST_INTERVAL_HOURS = 8
LOG_FILE = 'post_log.json'
SCHEDULED_FILE = 'post_schedule.json'

if os.path.exists(LOG_FILE):
    with open(LOG_FILE) as f:
        post_log = json.load(f)
else:
    post_log = []

# Create schedule if not exists
if not os.path.exists(SCHEDULED_FILE):
    now = datetime.now()
    today_schedule = [(now + timedelta(hours=i*POST_INTERVAL_HOURS)).replace(second=0, microsecond=0).isoformat() for i in range(POSTS_PER_DAY)]
    with open(SCHEDULED_FILE, 'w') as f:
        json.dump(today_schedule, f, indent=2)

with open(SCHEDULED_FILE) as f:
    scheduled_times = [datetime.fromisoformat(t) for t in json.load(f)]

def save_log():
    with open(LOG_FILE, 'w') as f:
        json.dump(post_log, f, indent=2, default=str)

def generate_sqa_post():
    prompt = """
    আমি একজন experienced SQA expert। দয়া করে ১০০ থেকে ২০০ শব্দের মধ্যে একটি নতুন, সহজবোধ্য এবং ইউনিক পোস্ট লিখুন software testing নিয়ে, যেখানে বাংলা এবং ইংরেজির মিক্স থাকবে। পোস্টে থাকতে হবে:

    - software testing এর কোনো একটা specific টপিক  
    - practical example বা simple tips  
    - friendly এবং professional tone  
    - শেষে একটি প্রশ্ন  
    - অন্তত দুইটা hashtag: #SoftwareTesting #SQA
    ⚠️ Only return the post content.
    """
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)
    return response.text.strip()

def post_to_facebook():
    message = generate_sqa_post()
    url = f"https://graph.facebook.com/{FB_PAGE_ID}/feed"
    payload = { "message": message, "access_token": FB_ACCESS_TOKEN }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        post_log.append({ "time": datetime.now().isoformat(), "content": message })
        save_log()
        print("✅ Auto-posted successfully!")
    else:
        print("❌ Facebook post failed:", response.text)

scheduler = BackgroundScheduler()
for sched_time in scheduled_times:
    scheduler.add_job(post_to_facebook, 'date', run_date=sched_time)
scheduler.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    now = datetime.now()
    today = now.date()
    today_posts = [p for p in post_log if datetime.fromisoformat(p["time"]).date() == today]
    num_posted = len(today_posts)
    remaining = POSTS_PER_DAY - num_posted

    future_times = [t for t in scheduled_times if t > now]
    if future_times:
        next_post_time = future_times[0]
        time_until_next = next_post_time - now
    else:
        next_post_time = None
        time_until_next = None

    return render_template('dashboard.html',
        total_posts=POSTS_PER_DAY,
        posted=num_posted,
        remaining=remaining,
        next_post_time=next_post_time,
        time_until_next=str(time_until_next).split('.')[0] if time_until_next else None,
        recent_posts=today_posts)
    
@app.route('/next-post-timer')
def next_post_timer():
    now = datetime.now()
    future_times = [t for t in scheduled_times if t > now]
    if future_times:
        next_post_time = future_times[0]
        time_until_next = next_post_time - now
        return jsonify({
            'next_post_time': next_post_time.strftime('%Y-%m-%d %H:%M:%S'),
            'time_until_next': str(time_until_next).split('.')[0]
        })
    else:
        return jsonify({
            'next_post_time': None,
            'time_until_next': None
        })

if __name__ == '__main__':
    app.run(debug=True)