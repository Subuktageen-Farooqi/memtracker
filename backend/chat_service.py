import json, os, re, requests
from models import Event, ChatMessage
KEYWORDS={'abandoned':['abandoned_object'],'bag':['abandoned_object','object_pickup','object_handoff','suspected_unauthorized_removal'],'picked':['suspected_unauthorized_removal','object_pickup'],'handoff':['object_handoff'],'restricted':['restricted_zone_entry'],'enter':['person_entered_scene','restricted_zone_entry']}
def relevant_events(db,user_id,camera_id,message):
    q=db.query(Event).filter(Event.user_id==user_id)
    if camera_id: q=q.filter(Event.camera_id==camera_id)
    events=q.order_by(Event.timestamp_seconds.asc()).all(); msg=message.lower(); wanted=set()
    if 'abandoned' in msg:
        wanted.update(['abandoned_object'])
    else:
        for k,types in KEYWORDS.items():
            if k in msg: wanted.update(types)
    if wanted: events=[e for e in events if e.event_type in wanted or e.scenario in wanted]
    elif 'person-' in msg:
        m=re.search(r'person-\d+',msg); events=[e for e in events if m and m.group(0) in (e.description or '').lower()]
    return events[:20]
def citation(e):
    return {'event_id':e.id,'timestamp_seconds':e.timestamp_seconds,'timestamp_label':e.timestamp_label,'event_type':e.event_type,'scenario':e.scenario,'actor_id':e.actor_id,'object_id':e.object_id,'description':e.description,'confidence':e.confidence}
def answer_chat(db,user_id,camera_id,message):
    events=relevant_events(db,user_id,camera_id,message)
    if not events:
        ans='I could not find that in the logs.'; cites=[]
    else:
        cites=[citation(e) for e in events]
        if os.getenv('GROQ_API_KEY'):
            try:
                payload={'model':os.getenv('GROQ_MODEL','llama-3.1-8b-instant'),'messages':[{'role':'system','content':'You are MemTracker Assistant. Answer only from event logs. Return cautious answers with timestamps.'},{'role':'user','content':json.dumps({'question':message,'events':cites})}], 'temperature':0.1}
                r=requests.post('https://api.groq.com/openai/v1/chat/completions',headers={'Authorization':'Bearer '+os.getenv('GROQ_API_KEY')},json=payload,timeout=10)
                ans=r.json()['choices'][0]['message']['content'] if r.ok else None
            except Exception: ans=None
        else: ans=None
        if not ans:
            first=events[0]; ans=f"I found {len(events)} matching event(s). {first.description} at {first.timestamp_label}."
    db.add(ChatMessage(user_id=user_id,camera_id=camera_id,role='user',content=message,citations_json='[]'))
    db.add(ChatMessage(user_id=user_id,camera_id=camera_id,role='assistant',content=ans,citations_json=json.dumps(cites)))
    db.commit(); return {'answer':ans,'citations':cites}
