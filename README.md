# Board Game P2P lai♟️

🌟 Giới thiệu

Dự án này là một ứng dụng Desktop được xây dựng bằng Python và Pygame, cho phép hai người chơi kết nối và thi đấu trực tiếp với nhau. Điểm đặc biệt là cơ chế kết nối mạng:

Sử dụng một Server trung gian (Matchmaking Server) để giúp hai máy tìm thấy nhau.

Sau khi kết nối, dữ liệu bàn cờ (nước đi, chat) sẽ được truyền trực tiếp (P2P) giữa hai máy, giảm độ trễ và giảm tải cho server.

✨ Tính năng chính

🎮 Hai loại cờ: Hỗ trợ đầy đủ luật chơi Cờ Vua (Chess) và Cờ Tướng (Xiangqi).

🌐 Chơi Online: Kết nối với bạn bè qua mạng Internet (sử dụng Radmin VPN hoặc Server Render để bắt tay).

💬 Trò chuyện (Chat): Chat trực tiếp với đối thủ ngay trong trận đấu.

🔄 Phân lượt & Đảo bàn cờ: Hệ thống tự động phân định lượt đi và xoay bàn cờ theo góc nhìn người chơi.

🏳️ Đầu hàng & Xin hòa: Tính năng gửi yêu cầu cầu hòa hoặc chịu thua.

🎨 Giao diện đẹp: Sử dụng pygame_gui với theme tùy chỉnh, hiệu ứng nền động (Animated Background).

## Cấu trúc thư mục

- `ai/`: Chứa mô hình AI cho 2 game
- `core/`: Logic game (bàn cờ, quân cờ, luật di chuyển)
- `network/`: Xử lý kết nối mạng (host/client)
- `ui/`: Giao diện pygame
- `games/`: Các loại game (cờ vua, cờ tướng)
- `utils/`: Các hàm tiện ích và hằng số
- `tests/`: Unit test
.......................................
🚀 Hướng dẫn cài đặt & Chạy
