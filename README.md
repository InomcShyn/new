# 🏘️ Enhanced Facebook Groups Comment Scraper

## ✨ Tính năng cải tiến

### 🔍 Xác định tên người dùng chính xác hơn
- **Multi-strategy approach**: Sử dụng nhiều phương pháp để tìm tên người dùng
- **Enhanced validation**: Kiểm tra tính hợp lệ của tên người dùng
- **Profile link extraction**: Trích xuất thông tin từ link profile
- **Display name detection**: Tìm tên hiển thị trong các element khác nhau
- **User mention parsing**: Xử lý các mention (@username) trong comment

### 📝 Xử lý content tối ưu
- **Smart content extraction**: Loại bỏ UI elements một cách thông minh
- **Multi-source content**: Lấy content từ nhiều nguồn khác nhau
- **Enhanced cleaning**: Làm sạch text với các pattern tối ưu
- **Content validation**: Kiểm tra tính hợp lệ của content
- **Duplicate detection**: Phát hiện và loại bỏ duplicate content

### 🎯 Cải tiến khác
- **Better comment type detection**: Phân biệt comment và reply chính xác hơn
- **Enhanced deduplication**: Loại bỏ duplicate với nhiều tiêu chí
- **User verification detection**: Phát hiện tài khoản verified
- **Layout optimization**: Tối ưu cho cả mobile và mbasic layout
- **Progress tracking**: Theo dõi tiến trình chi tiết hơn

## 🚀 Cài đặt

1. **Cài đặt Python dependencies:**
```bash
pip install -r requirements.txt
```

2. **Chạy ứng dụng:**
```bash
python fb_groups_comment_scraper_enhanced.py
```

## 📋 Hướng dẫn sử dụng

### 1. Chuẩn bị
- **Cookie Facebook**: Lấy cookie từ trình duyệt (F12 → Application → Cookies)
- **Link Groups**: Copy link bài viết trong Facebook Groups
- **Quyền truy cập**: Đảm bảo có quyền xem bài viết trong nhóm

### 2. Cấu hình
- **Enhanced extraction**: Bật để sử dụng tính năng nâng cao
- **Headless mode**: Tắt để debug (khuyến nghị)
- **UID extraction**: Bật để lấy ID người dùng
- **Limit**: Giới hạn số lượng comment (0 = tất cả)

### 3. Chạy scraping
- Nhập link bài viết Groups
- Paste cookie Facebook
- Chọn file output
- Nhấn "Bắt đầu Enhanced Scraping"

## 📊 Kết quả

### Các cột dữ liệu:
- **STT**: Số thứ tự
- **UID**: ID người dùng Facebook
- **Name**: Tên người dùng
- **DisplayName**: Tên hiển thị (nếu khác)
- **Content**: Nội dung comment
- **ProfileLink**: Link profile
- **Verified**: Tài khoản verified (True/False)
- **Type**: Loại (Comment/Reply)
- **Layout**: Layout được detect (mobile/mbasic)
- **ContentLength**: Độ dài content
- **Source**: Nguồn dữ liệu
- **ScrapedAt**: Thời gian scrape
- **EnhancedExtraction**: Sử dụng enhanced extraction

### Thống kê:
- Số lượng comments và replies
- Số người dùng unique
- Số tài khoản verified
- Độ dài trung bình comment
- Layout được sử dụng

## 🔧 Troubleshooting

### Không lấy được comment:
1. **Kiểm tra cookie**: Đảm bảo cookie còn valid
2. **Quyền truy cập**: Kiểm tra quyền xem bài viết trong nhóm
3. **Tắt headless**: Để debug và xem quá trình
4. **Xem debug file**: Kiểm tra file HTML được lưu

### Lỗi xác định tên người dùng:
1. **Enhanced extraction**: Đảm bảo đã bật
2. **Layout detection**: Kiểm tra layout được detect
3. **Profile links**: Xem có tìm thấy link profile không

### Performance:
1. **Limit comments**: Giới hạn số lượng nếu quá nhiều
2. **Headless mode**: Bật để tăng tốc
3. **Enhanced extraction**: Có thể chậm hơn nhưng chính xác hơn

## 🆚 So sánh với phiên bản cũ

| Tính năng | Phiên bản cũ | Enhanced |
|-----------|-------------|----------|
| User detection | Basic | Multi-strategy |
| Content extraction | Simple | Smart cleaning |
| Duplicate removal | Basic | Enhanced |
| Comment type | Basic | Advanced |
| Verification | Không | Có |
| Progress tracking | Basic | Detailed |
| Error handling | Basic | Comprehensive |

## 📝 Lưu ý

- **Cookie security**: Không chia sẻ cookie với người khác
- **Rate limiting**: Không scrape quá nhanh để tránh bị block
- **Terms of service**: Tuân thủ điều khoản sử dụng Facebook
- **Data privacy**: Chỉ sử dụng dữ liệu cho mục đích hợp pháp

## 🤝 Đóng góp

Nếu bạn muốn đóng góp cải tiến:
1. Fork repository
2. Tạo feature branch
3. Commit changes
4. Push và tạo Pull Request

## 📄 License

MIT License - Xem file LICENSE để biết chi tiết.