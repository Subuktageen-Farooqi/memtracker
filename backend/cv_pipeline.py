from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

try:
    from database import SessionLocal
    from event_engine import DetectionState, EventCandidate, EventEngine, FrameState, timestamp_label
    from models import CameraSource, Event, MonitoringSession
except ImportError:  # supports python -m backend.run_demo_cv
    from .database import SessionLocal
    from .event_engine import DetectionState, EventCandidate, EventEngine, FrameState, timestamp_label
    from .models import CameraSource, Event, MonitoringSession

_workers: Dict[int, threading.Event] = {}
_model = None
_model_lock = threading.Lock()


def get_cached_yolo_model():
    global _model
    with _model_lock:
        if _model is None:
            try:
                from ultralytics import YOLO
                _model = YOLO(os.getenv("YOLO_MODEL", "yolov8n.pt"))
            except Exception:
                _model = False
        return _model


def resolve_video_source(source: str) -> str:
    if source.startswith("demo://"):
        candidates = [
            Path("public/demo/sample_video.mp4"),
            Path("backend/demo/sample_video.mp4"),
            Path(__file__).resolve().parents[1] / "public/demo/sample_video.mp4",
            Path(__file__).resolve().parent / "demo/sample_video.mp4",
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        return source
    if source.startswith("file://"):
        return source.replace("file://", "", 1)
    return source


def start_worker(session_id: int):
    stop = threading.Event()
    _workers[session_id] = stop
    t = threading.Thread(target=_run_worker, args=(session_id, stop), daemon=True)
    t.start()


def stop_worker(session_id: int):
    ev = _workers.get(session_id)
    if ev:
        ev.set()


def _fail(db, session, msg):
    session.status = "failed"
    session.error_message = msg
    session.stopped_at = datetime.utcnow()
    db.commit()


def _run_worker(session_id: int, stop_event: threading.Event):
    db = SessionLocal()
    cap = None
    try:
        session = db.get(MonitoringSession, session_id)
        if not session:
            return
        camera = db.get(CameraSource, session.camera_id)
        if not camera:
            return _fail(db, session, "Camera not found")
        source = resolve_video_source(camera.rtsp_url)
        result = process_video_to_events(
            source=source,
            user_id=session.user_id,
            camera_id=session.camera_id,
            session_id=session.id,
            db=db,
            stop_event=stop_event,
            use_synthetic_fallback=camera.rtsp_url.startswith("demo://"),
        )
        session.frames_processed = result["frames_processed"]
        session.events_detected = result["events_detected"]
        session.detected_people_count = result["detected_people_count"]
        session.status = "stopped" if not stop_event.is_set() else "stopped"
        session.stopped_at = datetime.utcnow()
        camera.status = "stopped"
        db.commit()
    except Exception as e:
        try:
            s = db.get(MonitoringSession, session_id)
            if s:
                _fail(db, s, str(e))
        except Exception:
            pass
    finally:
        if cap:
            cap.release()
        db.close()
        _workers.pop(session_id, None)


def process_video_to_events(
    source: str,
    user_id: int,
    camera_id: int,
    session_id: Optional[int],
    db,
    stop_event: Optional[threading.Event] = None,
    use_synthetic_fallback: bool = True,
) -> Dict[str, object]:
    """Process a local video/RTSP source through detection normalization + EventEngine.

    If no readable demo video exists, a deterministic synthetic detection sequence is
    used. This still exercises the same EventEngine path and writes generated events,
    unlike the old seed-only demo.
    """
    engine = EventEngine()
    frames_processed = 0
    detected_people_count = 0
    generated: List[EventCandidate] = []

    frame_iter = _video_frame_states(source, stop_event)
    first_frame = None
    try:
        first_frame = next(frame_iter)
    except StopIteration:
        first_frame = None

    if first_frame is None:
        if not use_synthetic_fallback:
            raise RuntimeError(f"Unable to read video source: {source}")
        frame_iter = iter(synthetic_demo_sequence())
    else:
        frame_iter = _chain(first_frame, frame_iter)

    for frame_state in frame_iter:
        if stop_event and stop_event.is_set():
            break
        frames_processed += 1
        detected_people_count = max(detected_people_count, sum(1 for d in frame_state.detections if d.is_person))
        for candidate in engine.update_frame(frame_state):
            generated.append(candidate)
            db.add(_event_model(candidate, user_id, camera_id, session_id))
        if frames_processed % 10 == 0:
            db.commit()
    db.commit()
    return {
        "frames_processed": frames_processed,
        "events_detected": len(generated),
        "detected_people_count": detected_people_count,
        "events": generated,
    }


def _chain(first, rest):
    yield first
    yield from rest


def _video_frame_states(source: str, stop_event: Optional[threading.Event]) -> Iterable[FrameState]:
    try:
        import cv2
    except Exception:
        return iter(())

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        cap.release()
        return iter(())

    model = get_cached_yolo_model()
    sample = int(os.getenv("CV_FRAME_SAMPLE_RATE", "5"))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    def iterator():
        frame_index = 0
        try:
            while not (stop_event and stop_event.is_set()):
                ok, image = cap.read()
                if not ok:
                    break
                frame_index += 1
                if frame_index % sample:
                    continue
                timestamp = frame_index / fps
                yield FrameState(timestamp_seconds=timestamp, frame_index=frame_index, detections=_detections_from_frame(image, model))
        finally:
            cap.release()

    return iterator()


def _detections_from_frame(image, model) -> List[DetectionState]:
    if not model:
        return []
    detections: List[DetectionState] = []
    results = model.track(
        image,
        persist=True,
        conf=float(os.getenv("CV_CONFIDENCE_THRESHOLD", ".45")),
        iou=float(os.getenv("CV_IOU_THRESHOLD", ".5")),
        verbose=False,
    )
    names = getattr(model, "names", {}) or {}
    for result in results:
        for idx, box in enumerate(getattr(result, "boxes", []) or []):
            cls_id = int(box.cls[0]) if box.cls is not None else -1
            label = names.get(cls_id, str(cls_id))
            if label == "person" or label in {"backpack", "handbag", "suitcase", "laptop", "cell phone"}:
                if label == "cell phone":
                    label = "unknown_object"
                track = box.id[0] if getattr(box, "id", None) is not None else idx
                xyxy = tuple(float(v) for v in box.xyxy[0].tolist())
                conf = float(box.conf[0]) if box.conf is not None else 0.8
                prefix = "person" if label == "person" else "object"
                detections.append(DetectionState(track_id=f"{prefix}-{int(track)}", label=label, bbox=xyxy, confidence=conf))
    return detections


def _event_model(candidate: EventCandidate, user_id: int, camera_id: int, session_id: Optional[int]) -> Event:
    return Event(
        user_id=user_id,
        camera_id=camera_id,
        session_id=session_id,
        actor_id=_numeric_suffix(candidate.actor_id),
        object_id=_numeric_suffix(candidate.object_id),
        event_type=candidate.event_type,
        scenario=candidate.scenario,
        timestamp_seconds=candidate.timestamp_seconds,
        timestamp_label=candidate.timestamp_label,
        confidence=candidate.confidence,
        description=candidate.description,
        traits_json=json.dumps(candidate.traits),
        metadata_json=json.dumps(candidate.metadata),
    )


def _numeric_suffix(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    digits = "".join(ch for ch in value if ch.isdigit())
    return int(digits) if digits else None


def synthetic_demo_sequence() -> List[FrameState]:
    """Deterministic detection sequence that proves possession events end-to-end."""
    def person(pid, x):
        return DetectionState(track_id=pid, label="person", bbox=(x, 100, x + 60, 220), confidence=0.92)

    def bag(x):
        return DetectionState(track_id="object-1", label="backpack", bbox=(x, 180, x + 30, 220), confidence=0.88)

    frames: List[FrameState] = []
    # person-1 owns object after 3 processed frames -> object_pickup
    for i, t in enumerate([0, 1, 2], 1):
        frames.append(FrameState(t, [person("person-1", 100), bag(125)], i))
    # owner leaves, object stationary and unattended for 10 seconds -> abandoned_object
    for i, t in enumerate([3, 8, 12, 13], 4):
        frames.append(FrameState(t, [person("person-1", 360), bag(125)], i))
    # person-2 picks unattended object -> suspected_unauthorized_removal
    for i, t in enumerate([14, 15, 16], 8):
        frames.append(FrameState(t, [person("person-2", 112), bag(125)], i))
    # handoff sequence: person-2 to person-3 while nearby
    for i, t in enumerate([20, 21, 22], 11):
        frames.append(FrameState(t, [person("person-2", 105), person("person-3", 165), bag(178)], i))
    return frames
