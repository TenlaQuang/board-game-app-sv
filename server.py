# server.py (Bản nâng cấp hỗ trợ Loại Game)
import os
import time
import random
from typing import Dict
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

# --- MODELS MỚI: THÊM game_type ---
class UserSignal(BaseModel):
    username: str
    p2p_port: int
    ip: str | None = None
    # game_type không bắt buộc ở heartbeat

class CreateRoomRequest(BaseModel):
    username: str
    p2p_port: int
    game_type: str
    ip: str | None = None  # <-- THÊM DÒNG NÀY

class JoinRoomRequest(BaseModel):
    username: str
    room_id: str

class InviteRequest(BaseModel):
    challenger: str 
    target: str     
    room_id: str
    game_type: str # Thêm cái này để người nhận biết

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

@app.post("/heartbeat")
async def heartbeat(user: UserSignal, request: Request):
    # IP client gửi lên từ web_matchmaking
    client_ip = user.dict().get("ip")  # <-- LẤY IP RADMIN TỪ JSON

    if not client_ip:
        # Fallback: lấy IP từ request (KHÔNG DÙNG RADMIN)
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

# --- SỬA API TẠO PHÒNG ---
@app.post("/create-room")
async def create_room(req: CreateRoomRequest, request: Request):
    # IP client gửi từ client app
    client_ip = req.dict().get("ip")

    if not client_ip:
        client_ip = request.client.host
        if request.headers.get("x-forwarded-for"):
            client_ip = request.headers.get("x-forwarded-for").split(",")[0]

    room_id = str(random.randint(10000, 99999))
    while room_id in rooms:
        room_id = str(random.randint(10000, 99999))

    rooms[room_id] = {
        "host_username": req.username,
        "host_ip": client_ip,   # <---- LƯU IP RADMIN VÀO ĐÂY
        "host_port": req.p2p_port,
        "game_type": req.game_type,
        "created_at": time.time()
    }
    return {"room_id": room_id}

# --- SỬA API VÀO PHÒNG ---
@app.post("/join-room")
async def join_room(req: JoinRoomRequest):
    room = rooms.get(req.room_id)
    if not room: raise HTTPException(status_code=404, detail="Room not found")
    
    # Trả về thêm game_type để Client biết mà load bàn cờ
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
        "game_type": req.game_type, # Gửi kèm loại game
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