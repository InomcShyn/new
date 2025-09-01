#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script để kiểm tra việc phân tách tên Facebook và link profile
"""

import re

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

def validate_username(username):
    """Enhanced username validation"""
    if not username or len(username.strip()) < 2:
        return False
    
    # Remove common prefixes/suffixes
    username = re.sub(r'^(Mr\.|Ms\.|Mrs\.|Dr\.|Prof\.)\s*', '', username)
    username = re.sub(r'\s+(Jr\.|Sr\.|I|II|III|IV|V)$', '', username)
    
    # Check for UI elements
    ui_elements = ['like', 'reply', 'share', 'comment', 'thích', 'trả lời', 'chia sẻ', 'bình luận', 'groups', 'nhóm']
    if username.lower().strip() in ui_elements:
        return False
    
    # Check for valid characters
    if not re.match(r'^[a-zA-ZÀ-ỹ\s\-\.\']+$', username):
        return False
    
    # Check length
    if len(username) > 50:
        return False
    
    return True

def test_url_extraction():
    """Test URL extraction functionality"""
    print("=== TEST URL EXTRACTION ===")
    
    test_urls = [
        "https://www.facebook.com/profile.php?id=123456789",
        "https://m.facebook.com/user.php?id=987654321",
        "https://mbasic.facebook.com/john.doe.123",
        "https://facebook.com/123456789012345",
        "https://www.facebook.com/groups/123456789/posts/987654321/",
        "https://m.facebook.com/nguyen.van.a",
        "https://www.facebook.com/maria.garcia.123",
    ]
    
    for url in test_urls:
        info = extract_user_info_from_url(url)
        print(f"URL: {url}")
        print(f"  Extracted: {info}")
        print()

def test_username_validation():
    """Test username validation"""
    print("=== TEST USERNAME VALIDATION ===")
    
    test_usernames = [
        "Nguyễn Văn A",
        "John Doe",
        "Maria García",
        "Thuy Huong Le",
        "Like",
        "Reply",
        "Thích",
        "Bình luận",
        "Groups",
        "Nhóm",
        "12345",
        "A",
        "User@123",
        "Người tham gia danh 967",
        "Linh Đỗ",
        "Lan Nguyen"
    ]
    
    for username in test_usernames:
        is_valid = validate_username(username)
        status = "✅ VALID" if is_valid else "❌ INVALID"
        print(f"{status}: '{username}'")

def test_comment_parsing():
    """Test comment parsing with different formats"""
    print("\n=== TEST COMMENT PARSING ===")
    
    test_comments = [
        {
            "raw_text": "Nguyễn Văn A: Đây là comment rất hay!",
            "expected_name": "Nguyễn Văn A",
            "expected_content": "Đây là comment rất hay!"
        },
        {
            "raw_text": "Thuy Huong Le https://www.facebook.com/1FLeThhH...",
            "expected_name": "Thuy Huong Le",
            "expected_content": "https://www.facebook.com/1FLeThhH..."
        },
        {
            "raw_text": "Linh Đỗ không bạn ạ. Cái loại lấy tiền ủng hộ cho ...",
            "expected_name": "Linh Đỗ",
            "expected_content": "không bạn ạ. Cái loại lấy tiền ủng hộ cho ..."
        },
        {
            "raw_text": "Lan Nguyen chính hắn đấy bạn ơi. Con bệnh tật, con...",
            "expected_name": "Lan Nguyen",
            "expected_content": "chính hắn đấy bạn ơi. Con bệnh tật, con..."
        },
        {
            "raw_text": "Cảm động quá và cũng thấy tự hào ❤️❤️❤️",
            "expected_name": "Unknown",
            "expected_content": "Cảm động quá và cũng thấy tự hào ❤️❤️❤️"
        }
    ]
    
    for i, test_case in enumerate(test_comments, 1):
        print(f"\nTest {i}:")
        print(f"  Raw text: '{test_case['raw_text']}'")
        
        # Extract username from content
        username = extract_username_from_content(test_case['raw_text'])
        content = remove_username_from_content(test_case['raw_text'], username) if username else test_case['raw_text']
        
        print(f"  Extracted name: '{username}'")
        print(f"  Extracted content: '{content}'")
        print(f"  Expected name: '{test_case['expected_name']}'")
        print(f"  Expected content: '{test_case['expected_content']}'")
        
        name_match = username == test_case['expected_name']
        content_match = content == test_case['expected_content']
        
        print(f"  Name match: {'✅' if name_match else '❌'}")
        print(f"  Content match: {'✅' if content_match else '❌'}")

def extract_username_from_content(content):
    """Extract username from content using various patterns"""
    if not content:
        return None
    
    # Patterns to extract username from content - Reordered for better matching
    patterns = [
        (r'^([A-Z][a-zA-ZÀ-ỹ\s]+)\s+(https?://)', 'Name with URL'),  # Must come before Name: content
        (r'^([A-Z][a-zA-ZÀ-ỹ\s]+):\s*(.+)', 'Name: content'),
        (r'^@([a-zA-Z0-9_À-ỹ]+)\s+(.+)', '@username content'),
        (r'^([A-Z][a-zA-ZÀ-ỹ\s]+)\s+[0-9]+\s+(.+)', 'Name 123 content'),
        (r'^([A-Z][a-zA-ZÀ-ỹ\s]+)\s+[0-9]+$', 'Name 123'),
        (r'^([A-Z][a-zA-ZÀ-ỹ\s]+)\s*$', 'Name only'),
        # Additional patterns for Vietnamese names without colon - More specific
        (r'^([A-Z][a-zA-ZÀ-ỹ\s]+)\s+(không|chính|bạn|em|cô|chú|anh|chị)\s+(.+)', 'Name with Vietnamese words'),
    ]
    
    for pattern, description in patterns:
        match = re.match(pattern, content)
        if match:
            potential_name = match.group(1).strip()
            print(f"    DEBUG: Pattern '{description}' matched: '{potential_name}'")
            if validate_username(potential_name):
                print(f"    DEBUG: Valid username found: '{potential_name}'")
                return potential_name
            else:
                print(f"    DEBUG: Invalid username: '{potential_name}'")
    
    return None

def remove_username_from_content(content, username):
    """Remove username from content"""
    if not content or not username:
        return content
    
    # Remove username from beginning
    if content.startswith(username):
        content = content[len(username):].strip()
    
    # Remove username with word boundaries
    content = re.sub(rf'\b{re.escape(username)}\b', '', content, count=1).strip()
    
    # Remove leading/trailing punctuation
    content = re.sub(r'^[:\s]+', '', content)
    content = re.sub(r'[\s:]+$', '', content)
    
    return content

def main():
    """Run all tests"""
    print("🧪 TESTING USER EXTRACTION")
    print("=" * 50)
    
    test_url_extraction()
    test_username_validation()
    test_comment_parsing()
    
    print("\n🎉 Testing completed!")
    print("\n💡 Các tính năng đã được test:")
    print("  ✅ URL extraction từ Facebook links")
    print("  ✅ Username validation")
    print("  ✅ Comment parsing với tên tiếng Việt")
    print("  ✅ Content separation")

if __name__ == "__main__":
    main()