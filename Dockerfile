# Stage 1: Sử dụng Python 3.10-slim làm base image, nhẹ và hiệu quả
FROM python:3.10-slim

# Thiết lập biến môi trường để Python chạy ở chế độ không buffer, giúp log hiển thị ngay lập tức
ENV PYTHONUNBUFFERED=1

# Thiết lập thư mục làm việc bên trong container
WORKDIR /app

# Cài đặt các gói hệ thống cần thiết cho việc biên dịch một số thư viện Python
# --no-install-recommends giúp giảm kích thước image
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Sao chép file requirements.txt vào trước để tận dụng Docker layer caching.
# Docker sẽ chỉ chạy lại bước này nếu file requirements.txt thay đổi.
COPY backend/requirements.txt .

# Nâng cấp pip và cài đặt các thư viện Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ mã nguồn của dự án vào thư mục làm việc /app
# Điều này bao gồm main.py và thư mục src/
COPY . .

# Thêm thư mục /app vào PYTHONPATH.
# Đây là bước QUAN TRỌNG NHẤT để `main.py` có thể tìm thấy module `src`
# và thực hiện các import tuyệt đối như `from src.bot.trading_bot import TradingBot`
# mà không cần "hack" sys.path.
ENV PYTHONPATH=/app

# Lệnh để chạy ứng dụng của bạn khi container khởi động
# Railway sẽ tự động inject biến môi trường BOT_TOKEN bạn đã cấu hình
CMD ["python", "backend/main.py"]
