You are a senior fullstack AI/ML engineer. Build the complete MemTracker app exactly from this specification.

Priority:
Build a working end-to-end product over decorative UI. The app should be portfolio-quality, demo-ready, and technically credible as a Fullstack AI/ML Engineering portfolio project.

Project name:
MemTracker

Portfolio title:
MemTracker — RTSP CCTV Intelligence with Real-Time CV Tracking and LLM Video Memory Search

Product vision:
MemTracker is an AI-powered CCTV memory system. It lets users attach RTSP/CCTV streams, view them in-browser through WebRTC, run AI monitoring, detect people/objects/events, save timestamped logs, and ask a Groq-powered LLM what happened using grounded event logs with clickable timestamp citations.

Core demo flow:
User registers/logs in
→ attaches RTSP camera
→ backend validates stream and stores camera
→ frontend shows WebRTC preview using MediaMTX play_url
→ user starts AI monitoring
→ YOLO detects people and objects
→ tracker assigns persistent IDs
→ event engine writes logs
→ logs appear in Logs tab
→ user asks “When was a bag abandoned?”
→ Groq answers only from logs
→ answer includes timestamp citation
→ user clicks citation
→ monitor page opens and seeks/highlights that timestamp.

Important playback rule:
The browser must never try to play rtsp:// directly.
RTSP is backend/CV input.
WebRTC play_url is frontend playback input.
Use MediaMTX externally for RTSP → WebRTC.

Tech stack:
Frontend: Next.js / React
Backend: FastAPI
Database: SQLite local, Postgres-ready schema
Streaming: MediaMTX RTSP → WebRTC
CV: YOLOv8 or YOLOv11 through ultralytics
Tracking: YOLO track mode with ByteTrack or BoT-SORT style IDs
LLM: Groq API
Auth: email/password with hashed passwords
Demo mode: local sample video + sample events

Use one coherent codebase with:
frontend app
backend folder
README
docs/mediamtx_setup.md

Do not split into disconnected mock apps.
Everything should connect through real API calls.

========================
FRONTEND ROUTES
===============

Implement these routes:

/
/login
/register
/dashboard
/dashboard/streams
/dashboard/monitor
/dashboard/logs
/dashboard/chat
/dashboard/settings

Use a professional dashboard layout:
sidebar navigation
top bar with user info
main content area
cards, tables, forms
responsive layout
loading states
empty states
error states
success toasts
credential masking

Landing page:
Headline:
MemTracker

Subheadline:
AI-powered CCTV memory for searchable video intelligence.

Hero text:
Attach RTSP streams, track people and objects, detect events, and ask an LLM what happened — with clickable video timestamps.

Buttons:
Login
Create Account
View Demo Dashboard

/register:
Fields:
username
email
password
confirm password

Behavior:
validate password match
call POST /api/users/register
save user to localStorage/session
redirect to /dashboard
show backend errors

/login:
Fields:
email
password

Behavior:
call POST /api/auth/login
save user to localStorage/session
redirect to /dashboard
show 401 invalid login error

MVP auth:
Use localStorage session.
No JWT required yet.
Protected dashboard routes redirect to /login if no session exists.

/dashboard:
Cards:
Connected Cameras
Active Monitoring Sessions
Events Today
Tracked People
Recent Alerts

Quick actions:
Attach Stream
Start Monitoring
Ask Chat

/dashboard/streams:
Purpose: attach/manage RTSP cameras.

Attach form fields:
Camera Name
RTSP URL
MediaMTX Path

Helper text:
RTSP URL is used by backend AI processing.
MediaMTX path generates the WebRTC browser playback URL.

Example:
RTSP URL: rtsp://user:pass@192.168.1.10:554/stream1
MediaMTX Path: cam1
Generated play URL: http://localhost:8889/cam1

Submit behavior:
call POST /api/streams/attach
show loading while probing
show success if connected
show friendly error if failed

Error message mapping:
400 INVALID_URL → “Invalid RTSP URL. It must start with rtsp:// or rtsps://.”
401 UNAUTHORIZED → “Bad username or password for this camera.”
404 NOT_FOUND → “Camera host or stream path was not found.”
408 TIMEOUT → “Camera did not respond within 5 seconds.”
409 BUSY → “This stream is already attached.”
500 UNKNOWN → “Unexpected server error while checking stream.”

