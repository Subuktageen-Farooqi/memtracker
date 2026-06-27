# MediaMTX Setup for MemTracker

MemTracker keeps RTSP out of the browser. RTSP is used by the backend CV worker, while MediaMTX converts camera streams into browser-playable WebRTC pages.

## Example `mediamtx.yml`

```yaml
paths:
  cam1:
    source: rtsp://USER:PASS@CAMERA_IP:554/stream1
    sourceOnDemand: yes
```

`cam1` is the MediaMTX path. With `MEDIAMTX_WEBRTC_BASE_URL=http://localhost:8889`, MemTracker generates this browser play URL:

```text
http://localhost:8889/cam1
```

The frontend embeds the generated URL as:

```tsx
<iframe
  src={`${camera.play_url}?controls=true&muted=true&autoplay=true`}
  className="video"
  allow="autoplay; fullscreen"
/>
```

Do not put `rtsp://` in a browser `<video>` tag. Live WebRTC cannot seek backward without DVR/recording; demo video mode supports true timestamp seeking.
