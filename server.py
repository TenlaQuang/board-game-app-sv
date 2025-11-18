# server.py
import os
import time
import random
import uuid
from typing import Dict, List, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# --- CẤU HÌNH CORS (Quan trọng cho Render) ---
# Cho phép mọi nguồn kết nối để tránh lỗi "Connection Refused" từ Client lạ
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATABASE (IN-MEMORY) ---
# Lưu người chơi: { "username": { "ip": "...", "port": 123, "last_seen": 17000... } }
online_users: Dict[str, Dict] = {}

# Lưu phòng: { "12345": { "host_user": "...", "host_ip": "...", "host_port": 123, "created_at": ... } }
rooms: Dict[str, Dict] = {}

# --- MODELS ---
class UserSignal(BaseModel):
    username: str
    p2p_port: int

class JoinRoomRequest(BaseModel):
    username: str
    room_id: str

# --- HELPER: DỌN DẸP DỮ LIỆU RÁC ---
def cleanup_stale_data():
    now = time.time()
    # 1. Xóa người chơi không gửi heartbeat trong 15 giây
    expired_users = [u for u, data in online_users.items() if now - data['last_seen'] > 15]
    for u in expired_users:
        del online_users[u]
    
    # 2. Xóa phòng tạo quá 30 phút mà chưa ai vào (hoặc host đã offline)
    expired_rooms = [rid for rid, r in rooms.items() if now - r['created_at'] > 1800]
    for rid in expired_rooms:
        del rooms[rid]

# --- ENDPOINTS ---

@app.get("/")
def read_root():
    """Health Check Endpoint - Để Render biết Server đang sống"""
    return {"status": "Server is running", "users": len(online_users), "rooms": len(rooms)}

@app.post("/heartbeat")
async def heartbeat(user: UserSignal, request: Request):
    """Client báo danh mỗi 3-5s"""
    client_ip = request.client.host
    # Render có thể dùng Proxy, nên ta ưu tiên lấy header x-forwarded-for nếu có
    if request.headers.get("x-forwarded-for"):
        client_ip = request.headers.get("x-forwarded-for").split(",")[0]

    online_users[user.username] = {
        "ip": client_ip,
        "port": user.p2p_port,
        "last_seen": time.time()
    }
    cleanup_stale_data() # Tiện tay dọn dẹp luôn
    return {"status": "ok"}

@app.get("/users")
async def get_users():
    """Lấy danh sách online"""
    cleanup_stale_data()
    # Trả về list để client hiển thị
    return [{"username": u} for u in online_users]

@app.post("/create-room")
async def create_room(user: UserSignal, request: Request):
    """Tạo phòng mới"""
    client_ip = request.client.host
    if request.headers.get("x-forwarded-for"):
        client_ip = request.headers.get("x-forwarded-for").split(",")[0]

    # Tạo ID 5 số ngẫu nhiên
    room_id = str(random.randint(10000, 99999))
    
    # Nếu xui trùng ID cũ thì tạo lại
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
    """Vào phòng"""
    room = rooms.get(req.room_id)
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Trả về thông tin Host để Client kết nối P2P
    return {
        "status": "found",
        "host_ip": room["host_ip"],
        "host_port": room["host_port"],
        "host_username": room["host_username"]
    }

# --- CONFIG KHỞI CHẠY CHO RENDER ---
if __name__ == "__main__":
    import uvicorn
    # Lấy PORT từ biến môi trường của Render, mặc định là 10000 nếu không có
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
    # server.py (Cập nhật đoạn này vào file cũ hoặc thay thế)
# ... (Các import cũ giữ nguyên) ...

app = FastAPI()

# ... (online_users, rooms giữ nguyên) ...

# --- THÊM MỚI: LƯU LỜI MỜI ---
# Cấu trúc: { "nguoi_nhan": { "from": "nguoi_gui", "room_id": "..." } }
invites: Dict[str, Dict] = {} 

class InviteRequest(BaseModel):
    challenger: str # Người mời
    target: str     # Người được mời
    room_id: str

# ... (Các API heartbeat, users, create-room, join-room GIỮ NGUYÊN) ...

# --- THÊM 2 API MỚI NÀY XUỐNG DƯỚI ---

@app.post("/send-invite")
async def send_invite(req: InviteRequest):
    """Gửi lời mời thách đấu"""
    if req.target not in online_users:
        raise HTTPException(status_code=404, detail="User offline")
    
    invites[req.target] = {
        "from": req.challenger,
        "room_id": req.room_id,
        "timestamp": time.time()
    }
    print(f"[INVITE] {req.challenger} invited {req.target} to room {req.room_id}")
    return {"status": "sent"}

@app.get("/check-invite/{username}")
async def check_invite(username: str):
    """Kiểm tra xem mình có thư mời nào không"""
    invite = invites.get(username)
    if invite:
        # Kiểm tra xem lời mời còn mới không (trong vòng 10s)
        if time.time() - invite["timestamp"] < 10:
            # Đọc xong xóa luôn để không bị mời lại liên tục
            del invites[username]
            return invite
        else:
            # Lời mời quá cũ, xóa đi
            del invites[username]
    return {"status": "none"}

# ... (Phần main uvicorn giữ nguyên) ...