Stream list:
camera name
status
masked RTSP URL
MediaMTX path
play URL
actions: View, Start Monitoring, Delete

Mask credentials:
rtsp://user:****@192.168.1.10:554/stream1

/dashboard/monitor:
Layout:
left/main: WebRTC video preview or demo video
right panel: monitoring controls and live stats
bottom: recent event feed

For live mode use:

<iframe src={selectedCamera.play_url} />

Do not use: <video src="rtsp://..." />

Controls:
Start Monitoring
Stop Monitoring
Refresh Status

Stats:
Monitoring status
Frames processed
Detected people count
Events detected
Current session ID

Recent events:
timestamp
event type
actor
description
confidence

Timestamp click:
open /dashboard/monitor?camera_id=...&t=128.4

/dashboard/logs:
Filters:
Camera
Session
Actor ID
Event Type
Scenario
Start time
End time
Search text

Table columns:
Timestamp
Event Type
Scenario
Actor
Object
Description
Traits
Confidence
Source Camera

Timestamp click:
navigate to monitor page with timestamp.

/dashboard/chat:
Elements:
camera selector
chat history
message input
send button
assistant answers
citation cards
clickable timestamps
loading state
empty state
error state

Example questions:
When did person-2 enter the scene?
Was there any abandoned object?
Who picked up the bag?
Did anyone enter the restricted zone?
Show events between 2 and 4 minutes.
What visual traits were observed for person-3?

Citation click:
open /dashboard/monitor?camera_id=...&t=timestamp_seconds

/dashboard/settings:
Fields:
Groq API key status
Backend URL
MediaMTX base URL
Demo mode toggle
Default frame sampling rate

Do not expose full API key.

Frontend API helper:
Create a reusable API client using:
NEXT_PUBLIC_BACKEND_URL or http://localhost:8000

Functions:
registerUser
loginUser
attachStream
listStreams
deleteStream
startMonitoring
stopMonitoring
getMonitoringStatus
getEvents
sendChatQuery
getChatHistory

Do not hardcode backend URLs inside components.

========================
BACKEND STRUCTURE
=================

Use FastAPI.

Backend folder should include:
backend/main.py
backend/database.py
backend/models.py
backend/schemas.py
backend/security.py
backend/cv_pipeline.py
backend/event_engine.py
backend/chat_service.py
backend/requirements.txt
backend/.env.example

Base URL:
http://localhost:8000

Enable CORS for:
http://localhost:3000
http://localhost:3001

Environment variables:
DATABASE_URL=sqlite:///./memtracker.db
GROQ_API_KEY=
GROQ_MODEL=llama-3.1-8b-instant
MEDIAMTX_WEBRTC_BASE_URL=http://localhost:8889
DEMO_MODE=false
CV_FRAME_SAMPLE_RATE=5
CV_CONFIDENCE_THRESHOLD=0.45
CV_IOU_THRESHOLD=0.5

Frontend env:
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_MEDIAMTX_BASE_URL=http://localhost:8889
NEXT_PUBLIC_DEMO_MODE=false

========================
DATABASE SCHEMA
===============

Use SQLAlchemy.

SQLite engine must include:
connect_args={"check_same_thread": False}

SQLite must enable:
PRAGMA foreign_keys=ON

All important foreign keys must explicitly include:
ondelete="CASCADE"

SQLAlchemy relationships should use:
cascade="all, delete-orphan"

Deleting a user or camera source must not throw integrity errors.
Deleting a camera_source should automatically delete/clean up:
monitoring_sessions
actors
tracked_objects
events
chat_messages related to that camera when applicable.

users:
id integer primary key
username string
email string unique indexed
password_hash string
created_at datetime
updated_at datetime

camera_sources:
id integer primary key
user_id foreign key -> users.id with ondelete="CASCADE"
name string
rtsp_url text
mediamtx_path string
play_url text
status string
created_at datetime
updated_at datetime
last_checked_at datetime nullable
last_error text nullable

