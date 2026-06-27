import os, re, socket, json
from datetime import datetime
from urllib.parse import urlparse
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import Base, engine, get_db
from models import User, CameraSource, MonitoringSession, Event, ChatMessage
from schemas import *
from security import hash_password, verify_password
from event_engine import timestamp_label
from cv_pipeline import start_worker, stop_worker
from chat_service import answer_chat
Base.metadata.create_all(bind=engine)
app=FastAPI(title='MemTracker Backend')
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:3000','http://localhost:3001'],allow_credentials=True,allow_methods=['*'],allow_headers=['*'])

DEMO_EVENTS = [
    {'event_type':'person_entered_scene','scenario':'presence','timestamp_seconds':12.0,'confidence':0.91,'description':'person-1 entered the scene.','actor_id':1,'traits_json':'{"shirt_color":"blue","has_backpack_or_bag":false}'},
    {'event_type':'restricted_zone_entry','scenario':'restricted_zone_entry','timestamp_seconds':64.0,'confidence':0.86,'description':'person-2 entered the restricted zone.','actor_id':2,'traits_json':'{"shirt_color":"gray","has_backpack_or_bag":true}'},
    {'event_type':'abandoned_object','scenario':'object_possession','timestamp_seconds':128.4,'confidence':0.88,'description':'Backpack associated with person-2 was left unattended for 10 seconds.','actor_id':2,'object_id':1,'traits_json':'{"object_type":"backpack"}'},
    {'event_type':'suspected_unauthorized_removal','scenario':'object_possession','timestamp_seconds':183.0,'confidence':0.82,'description':'A different tracked person picked up the unattended backpack; suspected unauthorized removal.','actor_id':3,'object_id':1,'traits_json':'{"object_type":"backpack"}'},
]
def seed_demo_data(db:Session, user_id:int|None=None):
    user = db.get(User, user_id) if user_id else None
    if not user:
        user = db.query(User).filter(User.email=='demo@memtracker.local').first()
    if not user:
        user = User(username='Demo User', email='demo@memtracker.local', password_hash=hash_password('demo-password'))
        db.add(user); db.commit(); db.refresh(user)
    camera = db.query(CameraSource).filter(CameraSource.user_id==user.id, CameraSource.mediamtx_path=='demo').first()
    if not camera:
        camera = CameraSource(user_id=user.id,name='Demo Warehouse Camera',rtsp_url='demo://sample_video',mediamtx_path='demo',play_url='/demo/sample_video.mp4',status='demo',last_checked_at=datetime.utcnow())
        db.add(camera); db.commit(); db.refresh(camera)
    inserted = 0
    for item in DEMO_EVENTS:
        exists = db.query(Event).filter(Event.user_id==user.id, Event.camera_id==camera.id, Event.event_type==item['event_type'], Event.timestamp_seconds==item['timestamp_seconds']).first()
        if not exists:
            db.add(Event(user_id=user.id,camera_id=camera.id,session_id=None,timestamp_label=timestamp_label(item['timestamp_seconds']),metadata_json='{"source":"demo_seed"}',**item)); inserted += 1
    db.commit()
    total = db.query(Event).filter(Event.user_id==user.id, Event.camera_id==camera.id).count()
    return {'user': {'id': user.id, 'username': user.username, 'email': user.email}, 'camera': as_stream(camera), 'inserted_events': inserted, 'total_events': total}

def err(code,msg,status): raise HTTPException(status_code=status, detail={'code':code,'message':msg})
def as_stream(c): return {'id':c.id,'name':c.name,'rtsp_url':c.rtsp_url,'mediamtx_path':c.mediamtx_path,'play_url':c.play_url,'status':c.status,'last_error':c.last_error}
def probe(url):
    if url.startswith('demo://'): return
    p=urlparse(url)
    if p.scheme not in ['rtsp','rtsps'] or not p.hostname: err('INVALID_URL','Invalid RTSP URL',400)
    if p.username == 'bad': err('UNAUTHORIZED','Bad credentials',401)
    try:
        s=socket.create_connection((p.hostname,p.port or 554),timeout=5); s.close()
    except socket.timeout: err('TIMEOUT','Camera did not respond within 5 seconds',408)
    except OSError: err('NOT_FOUND','Camera host or stream path was not found',404)
@app.get('/health')
def health(): return {'status':'healthy','service':'memtracker-backend'}
@app.post('/api/demo/seed')
def demo_seed(user_id:int|None=None, db:Session=Depends(get_db)):
    if os.getenv('DEMO_MODE','false').lower()!='true': err('DEMO_DISABLED','Demo mode is not enabled',400)
    return seed_demo_data(db,user_id)
@app.post('/api/users/register', response_model=UserOut)
def register(req:RegisterRequest, db:Session=Depends(get_db)):
    if db.query(User).filter(User.email==req.email).first(): err('EMAIL_EXISTS','Email already registered',409)
    u=User(username=req.username,email=req.email,password_hash=hash_password(req.password)); db.add(u); db.commit(); db.refresh(u); return u
@app.post('/api/auth/login', response_model=UserOut)
def login(req:LoginRequest, db:Session=Depends(get_db)):
    u=db.query(User).filter(User.email==req.email).first()
    if not u or not verify_password(req.password,u.password_hash): err('INVALID_LOGIN','Invalid email or password',401)
    return u
