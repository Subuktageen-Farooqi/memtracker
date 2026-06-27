from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any
class RegisterRequest(BaseModel): username:str; email:EmailStr; password:str
class LoginRequest(BaseModel): email:EmailStr; password:str
class UserOut(BaseModel): id:int; username:str; email:str
class StreamAttach(BaseModel): user_id:int; name:str; rtsp_url:str; mediamtx_path:str
class StreamOut(BaseModel): id:int; name:str; rtsp_url:str; mediamtx_path:str; play_url:str; status:str; last_error:Optional[str]=None
class StartMonitoring(BaseModel): user_id:int; camera_id:int
class StopMonitoring(BaseModel): session_id:int
class EventCreate(BaseModel): user_id:int; camera_id:int; session_id:Optional[int]=None; actor_id:Optional[int]=None; object_id:Optional[int]=None; event_type:str; scenario:str='general'; timestamp_seconds:float; confidence:float=.8; description:str; traits_json:Optional[str]=None; metadata_json:Optional[str]=None
class ChatQuery(BaseModel): user_id:int; camera_id:Optional[int]=None; message:str
