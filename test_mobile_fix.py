#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for Facebook Groups Comment Scraper - Mobile Facebook Fix
"""

import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fb_groups_comment_scraper import FacebookGroupsScraper

def test_mobile_fix():
    """Test the scraper with mobile Facebook fix"""
    
    print("🧪 Testing Facebook Groups Comment Scraper - Mobile Facebook Fix")
    print("=" * 70)
    
    # Test URL (replace with your actual Groups post URL)
    test_url = "https://www.facebook.com/groups/zui.vn/posts/24265734123027065"
    
    # Cookie string (you need to provide this)
    cookie_str = input("Paste your Facebook cookie string: ").strip()
    
    if not cookie_str:
        print("❌ No cookie provided. Exiting.")
        return
    
    print("\n🚀 Starting test with mobile Facebook fix...")
    
    try:
        # Initialize scraper (headless=False for debugging)
        print("🌐 Initializing scraper...")
        scraper = FacebookGroupsScraper(cookie_str, headless=False)
        
        # Load post (this will automatically try to switch to "All comments")
        print(f"📄 Loading post: {test_url}")
        success = scraper.load_post(test_url)
        
        if not success:
            print("❌ Failed to load post")
            return
        
        print("✅ Post loaded successfully!")
        print("🔄 The scraper should have automatically switched to 'All comments' view")
        
        # Wait a bit for comments to load
        print("⏳ Waiting for comments to load...")
        import time
        time.sleep(5)
        
        # Extract comments
        print("\n🔍 Extracting comments from mobile Facebook...")
        comments = scraper.extract_groups_comments()
        
        print(f"\n📊 Results: {len(comments)} comments found")
        
        if comments:
            # Display results
            print("\n" + "="*50)
            print("📋 EXTRACTED COMMENTS:")
            print("="*50)
            
            for i, comment in enumerate(comments[:10]):  # Show first 10
                print(f"\n--- Comment {i+1} ---")
                print(f"Name: {comment['Name']}")
                print(f"UID: {comment['UID']}")
                print(f"Profile: {comment['ProfileLink']}")
                print(f"Comment Link: {comment['CommentLink']}")
                print(f"Type: {comment['Type']}")
                print(f"Layout: {comment['Layout']}")
            
            if len(comments) > 10:
                print(f"\n... and {len(comments) - 10} more comments")
            
            # Statistics
            main_count = len([c for c in comments if c['Type'] == 'Comment'])
            reply_count = len([c for c in comments if c['Type'] == 'Reply'])
            unique_users = len(set(c['Name'] for c in comments if c['Name'] != 'Unknown'))
            profile_links = len([c for c in comments if c['ProfileLink']])
            comment_links = len([c for c in comments if c['CommentLink']])
            uid_count = len([c for c in comments if c['UID'] != 'Unknown'])
            
            print(f"\n📈 STATISTICS:")
            print(f"Main Comments: {main_count}")
            print(f"Replies: {reply_count}")
            print(f"Unique Users: {unique_users}")
            print(f"Profile Links: {profile_links}")
            print(f"Comment Links: {comment_links}")
            print(f"UIDs Found: {uid_count}")
            
        else:
            print("⚠️ No comments found. This might indicate:")
            print("   - The post doesn't have comments")
            print("   - Access permission issues")
            print("   - The mobile selectors need further adjustment")
            print("   - Check the debug HTML file for more details")
            
            # Try to analyze the page structure
            print("\n🔍 Analyzing page structure...")
            try:
                page_source = scraper.driver.page_source
                
                # Look for specific patterns from your div example
                if 'class="m"' in page_source:
                    print("✅ Found 'class=\"m\"' elements in page")
                else:
                    print("❌ No 'class=\"m\"' elements found")
                    
                if 'class="f20"' in page_source:
                    print("✅ Found 'class=\"f20\"' elements in page")
                else:
                    print("❌ No 'class=\"f20\"' elements found")
                    
                if 'data-action-id' in page_source:
                    print("✅ Found 'data-action-id' elements in page")
                else:
                    print("❌ No 'data-action-id' elements found")
                    
                if 'Đăng Trung' in page_source:
                    print("✅ Found 'Đăng Trung' text in page")
                else:
                    print("❌ No 'Đăng Trung' text found")
                    
            except Exception as e:
                print(f"⚠️ Error analyzing page structure: {e}")
        
        # Clean up
        scraper.close()
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_mobile_fix()