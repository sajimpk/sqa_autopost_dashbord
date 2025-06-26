from flask import Flask, render_template, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import os, json, random, requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")
AI_API_KEY = os.getenv("AI_API_KEY")

# Configure the Generative AI client
genai.configure(api_key=AI_API_KEY)
app = Flask(__name__)

# --- Configuration ---
POSTS_PER_DAY = 12
POST_INTERVAL_HOURS = 24 / POSTS_PER_DAY # Ensures posts are spread out over 24 hours
LOG_FILE = 'post_log.json'
SCHEDULED_FILE = 'post_schedule.json'

# --- Initial Setup ---

# Load post log or create a new one
if os.path.exists(LOG_FILE):
    with open(LOG_FILE) as f:
        post_log = json.load(f)
else:
    post_log = []

# Create schedule file if it doesn't exist
if not os.path.exists(SCHEDULED_FILE):
    now = datetime.now()
    # Create the initial schedule for the first day
    today_schedule = [(now + timedelta(hours=i*POST_INTERVAL_HOURS)).replace(second=0, microsecond=0).isoformat() for i in range(POSTS_PER_DAY)]
    with open(SCHEDULED_FILE, 'w') as f:
        json.dump(today_schedule, f, indent=2)

# Load the scheduled times from the file
with open(SCHEDULED_FILE) as f:
    # Convert ISO format strings to datetime objects
    scheduled_times = [datetime.fromisoformat(t) for t in json.load(f)]

def save_log():
    """Saves the post log to the JSON file."""
    with open(LOG_FILE, 'w') as f:
        json.dump(post_log, f, indent=2, default=str)

def generate_sqa_post():
    prompt = """
    আমি একজন experienced SQA expert। দয়া করে ১০০ থেকে ২০০ শব্দের মধ্যে একটি নতুন, সহজবোধ্য এবং ইউনিক পোস্ট লিখুন software testing নিয়ে, যেখানে বাংলা এবং ইংরেজির মিক্স থাকবে। পোস্টে থাকতে হবে:

    - software testing এর কোনো একটা specific টপিক  
    - practical example বা simple tips  
    - friendly এবং professional tone  
    - শেষে একটি প্রশ্ন  
    - 7-10 hashtag: include(#SoftwareTesting #SQA)
    ⚠️ Only return the post content.
    """
    model = genai.GenerativeModel("gemini-1.5-flash") # Updated to a newer model
    response = model.generate_content(prompt)
    return response.text.strip()

def execute_and_reschedule_post(sched_time_to_run):
    """
    Generates content, posts to Facebook, logs the result, and reschedules the next post.
    This function ensures the posting cycle continues perpetually.
    """
    try:
        print(f"🚀 Running job for scheduled time: {sched_time_to_run.isoformat()}")
        message = generate_sqa_post()
        url = f"https://graph.facebook.com/{FB_PAGE_ID}/feed"
        payload = {"message": message, "access_token": FB_ACCESS_TOKEN}
        response = requests.post(url, data=payload)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        print(f"✅ Auto-posted successfully!")
        # Log the successful post
        post_log.append({"time": datetime.now().isoformat(), "content": message})
        save_log()

    except requests.exceptions.RequestException as e:
        print(f"❌ Facebook post failed: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during post generation or posting: {e}")

    finally:
        # --- This block runs whether the post succeeded or failed to ensure rescheduling ---
        global scheduled_times
        
        print(f"🔄 Rescheduling job that was set for {sched_time_to_run.isoformat()}...")
        
        # Load the schedule from the file to ensure we have the latest version
        with open(SCHEDULED_FILE, 'r') as f:
            schedule_iso = json.load(f)

        # The new time is 24 hours from the time that was *supposed* to run
        new_sched_time = sched_time_to_run + timedelta(days=1)
        old_time_iso = sched_time_to_run.isoformat()

        # Update the schedule list by replacing the old time with the new one
        try:
            # Find the index of the old time string and replace it
            idx = schedule_iso.index(old_time_iso)
            schedule_iso[idx] = new_sched_time.isoformat()
        except ValueError:
            # Fallback if the old time isn't found: just append the new one.
            print(f"⚠️ Warning: {old_time_iso} not found in schedule file. Appending new time.")
            schedule_iso.append(new_sched_time.isoformat())
            
        # Save the updated schedule back to the file
        with open(SCHEDULED_FILE, 'w') as f:
            json.dump(schedule_iso, f, indent=2)

        # Update the global datetime object list used by the dashboard
        if sched_time_to_run in scheduled_times:
            scheduled_times.remove(sched_time_to_run)
        scheduled_times.append(new_sched_time)
        scheduled_times.sort() # Keep the list sorted for predictable 'next post' logic

        # Add the new job to the running scheduler instance
        scheduler.add_job(execute_and_reschedule_post, 'date', run_date=new_sched_time, args=[new_sched_time])
        print(f"👍 Rescheduled. Next run for this slot is now {new_sched_time.isoformat()}")

# --- Scheduler Setup ---
scheduler = BackgroundScheduler(timezone="Asia/Dhaka")
# The initial jobs are now self-managing
for sched_time in scheduled_times:
    # We pass the specific datetime object to the job so it knows which time it's running for
    scheduler.add_job(execute_and_reschedule_post, 'date', run_date=sched_time, args=[sched_time])
scheduler.start()


# --- Flask Web Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    now = datetime.now()
    today = now.date()
    today_posts = [p for p in post_log if datetime.fromisoformat(p["time"]).date() == today]
    num_posted_today = len(today_posts)
    
    # Filter for times that are still in the future
    future_times = sorted([t for t in scheduled_times if t > now])
    
    next_post_time = None
    time_until_next = None

    if future_times:
        next_post_time = future_times[0]
        time_until_next = next_post_time - now

    return render_template('dashboard.html',
        total_posts=POSTS_PER_DAY,
        posted=num_posted_today,
        remaining=POSTS_PER_DAY - num_posted_today,
        next_post_time=next_post_time,
        time_until_next=str(time_until_next).split('.')[0] if time_until_next else "Not scheduled",
        recent_posts=reversed(post_log[-10:])) # Show the last 10 posts
    
@app.route('/next-post-timer')
def next_post_timer():
    now = datetime.now()
    future_times = sorted([t for t in scheduled_times if t > now])
    
    if future_times:
        next_post_time = future_times[0]
        time_until_next = next_post_time - now
        return jsonify({
            'next_post_time': next_post_time.strftime('%Y-%m-%d %H:%M:%S'),
            'time_until_next': str(time_until_next).split('.')[0]
        })
    else:
        return jsonify({
            'next_post_time': 'None',
            'time_until_next': 'None'
        })

if __name__ == '__main__':
    # Note: Using debug=True with a scheduler can cause jobs to run twice.
    # It's better to run with debug=False in a production-like environment
    app.run(debug=False, use_reloader=False)
