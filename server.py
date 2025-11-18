# server.py (Full Code - Có tính năng Mời)
import os
import time
import random
import uuid
from typing import Dict, List, Optional

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

# --- CƠ SỞ DỮ LIỆU ---
online_users: Dict[str, Dict] = {}
rooms: Dict[str, Dict] = {}

# Cấu trúc: { "nguoi_nhan": { "from": "nguoi_gui", "room_id": "..." } }
invites: Dict[str, Dict] = {} 

# --- MODELS ---
class UserSignal(BaseModel):
    username: str
    p2p_port: int

class JoinRoomRequest(BaseModel):
    username: str
    room_id: str

class InviteRequest(BaseModel):
    challenger: str 
    target: str     
    room_id: str

# --- HELPERS ---
def cleanup_stale_data():
    now = time.time()
    expired_users = [u for u, data in online_users.items() if now - data['last_seen'] > 15]
    for u in expired_users:
        del online_users[u]
    
    expired_rooms = [rid for rid, r in rooms.items() if now - r['created_at'] > 1800]
    for rid in expired_rooms:
        del rooms[rid]

# --- ENDPOINTS CŨ ---
@app.get("/")
def read_root():
    return {"status": "Server is running", "users": len(online_users)}

@app.post("/heartbeat")
async def heartbeat(user: UserSignal, request: Request):
    client_ip = request.client.host
    if request.headers.get("x-forwarded-for"):
        client_ip = request.headers.get("x-forwarded-for").split(",")[0]

    online_users[user.username] = {
        "ip": client_ip,
        "port": user.p2p_port,
        "last_seen": time.time()
    }
    cleanup_stale_data()
    return {"status": "ok"}

@app.get("/users")
async def get_users():
    cleanup_stale_data()
    return [{"username": u} for u in online_users]

@app.post("/create-room")
async def create_room(user: UserSignal, request: Request):
    client_ip = request.client.host
    if request.headers.get("x-forwarded-for"):
        client_ip = request.headers.get("x-forwarded-for").split(",")[0]

    room_id = str(random.randint(10000, 99999))
    while room_id in rooms:
        room_id = str(random.randint(10000, 99999))

    rooms[room_id] = {
        "host_username": user.username,
        "host_ip": client_ip,
        "host_port": user.p2p_port,
        "created_at": time.time()
    }
    print(f"[ROOM] Created {room_id} by {user.username}")
    return {"room_id": room_id}

@app.post("/join-room")
async def join_room(req: JoinRoomRequest):
    room = rooms.get(req.room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    return {
        "status": "found",
        "host_ip": room["host_ip"],
        "host_port": room["host_port"],
        "host_username": room["host_username"]
    }

# --- ENDPOINTS MỚI (INVITE) ---

@app.post("/send-invite")
async def send_invite(req: InviteRequest):
    """Gửi lời mời"""
    if req.target not in online_users:
        raise HTTPException(status_code=404, detail="User offline")
    
    invites[req.target] = {
        "from": req.challenger,
        "room_id": req.room_id,
        "timestamp": time.time()
    }
    print(f"[INVITE] {req.challenger} -> {req.target}")
    return {"status": "sent"}

@app.get("/check-invite/{username}")
async def check_invite(username: str):
    """Kiểm tra lời mời"""
    invite = invites.get(username)
    if invite:
        # Lời mời chỉ tồn tại 10 giây
        if time.time() - invite["timestamp"] < 10:
            del invites[username] # Đọc xong xóa luôn
            return invite
        else:
            del invites[username]
    return {"status": "none"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)