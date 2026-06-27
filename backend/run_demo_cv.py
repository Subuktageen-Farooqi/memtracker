from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Existing modules support direct `cd backend && uvicorn main:app`; add backend
# directory to sys.path so `python -m backend.run_demo_cv` works from repo root.
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import Base, SessionLocal, engine
from cv_pipeline import process_video_to_events, resolve_video_source, synthetic_demo_sequence
from models import CameraSource, Event, MonitoringSession, User
from security import hash_password


def ensure_demo_records(db):
    Base.metadata.create_all(bind=engine)
    user = db.query(User).filter(User.email == "demo-cv@memtracker.local").first()
    if not user:
        user = User(username="Demo CV User", email="demo-cv@memtracker.local", password_hash=hash_password("demo-password"))
        db.add(user)
        db.commit()
        db.refresh(user)
    camera = db.query(CameraSource).filter(CameraSource.user_id == user.id, CameraSource.mediamtx_path == "demo-cv").first()
    if not camera:
        camera = CameraSource(
            user_id=user.id,
            name="Demo CV Local Video",
            rtsp_url="demo://sample_video",
            mediamtx_path="demo-cv",
            play_url="/demo/sample_video.mp4",
            status="demo",
            last_checked_at=datetime.now(timezone.utc),
        )
        db.add(camera)
        db.commit()
        db.refresh(camera)
    session = MonitoringSession(user_id=user.id, camera_id=camera.id, status="running")
    db.add(session)
    db.commit()
    db.refresh(session)
    return user, camera, session


def main():
    parser = argparse.ArgumentParser(description="Run MemTracker demo CV/event pipeline.")
    parser.add_argument("--source", default="demo://sample_video", help="Video path, file:// path, RTSP URL, or demo://sample_video")
    parser.add_argument("--database-url", default=None, help="Optional DATABASE_URL override, e.g. sqlite:///./backend/demo_cv.db")
    args = parser.parse_args()
    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    db = SessionLocal()
    try:
        user, camera, session = ensure_demo_records(db)
        source = resolve_video_source(args.source)
        result = process_video_to_events(
            source=source,
            user_id=user.id,
            camera_id=camera.id,
            session_id=session.id,
            db=db,
            use_synthetic_fallback=True,
        )
        session.frames_processed = result["frames_processed"]
        session.events_detected = result["events_detected"]
        session.detected_people_count = result["detected_people_count"]
        session.status = "stopped"
        session.stopped_at = datetime.now(timezone.utc)
        camera.status = "stopped"
        db.commit()
        events = db.query(Event).filter(Event.session_id == session.id).order_by(Event.timestamp_seconds.asc()).all()
        print("MemTracker demo CV complete")
        print(f"source={source}")
        print(f"session_id={session.id}")
        print(f"frames_processed={session.frames_processed}")
        print(f"events_detected={session.events_detected}")
        for event in events:
            print(f"- {event.timestamp_label} {event.event_type}: {event.description}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