Status values:
connected
disconnected
error
monitoring
stopped

monitoring_sessions:
id integer primary key
camera_id foreign key -> camera_sources.id with ondelete="CASCADE"
user_id foreign key -> users.id with ondelete="CASCADE"
status string
started_at datetime
stopped_at datetime nullable
frames_processed integer default 0
events_detected integer default 0
detected_people_count integer default 0
error_message text nullable

Status values:
running
stopped
failed

actors:
id integer primary key
session_id foreign key -> monitoring_sessions.id with ondelete="CASCADE"
camera_id foreign key -> camera_sources.id with ondelete="CASCADE"
track_id string
first_seen_at float
last_seen_at float
traits_json text
created_at datetime

tracked_objects:
id integer primary key
session_id foreign key -> monitoring_sessions.id with ondelete="CASCADE"
camera_id foreign key -> camera_sources.id with ondelete="CASCADE"
object_track_id string
object_type string
first_seen_at float
last_seen_at float
last_owner_actor_id integer nullable
current_owner_actor_id integer nullable
is_stationary boolean default false
created_at datetime

events:
id integer primary key
user_id foreign key -> users.id with ondelete="CASCADE"
camera_id foreign key -> camera_sources.id with ondelete="CASCADE"
session_id foreign key -> monitoring_sessions.id nullable with ondelete="SET NULL" or "CASCADE"
actor_id integer nullable
object_id integer nullable
event_type string
scenario string
timestamp_seconds float
timestamp_label string
confidence float
description text
traits_json text nullable
metadata_json text nullable
created_at datetime

chat_messages:
id integer primary key
user_id foreign key -> users.id with ondelete="CASCADE"
camera_id foreign key -> camera_sources.id nullable with ondelete="CASCADE"
role string
content text
citations_json text nullable
created_at datetime

========================
BACKEND API CONTRACT
====================

GET /health
Response:
{
"status": "healthy",
"service": "memtracker-backend"
}

POST /api/users/register
Request:
{
"username": "Subuk",
"email": "[subuk@example.com](mailto:subuk@example.com)",
"password": "password123"
}

Response:
{
"id": 1,
"username": "Subuk",
"email": "[subuk@example.com](mailto:subuk@example.com)"
}

Rules:
hash password
409 if email exists

POST /api/auth/login
Request:
{
"email": "[subuk@example.com](mailto:subuk@example.com)",
"password": "password123"
}

Response:
{
"id": 1,
"username": "Subuk",
"email": "[subuk@example.com](mailto:subuk@example.com)"
}

Rules:
verify password hash
401 if invalid

POST /api/streams/attach
Request:
{
"user_id": 1,
"name": "Lab Camera",
"rtsp_url": "rtsp://user:pass@192.168.1.10:554/stream1",
"mediamtx_path": "cam1"
}

Response:
{
"id": 1,
"name": "Lab Camera",
"rtsp_url": "rtsp://user:pass@192.168.1.10:554/stream1",
"mediamtx_path": "cam1",
"play_url": "http://localhost:8889/cam1",
"status": "connected"
}

Validation:
RTSP URL starts with rtsp:// or rtsps://
hostname required
mediamtx_path is lowercase URL-safe
duplicate stream for same user returns 409
probe stream with 5 second timeout

Errors:
400 INVALID_URL
401 UNAUTHORIZED
404 NOT_FOUND
408 TIMEOUT
409 BUSY
500 UNKNOWN

GET /api/streams?user_id=1
Return list of streams.

DELETE /api/streams/{stream_id}
Delete stream and cascade associated camera data safely.

POST /api/monitoring/start
Request:
{
"user_id": 1,
"camera_id": 1
}

Response:
{
"session_id": 1,
"camera_id": 1,
"status": "running"
}

Behavior:
start background CV task
use camera.rtsp_url
do not block request

POST /api/monitoring/stop
Request:
{
"session_id": 1
}

Response:
{
"session_id": 1,
"status": "stopped"
}

