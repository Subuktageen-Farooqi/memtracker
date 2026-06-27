# MemTracker Screenshot Checklist

Use this file as a portfolio screenshot plan. Add captured images under `docs/screenshots/` when running the app locally with real or demo data.

## 1. Dashboard

**Target file:** `docs/screenshots/dashboard.png`

Capture `/dashboard` after demo mode is seeded. Show the summary cards for connected cameras, active monitoring sessions, events today, tracked people, and recent alerts.

## 2. Streams Page

**Target file:** `docs/screenshots/streams.png`

Capture `/dashboard/streams` with the Demo Warehouse Camera visible. Show masked RTSP/demo source, MediaMTX path, generated play URL, and actions.

## 3. Monitor Page

**Target file:** `docs/screenshots/monitor.png`

Capture `/dashboard/monitor?camera_id=<demo_camera_id>&t=128.4`. Show the player area, monitoring status, and selected evidence timestamp card.

## 4. Logs Page

**Target file:** `docs/screenshots/logs.png`

Capture `/dashboard/logs` filtered to `event_type=abandoned_object`. Show timestamp, event type, actor, object, description, confidence, and source camera.

## 5. Chat with Citation

**Target file:** `docs/screenshots/chat-citation.png`

Capture `/dashboard/chat` after asking: “When was a bag abandoned?” Show the assistant answer and clickable `00:02:08 abandoned_object` citation.
