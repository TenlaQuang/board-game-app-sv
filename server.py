# server.py (Đã hợp nhất logic IP Radmin và Game Type)
import os
import time
import random
from typing import Dict, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

online_users: Dict[str, Dict] = {}
rooms: Dict[str, Dict] = {}
invites: Dict[str, Dict] = {} 

# --- MODELS MỚI: THÊM ip OPTIONAL CHO TÍNH NĂNG RADMIN ---
class UserSignal(BaseModel):
    username: str
    p2p_port: int
    ip: Optional[str] = None # <--- THÊM: IP Radmin/LAN

class CreateRoomRequest(BaseModel): 
    username: str
    p2p_port: int
    game_type: str # 'chess' hoặc 'chinese_chess'
    ip: Optional[str] = None # <--- THÊM: IP Radmin/LAN

class JoinRoomRequest(BaseModel):
    username: str
    room_id: str

class InviteRequest(BaseModel):
    challenger: str 
    target: str     
    room_id: str
    game_type: str 
    ip: Optional[str] = None # <--- THÊM: IP Radmin/LAN

# --- HELPERS GIỮ NGUYÊN ---
def cleanup_stale_data():
    now = time.time()
    expired_users = [u for u, data in online_users.items() if now - data['last_seen'] > 15]
    for u in expired_users: del online_users[u]
    expired_rooms = [rid for rid, r in rooms.items() if now - r['created_at'] > 1800]
    for rid in expired_rooms: del rooms[rid]

# --- ENDPOINTS ---
@app.get("/")
def read_root(): return {"status": "Server OK"}

# --- SỬA API HEARTBEAT (Ưu tiên IP Radmin/Payload) ---
@app.post("/heartbeat")
async def heartbeat(user: UserSignal, request: Request):
    # LẤY IP: Ưu tiên IP từ payload (IP Radmin), nếu không có thì lấy Public IP từ request
    client_ip = user.ip if user.ip else request.client.host 
    
    online_users[user.username] = {"ip": client_ip, "port": user.p2p_port, "last_seen": time.time()}
    cleanup_stale_data()
    return {"status": "ok"}

@app.get("/users")
async def get_users():
    cleanup_stale_data()
    return [{"username": u} for u in online_users]

# --- SỬA API TẠO PHÒNG (Ưu tiên IP Radmin/Payload) ---
@app.post("/create-room")
async def create_room(req: CreateRoomRequest, request: Request):
    # LẤY IP: Ưu tiên IP từ payload (IP Radmin), nếu không có thì lấy Public IP từ request
    client_ip = req.ip if req.ip else request.client.host 
    
    room_id = str(random.randint(10000, 99999))
    while room_id in rooms: room_id = str(random.randint(10000, 99999))

    rooms[room_id] = {
        "host_username": req.username,
        "host_ip": client_ip, 
        "host_port": req.p2p_port,
        "game_type": req.game_type, 
        "created_at": time.time()
    }
    print(f"[ROOM] {room_id} ({req.game_type}) by {req.username}")
    return {"room_id": room_id}

# --- SỬA API VÀO PHÒNG ---
@app.post("/join-room")
async def join_room(req: JoinRoomRequest):
    room = rooms.get(req.room_id)
    if not room: raise HTTPException(status_code=404, detail="Room not found")
    
    # Trả về IP đã được lưu (là IP Radmin)
    return {
        "status": "found",
        "host_ip": room["host_ip"], 
        "host_port": room["host_port"],
        "host_username": room["host_username"],
        "game_type": room.get("game_type", "chess") 
    }

# --- SỬA API MỜI ---
@app.post("/send-invite")
async def send_invite(req: InviteRequest):
    if req.target not in online_users:
        raise HTTPException(status_code=404, detail="User offline")
    
    invites[req.target] = {
        "from": req.challenger,
        "room_id": req.room_id,
        "game_type": req.game_type, 
        "timestamp": time.time()
    }
    return {"status": "sent"}

@app.get("/check-invite/{username}")
async def check_invite(username: str):
    invite = invites.get(username)
    if invite:
        if time.time() - invite["timestamp"] < 10:
            del invites[username]
            return invite
        else:
            del invites[username]
    return {"status": "none"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)