GET /api/monitoring/status?session_id=1
Response:
{
"session_id": 1,
"status": "running",
"frames_processed": 1200,
"events_detected": 14,
"detected_people_count": 3
}

GET /api/events
Query params:
user_id
camera_id
session_id
actor_id
event_type
scenario
start_time
end_time
search

Return filtered event list.

POST /api/events
For demo/testing event creation.

POST /api/chat/query
Request:
{
"user_id": 1,
"camera_id": 1,
"message": "When was a bag abandoned?"
}

Response:
{
"answer": "A backpack was abandoned at 00:02:08. It was previously associated with person-2 and remained unattended for about 10 seconds.",
"citations": [
{
"event_id": 12,
"timestamp_seconds": 128.4,
"timestamp_label": "00:02:08",
"event_type": "abandoned_object",
"description": "Backpack associated with person-2 was left unattended for 10 seconds."
}
]
}

GET /api/chat/history?user_id=1&camera_id=1
Return persistent chat messages.

========================
MEDIAMTX / WEBRTC
=================

Create:
docs/mediamtx_setup.md

Include example mediamtx.yml:

paths:
cam1:
source: rtsp://USER:PASS@CAMERA_IP:554/stream1
sourceOnDemand: yes

Explain:
cam1 is the MediaMTX path.
Browser play URL:
http://localhost:8889/cam1

When stream is attached:
play_url = MEDIAMTX_WEBRTC_BASE_URL + "/" + mediamtx_path

Frontend iframe:

<iframe
  src={`${camera.play_url}?controls=true&muted=true&autoplay=true`}
  className="w-full h-full rounded-xl border"
  allow="autoplay; fullscreen"
/>

========================
CV PIPELINE
===========

Implement background CV pipeline.

Input:
camera.rtsp_url

Output:
actors
tracked_objects
events
monitoring_sessions

Core loop:
open RTSP stream with OpenCV
load YOLO model once
for sampled frames:
detect people and target objects
track detections
update actor/object states
run event rules
save new events
update session stats

Use ultralytics.
Use YOLOv8n or YOLOv8s for MVP.

Target classes:
person
backpack
handbag
suitcase
bag if available
laptop
cell phone optional
unknown_object fallback

Frame sampling:
CV_FRAME_SAMPLE_RATE=5 means process every 5th frame.
CV_CONFIDENCE_THRESHOLD=0.45
CV_IOU_THRESHOLD=0.5

Tracking:
Use YOLO track mode with ByteTrack/BoT-SORT style IDs.
People become:
person-1
person-2
person-3

Objects become:
object-1
object-2

Track state:
track_id
bbox
center point
first_seen_time
last_seen_time
last_seen_frame
current_traits
current_zone

Critical FastAPI/OpenCV threading rule:
The background CV pipeline must not run directly inside the FastAPI async event loop.

The OpenCV stream-reading loop must run inside either:

1. a standard Python threading.Thread, or
2. anyio.to_thread.run_sync

Use synchronous SQLAlchemy sessions inside the CV worker.

Do not mix async database calls inside the synchronous OpenCV loop.

Each worker thread must use its own database session.

Use a thread-safe SQLAlchemy scoped_session or create a fresh SessionLocal() inside the worker thread and close it cleanly.

Do not reuse a request-scoped database session inside a background thread.
Do not share one SQLAlchemy session across multiple threads.
Do not leave sessions open after worker stop/error.

YOLO model caching:
The YOLO model must be loaded once per backend process or once per worker startup and cached in memory.

Do not instantiate YOLO() inside the frame loop.

Bad example:
for frame in stream:
model = YOLO("yolov8n.pt")

Correct behavior:
model = get_cached_yolo_model()
for frame in stream:
results = model.track(...)

Worker safety:
run background task/thread
do not block FastAPI
handle disconnects
release VideoCapture
stop when requested
mark session failed on stream error
avoid runaway loops

Worker stop behavior:
Each monitoring session must have a stop flag or registry entry.

When stop is requested:
set stop flag
exit frame loop
release cv2.VideoCapture
close DB session
mark monitoring_sessions.status = "stopped"

If stream read fails:
release cv2.VideoCapture
close DB session
mark monitoring_sessions.status = "failed"
save error_message
do not crash the FastAPI server

