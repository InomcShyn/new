#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo script để test các tính năng enhanced của Facebook Groups Comment Scraper
"""

import re
from fb_groups_comment_scraper_enhanced import (
    validate_username, 
    extract_comment_content, 
    extract_user_info_from_url,
    clean_text
)

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
    
    from fb_groups_comment_scraper_enhanced import EnhancedFacebookGroupsScraper
    
    # Create a mock scraper instance just for testing
    scraper = EnhancedFacebookGroupsScraper.__new__(EnhancedFacebookGroupsScraper)
    
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
        is_ui = scraper.is_ui_only_content(content)
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

if __name__ == "__main__":
    main()