from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Optional, List, Dict
import uuid
import time

# Khởi tạo ứng dụng FastAPI
app = FastAPI()

# --- Cơ sở dữ liệu "in-memory" đơn giản ---
# Lưu người chơi đang chờ (dạng hàng đợi)
waiting_queue: List[Dict] = []
# Lưu các trận đã ghép cặp
matches: Dict[str, Dict] = {}
# -----------------------------------------

# --- Pydantic Models (để xác thực data gửi lên) ---
class RegisterRequest(BaseModel):
    username: str
    p2p_port: Optional[int] = None

class UnregisterRequest(BaseModel):
    username: str
    p2p_port: Optional[int] = None
# -----------------------------------------

@app.get("/")
def read_root():
    """Endpoint gốc để kiểm tra server có đang chạy không."""
    return {"status": "Matchmaking Server is running", "waiting_players": len(waiting_queue)}

@app.post("/register")
async def register(player: RegisterRequest, request: Request):
    """
    Endpoint chính: Người chơi đăng ký tìm trận.
    - Nếu không có ai chờ, thêm vào hàng chờ.
    - Nếu có người chờ, ghép cặp họ.
    """
    global waiting_queue, matches
    
    # Lấy IP public của người chơi
    client_ip = request.client.host
    session_id = str(uuid.uuid4())
    current_time = time.time()

    player_data = {
        "session_id": session_id,
        "username": player.username,
        "p2p_port": player.p2p_port,
        "client_ip": client_ip,
        "timestamp": current_time
    }

    # Dọn dẹp hàng chờ: Xóa bất kỳ ai chờ quá 70 giây
    new_queue = []
    for p in waiting_queue:
        if current_time - p["timestamp"] < 70: # Client timeout là 60s
            new_queue.append(p)
        else:
            # Xóa khỏi `matches` nếu họ bị timeout
            matches.pop(p["session_id"], None)
    waiting_queue = new_queue
    # --- Kết thúc dọn dẹp ---

    if waiting_queue:
        # --- TÌM THẤY ĐỐI THỦ ---
        # Lấy người chơi đầu tiên trong hàng chờ
        opponent = waiting_queue.pop(0) 
        
        # Tạo bản ghi "matched" cho đối thủ
        matches[opponent["session_id"]] = {
            "status": "matched",
            "peer_ip": player_data["client_ip"],
            "peer_p2p_port": player_data["p2p_port"],
            "peer_username": player_data["username"]
        }
        
        # Tạo bản ghi "matched" cho người chơi hiện tại
        matches[session_id] = {
            "status": "matched",
            "peer_ip": opponent["client_ip"],
            "peer_p2p_port": opponent["p2p_port"],
            "peer_username": opponent["username"]
        }
        
        print(f"MATCHED: {player_data['username']} vs {opponent['username']}")
    
    else:
        # --- KHÔNG CÓ AI CHỜ ---
        # Thêm người chơi này vào hàng chờ
        waiting_queue.append(player_data)
        matches[session_id] = {"status": "waiting"}
        print(f"WAITING: {player_data['username']} added to queue.")

    # Luôn trả về session_id cho client
    return {"session_id": session_id}

@app.get("/match/{session_id}")
async def get_match(session_id: str):
    """
    Endpoint để client "poll" (hỏi liên tục) xem đã được ghép cặp chưa.
    """
    match_info = matches.get(session_id)
    
    if not match_info:
        return {"status": "error", "detail": "Session not found or expired"}

    if match_info["status"] == "matched":
        # Ghép cặp thành công! Trả về thông tin đối thủ
        # Chúng ta xóa trận đấu khỏi 'matches' sau khi cả hai đã lấy
        # (Để đơn giản, chúng ta chỉ xóa sau khi một người lấy)
        # matches.pop(session_id, None) 
        return match_info
    
    else: 
        # Vẫn đang chờ
        return {"status": "waiting"}

@app.post("/unregister")
async def unregister(player: UnregisterRequest):
    """
    Client thông báo họ hủy tìm trận (ví dụ: timeout).
    (Hàm này mang tính lịch sự, không bắt buộc)
    """
    global waiting_queue
    # Xóa người chơi khỏi hàng chờ (nếu họ còn ở đó)
    waiting_queue = [p for p in waiting_queue if p["username"] != player.username]
    print(f"UNREGISTER: {player.username} removed from queue (if existed).")
    return {"status": "unregistered (best effort)"}

# --- Cấu hình cho Render ---
if __name__ == "__main__":
    import uvicorn
    # Render sẽ tự động dùng gunicorn/uvicorn, 
    # nhưng dòng này để bạn test local
    uvicorn.run(app, host="0.0.0.0", port=8000)