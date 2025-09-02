# fb_groups_comment_scraper.py - Specialized for Facebook Groups
import time, random, threading, re, requests, pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ----------------------------
# Helper utils
# ----------------------------
def parse_cookies_to_list(cookie_str):
    cookies_list = []
    for pair in cookie_str.split(';'):
        pair = pair.strip()
        if '=' in pair:
            name, value = pair.split('=', 1)
            cookies_list.append({'name': name.strip(), 'value': value.strip(), 'domain': '.facebook.com'})
    return cookies_list

def parse_cookies_to_dict(cookie_str):
    d = {}
    for pair in cookie_str.split(';'):
        pair = pair.strip()
        if '=' in pair:
            name, value = pair.split('=', 1)
            d[name.strip()] = value.strip()
    return d

def clean_text(text):
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

# ----------------------------
# Facebook Groups Specialized Scraper
# ----------------------------
class FacebookGroupsScraper:
    def __init__(self, cookie_str, headless=True):
        options = Options()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        # User agent that works well with Facebook groups
        options.add_argument("user-agent=Mozilla/5.0 (Android 10; Mobile; rv:109.0) Gecko/111.0 Firefox/109.0")
        options.add_argument("window-size=414,896")
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        self.wait = WebDriverWait(self.driver, 15)
        self.cookie_str = cookie_str or ""
        self.cookies_list = parse_cookies_to_list(self.cookie_str)
        self.cookies_dict = parse_cookies_to_dict(self.cookie_str)
        self._stop_flag = False
        self.current_layout = None
        
        if self.cookies_list:
            self._login_with_cookies()

    def _login_with_cookies(self):
        # Start with mobile Facebook for groups
        self.driver.get("https://m.facebook.com")
        time.sleep(3)
        
        for c in self.cookies_list:
            cookie = c.copy()
            cookie.pop('sameSite', None)
            cookie.pop('httpOnly', None) 
            cookie.pop('secure', None)
            cookie.setdefault('domain', '.facebook.com')
            try:
                self.driver.add_cookie(cookie)
            except: 
                pass
        
        self.driver.get("https://m.facebook.com")
        time.sleep(4)

    def load_post(self, post_url):
        print(f"Loading groups post: {post_url}")
        
        # For groups, try both mobile and mbasic
        urls_to_try = []
        
        if "groups/" in post_url:
            # Create both mobile and mbasic versions
            mobile_url = post_url.replace("mbasic.facebook.com", "m.facebook.com").replace("www.facebook.com", "m.facebook.com")
            mbasic_url = post_url.replace("m.facebook.com", "mbasic.facebook.com").replace("www.facebook.com", "mbasic.facebook.com")
            
            urls_to_try = [mobile_url, mbasic_url]
        else:
            urls_to_try = [post_url]
        
        for url_attempt in urls_to_try:
            try:
                print(f"Trying URL: {url_attempt}")
                self.driver.get(url_attempt)
                time.sleep(6)
                
                current_url = self.driver.current_url
                page_title = self.driver.title
                
                print(f"Current URL: {current_url}")
                print(f"Page title: {page_title}")
                
                # Detect layout
                if "m.facebook.com" in current_url:
                    self.current_layout = "mobile"
                elif "mbasic.facebook.com" in current_url:
                    self.current_layout = "mbasic"
                else:
                    self.current_layout = "www"
                
                print(f"Detected layout: {self.current_layout}")
                
                # Check login status
                if any(keyword in page_title.lower() for keyword in ["log in", "login", "đăng nhập"]):
                    print("❌ Not logged in with this URL, trying next...")
                    continue
                
                # Check if we can see group content
                group_indicators = self.driver.find_elements(By.XPATH, 
                    "//div[contains(text(),'group') or contains(text(),'nhóm') or contains(text(),'Group')]")
                
                if group_indicators or "groups/" in current_url:
                    print(f"✅ Successfully loaded groups post with {self.current_layout} layout")
                    
                    # Try to switch to "Tất cả bình luận" (All comments) view
                    self._switch_to_all_comments()
                    
                    return True
                else:
                    print("⚠️ No group indicators found, but proceeding...")
                    return True
                    
            except Exception as e:
                print(f"Failed to load {url_attempt}: {e}")
                continue
        
        print("❌ Failed to load post with any URL variant")
        return False

    def _switch_to_all_comments(self):
        """Switch to 'All comments' view to get more comments"""
        print("🔄 Attempting to switch to 'All comments' view...")
        
        try:
            # Wait a bit for page to fully load
            time.sleep(3)
            
            # Try to find and click "Tất cả bình luận" or "All comments" button
            all_comments_selectors = [
                # Vietnamese selectors
                "//a[contains(text(),'Tất cả bình luận')]",
                "//span[contains(text(),'Tất cả bình luận')]",
                "//div[contains(text(),'Tất cả bình luận')]",
                "//button[contains(text(),'Tất cả bình luận')]",
                
                # English selectors
                "//a[contains(text(),'All comments')]",
                "//span[contains(text(),'All comments')]",
                "//div[contains(text(),'All comments')]",
                "//button[contains(text(),'All comments')]",
                
                # Mobile specific selectors
                "//div[@role='button' and contains(text(),'Tất cả bình luận')]",
                "//div[@role='button' and contains(text(),'All comments')]",
                "//div[@data-sigil='comment-sort']//a[contains(text(),'Tất cả')]",
                "//div[@data-sigil='comment-sort']//a[contains(text(),'All')]",
                
                # Alternative selectors for comment sorting
                "//a[contains(@href,'sort') and contains(text(),'Tất cả')]",
                "//a[contains(@href,'sort') and contains(text(),'All')]",
                "//a[contains(@href,'comments') and contains(text(),'Tất cả')]",
                "//a[contains(@href,'comments') and contains(text(),'All')]"
            ]
            
            clicked = False
            for selector in all_comments_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            print(f"  Found 'All comments' button: {element.text}")
                            
                            # Scroll into view
                            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                            time.sleep(1)
                            
                            # Try to click
                            try:
                                element.click()
                                clicked = True
                                print("  ✅ Successfully clicked 'All comments' button")
                                time.sleep(3)  # Wait for comments to load
                                break
                            except:
                                # Try JavaScript click
                                try:
                                    self.driver.execute_script("arguments[0].click();", element)
                                    clicked = True
                                    print("  ✅ Successfully clicked 'All comments' button (JS)")
                                    time.sleep(3)
                                    break
                                except:
                                    continue
                    
                    if clicked:
                        break
                        
                except Exception as e:
                    continue
            
            if not clicked:
                print("  ⚠️ Could not find or click 'All comments' button, proceeding with current view")
            else:
                print("  🎯 Switched to 'All comments' view successfully")
                
        except Exception as e:
            print(f"  ⚠️ Error switching to 'All comments' view: {e}")
            print("  Proceeding with current view...")

    def get_groups_selectors(self):
        """Get selectors optimized for Facebook Groups"""
        if self.current_layout == "mobile":
            return {
                'expand_links': [
                    # Mobile groups expand links
                    "//a[contains(text(),'View more comments')]",
                    "//a[contains(text(),'View previous comments')]",
                    "//a[contains(text(),'View more replies')]",
                    "//a[contains(text(),'Show more')]",
                    "//a[contains(text(),'See more')]",
                    "//a[contains(text(),'Xem thêm')]",
                    "//a[contains(text(),'Hiển thị thêm')]",
                    "//div[@role='button' and (contains(text(),'more') or contains(text(),'thêm'))]",
                    "//span[contains(text(),'View') and contains(text(),'more')]/ancestor::*[@role='button' or self::a][1]",
                    "//div[@data-sigil='more' or @data-sigil='expand']",
                    "//*[contains(@data-sigil,'comment')]//*[contains(text(),'more') or contains(text(),'thêm')]",
                    # More generic mobile expand selectors
                    "//div[@role='button' and (contains(.,'more') or contains(.,'thêm') or contains(.,'bình luận') or contains(.,'comments'))]",
                    "//*[contains(text(),'more') or contains(text(),'thêm') or contains(text(),'bình luận') or contains(text(),'comments')]/ancestor::*[@role='button' or self::a][1]"
                ],
                'comment_containers': [
                    # Mobile groups comment containers - more targeted
                    "//div[@data-sigil='comment']",
                    "//div[@data-sigil='comment-body']", 
                    "//div[contains(@data-ft, 'comment')]",
                    "//div[contains(@id, 'comment_')]",
                    "//article//div[.//a[contains(@href, 'profile.php')]]",
                    "//div[@role='article']//div[.//a[contains(@href, 'profile.php')]]",
                    "//div[contains(@class, 'story_body_container')]//div[.//a[contains(@href, 'profile.php')]]",
                    "//div[.//strong/a[contains(@href, 'profile.php')]]",
                    "//div[.//h3/a[contains(@href, 'profile.php')]]",
                    "//div[.//span/a[contains(@href, 'profile.php')]]",
                    
                    # New mobile selectors based on current Facebook structure
                    "//div[contains(@class, 'm') and .//span[contains(@class, 'f20')]]",  # Based on your div example
                    "//div[contains(@class, 'm') and .//div[contains(@class, 'native-text')]]",
                    "//div[@data-action-id and .//span[contains(@class, 'f20')]]",
                    "//div[@data-type='text' and .//span[contains(@class, 'f20')]]",
                    
                    # Broader selectors for groups
                    "//div[.//a[contains(@href, 'facebook.com/')] and string-length(normalize-space(text())) > 25]",
                    "//div[string-length(normalize-space(text())) > 40 and .//a[contains(@href, 'profile')]]",
                    
                    # Very broad mobile selectors
                    "//div[contains(@class, 'm') and string-length(normalize-space(text())) > 20]",
                    "//div[@data-action-id and string-length(normalize-space(text())) > 15]",
                    
                    # NEW: More specific selectors based on user feedback
                    "//div[.//a[contains(@href, 'facebook.com/') and string-length(normalize-space(text())) > 2] and string-length(normalize-space(text())) > 30]",
                    "//div[.//span[contains(@class, 'f20')] and string-length(normalize-space(text())) > 20]",
                    "//div[@data-action-id and .//a[contains(@href, 'facebook.com/')] and string-length(normalize-space(text())) > 25]",
                    "//div[contains(@class, 'm') and .//a[contains(@href, 'facebook.com/')] and string-length(normalize-space(text())) > 30]",
                    
                    # Emergency fallback - look for any div with Facebook links and substantial text
                    "//div[.//a[contains(@href, 'facebook.com/')] and string-length(normalize-space(text())) > 35]",
                    "//div[string-length(normalize-space(text())) > 50 and .//a[contains(@href, 'facebook.com/')]]"
                ]
            }
        else:
            # mbasic layout
            return {
                'expand_links': [
                    "//a[contains(text(),'View more comments')]",
                    "//a[contains(text(),'View previous comments')]",
                    "//a[contains(text(),'View more replies')]", 
                    "//a[contains(text(),'Show more')]",
                    "//a[contains(text(),'See more')]",
                    "//a[contains(text(),'Xem thêm')]",
                    "//a[contains(@href,'comment') and contains(text(),'more')]",
                    "//a[contains(@href,'reply') and contains(text(),'more')]"
                ],
                'comment_containers': [
                    "//div[@data-ft and contains(@data-ft, 'comment')]",
                    "//div[contains(@id, 'comment_')]",
                    "//table//div[.//a[contains(@href, 'profile.php')]]",
                    "//div[.//a[contains(@href, 'profile.php?id=')]]",
                    "//div[.//a[contains(@href, 'user.php?id=')]]",
                    "//div[.//h3/a[contains(@href, 'profile.php')]]"
                ]
            }

    def expand_groups_comments(self, max_iterations=120):
        """Specialized expansion for Facebook Groups"""
        print(f"=== EXPANDING GROUPS COMMENTS ({self.current_layout}) ===")
        
        selectors = self.get_groups_selectors()
        expand_selectors = selectors['expand_links']
        
        iteration = 0
        consecutive_failures = 0
        total_expansions = 0
        
        # First, try to find and click "View more comments" or similar buttons
        print("🔍 Looking for initial comment expansion buttons...")
        self._click_initial_expand_buttons()
        
        while iteration < max_iterations and consecutive_failures < 8:
            if self._stop_flag:
                break
                
            iteration += 1
            expanded_this_round = 0
            
            print(f"[Iteration {iteration}] Searching for expand links...")
            
            # Scroll to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(2, 3))
            
            # Also try scrolling up a bit to trigger lazy loading
            if iteration % 3 == 0:
                self.driver.execute_script("window.scrollBy(0, -200);")
                time.sleep(1)
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            
            # Find expandable elements
            expandable_elements = []
            for selector in expand_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for elem in elements:
                        try:
                            if elem.is_displayed() and elem.is_enabled():
                                elem_text = elem.text.strip().lower()
                                # Validate expand keywords
                                expand_keywords = ['view', 'more', 'show', 'see', 'xem', 'thêm', 'hiển thị', 'comment', 'reply', 'bình luận', 'phản hồi']
                                if any(keyword in elem_text for keyword in expand_keywords):
                                    if elem not in expandable_elements:
                                        expandable_elements.append(elem)
                        except:
                            continue
                except:
                    continue
            
            print(f"  Found {len(expandable_elements)} expandable elements")
            
            # Click expandable elements
            for i, elem in enumerate(expandable_elements):
                if self._stop_flag:
                    break
                    
                try:
                    elem_text = elem.text.strip()
                    print(f"    Attempting {i+1}/{len(expandable_elements)}: '{elem_text}'")
                    
                    # Scroll into view
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", elem)
                    time.sleep(1.5)
                    
                    # Try multiple click methods
                    click_success = False
                    
                    # Method 1: Regular click
                    try:
                        elem.click()
                        click_success = True
                    except:
                        pass
                    
                    # Method 2: JavaScript click
                    if not click_success:
                        try:
                            self.driver.execute_script("arguments[0].click();", elem)
                            click_success = True
                        except:
                            pass
                    
                    # Method 3: Action chains click
                    if not click_success:
                        try:
                            from selenium.webdriver.common.action_chains import ActionChains
                            ActionChains(self.driver).move_to_element(elem).click().perform()
                            click_success = True
                        except:
                            pass
                    
                    if click_success:
                        expanded_this_round += 1
                        print(f"    ✓ Successfully clicked")
                        time.sleep(random.uniform(2, 4))
                    else:
                        print(f"    ✗ All click methods failed")
                    
                except Exception as e:
                    print(f"    ✗ Error clicking: {e}")
                    continue
            
            total_expansions += expanded_this_round
            
            if expanded_this_round > 0:
                print(f"✓ Expanded {expanded_this_round} elements in iteration {iteration}")
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                print(f"✗ No expansion in iteration {iteration} (consecutive failures: {consecutive_failures})")
        
        print(f"=== EXPANSION COMPLETE: {total_expansions} total expansions ===")
        
        # Final loading wait
        for _ in range(3):
            if self._stop_flag:
                break
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

    def _click_initial_expand_buttons(self):
        """Click initial comment expansion buttons to show more comments"""
        try:
            # Look for initial comment expansion buttons
            initial_expand_selectors = [
                # Vietnamese
                "//a[contains(text(),'Xem bình luận')]",
                "//a[contains(text(),'Xem thêm bình luận')]",
                "//a[contains(text(),'Hiển thị bình luận')]",
                "//div[contains(text(),'Xem bình luận')]",
                "//span[contains(text(),'Xem bình luận')]",
                
                # English
                "//a[contains(text(),'View comments')]",
                "//a[contains(text(),'View more comments')]",
                "//a[contains(text(),'Show comments')]",
                "//div[contains(text(),'View comments')]",
                "//span[contains(text(),'View comments')]",
                
                # Mobile specific
                "//div[@role='button' and contains(text(),'Xem bình luận')]",
                "//div[@role='button' and contains(text(),'View comments')]",
                "//div[@data-sigil='comment-expand']//a[contains(text(),'Xem')]",
                "//div[@data-sigil='comment-expand']//a[contains(text(),'View')]"
            ]
            
            for selector in initial_expand_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            print(f"  Found initial expand button: {element.text}")
                            
                            # Scroll into view
                            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                            time.sleep(1)
                            
                            # Try to click
                            try:
                                element.click()
                                print("  ✅ Successfully clicked initial expand button")
                                time.sleep(3)  # Wait for comments to load
                                break
                            except:
                                # Try JavaScript click
                                try:
                                    self.driver.execute_script("arguments[0].click();", element)
                                    print("  ✅ Successfully clicked initial expand button (JS)")
                                    time.sleep(3)
                                    break
                                except:
                                    continue
                except:
                    continue
                    
        except Exception as e:
            print(f"  ⚠️ Error clicking initial expand buttons: {e}")

    def extract_groups_comments(self):
        """Extract comments from Facebook Groups with enhanced debugging"""
        print(f"\n=== EXTRACTING GROUPS COMMENTS ({self.current_layout}) ===")
        
        # Get selectors for current layout
        selectors = self.get_groups_selectors()
        comment_selectors = selectors['comment_containers']
        
        # Try to find comment elements with each selector
        all_comment_elements = []
        
        print(f"🔍 Searching for comment elements using {len(comment_selectors)} selectors...")
        
        for i, selector in enumerate(comment_selectors):
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
                if elements:
                    print(f"  Selector {i+1}: '{selector}' found {len(elements)} elements")
                    for elem in elements[:3]:  # Show first 3 elements
                        try:
                            elem_text = elem.text.strip()[:100]
                            print(f"    - Element text: '{elem_text}...'")
                        except:
                            print(f"    - Element text: [Could not read]")
                    
                    # Add unique elements
                    for elem in elements:
                        if elem not in all_comment_elements:
                            all_comment_elements.append(elem)
                else:
                    print(f"  Selector {i+1}: '{selector}' found 0 elements")
            except Exception as e:
                print(f"  Selector {i+1}: '{selector}' error: {e}")
        
        print(f"\n📊 Total unique comment elements found: {len(all_comment_elements)}")
        
        if not all_comment_elements:
            print("❌ No comment elements found with any selector!")
            print("🔍 Trying emergency fallback selectors...")
            
            # Emergency fallback - very broad selectors
            emergency_selectors = [
                "//div[string-length(normalize-space(text())) > 30]",
                "//div[.//a[contains(@href, 'facebook.com/')]]",
                "//div[contains(@class, 'm')]",
                "//div[@data-action-id]"
            ]
            
            for selector in emergency_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements:
                        print(f"  Emergency selector '{selector}' found {len(elements)} elements")
                        for elem in elements[:3]:
                            try:
                                elem_text = elem.text.strip()[:100]
                                print(f"    - Emergency element: '{elem_text}...'")
                            except:
                                print(f"    - Emergency element: [Could not read]")
                        
                        # Add unique elements
                        for elem in elements:
                            if elem not in all_comment_elements:
                                all_comment_elements.append(elem)
                except Exception as e:
                    print(f"  Emergency selector '{selector}' error: {e}")
            
            print(f"📊 After emergency fallback: {len(all_comment_elements)} total elements")
        
        if not all_comment_elements:
            print("❌ Still no elements found. This might indicate:")
            print("   - The page structure has changed")
            print("   - Comments are not loaded yet")
            print("   - Access permission issues")
            return []
        
        # Process found elements
        comments = []
        seen_content = set()
        
        print(f"\n🔍 Processing {len(all_comment_elements)} elements for comment data...")
        
        for i, element in enumerate(all_comment_elements):
            if self._stop_flag:
                break
                
            try:
                print(f"\n--- Element {i+1}/{len(all_comment_elements)} ---")
                
                comment_data = self.extract_groups_comment_data(element, i)
                
                if not comment_data:
                    continue
                
                # Deduplication based on profile link and name - more lenient
                if comment_data['Name'] == "Unknown":
                    print("  ✗ Skipped: no username found")
                    continue
                    
                # Check for duplicates - only skip if same name AND same profile link
                content_signature = f"{comment_data['Name']}_{comment_data['ProfileLink']}"
                if content_signature in seen_content:
                    print("  ✗ Skipped: duplicate user")
                    continue
                seen_content.add(content_signature)
                
                # Determine type for groups
                comment_type = self.determine_groups_comment_type(element, all_comment_elements, i)
                comment_data['Type'] = comment_type
                comment_data['Layout'] = self.current_layout
                
                comments.append(comment_data)
                print(f"  ✅ Added {comment_type}: {comment_data['Name']} - Profile: {comment_data['ProfileLink'][:50]}...")
                
            except Exception as e:
                print(f"  Error processing element {i}: {e}")
                continue
        
        # Final cleanup and organization
        final_comments = self.cleanup_groups_comments(comments)
        
        print(f"\n=== GROUPS EXTRACTION COMPLETE ===")
        main_count = len([c for c in final_comments if c['Type'] == 'Comment'])
        reply_count = len([c for c in final_comments if c['Type'] == 'Reply'])
        print(f"Final results: {main_count} main comments + {reply_count} replies = {len(final_comments)} total")
        
        return final_comments

    def extract_groups_comment_data(self, element, index):
        """Extract comment data optimized for groups - focus on links and names"""
        try:
            full_text = element.text.strip()
            if len(full_text) < 5:
                return None
            
            print(f"  Processing: '{full_text[:80]}...'")
            
            # Skip anonymous users
            if any(keyword in full_text.lower() for keyword in ['ẩn danh', 'người tham gia ẩn danh', 'anonymous']):
                print("  ⚠️ Skipping anonymous user comment")
                return None
            
            username = "Unknown"
            profile_href = ""
            uid = "Unknown"
            comment_link = ""
            
            # NEW STRATEGY: Based on user hint about clicking on black names and comment times
            
            # Strategy 1: Look for clickable names (black names that lead to FB profile)
            # These are typically the first clickable text in a comment
            try:
                # Find all clickable links that could be usernames
                name_candidates = element.find_elements(By.XPATH, 
                    ".//a[contains(@href, 'facebook.com/') and string-length(normalize-space(text())) > 2 and string-length(normalize-space(text())) < 50]")
                
                for candidate in name_candidates:
                    candidate_text = candidate.text.strip()
                    candidate_href = candidate.get_attribute("href") or ""
                    
                    # Skip obvious UI elements and validate as potential username
                    if (candidate_text and 
                        not any(ui in candidate_text.lower() for ui in [
                            'ẩn danh', 'người tham gia', 'like', 'reply', 'share', 'comment', 
                            'thành viên', 'bài viết của', 'nhà mình', 'cảm ơn', 'cha ta', 'mẹ ta',
                            'thích', 'trả lời', 'chia sẻ', 'bình luận', 'theo dõi', 'follow',
                            '1 tuần', '2 tuần', '3 tuần', '1 ngày', '2 ngày', '1 giờ', '2 giờ',
                            'min', 'minutes', 'hours', 'days', 'phút', 'giờ', 'ngày', 'giây'
                        ]) and
                        'facebook.com' in candidate_href and
                        not candidate_text.isdigit() and
                        not candidate_text.startswith('http')):
                        
                        username = candidate_text
                        profile_href = candidate_href
                        
                        # Extract UID from various formats
                        uid_patterns = [
                            r'profile\.php\?id=(\d+)',
                            r'user\.php\?id=(\d+)',
                            r'/(\d+)(?:\?|$)',
                            r'id=(\d+)',
                            r'(\d{10,})'  # Facebook UIDs are usually 10+ digits
                        ]
                        
                        for pattern in uid_patterns:
                            uid_match = re.search(pattern, candidate_href)
                            if uid_match:
                                uid = uid_match.group(1)
                                break
                        
                        print(f"  ✅ Found username via Strategy 1: {username}")
                        break
                        
            except Exception as e:
                print(f"  ⚠️ Strategy 1 failed: {e}")
            
            # Strategy 2: If no username found, try to find it in the text structure
            if username == "Unknown":
                try:
                    # Look for text that looks like a name but might not be clickable
                    # This handles cases where the name is visible but not a link
                    text_elements = element.find_elements(By.XPATH, 
                        ".//*[string-length(normalize-space(text())) > 2 and string-length(normalize-space(text())) < 50]")
                    
                    for text_elem in text_elements:
                        text_content = text_elem.text.strip()
                        
                        # Check if this looks like a name (not UI text)
                        if (text_content and 
                            not any(ui in text_content.lower() for ui in [
                                'ẩn danh', 'người tham gia', 'like', 'reply', 'share', 'comment', 
                                'thành viên', 'bài viết của', 'nhà mình', 'cảm ơn', 'cha ta', 'mẹ ta',
                                'thích', 'trả lời', 'chia sẻ', 'bình luận', 'theo dõi', 'follow',
                                '1 tuần', '2 tuần', '3 tuần', '1 ngày', '2 ngày', '1 giờ', '2 giờ',
                                'min', 'minutes', 'hours', 'days', 'phút', 'giờ', 'ngày', 'giây'
                            ]) and
                            not text_content.isdigit() and
                            not text_content.startswith('http') and
                            len(text_content.split()) <= 4):  # Names are usually 1-4 words
                            
                            # Try to find a Facebook link in the same element or nearby
                            parent_elem = text_elem.find_element(By.XPATH, "./ancestor::div[string-length(normalize-space(text())) > 30][1]")
                            if parent_elem:
                                fb_links = parent_elem.find_elements(By.XPATH, ".//a[contains(@href, 'facebook.com/')]")
                                
                                for link in fb_links:
                                    link_href = link.get_attribute("href") or ""
                                    if 'facebook.com' in link_href:
                                        username = text_content
                                        profile_href = link_href
                                        
                                        # Extract UID
                                        uid_match = re.search(r'profile\.php\?id=(\d+)', link_href)
                                        if uid_match:
                                            uid = uid_match.group(1)
                                        break
                                
                                if username != "Unknown":
                                    print(f"  ✅ Found username via Strategy 2: {username}")
                                    break
                                    
                except Exception as e:
                    print(f"  ⚠️ Strategy 2 failed: {e}")
            
            # Strategy 3: Mobile Facebook specific - look for span.f20 elements (from your div example)
            if username == "Unknown":
                try:
                    # Look for username in span.f20 elements (like in your div example)
                    username_spans = element.find_elements(By.XPATH, ".//span[contains(@class, 'f20')]")
                    
                    for span in username_spans:
                        span_text = span.text.strip()
                        if (span_text and 
                            len(span_text) > 2 and 
                            len(span_text) < 50 and
                            not any(ui in span_text.lower() for ui in [
                                'ẩn danh', 'người tham gia', 'like', 'reply', 'share', 'comment', 
                                'thành viên', 'bài viết của', 'nhà mình', 'cảm ơn', 'cha ta', 'mẹ ta',
                                'thích', 'trả lời', 'chia sẻ', 'bình luận', 'theo dõi', 'follow'
                            ])):
                            
                            # Try to find profile link in parent or sibling elements
                            try:
                                parent_div = span.find_element(By.XPATH, "./ancestor::div[contains(@class, 'm')][1]")
                                if parent_div:
                                    # Look for any Facebook link in the parent
                                    profile_links = parent_div.find_elements(By.XPATH, ".//a[contains(@href, 'facebook.com/')]")
                                    
                                    for link in profile_links:
                                        link_href = link.get_attribute("href") or ""
                                        if 'facebook.com' in link_href:
                                            username = span_text
                                            profile_href = link_href
                                            
                                            # Extract UID
                                            uid_match = re.search(r'profile\.php\?id=(\d+)', link_href)
                                            if uid_match:
                                                uid = uid_match.group(1)
                                            break
                                    
                                    if username != "Unknown":
                                        print(f"  ✅ Found username via Strategy 3: {username}")
                                        break
                            except:
                                continue
                                
                except Exception as e:
                    print(f"  ⚠️ Strategy 3 failed: {e}")
            
            # Strategy 4: Look for comment links based on time elements (user's hint about comment time)
            # Comment links are often associated with time elements like "1 tuần", "1 week", etc.
            try:
                # Look for time-related elements that might have comment links
                time_selectors = [
                    ".//*[contains(text(), 'tuần')]",
                    ".//*[contains(text(), 'week')]",
                    ".//*[contains(text(), 'ngày')]",
                    ".//*[contains(text(), 'day')]",
                    ".//*[contains(text(), 'giờ')]",
                    ".//*[contains(text(), 'hour')]",
                    ".//*[contains(text(), 'phút')]",
                    ".//*[contains(text(), 'minute')]",
                    ".//*[contains(text(), 'giây')]",
                    ".//*[contains(text(), 'second')]"
                ]
                
                for time_selector in time_selectors:
                    try:
                        time_elements = element.find_elements(By.XPATH, time_selector)
                        for time_elem in time_elements:
                            # Look for clickable links near the time element
                            parent_elem = time_elem.find_element(By.XPATH, "./ancestor::div[string-length(normalize-space(text())) > 20][1]")
                            if parent_elem:
                                # Look for comment links
                                comment_links = parent_elem.find_elements(By.XPATH, 
                                    ".//a[contains(@href, 'permalink') or contains(@href, 'comment') or contains(@href, 'story_fbid')]")
                                
                                for link in comment_links:
                                    link_href = link.get_attribute("href") or ""
                                    if link_href and "facebook.com" in link_href:
                                        comment_link = link_href
                                        break
                                
                                if comment_link:
                                    break
                        
                        if comment_link:
                            break
                            
                    except:
                        continue
                        
            except Exception as e:
                print(f"  ⚠️ Comment link extraction failed: {e}")
            
            # Strategy 5: If still no comment link, try to construct from current page
            if not comment_link:
                try:
                    current_url = self.driver.current_url
                    if "groups/" in current_url:
                        # Try to find comment ID in the element
                        comment_id_selectors = [
                            ".//div[contains(@id, 'comment_')]",
                            ".//div[contains(@data-ft, 'comment')]",
                            ".//div[@data-sigil='comment']",
                            ".//div[contains(@class, 'comment')]"
                        ]
                        
                        for selector in comment_id_selectors:
                            try:
                                comment_elem = element.find_element(By.XPATH, selector)
                                comment_id = comment_elem.get_attribute("id") or comment_elem.get_attribute("data-ft") or ""
                                if comment_id:
                                    # Construct comment link
                                    if "comment_" in comment_id:
                                        comment_id = comment_id.replace("comment_", "")
                                    comment_link = f"{current_url}#comment_{comment_id}"
                                    break
                            except:
                                continue
                except:
                    pass
            
            # Final validation - we need at least a username to be valid
            if username == "Unknown":
                print("  ❌ Could not extract username from this element")
                return None
                
            print(f"  ✅ Extracted: {username} - Profile: {profile_href[:50]}... - UID: {uid}")
            
            return {
                "UID": uid,
                "Name": username,
                "ProfileLink": profile_href,
                "CommentLink": comment_link,
                "ElementIndex": index
            }
            
        except Exception as e:
            print(f"Error extracting groups comment data: {e}")
            return None

    def determine_groups_comment_type(self, element, all_elements, index):
        """Determine comment type specifically for groups"""
        try:
            # Groups-specific reply detection
            
            # Method 1: Check data attributes
            data_sigil = element.get_attribute("data-sigil") or ""
            if "reply" in data_sigil.lower():
                return "Reply"
            
            # Method 2: Check for indentation in groups
            try:
                elem_location = element.location
                elem_size = element.size
                
                # Compare with nearby elements
                for compare_index in range(max(0, index-3), index):
                    if compare_index < len(all_elements):
                        try:
                            compare_elem = all_elements[compare_index]
                            compare_location = compare_elem.location
                            
                            # If this element is significantly more indented
                            if elem_location['x'] > compare_location['x'] + 30:
                                return "Reply"
                        except:
                            continue
            except:
                pass
            
            # Method 3: Check parent-child relationship in DOM
            try:
                # If this element is nested within another comment-like element
                comment_ancestors = element.find_elements(By.XPATH, 
                    "./ancestor::div[.//a[contains(@href,'profile.php')] and string-length(normalize-space(text())) > 50]")
                
                # If there are comment-like ancestors, this might be a reply
                if len(comment_ancestors) > 0:
                    # Additional check: make sure the ancestor is not just a container
                    for ancestor in comment_ancestors:
                        try:
                            ancestor_text = ancestor.text.strip()
                            element_text = element.text.strip()
                            
                            # If ancestor contains this element's text, it's likely a container
                            if element_text in ancestor_text and len(ancestor_text) > len(element_text) * 1.5:
                                return "Reply"
                        except:
                            continue
            except:
                pass
            
            # Method 4: Text-based indicators
            try:
                element_text = element.text.lower()
                reply_indicators = [
                    'replied to', 'replying to', 'in reply to', 
                    'trả lời', 'phản hồi', 'đáp lại',
                    '@', 'reply:', 'phản hồi:'
                ]
                if any(indicator in element_text for indicator in reply_indicators):
                    return "Reply"
            except:
                pass
            
            # Default to main comment for groups
            return "Comment"
            
        except Exception as e:
            print(f"Error determining groups comment type: {e}")
            return "Comment"

    def cleanup_groups_comments(self, comments):
        """Final cleanup specifically for groups comments - only main comments"""
        print("=== CLEANING UP GROUPS COMMENTS ===")
        
        cleaned = []
        final_seen = set()
        
        for comment in comments:
            # Only keep main comments, skip replies
            if comment['Type'] == 'Reply':
                print(f"  ✗ Skipped reply: {comment['Name']}")
                continue
                
            # Basic deduplication
            if comment['Name'] == "Unknown" or not comment['ProfileLink']:
                print(f"  ✗ Skipped invalid: {comment['Name']} - {comment['ProfileLink']}")
                continue
                
            # Check for duplicates
            signature = f"{comment['Name']}_{comment['ProfileLink']}"
            if signature in final_seen:
                print(f"  ✗ Skipped duplicate: {comment['Name']}")
                continue
                
            final_seen.add(signature)
            cleaned.append(comment)
            print(f"  ✅ Kept main comment: {comment['Name']} - {comment['ProfileLink']}")
        
        # Sort by element index
        cleaned.sort(key=lambda x: x.get('ElementIndex', 999))
        
        print(f"Final cleaned main comments: {len(cleaned)}")
        return cleaned

    def scrape_all_comments(self, limit=0, resolve_uid=True, progress_callback=None):
        """Main scraping orchestrator for groups"""
        print(f"=== STARTING GROUPS SCRAPING ===")
        
        # Step 1: Expand all content
        self.expand_groups_comments()
        
        if self._stop_flag:
            return []
        
        # Step 2: Extract comments
        comments = self.extract_groups_comments()
        
        # Step 3: Apply limit
        if limit > 0:
            comments = comments[:limit]
        
        # Step 4: Progress reporting
        if progress_callback:
            progress_callback(len(comments))
        
        return comments

    def close(self):
        try: 
            self.driver.quit()
        except: 
            pass