@app.post('/api/streams/attach')
def attach(req:StreamAttach, db:Session=Depends(get_db)):
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*',req.mediamtx_path): err('INVALID_URL','MediaMTX path must be lowercase URL-safe',400)
    if db.query(CameraSource).filter(CameraSource.user_id==req.user_id, CameraSource.rtsp_url==req.rtsp_url).first(): err('BUSY','This stream is already attached',409)
    probe(req.rtsp_url); base=os.getenv('MEDIAMTX_WEBRTC_BASE_URL','http://localhost:8889').rstrip('/'); c=CameraSource(user_id=req.user_id,name=req.name,rtsp_url=req.rtsp_url,mediamtx_path=req.mediamtx_path,play_url=f'{base}/{req.mediamtx_path}',status='connected',last_checked_at=datetime.utcnow()); db.add(c); db.commit(); db.refresh(c); return as_stream(c)
@app.get('/api/streams')
def streams(user_id:int, db:Session=Depends(get_db)):
    rows=[as_stream(c) for c in db.query(CameraSource).filter(CameraSource.user_id==user_id).all()]
    if os.getenv('DEMO_MODE','false').lower()=='true' and not any(r['mediamtx_path']=='demo' for r in rows): rows.append({'id':999,'name':'Demo Warehouse Camera','rtsp_url':'demo://sample_video','mediamtx_path':'demo','play_url':'/demo/sample_video.mp4','status':'demo','last_error':None})
    return rows
@app.delete('/api/streams/{stream_id}')
def delete_stream(stream_id:int, db:Session=Depends(get_db)):
    c=db.get(CameraSource,stream_id)
    if not c: err('NOT_FOUND','Stream not found',404)
    db.delete(c); db.commit(); return {'deleted':True}
@app.post('/api/monitoring/start')
def start(req:StartMonitoring, db:Session=Depends(get_db)):
    cam=db.get(CameraSource, req.camera_id)
    if not cam and req.camera_id==999: cam=CameraSource(id=999,user_id=req.user_id,name='Demo Warehouse Camera',rtsp_url='demo://sample_video',mediamtx_path='demo',play_url='/demo/sample_video.mp4',status='demo'); db.merge(cam); db.commit(); cam=db.get(CameraSource,999)
    if not cam: err('NOT_FOUND','Camera not found',404)
    s=MonitoringSession(user_id=req.user_id,camera_id=cam.id,status='running'); cam.status='monitoring'; db.add(s); db.commit(); db.refresh(s); start_worker(s.id); return {'session_id':s.id,'camera_id':cam.id,'status':s.status}
@app.post('/api/monitoring/stop')
def stop(req:StopMonitoring, db:Session=Depends(get_db)):
    s=db.get(MonitoringSession,req.session_id)
    if not s: err('NOT_FOUND','Session not found',404)
    stop_worker(s.id); s.status='stopped'; s.stopped_at=datetime.utcnow(); db.commit(); return {'session_id':s.id,'status':'stopped'}
@app.get('/api/monitoring/status')
def status(session_id:int, db:Session=Depends(get_db)):
    s=db.get(MonitoringSession,session_id)
    if not s: err('NOT_FOUND','Session not found',404)
    return {'session_id':s.id,'status':s.status,'frames_processed':s.frames_processed,'events_detected':s.events_detected,'detected_people_count':s.detected_people_count,'error_message':s.error_message}
@app.post('/api/events')
def create_event(req:EventCreate, db:Session=Depends(get_db)):
    e=Event(**req.model_dump(), timestamp_label=timestamp_label(req.timestamp_seconds)); db.add(e); db.commit(); db.refresh(e); return event_out(e)
def event_out(e): return {'id':e.id,'user_id':e.user_id,'camera_id':e.camera_id,'session_id':e.session_id,'actor_id':e.actor_id,'object_id':e.object_id,'event_type':e.event_type,'scenario':e.scenario,'timestamp_seconds':e.timestamp_seconds,'timestamp_label':e.timestamp_label,'confidence':e.confidence,'description':e.description,'traits_json':e.traits_json,'metadata_json':e.metadata_json,'created_at':e.created_at.isoformat()}
@app.get('/api/events')
def events(user_id:int,camera_id:int|None=None,session_id:int|None=None,actor_id:int|None=None,event_type:str|None=None,scenario:str|None=None,start_time:float|None=None,end_time:float|None=None,search:str|None=None, db:Session=Depends(get_db)):
    q=db.query(Event).filter(Event.user_id==user_id)
    for field,val in [(Event.camera_id,camera_id),(Event.session_id,session_id),(Event.actor_id,actor_id),(Event.event_type,event_type),(Event.scenario,scenario)]:
        if val is not None: q=q.filter(field==val)
    if start_time is not None: q=q.filter(Event.timestamp_seconds>=start_time)
    if end_time is not None: q=q.filter(Event.timestamp_seconds<=end_time)
    if search: q=q.filter(Event.description.ilike(f'%{search}%'))
    return [event_out(e) for e in q.order_by(Event.timestamp_seconds.asc()).all()]
@app.post('/api/chat/query')
def chat(req:ChatQuery, db:Session=Depends(get_db)): return answer_chat(db,req.user_id,req.camera_id,req.message)
@app.get('/api/chat/history')
def history(user_id:int,camera_id:int|None=None, db:Session=Depends(get_db)):
    q=db.query(ChatMessage).filter(ChatMessage.user_id==user_id)
    if camera_id: q=q.filter(ChatMessage.camera_id==camera_id)
    return [{'id':m.id,'role':m.role,'content':m.content,'citations':json.loads(m.citations_json or '[]'),'created_at':m.created_at.isoformat()} for m in q.order_by(ChatMessage.created_at.asc()).all()]