========================
EVENT SCENARIOS
===============

Required basic events:
person_entered_scene
person_presence
person_exited_scene

Visual traits:
shirt_color
has_backpack_or_bag
optional helmet/no_helmet

Custom scenario 1:
restricted_zone_entry

Custom scenario 2:
object possession tracking:
object_pickup
object_handoff
abandoned_object
suspected_object_swap
suspected_unauthorized_removal

Use cautious language:
Never say theft confirmed.
Say suspected unauthorized removal.

Person presence rules:
new person visible for 3 processed frames → person_entered_scene
person visible for interval → person_presence
person missing for 5 seconds → person_exited_scene
presence cooldown 10 seconds

Shirt color:
sample upper-body crop
compute dominant color
map to:
black, white, gray, red, blue, green, yellow, orange, brown, unknown

Bag/backpack trait:
bag/backpack/handbag/suitcase near or overlapping person for N frames → has_backpack_or_bag true

Restricted zone:
support default polygon:
{
"name": "Restricted Zone",
"points": [[100,100], [400,100], [400,300], [100,300]]
}

Rule:
person center enters polygon → restricted_zone_entry
cooldown 15 seconds per actor-zone pair

Object possession:
objects:
backpack
handbag
suitcase
bag
laptop
unknown_object

Ownership:
object bbox overlaps person bbox OR object center near person center
association persists 3 processed frames
then ownership association is created

Abandoned object:
object was associated with person A
object becomes stationary
person A moves away
object remains unattended for 10 seconds
log abandoned_object

Handoff:
object associated with person A
then associated with person B
A and B close during transition
log object_handoff

Suspected unauthorized removal:
object stationary/unattended
new person B picks it up
previous owner A not nearby
log suspected_unauthorized_removal

========================
EVENT ENGINE
============

Every event must include:
event_type
scenario
timestamp_seconds
timestamp_label
actor_id optional
object_id optional
confidence
description
metadata_json
traits_json optional

timestamp_label format:
HH:MM:SS

Deduplication cooldowns:
person_entered_scene once per actor
person_presence every 10 seconds max per actor
person_exited_scene once after disappearance
restricted_zone_entry once every 15 seconds per actor-zone
object_pickup once per object-owner association
abandoned_object once per abandonment episode
object_handoff once per transition
suspected_unauthorized_removal once per pickup episode

Confidence:
person_presence = detection confidence
restricted_zone_entry = person confidence
object_pickup = average person/object confidence
abandoned_object = average object/ownership/stationary confidence
suspected_unauthorized_removal = average object/pickup confidence

========================
GROQ CHAT
=========

Use Groq API.

System prompt:
You are MemTracker Assistant, a grounded CCTV event-log assistant.

You answer questions only using the provided event logs.
Do not invent people, actions, events, timestamps, or object ownership.
If the logs do not contain enough evidence, say: "I could not find that in the logs."
When you mention an event, include its timestamp.
Use cautious language for security events. Never say theft confirmed. Say suspected unauthorized removal.
Return citations for every event used.

Before calling Groq:
retrieve relevant events from DB
filter by user_id and camera_id
filter by obvious keywords/event types/actors/time ranges
pass only relevant logs to Groq

If zero relevant logs:
return:
{
"answer": "I could not find that in the logs.",
"citations": []
}

If GROQ_API_KEY missing:
do not crash
use simple rule-based fallback from logs or show clear config message

Chat must not:
invent timestamps
invent people
invent events
claim identity recognition
claim crime certainty
say theft confirmed

Use:
tracked person-2
person with blue shirt
possible handoff
object remained unattended
suspected unauthorized removal

========================
CLICKABLE CITATIONS
===================

Every citation object:
event_id
timestamp_seconds
timestamp_label
event_type
scenario
actor_id optional
object_id optional
description
confidence

Frontend behavior:
Click citation
→ route to /dashboard/monitor?camera_id=1&t=128.4

In demo video mode:
seek video.currentTime = 128.4

In live WebRTC mode:
live WebRTC cannot seek backward without DVR
so show selected timestamp/event evidence card beside player

