from backend.event_engine import DetectionState, EventEngine, FrameState


def person(pid, x):
    return DetectionState(track_id=pid, label="person", bbox=(x, 100, x + 60, 220), confidence=0.9)


def bag(x=125):
    return DetectionState(track_id="object-1", label="backpack", bbox=(x, 180, x + 30, 220), confidence=0.88)


def event_types(events):
    return [event.event_type for event in events]


def test_object_near_person_for_three_frames_creates_pickup():
    engine = EventEngine()
    emitted = []
    for idx, ts in enumerate([0, 1, 2], 1):
        emitted.extend(engine.update_frame(FrameState(ts, [person("person-1", 100), bag()], idx)))
    assert event_types(emitted) == ["object_pickup"]
    assert emitted[0].actor_id == "person-1"
    assert emitted[0].object_id == "object-1"


def test_stationary_object_owner_walks_away_creates_abandoned_object():
    engine = EventEngine()
    emitted = []
    for idx, ts in enumerate([0, 1, 2], 1):
        emitted.extend(engine.update_frame(FrameState(ts, [person("person-1", 100), bag()], idx)))
    for idx, ts in enumerate([3, 8, 12, 13], 4):
        emitted.extend(engine.update_frame(FrameState(ts, [person("person-1", 360), bag()], idx)))
    assert "abandoned_object" in event_types(emitted)
    abandoned = [event for event in emitted if event.event_type == "abandoned_object"][0]
    assert abandoned.actor_id == "person-1"
    assert abandoned.timestamp_seconds >= 13


def test_unattended_object_picked_by_different_person_creates_suspected_unauthorized_removal():
    engine = EventEngine()
    emitted = []
    for idx, ts in enumerate([0, 1, 2], 1):
        emitted.extend(engine.update_frame(FrameState(ts, [person("person-1", 100), bag()], idx)))
    for idx, ts in enumerate([3, 8, 12, 13], 4):
        emitted.extend(engine.update_frame(FrameState(ts, [person("person-1", 360), bag()], idx)))
    for idx, ts in enumerate([14, 15, 16], 8):
        emitted.extend(engine.update_frame(FrameState(ts, [person("person-2", 112), bag()], idx)))
    assert "suspected_unauthorized_removal" in event_types(emitted)
    removal = [event for event in emitted if event.event_type == "suspected_unauthorized_removal"][0]
    assert removal.actor_id == "person-2"
    assert removal.metadata["previous_owner"] == "person-1"


def test_object_transfer_between_nearby_people_creates_handoff():
    engine = EventEngine()
    emitted = []
    for idx, ts in enumerate([0, 1, 2], 1):
        emitted.extend(engine.update_frame(FrameState(ts, [person("person-1", 100), bag()], idx)))
    for idx, ts in enumerate([3, 4, 5], 4):
        emitted.extend(engine.update_frame(FrameState(ts, [person("person-1", 105), person("person-2", 165), bag(178)], idx)))
    assert "object_handoff" in event_types(emitted)
    handoff = [event for event in emitted if event.event_type == "object_handoff"][0]
    assert handoff.actor_id == "person-2"
    assert handoff.metadata["previous_owner"] == "person-1"
