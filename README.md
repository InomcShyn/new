# 🏘️ Facebook Groups Comment Scraper

Scraper chuyên dụng cho Facebook Groups - **Chỉ lấy Main Comments** (không lấy replies)

## 🎯 **Mục đích**

Lấy thông tin từ Facebook Groups:
- **Tên người comment**
- **Link profile Facebook** 
- **Link comment**
- **UID người dùng**
- **Loại comment** (Main Comment/Reply)

**✨ Tính năng đặc biệt:** Tự động chọn "Tất cả bình luận" thay vì chỉ "Bình luận phù hợp nhất" để lấy được nhiều comment hơn!

## 📋 **Yêu cầu**

- Python 3.8+
- Chrome browser
- Facebook account với quyền truy cập Groups

## 🚀 **Cài đặt**

1. **Clone repository:**
```bash
git clone <repository-url>
cd fb-groups-scraper
```

2. **Cài đặt dependencies:**
```bash
pip install -r requirements.txt
```

3. **Chạy scraper:**
```bash
python fb_groups_comment_scraper.py
```

## 🍪 **Lấy Cookie Facebook**

1. Đăng nhập Facebook trên Chrome
2. Mở Developer Tools (F12)
3. Vào tab **Application** → **Cookies** → **https://www.facebook.com**
4. Copy tất cả cookies (Ctrl+A, Ctrl+C)
5. Paste vào ô "Cookie Facebook" trong scraper

## 📝 **Cách sử dụng**

1. **Nhập link bài viết Groups** (phải có "groups/" trong URL)
2. **Paste cookie Facebook** vào ô tương ứng
3. **Chọn file output** (.xlsx hoặc .csv)
4. **Nhấn "Bắt đầu lấy Groups Comments"**
5. **Chờ scraper hoàn thành**

## ⚙️ **Tùy chọn**

- **Số lượng comment**: 0 = tất cả, >0 = giới hạn số lượng
- **Chạy ẩn**: Tắt/bật hiển thị browser
- **Lấy UID**: Bật/tắt việc extract User ID

## 📊 **Output**

File Excel/CSV sẽ có các cột:
- **STT**: Số thứ tự
- **UID**: Facebook User ID
- **Name**: Tên người comment
- **ProfileLink**: Link profile Facebook
- **CommentLink**: Link trực tiếp đến comment
- **Type**: Loại (Comment/Reply)
- **Layout**: Layout được detect (mobile/mbasic)
- **ElementIndex**: Vị trí element
- **Source**: Nguồn (Facebook Groups)
- **ScrapedAt**: Thời gian scrape

## 🔍 **Tính năng**

- **Auto-detect layout**: Mobile/MBasic Facebook
- **Smart expansion**: Tự động click "View more comments"
- **Deduplication**: Loại bỏ comment trùng lặp
- **Reply filtering**: Chỉ lấy main comments
- **Debug mode**: Lưu HTML để debug
- **Progress tracking**: Hiển thị tiến trình real-time
- **🎯 Auto "All Comments"**: Tự động chọn "Tất cả bình luận" để lấy nhiều comment hơn
- **🚀 Initial expansion**: Tự động click các nút expand ban đầu

## ⚠️ **Lưu ý**

- **Cookie phải valid** và có quyền truy cập Groups
- **Bài viết phải public** trong Groups
- **Tài khoản không bị khóa** hoặc hạn chế
- **Chrome browser** phải được cài đặt
- **Internet ổn định** để load Groups

## 🐛 **Troubleshooting**

- **Không tìm thấy comment**: Kiểm tra quyền truy cập Groups
- **Lỗi login**: Kiểm tra cookie có đúng không
- **Browser crash**: Tắt headless mode để debug
- **Slow performance**: Giảm số lượng comment limit

## 📱 **Hỗ trợ**

- **Layout**: Mobile Facebook Groups
- **Groups**: Tất cả Facebook Groups
- **Languages**: Tiếng Việt + English
- **Browsers**: Chrome (recommended)

## 🔒 **Bảo mật**

- Cookie được lưu local, không gửi đi đâu
- Không lưu nội dung comment
- Chỉ lấy thông tin công khai
- Tuân thủ Facebook ToS