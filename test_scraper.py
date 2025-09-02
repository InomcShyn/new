#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for Facebook Groups Comment Scraper
"""

import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fb_groups_comment_scraper import FacebookGroupsScraper

def test_scraper():
    """Test the scraper with a sample URL"""
    
    # Test URL (replace with your actual Groups post URL)
    test_url = "https://www.facebook.com/groups/zui.vn/posts/24265734123027065"
    
    # Cookie string (you need to provide this)
    cookie_str = input("Paste your Facebook cookie string: ").strip()
    
    if not cookie_str:
        print("❌ No cookie provided. Exiting.")
        return
    
    print("🚀 Starting test...")
    
    try:
        # Initialize scraper
        scraper = FacebookGroupsScraper(cookie_str, headless=False)  # Set to False for debugging
        
        # Load post
        print(f"📄 Loading post: {test_url}")
        success = scraper.load_post(test_url)
        
        if not success:
            print("❌ Failed to load post")
            return
        
        # Extract comments
        print("🔍 Extracting comments...")
        comments = scraper.extract_groups_comments()
        
        print(f"\n📊 Results: {len(comments)} comments found")
        
        # Display results
        for i, comment in enumerate(comments[:5]):  # Show first 5
            print(f"\n--- Comment {i+1} ---")
            print(f"Name: {comment['Name']}")
            print(f"UID: {comment['UID']}")
            print(f"Profile: {comment['ProfileLink']}")
            print(f"Comment Link: {comment['CommentLink']}")
            print(f"Type: {comment['Type']}")
        
        # Clean up
        scraper.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_scraper()