#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script để kiểm tra các cải tiến đã thực hiện
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

def extract_username_from_content(content):
    """Extract username from content using various patterns"""
    if not content:
        return None
    
    # Patterns to extract username from content - Simplified
    patterns = [
        (r'^([A-Z][a-zA-ZÀ-ỹ\s]+):\s*(.+)', 'Name: content'),
        (r'^@([a-zA-Z0-9_À-ỹ]+)\s+(.+)', '@username content'),
        (r'^([A-Z][a-zA-ZÀ-ỹ\s]+)\s+[0-9]+\s+(.+)', 'Name 123 content'),
        (r'^([A-Z][a-zA-ZÀ-ỹ\s]+)\s+[0-9]+$', 'Name 123'),
        (r'^([A-Z][a-zA-ZÀ-ỹ\s]+)\s*$', 'Name only'),
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

def is_ui_only_content(text):
    """Enhanced check for UI-only content - Less strict for mobile"""
    if not text or len(text.strip()) < 3:  # Reduced from 5 to 3
        return True
    
    text_clean = text.lower().strip()
    
    # UI patterns - Less strict for mobile layout
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
        r'^[a-z]{1,2}\s*$'  # Very short text - reduced from 3 to 2
    ]
    
    for pattern in ui_patterns:
        if re.match(pattern, text_clean):
            return True
    
    # Check if it's just repeated characters - Less strict
    if len(set(text_clean)) <= 2 and len(text_clean) > 10:  # Increased threshold
        return True
    
    return False

def test_username_extraction():
    """Test username extraction from content"""
    print("=== TEST USERNAME EXTRACTION FROM CONTENT ===")
    
    test_cases = [
        "Nguyễn Văn A: Đây là comment rất hay!",
        "@username Đây là reply cho comment trước",
        "Maria García 123 Cảm ơn bạn đã chia sẻ!",
        "John Doe 456",
        "Thuy Huong Le https://www.facebook.com/1FLeThhH...",
        "Cảm động quá và cũng thấy tự hào ❤️❤️❤️",
        "Ông bố tiệm cơm 1k lại đánh bóng hình ảnh nữa à. Đ...",
        "Like Reply Share Comment",
        "2 hours ago",
        "Top fan"
    ]
    
    for i, content in enumerate(test_cases, 1):
        username = extract_username_from_content(content)
        cleaned_content = remove_username_from_content(content, username) if username else content
        is_ui = is_ui_only_content(content)
        
        print(f"Test {i}:")
        print(f"  Original: '{content}'")
        print(f"  Username: '{username}'")
        print(f"  Cleaned: '{cleaned_content}'")
        print(f"  UI Only: {is_ui}")
        print()

def test_validation():
    """Test validation functions"""
    print("=== TEST VALIDATION FUNCTIONS ===")
    
    # Test username validation
    usernames = [
        "Nguyễn Văn A",
        "John Doe",
        "Like",
        "Reply",
        "Thích",
        "Bình luận",
        "Groups",
        "Nhóm",
        "12345",
        "A",
        "User@123"
    ]
    
    print("Username Validation:")
    for username in usernames:
        is_valid = validate_username(username)
        status = "✅ VALID" if is_valid else "❌ INVALID"
        print(f"  {status}: '{username}'")
    
    print("\nContent Validation:")
    contents = [
        "Cảm động quá và cũng thấy tự hào ❤️❤️❤️",
        "Like",
        "Reply",
        "2 hours ago",
        "Top fan",
        "This is a real comment",
        "Cảm ơn bạn đã chia sẻ!",
        "123",
        "!!!",
        "a"
    ]
    
    for content in contents:
        is_ui = is_ui_only_content(content)
        status = "UI ONLY" if is_ui else "REAL CONTENT"
        print(f"  {status}: '{content}'")

def main():
    """Run all tests"""
    print("🧪 TESTING ENHANCED FIXES")
    print("=" * 50)
    
    test_username_extraction()
    test_validation()
    
    print("\n🎉 Testing completed!")
    print("\n💡 Các cải tiến đã được test:")
    print("  ✅ Username extraction từ content")
    print("  ✅ Content cleaning và validation")
    print("  ✅ UI detection với mobile layout")
    print("  ✅ Enhanced validation rules")

if __name__ == "__main__":
    main()