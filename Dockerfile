# Dùng Python base image
FROM python:3.11-slim

# Tạo thư mục app
WORKDIR /app

# Cài đặt các dependencies của hệ thống
RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements và cài đặt dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ project
COPY . .

# Thiết lập biến môi trường
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Thiết lập working directory
WORKDIR /app/backend

# Debug: Hiển thị cấu trúc thư mục
RUN echo "=== App structure ===" && \
    find /app -type f -name "*.py" | head -20

# Khai báo cổng
EXPOSE $PORT

# Khởi chạy bot
CMD ["python3", "main.py"]