# ----------------------------
# Groups-Optimized GUI
# ----------------------------
class FBGroupsAppGUI:
    def __init__(self, root):
        self.root = root
        root.title("🏘️ FB Groups Comment Scraper")
        root.geometry("1000x900")
        root.configure(bg="#e8f5e8")

        # Main frame
        main_frame = tk.Frame(root, bg="#e8f5e8")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # Header
        header_frame = tk.Frame(main_frame, bg="#e8f5e8")
        header_frame.pack(fill="x", pady=(0,20))
        
        title_label = tk.Label(header_frame, text="🏘️ Facebook Groups Comment Scraper", 
                              font=("Arial", 20, "bold"), bg="#e8f5e8", fg="#2d5a2d")
        title_label.pack()
        
        subtitle_label = tk.Label(header_frame, text="✨ Chuyên dụng cho Facebook Groups - Tự động chọn 'Tất cả bình luận' - Chỉ lấy Main Comments", 
                                 font=("Arial", 11), bg="#e8f5e8", fg="#5a5a5a")
        subtitle_label.pack(pady=(5,0))

        # Input section
        input_frame = tk.LabelFrame(main_frame, text="📝 Thông tin bài viết Groups", font=("Arial", 12, "bold"), 
                                   bg="#e8f5e8", fg="#2d5a2d", relief="groove", bd=2)
        input_frame.pack(fill="x", pady=(0,15))

        tk.Label(input_frame, text="🔗 Link bài viết trong Groups:", bg="#e8f5e8", font=("Arial", 10)).pack(anchor="w", padx=15, pady=(15,5))
        self.entry_url = tk.Entry(input_frame, width=100, font=("Arial", 9))
        self.entry_url.pack(fill="x", padx=15, pady=(0,10))

        tk.Label(input_frame, text="🍪 Cookie Facebook (để truy cập Groups):", bg="#e8f5e8", font=("Arial", 10)).pack(anchor="w", padx=15, pady=(5,5))
        self.txt_cookie = tk.Text(input_frame, height=4, font=("Arial", 8))
        self.txt_cookie.pack(fill="x", padx=15, pady=(0,15))

        # Options section
        options_frame = tk.LabelFrame(main_frame, text="⚙️ Cấu hình Groups", font=("Arial", 12, "bold"), 
                                     bg="#e8f5e8", fg="#2d5a2d", relief="groove", bd=2)
        options_frame.pack(fill="x", pady=(0,15))
        
        opt_grid = tk.Frame(options_frame, bg="#e8f5e8")
        opt_grid.pack(fill="x", padx=15, pady=15)
        
        # Options grid
        tk.Label(opt_grid, text="📊 Số lượng comment:", bg="#e8f5e8").grid(row=0, column=0, sticky="w")
        self.entry_limit = tk.Entry(opt_grid, width=10)
        self.entry_limit.insert(0, "0")
        self.entry_limit.grid(row=0, column=1, sticky="w", padx=(10,20))
        tk.Label(opt_grid, text="(0 = tất cả)", bg="#e8f5e8", fg="#6c757d").grid(row=0, column=2, sticky="w")

        self.headless_var = tk.BooleanVar(value=False)  # Default to visible for groups debugging
        tk.Checkbutton(opt_grid, text="👻 Chạy ẩn", variable=self.headless_var, 
                      bg="#e8f5e8", font=("Arial", 9)).grid(row=1, column=0, sticky="w", pady=(10,0))

        self.resolve_uid_var = tk.BooleanVar(value=False)
        tk.Checkbutton(opt_grid, text="🆔 Lấy UID", variable=self.resolve_uid_var, 
                      bg="#e8f5e8", font=("Arial", 9)).grid(row=1, column=1, sticky="w", pady=(10,0))

        # File section
        file_frame = tk.LabelFrame(main_frame, text="💾 Xuất kết quả", font=("Arial", 12, "bold"), 
                                  bg="#e8f5e8", fg="#2d5a2d", relief="groove", bd=2)
        file_frame.pack(fill="x", pady=(0,15))
        
        file_row = tk.Frame(file_frame, bg="#e8f5e8")
        file_row.pack(fill="x", padx=15, pady=15)
        
        self.entry_file = tk.Entry(file_row, width=70, font=("Arial", 9))
        self.entry_file.insert(0, "facebook_groups_comments.xlsx")
        self.entry_file.pack(side="left", fill="x", expand=True)
        
        tk.Button(file_row, text="📁 Chọn", command=self.choose_file, 
                 bg="#17a2b8", fg="white", font=("Arial", 9)).pack(side="right", padx=(10,0))

        # Status section
        status_frame = tk.LabelFrame(main_frame, text="📊 Trạng thái thực thi", font=("Arial", 12, "bold"), 
                                    bg="#e8f5e8", fg="#2d5a2d", relief="groove", bd=2)
        status_frame.pack(fill="x", pady=(0,15))
        
        self.lbl_status = tk.Label(status_frame, text="✅ Sẵn sàng scrape Facebook Groups", fg="#28a745", 
                                  wraplength=900, justify="left", font=("Arial", 11), bg="#e8f5e8")
        self.lbl_status.pack(anchor="w", padx=15, pady=(15,5))

                self.lbl_progress_detail = tk.Label(status_frame, text="💡 Nhập link Groups và cookie → Nhấn Bắt đầu → Scraper sẽ tự động chọn 'Tất cả bình luận' và lấy Main Comments: Name, Profile Link, Comment Link, UID",
                                          fg="#6c757d", wraplength=900, justify="left", font=("Arial", 9), bg="#e8f5e8")
        self.lbl_progress_detail.pack(anchor="w", padx=15, pady=(0,10))

        # Progress bar
        self.progress_bar = ttk.Progressbar(status_frame, mode='indeterminate')
        self.progress_bar.pack(fill="x", padx=15, pady=(0,15))

        # Control buttons
        button_frame = tk.Frame(main_frame, bg="#e8f5e8")
        button_frame.pack(fill="x", pady=20)
        
        self.btn_start = tk.Button(button_frame, text="🚀 Bắt đầu lấy Groups Comments", bg="#28a745", fg="white", 
                                  font=("Arial", 14, "bold"), command=self.start_scrape_thread, 
                                  pady=12, padx=40)
        self.btn_start.pack(side="left")

        self.btn_stop = tk.Button(button_frame, text="⏹️ Dừng", bg="#dc3545", fg="white", 
                                 font=("Arial", 14, "bold"), command=self.stop_scrape, 
                                 state=tk.DISABLED, pady=12, padx=40)
        self.btn_stop.pack(side="left", padx=(25,0))

        self.progress_var = tk.IntVar(value=0)
        self.progress_label = tk.Label(button_frame, textvariable=self.progress_var, fg="#28a745", 
                                     font=("Arial", 18, "bold"), bg="#e8f5e8")
        self.progress_label.pack(side="right")

        self._scrape_thread = None
        self._stop_flag = False
        self.scraper = None

    def choose_file(self):
        f = filedialog.asksaveasfilename(
            defaultextension=".xlsx", 
            filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv")],
            title="Chọn file để lưu Groups comments"
        )
        if f:
            self.entry_file.delete(0, tk.END)
            self.entry_file.insert(0, f)

    def start_scrape_thread(self):
        url = self.entry_url.get().strip()
        cookie_str = self.txt_cookie.get("1.0", tk.END).strip()
        file_out = self.entry_file.get().strip() or "facebook_groups_comments.xlsx"
        
        if not url:
            messagebox.showerror("❌ Lỗi", "Vui lòng nhập link bài viết Groups.")
            return
        
        if "groups/" not in url:
            result = messagebox.askyesno("⚠️ Xác nhận", 
                                       "Link này có vẻ không phải Groups. Bạn có muốn tiếp tục không?")
            if not result:
                return
        
        try: 
            limit = int(self.entry_limit.get().strip())
        except: 
            limit = 0

        self._stop_flag = False
        self.progress_var.set(0)
        self.progress_bar.start()
        self.lbl_status.config(text="🔄 Đang khởi động Groups scraper...", fg="#fd7e14")
        self.lbl_progress_detail.config(text="⏳ Đang chuẩn bị trình duyệt cho Facebook Groups...")
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)

        self._scrape_thread = threading.Thread(target=self._scrape_worker, 
                                             args=(url, cookie_str, file_out, limit, 
                                                   self.headless_var.get(), self.resolve_uid_var.get()))
        self._scrape_thread.daemon = True
        self._scrape_thread.start()

    def stop_scrape(self):
        self._stop_flag = True
        if self.scraper:
            self.scraper._stop_flag = True
        self.lbl_status.config(text="⏹️ Đang dừng Groups scraper...", fg="#dc3545")
        self.btn_stop.config(state=tk.DISABLED)

    def _progress_cb(self, count):
        self.progress_var.set(count)
        self.lbl_status.config(text=f"📈 Đang xử lý Groups... Đã lấy {count} comment/reply", fg="#28a745")
        self.root.update_idletasks()

    def _scrape_worker(self, url, cookie_str, file_out, limit, headless, resolve_uid):
        try:
            # Initialize
            self.lbl_status.config(text="🌐 Khởi tạo Groups scraper...", fg="#fd7e14")
            self.scraper = FacebookGroupsScraper(cookie_str, headless=headless)
            
            if self._stop_flag: return
            
            # Load post
            self.lbl_status.config(text="📄 Đang tải bài viết Groups...", fg="#fd7e14")
            self.lbl_progress_detail.config(text="⏳ Đang kết nối và detect layout tối ưu cho Groups...")
            success = self.scraper.load_post(url)
            
            if not success:
                self.lbl_status.config(text="❌ Không thể tải bài viết Groups", fg="#dc3545")
                self.lbl_progress_detail.config(text="💡 Groups thường yêu cầu: 1) Cookie valid, 2) Quyền truy cập nhóm, 3) Bài viết public trong nhóm")
                return
            
            # Show detected layout
            layout = getattr(self.scraper, 'current_layout', 'unknown')
            self.lbl_progress_detail.config(text=f"🎯 Layout detected: {layout} - Optimizing for Groups structure...")
                
            if self._stop_flag: return
            
            # Scrape
            self.lbl_status.config(text=f"🔍 Đang lấy Groups comments ({layout})...", fg="#fd7e14")
            self.lbl_progress_detail.config(text="⏳ Đang expand comments và extract data từ Groups (đã chọn 'Tất cả bình luận')...")
            
            comments = self.scraper.scrape_all_comments(limit=limit, resolve_uid=resolve_uid, 
                                                       progress_callback=self._progress_cb)
            
            if self._stop_flag: return
            
            # Save
            self.lbl_status.config(text="💾 Đang lưu Groups data...", fg="#fd7e14")
            
            if comments:
                df = pd.DataFrame(comments)
                
                # Add metadata
                df.insert(0, 'STT', range(1, len(df) + 1))
                df['Source'] = 'Facebook Groups'
                df['ScrapedAt'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # File handling
                if not file_out.lower().endswith((".xlsx", ".csv")):
                    file_out += ".xlsx"
                
                if file_out.lower().endswith(".csv"):
                    df.to_csv(file_out, index=False, encoding="utf-8-sig")
                else:
                    df.to_excel(file_out, index=False, engine="openpyxl")
                
                # Statistics
                main_comments_count = len([c for c in comments if c['Type'] == 'Comment'])
                replies_count = len([c for c in comments if c['Type'] == 'Reply'])
                unique_users = len(set(c['Name'] for c in comments if c['Name'] != 'Unknown'))
                profile_links = len([c for c in comments if c['ProfileLink']])
                comment_links = len([c for c in comments if c['CommentLink']])
                uid_count = len([c for c in comments if c['UID'] != 'Unknown'])
                
                self.lbl_status.config(text=f"🎉 GROUPS SCRAPING HOÀN THÀNH!", fg="#28a745")
                self.lbl_progress_detail.config(text=f"📊 Kết quả: {main_comments_count} main comments | {unique_users} users | {profile_links} profile links | {comment_links} comment links | {uid_count} UIDs | {layout} layout | File: {file_out}")
                
            else:
                self.lbl_status.config(text="⚠️ Không tìm thấy comment trong Groups", fg="#ffc107")
                self.lbl_progress_detail.config(text=f"💡 Layout: {layout} | Thử: 1) Kiểm tra quyền truy cập Groups, 2) Tắt headless, 3) Xem debug file")
                
        except Exception as e:
            error_msg = str(e)[:120]
            self.lbl_status.config(text=f"❌ Lỗi Groups scraping: {error_msg}...", fg="#dc3545")
            self.lbl_progress_detail.config(text="🔍 Xem console để biết chi tiết. Groups có thể có security khác thường.")
            print(f"Groups scraping error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.progress_bar.stop()
            if self.scraper: 
                self.scraper.close()
            self.btn_start.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)

# ----------------------------
# Run app
# ----------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = FBGroupsAppGUI(root)
    root.mainloop()