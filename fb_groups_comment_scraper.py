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
                    return True
                else:
                    print("⚠️ No group indicators found, but proceeding...")
                    return True
                    
            except Exception as e:
                print(f"Failed to load {url_attempt}: {e}")
                continue
        
        print("❌ Failed to load post with any URL variant")
        return False

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
                    "//*[contains(@data-sigil,'comment')]//*[contains(text(),'more') or contains(text(),'thêm')]"
                ],
                'comment_containers': [
                    # Mobile groups comment containers
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
                    # Broader selectors for groups
                    "//div[.//a[contains(@href, 'facebook.com/')] and string-length(normalize-space(text())) > 25]",
                    "//div[string-length(normalize-space(text())) > 40 and .//a[contains(@href, 'profile')]]"
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

    def extract_groups_comments(self):
        """Extract comments specifically optimized for Facebook Groups"""
        print(f"=== EXTRACTING GROUPS COMMENTS ({self.current_layout}) ===")
        
        # Save page for debugging
        try:
            with open(f"debug_groups_{self.current_layout}.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            print(f"Saved page to debug_groups_{self.current_layout}.html")
        except:
            pass
        
        selectors = self.get_groups_selectors()
        comment_selectors = selectors['comment_containers']
        
        # Collect all comment elements
        all_comment_elements = []
        
        for i, selector in enumerate(comment_selectors):
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
                print(f"Groups selector {i+1}: Found {len(elements)} elements")
                
                for elem in elements:
                    if elem not in all_comment_elements:
                        all_comment_elements.append(elem)
                        
            except Exception as e:
                print(f"Groups selector {i+1} failed: {e}")
                continue
        
        print(f"Total unique comment elements: {len(all_comment_elements)}")
        
        # If still no elements, try very broad search
        if len(all_comment_elements) == 0:
            print("⚠️ No comments with standard selectors, trying emergency fallback...")
            
            emergency_selectors = [
                "//div[.//a[contains(@href, 'facebook.com/')] and string-length(normalize-space(text())) > 20]",
                "//div[string-length(normalize-space(text())) > 30]",
                "//*[contains(text(), 'Like') or contains(text(), 'Thích')]/ancestor::div[string-length(text()) > 40][1]",
                "//span[string-length(normalize-space(text())) > 25]/ancestor::div[1]",
                "//a[contains(@href,'profile.php')]/ancestor::div[string-length(text()) > 30][1]"
            ]
            
            for selector in emergency_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    print(f"Emergency selector: Found {len(elements)} elements")
                    for elem in elements:
                        if elem not in all_comment_elements:
                            all_comment_elements.append(elem)
                    
                    # Stop if we found some elements
                    if len(all_comment_elements) > 10:
                        break
                except:
                    continue
        
        # Sort by position
        try:
            all_comment_elements.sort(key=lambda x: (x.location['y'], x.location['x']))
        except:
            pass
        
        comments = []
        seen_content = set()
        processed_elements = set()
        
        print(f"Processing {len(all_comment_elements)} potential comment elements...")
        
        # Process each element
        for i, element in enumerate(all_comment_elements):
            if self._stop_flag:
                break
                
            try:
                # Skip if already processed
                elem_id = id(element)
                if elem_id in processed_elements:
                    continue
                processed_elements.add(elem_id)
                
                print(f"\n--- Element {i+1}/{len(all_comment_elements)} ---")
                
                comment_data = self.extract_groups_comment_data(element, i)
                
                if not comment_data:
                    continue
                
                # Deduplication
                content_signature = f"{comment_data['Name'][:20]}_{comment_data['Content'][:40]}"
                if content_signature in seen_content:
                    print("  ✗ Skipped: duplicate")
                    continue
                seen_content.add(content_signature)
                
                # Determine type for groups
                comment_type = self.determine_groups_comment_type(element, all_comment_elements, i)
                comment_data['Type'] = comment_type
                comment_data['Layout'] = self.current_layout
                
                comments.append(comment_data)
                print(f"  ✅ Added {comment_type}: {comment_data['Name']} - {comment_data['Content'][:50]}...")
                
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
        """Extract comment data optimized for groups"""
        try:
            full_text = element.text.strip()
            if len(full_text) < 8:
                return None
            
            print(f"  Processing: '{full_text[:80]}...'")
            
            # Find profile links (groups often have different structure)
            profile_link_selectors = [
                ".//a[contains(@href, 'profile.php')]",
                ".//a[contains(@href, 'user.php')]",
                ".//a[contains(@href, '/profile/')]",
                ".//strong/a[contains(@href, 'facebook.com/')]",
                ".//h3/a[contains(@href, 'facebook.com/')]",
                ".//span/a[contains(@href, 'facebook.com/')]"
            ]
            
            username = "Unknown"
            profile_href = ""
            uid = "Unknown"
            
            for selector in profile_link_selectors:
                try:
                    links = element.find_elements(By.XPATH, selector)
                    for link in links[:2]:
                        link_text = link.text.strip()
                        link_href = link.get_attribute("href") or ""
                        
                        # Validate name for groups
                        if (link_text and 
                            3 <= len(link_text) <= 100 and 
                            not link_text.startswith('http') and
                            not link_text.isdigit() and
                            not any(ui in link_text.lower() for ui in ['like', 'reply', 'share', 'comment'])):
                            
                            username = link_text
                            profile_href = link_href
                            
                            # Extract UID
                            uid_match = re.search(r'profile\.php\?id=(\d+)', link_href)
                            if uid_match:
                                uid = uid_match.group(1)
                            break
                    
                    if username != "Unknown":
                        break
                        
                except:
                    continue
            
            # Extract content for groups
            content = self.extract_groups_content(element, username, full_text)
            
            if not content or len(content) < 8 or self.is_groups_ui_only(content):
                return None
            
            return {
                "UID": uid,
                "Name": username,
                "Content": content,
                "ProfileLink": profile_href,
                "ContentLength": len(content),
                "ElementIndex": index
            }
            
        except Exception as e:
            print(f"Error extracting groups comment data: {e}")
            return None

    def extract_groups_content(self, element, username, full_text):
        """Extract content specifically for groups layout"""
        content_candidates = []
        
        # Strategy 1: Remove username and clean
        content = full_text
        if username != "Unknown":
            # Remove username from beginning
            if content.startswith(username):
                content = content[len(username):].strip()
            # Remove username with word boundaries
            content = re.sub(rf'\b{re.escape(username)}\b', '', content, count=1).strip()
        
        content_candidates.append(content)
        
        # Strategy 2: Groups-specific content extraction
        if self.current_layout == "mobile":
            try:
                # Mobile groups: look for data-sigil="comment-body"
                comment_bodies = element.find_elements(By.XPATH, ".//div[@data-sigil='comment-body'] | .//span[@data-sigil='comment-body']")
                for body in comment_bodies:
                    body_text = body.text.strip()
                    if body_text and body_text != username:
                        content_candidates.append(body_text)
            except:
                pass
        
        # Strategy 3: Look for pure text elements
        try:
            text_elements = element.find_elements(By.XPATH, ".//div[not(.//a) and not(.//button) and string-length(normalize-space(text())) > 15] | .//span[not(.//a) and not(.//button) and string-length(normalize-space(text())) > 15]")
            for text_elem in text_elements:
                text_content = text_elem.text.strip()
                if text_content and text_content != username:
                    content_candidates.append(text_content)
        except:
            pass
        
        # Choose best content
        valid_contents = []
        for candidate in content_candidates:
            cleaned = clean_text(candidate)
            if cleaned and len(cleaned) >= 8 and not self.is_groups_ui_only(cleaned):
                valid_contents.append(cleaned)
        
        if not valid_contents:
            return ""
        
        # Return longest valid content
        best_content = max(valid_contents, key=len)
        
        # Final cleanup for groups
        best_content = re.sub(r'^(Like|Reply|Share|Comment|Thích|Trả lời|Chia sẻ|Bình luận)\s*', '', best_content)
        best_content = re.sub(r'\s*(Like|Reply|Share|Comment|Thích|Trả lời|Chia sẻ|Bình luận)$', '', best_content)
        
        return best_content.strip()

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

    def is_groups_ui_only(self, text):
        """Check if text is UI-only for groups context"""
        if not text or len(text.strip()) < 5:
            return True
        
        text_clean = text.lower().strip()
        
        # Groups-specific UI patterns
        groups_ui_patterns = [
            r'^(like|reply|share|comment|translate|hide|report|block)(\s+\d+)?\s*$',
            r'^(thích|trả lời|chia sẻ|bình luận|dịch|ẩn|báo cáo|chặn)(\s+\d+)?\s*$',
            r'^\d+\s*(min|minutes?|hours?|days?|phút|giờ|ngày)\s*(ago|trước)?\s*$',
            r'^(top fan|most relevant|newest|all comments|view more|see more)\s*$',
            r'^(bình luận hàng đầu|xem thêm|hiển thị thêm)\s*$',
            r'^\d+\s*(like|love|reaction|thích|yêu|cảm xúc)\s*$',
            r'^(see translation|xem bản dịch|translate|dịch)\s*$',
            r'^(write a comment|viết bình luận|comment|bình luận)\s*$',
            r'^(group|nhóm|groups|các nhóm)\s*$'
        ]
        
        for pattern in groups_ui_patterns:
            if re.match(pattern, text_clean):
                return True
        
        # Just punctuation or numbers
        if re.match(r'^[\s\d\.\,\!\?\-\+\=\(\)\[\]]+$', text_clean):
            return True
        
        # Very short content
        if len(text_clean) < 8:
            return True
        
        return False

    def cleanup_groups_comments(self, comments):
        """Final cleanup specifically for groups comments"""
        print("=== CLEANING UP GROUPS COMMENTS ===")
        
        cleaned = []
        final_seen = set()
        
        for comment in comments:
            # More aggressive deduplication for groups
            signatures = [
                f"{comment['Name']}_{comment['Content'][:30]}",
                comment['Content'][:60] if len(comment['Content']) > 60 else comment['Content'],
                f"{comment['UID']}_{comment['Content'][:25]}" if comment['UID'] != "Unknown" else None
            ]
            
            is_duplicate = any(sig in final_seen for sig in signatures if sig)
            
            if not is_duplicate and comment['Content'] and len(comment['Content']) >= 8:
                cleaned.append(comment)
                for sig in signatures:
                    if sig:
                        final_seen.add(sig)
        
        # Sort: main comments first, then replies
        cleaned.sort(key=lambda x: (
            x['Type'] == 'Reply',
            x.get('ElementIndex', 999)
        ))
        
        print(f"Final cleaned comments: {len(cleaned)}")
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
        
        subtitle_label = tk.Label(header_frame, text="✨ Chuyên dụng cho Facebook Groups - Tự động detect mobile/mbasic layout", 
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

        self.lbl_progress_detail = tk.Label(status_frame, text="💡 Nhập link Groups và cookie → Nhấn Bắt đầu → Scraper sẽ tự động detect layout và optimize", 
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
            self.lbl_progress_detail.config(text="⏳ Đang expand và extract comments từ Groups...")
            
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
                comments_count = len([c for c in comments if c['Type'] == 'Comment'])
                replies_count = len([c for c in comments if c['Type'] == 'Reply'])
                unique_users = len(set(c['Name'] for c in comments if c['Name'] != 'Unknown'))
                avg_length = sum(len(c['Content']) for c in comments) // len(comments) if comments else 0
                
                self.lbl_status.config(text=f"🎉 GROUPS SCRAPING HOÀN THÀNH!", fg="#28a745")
                self.lbl_progress_detail.config(text=f"📊 Kết quả: {comments_count} comments + {replies_count} replies | {unique_users} users | TB: {avg_length} chars | {layout} layout | File: {file_out}")
                
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