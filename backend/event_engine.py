from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

TARGET_OBJECTS = {"backpack", "handbag", "suitcase", "bag", "laptop", "unknown_object"}

BBox = Tuple[float, float, float, float]


def timestamp_label(seconds: float) -> str:
    seconds = max(0, int(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def center(bbox: BBox) -> Tuple[float, float]:
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def distance(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def overlaps(a: BBox, b: BBox) -> bool:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return max(ax1, bx1) <= min(ax2, bx2) and max(ay1, by1) <= min(ay2, by2)


@dataclass(frozen=True)
class DetectionState:
    track_id: str
    label: str
    bbox: BBox
    confidence: float = 0.8
    traits: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_person(self) -> bool:
        return self.label == "person"

    @property
    def is_object(self) -> bool:
        return self.label in TARGET_OBJECTS


@dataclass(frozen=True)
class FrameState:
    timestamp_seconds: float
    detections: List[DetectionState]
    frame_index: int = 0


@dataclass(frozen=True)
class EventCandidate:
    event_type: str
    scenario: str
    timestamp_seconds: float
    timestamp_label: str
    actor_id: Optional[str]
    object_id: Optional[str]
    confidence: float
    description: str
    traits: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ObjectTrackState:
    object_id: str
    object_type: str
    first_seen: float
    last_seen: float
    last_center: Tuple[float, float]
    current_owner: Optional[str] = None
    previous_owner: Optional[str] = None
    association_counts: Dict[str, int] = field(default_factory=dict)
    unattended_since: Optional[float] = None
    stationary_since: Optional[float] = None
    abandoned_reported: bool = False
    unauthorized_reported: bool = False
    emitted_pickups: set[str] = field(default_factory=set)
    emitted_handoffs: set[Tuple[str, str]] = field(default_factory=set)


class EventEngine:
    """Stateful, YOLO-independent event rules over normalized detections.

    The CV layer converts raw model results into `FrameState`. Tests can bypass YOLO
    entirely by constructing `FrameState` values directly.
    """

    def __init__(
        self,
        ownership_frames: int = 3,
        unattended_seconds: float = 10.0,
        near_distance_px: float = 90.0,
        stationary_distance_px: float = 8.0,
        handoff_distance_px: float = 140.0,
    ):
        self.ownership_frames = ownership_frames
        self.unattended_seconds = unattended_seconds
        self.near_distance_px = near_distance_px
        self.stationary_distance_px = stationary_distance_px
        self.handoff_distance_px = handoff_distance_px
        self.objects: Dict[str, ObjectTrackState] = {}

    def update_frame(self, frame: FrameState) -> List[EventCandidate]:
        people = {d.track_id: d for d in frame.detections if d.is_person}
        objects = [d for d in frame.detections if d.is_object]
        events: List[EventCandidate] = []
        for obj in objects:
            state = self._state_for_object(obj, frame.timestamp_seconds)
            obj_center = center(obj.bbox)
            moved = distance(obj_center, state.last_center)
            if moved <= self.stationary_distance_px:
                state.stationary_since = state.stationary_since or frame.timestamp_seconds
            else:
                state.stationary_since = None
                state.abandoned_reported = False
                state.unauthorized_reported = False
            state.last_center = obj_center
            state.last_seen = frame.timestamp_seconds

            nearest_owner = self._nearest_person(obj, people.values())
            confirmed_owner = self._confirmed_owner(state, nearest_owner)
            if confirmed_owner:
                events.extend(self._handle_confirmed_owner(state, obj, confirmed_owner, people, frame.timestamp_seconds))
            elif nearest_owner is None:
                events.extend(self._handle_unattended(state, obj, frame.timestamp_seconds))
        return events

    def _state_for_object(self, obj: DetectionState, now: float) -> ObjectTrackState:
        if obj.track_id not in self.objects:
            self.objects[obj.track_id] = ObjectTrackState(
                object_id=obj.track_id,
                object_type=obj.label,
                first_seen=now,
                last_seen=now,
                last_center=center(obj.bbox),
            )
        return self.objects[obj.track_id]

    def _nearest_person(self, obj: DetectionState, people: Iterable[DetectionState]) -> Optional[DetectionState]:
        best: Optional[DetectionState] = None
        best_distance = float("inf")
        obj_center = center(obj.bbox)
        for person in people:
            d = 0.0 if overlaps(obj.bbox, person.bbox) else distance(obj_center, center(person.bbox))
            if d <= self.near_distance_px and d < best_distance:
                best = person
                best_distance = d
        return best

    def _confirmed_owner(self, state: ObjectTrackState, nearest_owner: Optional[DetectionState]) -> Optional[str]:
        if nearest_owner is None:
            state.association_counts.clear()
            return None
        owner_id = nearest_owner.track_id
        state.association_counts[owner_id] = state.association_counts.get(owner_id, 0) + 1
        for other in list(state.association_counts):
            if other != owner_id:
                state.association_counts[other] = 0
        if state.association_counts[owner_id] >= self.ownership_frames:
            return owner_id
        return None

    def _handle_confirmed_owner(
        self,
        state: ObjectTrackState,
        obj: DetectionState,
        owner_id: str,
        people: Dict[str, DetectionState],
        now: float,
    ) -> List[EventCandidate]:
        events: List[EventCandidate] = []
        old_owner = state.current_owner
        previous_owner = state.previous_owner or old_owner
        was_unattended = state.unattended_since is not None and (now - state.unattended_since) >= self.unattended_seconds
        state.unattended_since = None
        if old_owner is None:
            state.current_owner = owner_id
            if was_unattended and previous_owner and previous_owner != owner_id and not state.unauthorized_reported:
                state.unauthorized_reported = True
                events.append(self._event("suspected_unauthorized_removal", state, obj, owner_id, now, obj.confidence))
            elif owner_id not in state.emitted_pickups:
                state.emitted_pickups.add(owner_id)
                events.append(self._event("object_pickup", state, obj, owner_id, now, obj.confidence))
        elif old_owner != owner_id:
            if self._people_near(old_owner, owner_id, people) and (old_owner, owner_id) not in state.emitted_handoffs:
                state.emitted_handoffs.add((old_owner, owner_id))
                events.append(self._event("object_handoff", state, obj, owner_id, now, obj.confidence, previous_actor=old_owner))
            state.previous_owner = old_owner
            state.current_owner = owner_id
        return events

    def _handle_unattended(self, state: ObjectTrackState, obj: DetectionState, now: float) -> List[EventCandidate]:
        if state.current_owner:
            state.previous_owner = state.current_owner
        state.current_owner = None
        state.unattended_since = state.unattended_since or now
        stationary_long_enough = state.stationary_since is not None and (now - state.stationary_since) >= self.unattended_seconds
        unattended_long_enough = (now - state.unattended_since) >= self.unattended_seconds
        if state.previous_owner and stationary_long_enough and unattended_long_enough and not state.abandoned_reported:
            state.abandoned_reported = True
            return [self._event("abandoned_object", state, obj, state.previous_owner, now, obj.confidence)]
        return []

    def _people_near(self, a: str, b: str, people: Dict[str, DetectionState]) -> bool:
        if a not in people or b not in people:
            return False
        return distance(center(people[a].bbox), center(people[b].bbox)) <= self.handoff_distance_px

    def _event(
        self,
        event_type: str,
        state: ObjectTrackState,
        obj: DetectionState,
        actor_id: str,
        now: float,
        confidence: float,
        previous_actor: Optional[str] = None,
    ) -> EventCandidate:
        descriptions = {
            "object_pickup": f"{actor_id} became associated with {state.object_type} {state.object_id}.",
            "abandoned_object": f"{state.object_type.title()} {state.object_id} associated with {actor_id} remained stationary and unattended for {int(self.unattended_seconds)} seconds.",
            "suspected_unauthorized_removal": f"{actor_id} picked up unattended {state.object_type} {state.object_id}; suspected unauthorized removal.",
            "object_handoff": f"{state.object_type.title()} {state.object_id} moved from {previous_actor} to {actor_id} while both people were nearby.",
        }
        return EventCandidate(
            event_type=event_type,
            scenario="object_possession",
            timestamp_seconds=now,
            timestamp_label=timestamp_label(now),
            actor_id=actor_id,
            object_id=state.object_id,
            confidence=confidence,
            description=descriptions[event_type],
            traits={"object_type": state.object_type},
            metadata={"previous_owner": previous_actor or state.previous_owner, "current_owner": state.current_owner},
        )

    # Backward-compatible helper retained for existing callers.
    def object_possession_events(self, object_id, owner, previous_owner, stationary, unattended_seconds, now):
        events = []
        if owner and previous_owner and owner != previous_owner:
            events.append("object_handoff")
        if owner and not previous_owner:
            events.append("object_pickup")
        if stationary and previous_owner and not owner and unattended_seconds >= self.unattended_seconds:
            events.append("abandoned_object")
        if owner and previous_owner and owner != previous_owner and unattended_seconds >= self.unattended_seconds:
            events.append("suspected_unauthorized_removal")
        return events