This is required:
citations must be clickable.

========================
DEMO MODE
=========

Support:

1. Live RTSP/WebRTC mode
2. Demo video mode

Use:
DEMO_MODE=true

When demo mode is enabled:
allow local sample video playback
allow fake/demo camera source
allow preloaded sample events
allow chat over sample events
allow clickable citations to seek sample video

Create:
public/demo/sample_video.mp4 placeholder/documentation
public/demo/sample_events.json

If no video:
show “No demo video found. Add public/demo/sample_video.mp4.”

Demo camera:
{
"id": 999,
"name": "Demo Warehouse Camera",
"rtsp_url": "demo://sample_video",
"mediamtx_path": "demo",
"play_url": "/demo/sample_video.mp4",
"status": "demo"
}

Sample events:
person_entered_scene at 00:00:12
restricted_zone_entry at 00:01:04
abandoned_object at 00:02:08
suspected_unauthorized_removal at 00:03:03

In demo monitor:
use: <video controls src="/demo/sample_video.mp4" />

Citation click should seek actual video.

========================
README REQUIREMENTS
===================

Create a strong README.md with:
project overview
portfolio positioning
architecture diagram
tech stack
features
assignment compliance matrix
local setup
MediaMTX setup
backend setup
frontend setup
environment variables
demo mode instructions
known limitations
future improvements

Architecture should explain:
RTSP camera → MediaMTX → WebRTC frontend
RTSP camera → FastAPI CV worker → YOLO/tracker → events DB
events DB → Groq chat → clickable citations

Known limitations:
Live WebRTC cannot seek backward without DVR/recording.
Demo video mode supports true timestamp seeking.
Object possession tracking is heuristic-based and may fail under occlusion.
The system does not identify real people by identity/name.
Security events are reported as suspected, not confirmed.

Run instructions:

1. Run MediaMTX:
   .\mediamtx.exe

Example mediamtx.yml:
paths:
cam1:
source: rtsp://USER:PASS@CAMERA_IP:554/stream1
sourceOnDemand: yes

2. Run backend:
   cd backend
   py -m venv .venv
   ..venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   uvicorn main:app --reload --port 8000

Health:
http://localhost:8000/health

3. Run frontend:
   npm install
   npm run dev

Open:
http://localhost:3000

========================
ACCEPTANCE TESTS
================

Auth:
register new user works
same email gives 409
valid login works
invalid login gives 401
dashboard without login redirects to /login

Stream attach:
invalid URL “hello” gives 400
duplicate stream gives 409
unreachable RTSP host gives 408 or 404
valid RTSP saves camera
frontend never renders rtsp:// in video tag
frontend uses play_url iframe for WebRTC

Monitoring:
start monitoring creates session
status returns running/stopped
stop monitoring works
bad stream does not crash backend
session becomes failed on stream read error
YOLO model is not reloaded inside the frame loop
OpenCV loop does not block FastAPI event loop
each worker uses its own DB session

Events/logs:
events save timestamp_seconds and timestamp_label
logs page loads events
logs filter by actor
logs filter by scenario
logs filter by event type
timestamp click routes to monitor with ?t=

Chat:
ask “When was a bag abandoned?” returns abandoned_object event
answer includes citation
citation clickable
unknown question returns “I could not find that in the logs.”
chat history survives refresh
no hallucinated timestamps/events

Object possession:
object near person for 3 processed frames creates ownership
stationary object + owner walks away creates abandoned_object
unattended object picked by different person creates suspected_unauthorized_removal
person A to B transfer creates object_handoff

Database:
deleting camera_source does not throw integrity errors
associated monitoring sessions/events/actors/tracked objects are cleaned up safely
SQLite foreign keys are enabled

========================
QUALITY BAR
===========

Build a complete runnable app.
Do not leave pages as pure mockups.
Use real backend calls.
Use real database persistence.
Use demo mode where real RTSP is unavailable.
Keep code clean and understandable.
Prefer simple reliable implementation over over-engineered abstraction.
Make the project look like a serious Fullstack AI/ML Engineer portfolio project.
