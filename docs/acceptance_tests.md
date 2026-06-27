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
