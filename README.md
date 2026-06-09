# AI Image Studio

Ứng dụng desktop cá nhân dùng PySide6 để mở rộng prompt bằng `gpt-5.1`, tạo ảnh
và chỉnh sửa ảnh nguồn bằng các model ảnh được cấu hình.

## Chế độ

- **Direct Prompt**: gửi prompt trực tiếp để tạo ảnh.
- **AI Prompt Generator**: mở rộng mô tả ngắn rồi tạo ảnh.
- **Chỉnh/Ghép ảnh**: chọn một ảnh PNG, JPEG hoặc WebP, nhập yêu cầu chỉnh sửa,
  sau đó xem và lưu kết quả như ảnh tạo mới.

## Chạy ứng dụng

```powershell
python -m pip install -r requirements.txt
python main.py
```

Python 3.12 trở lên được khuyến nghị.

## Cấu hình API

Nhập API key trong giao diện và bấm **Lưu**, hoặc sửa `.env`:

```env
API_KEY=your_key
API_BASE_URL=https://api.openai.com/v1
IMAGE_API_BASE_URL=
PROMPT_ENDPOINT=/responses
IMAGE_ENDPOINT=/images/generations
IMAGE_EDIT_ENDPOINT=/images/edits
IMAGE_MODELS=gpt-image-2,gpt-image-1.5,gpt-image-1-mini
```

Có thể sao chép cấu trúc từ `.env.example`. File `.env` đã được loại khỏi Git để
tránh commit nhầm API key.

Với nhà cung cấp tương thích khác, thay `API_BASE_URL`, `PROMPT_ENDPOINT` và
`IMAGE_ENDPOINT`/`IMAGE_EDIT_ENDPOINT`. `PROMPT_ENDPOINT` hỗ trợ cả `/responses` và
`/chat/completions`; ứng dụng tự chọn payload phù hợp. Có thể dùng thêm:

```env
API_AUTH_HEADER=Authorization
API_AUTH_PREFIX=Bearer
API_TIMEOUT_SECONDS=180
API_MAX_RETRIES=2
API_RETRY_BACKOFF_SECONDS=2
```

`IMAGE_API_BASE_URL` cho phép dùng base URL riêng cho các tác vụ tạo/chỉnh ảnh.
Với ShopAIKey nên đặt `https://direct.shopaikey.com/v1` để dùng endpoint Direct.
Tác vụ ảnh không được tự động retry vì timeout không chứng minh tác vụ phía server
đã thất bại; gửi lại có thể tạo tác vụ trùng và phát sinh thêm chi phí.

Client tự kiểm tra status code, header, content type và có thể đọc ảnh từ binary,
URL, base64, data URL, JSON lồng nhau hoặc danh sách ảnh.
Các lỗi tạm thời `429`, `502`, `503`, `504` được tự động thử lại với thời gian chờ
tăng dần; header `Retry-After` của nhà cung cấp được ưu tiên nếu có.

## Dữ liệu cục bộ

- `history.json`: lịch sử các ảnh đã lưu.
- `settings.json`: thư mục lưu gần nhất và tùy chọn giao diện.
- `temp/`: ảnh tạm, tự dọn theo tuổi và giới hạn số tệp.
- `logs/app.log`: request, response rút gọn, thời gian và lỗi. API key được che.

## Kiểm thử

```powershell
$env:QT_QPA_PLATFORM="offscreen"
python -m unittest discover -v
```
