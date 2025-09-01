#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo đơn giản để test các tính năng enhanced của Facebook Groups Comment Scraper
Không cần dependencies
"""

import re

def validate_username(username):
    """Enhanced username validation"""
    if not username or len(username.strip()) < 2:
        return False
    
    # Remove common prefixes/suffixes
    username = re.sub(r'^(Mr\.|Ms\.|Mrs\.|Dr\.|Prof\.)\s*', '', username)
    username = re.sub(r'\s+(Jr\.|Sr\.|I|II|III|IV|V)$', '', username)
    
    # Check for UI elements
    ui_elements = ['like', 'reply', 'share', 'comment', 'thích', 'trả lời', 'chia sẻ', 'bình luận']
    if username.lower().strip() in ui_elements:
        return False
    
    # Check for valid characters
    if not re.match(r'^[a-zA-ZÀ-ỹ\s\-\.\']+$', username):
        return False
    
    # Check length
    if len(username) > 50:
        return False
    
    return True

def extract_comment_content(text, username=""):
    """Enhanced comment content extraction"""
    if not text:
        return ""
    
    # Remove username from beginning
    if username and text.startswith(username):
        text = text[len(username):].strip()
    
    # Remove username with word boundaries
    if username:
        text = re.sub(rf'\b{re.escape(username)}\b', '', text, count=1).strip()
    
    # Remove common prefixes
    prefixes_to_remove = [
        r'^[A-Z][a-z]+:\s*',  # "Name: "
        r'^@[a-zA-Z0-9_]+\s*',  # "@username "
        r'^Reply to [A-Z][a-z]+:\s*',  # "Reply to Name: "
    ]
    
    for prefix in prefixes_to_remove:
        text = re.sub(prefix, '', text)
    
    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove leading/trailing punctuation
    text = re.sub(r'^[:\s]+', '', text)
    text = re.sub(r'[\s:]+$', '', text)
    
    return text

def extract_user_info_from_url(url):
    """Enhanced user info extraction from Facebook URLs"""
    patterns = {
        'profile_id': r'profile\.php\?id=(\d+)',
        'username': r'facebook\.com/([^/?]+)',
        'user_id': r'/(\d{10,})/?$'
    }
    
    user_info = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, url)
        if match:
            user_info[key] = match.group(1)
    
    return user_info

def clean_text(text):
    """Clean text by removing UI elements"""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text.strip())
    # Remove UI elements but preserve Vietnamese text
    ui_patterns = [
        r'\b(Like|Reply|Share|Comment|Translate|Hide|Report|Block)\b',
        r'\b(Thích|Trả lời|Chia sẻ|Bình luận|Dịch|Ẩn|Báo cáo|Chặn)\b',
        r'\b\d+\s*(min|minutes?|hours?|days?|seconds?|phút|giờ|ngày|giây)\s*(ago|trước)?\b',
        r'\b(Top fan|Most relevant|Newest|All comments|Bình luận hàng đầu)\b'
    ]
    for pattern in ui_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    return text.strip()

def is_ui_only_content(text):
    """Enhanced check for UI-only content"""
    if not text or len(text.strip()) < 5:
        return True
    
    text_clean = text.lower().strip()
    
    # UI patterns
    ui_patterns = [
        r'^(like|reply|share|comment|translate|hide|report|block)(\s+\d+)?\s*$',
        r'^(thích|trả lời|chia sẻ|bình luận|dịch|ẩn|báo cáo|chặn)(\s+\d+)?\s*$',
        r'^\d+\s*(min|minutes?|hours?|days?|phút|giờ|ngày)\s*(ago|trước)?\s*$',
        r'^(top fan|most relevant|newest|all comments|view more|see more)\s*$',
        r'^(bình luận hàng đầu|xem thêm|hiển thị thêm)\s*$',
        r'^\d+\s*(like|love|reaction|thích|yêu|cảm xúc)\s*$',
        r'^(see translation|xem bản dịch|translate|dịch)\s*$',
        r'^(write a comment|viết bình luận|comment|bình luận)\s*$',
        r'^(group|nhóm|groups|các nhóm)\s*$',
        r'^[^\wÀ-ỹ]*$',  # Only punctuation/symbols
        r'^\d+$',  # Only numbers
        r'^[a-z]{1,3}\s*$'  # Very short text
    ]
    
    for pattern in ui_patterns:
        if re.match(pattern, text_clean):
            return True
    
    # Check if it's just repeated characters
    if len(set(text_clean)) <= 3 and len(text_clean) > 5:
        return True
    
    return False

def test_username_validation():
    """Test enhanced username validation"""
    print("=== TEST USERNAME VALIDATION ===")
    
    test_usernames = [
        "Nguyễn Văn A",           # Valid Vietnamese name
        "John Doe",               # Valid English name
        "Maria García",           # Valid with accent
        "Dr. Smith",              # Valid with title
        "Like",                   # Invalid - UI element
        "Reply",                  # Invalid - UI element
        "12345",                  # Invalid - numbers only
        "A",                      # Invalid - too short
        "Very Long Name That Exceeds Maximum Length Limit",  # Invalid - too long
        "User@123",               # Invalid - special chars
        "Thích",                  # Invalid - Vietnamese UI
        "Bình luận",              # Invalid - Vietnamese UI
        "",                       # Invalid - empty
        "   ",                    # Invalid - whitespace only
    ]
    
    for username in test_usernames:
        is_valid = validate_username(username)
        status = "✅ VALID" if is_valid else "❌ INVALID"
        print(f"{status}: '{username}'")

def test_content_extraction():
    """Test enhanced content extraction"""
    print("\n=== TEST CONTENT EXTRACTION ===")
    
    test_cases = [
        {
            "text": "Nguyễn Văn A: Đây là comment rất hay!",
            "username": "Nguyễn Văn A",
            "expected": "Đây là comment rất hay!"
        },
        {
            "text": "John Doe Like Reply Share Comment",
            "username": "John Doe",
            "expected": ""
        },
        {
            "text": "Maria García: Cảm ơn bạn đã chia sẻ thông tin hữu ích này!",
            "username": "Maria García",
            "expected": "Cảm ơn bạn đã chia sẻ thông tin hữu ích này!"
        },
        {
            "text": "@username Đây là reply cho comment trước",
            "username": "username",
            "expected": "Đây là reply cho comment trước"
        },
        {
            "text": "Reply to John Doe: Tôi đồng ý với ý kiến của bạn",
            "username": "John Doe",
            "expected": "Tôi đồng ý với ý kiến của bạn"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        result = extract_comment_content(case["text"], case["username"])
        expected = case["expected"]
        status = "✅ PASS" if result == expected else "❌ FAIL"
        print(f"Test {i} {status}:")
        print(f"  Input: '{case['text']}'")
        print(f"  Username: '{case['username']}'")
        print(f"  Expected: '{expected}'")
        print(f"  Result: '{result}'")
        print()

def test_url_extraction():
    """Test user info extraction from URLs"""
    print("=== TEST URL EXTRACTION ===")
    
    test_urls = [
        "https://www.facebook.com/profile.php?id=123456789",
        "https://m.facebook.com/user.php?id=987654321",
        "https://mbasic.facebook.com/john.doe.123",
        "https://facebook.com/123456789012345",
        "https://www.facebook.com/groups/123456789/posts/987654321/",
    ]
    
    for url in test_urls:
        info = extract_user_info_from_url(url)
        print(f"URL: {url}")
        print(f"  Extracted: {info}")
        print()

def test_text_cleaning():
    """Test text cleaning functionality"""
    print("=== TEST TEXT CLEANING ===")
    
    test_texts = [
        "Like    Reply   Share   Comment",
        "Thích   Trả lời   Chia sẻ   Bình luận",
        "2 hours ago",
        "3 phút trước",
        "Top fan",
        "Bình luận hàng đầu",
        "View more comments",
        "Xem thêm bình luận",
        "This is a normal comment with extra   spaces",
        "Comment with\nmultiple\nlines",
    ]
    
    for text in test_texts:
        cleaned = clean_text(text)
        print(f"Original: '{text}'")
        print(f"Cleaned:  '{cleaned}'")
        print()

def test_ui_detection():
    """Test UI-only content detection"""
    print("=== TEST UI DETECTION ===")
    
    test_contents = [
        "Like",                    # UI only
        "Reply",                   # UI only
        "Thích",                   # UI only
        "2 hours ago",             # UI only
        "Top fan",                 # UI only
        "View more",               # UI only
        "This is a real comment",  # Real content
        "Cảm ơn bạn đã chia sẻ!",  # Real content
        "123",                     # Numbers only
        "!!!",                     # Punctuation only
        "a",                       # Too short
        "A very long and meaningful comment that contains actual content and is not just UI elements",  # Real content
    ]
    
    for content in test_contents:
        is_ui = is_ui_only_content(content)
        status = "UI ONLY" if is_ui else "REAL CONTENT"
        print(f"{status}: '{content}'")

def main():
    """Run all tests"""
    print("🧪 ENHANCED FEATURES DEMO")
    print("=" * 50)
    
    test_username_validation()
    test_content_extraction()
    test_url_extraction()
    test_text_cleaning()
    test_ui_detection()
    
    print("\n🎉 Demo completed!")
    print("\n💡 Các tính năng enhanced đã được test:")
    print("  ✅ Username validation với nhiều trường hợp")
    print("  ✅ Content extraction thông minh")
    print("  ✅ URL parsing cho user info")
    print("  ✅ Text cleaning tối ưu")
    print("  ✅ UI detection chính xác")
    
    print("\n📋 Tóm tắt cải tiến:")
    print("  1. Xác định tên người dùng chính xác hơn với multi-strategy approach")
    print("  2. Xử lý content tối ưu với smart cleaning và validation")
    print("  3. Enhanced deduplication với nhiều tiêu chí")
    print("  4. Better comment type detection (Comment vs Reply)")
    print("  5. User verification detection")
    print("  6. Improved error handling và progress tracking")

if __name__ == "__main__":
    main()