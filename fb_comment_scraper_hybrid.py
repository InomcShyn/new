# fb_comment_scraper_hybrid.py - Support both mbasic and mobile Facebook
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
    # Remove UI elements
    ui_patterns = [
        r'\b(Like|Reply|Share|Comment|Translate|Hide|Report|Block|Thích|Trả lời|Chia sẻ|Bình luận)\b',
        r'\b\d+\s*(min|minutes?|hours?|days?|seconds?|phút|giờ|ngày|giây)\s*(ago|trước)?\b',
        r'\b(Top fan|Most relevant|Newest|All comments)\b'
    ]
    for pattern in ui_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    return text.strip()

# ----------------------------
# Hybrid Facebook Scraper (supports both mbasic and mobile)
# ----------------------------
class FacebookHybridScraper:
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
        
        # Mobile user agent that works well with both mbasic and mobile
        options.add_argument("user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) "
                             "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1")
        options.add_argument("window-size=414,896")
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        self.wait = WebDriverWait(self.driver, 15)
        self.cookie_str = cookie_str or ""
        self.cookies_list = parse_cookies_to_list(self.cookie_str)
        self.cookies_dict = parse_cookies_to_dict(self.cookie_str)
        self._stop_flag = False
        self.facebook_layout = None  # Will be detected: 'mbasic', 'mobile', or 'www'
        
        if self.cookies_list:
            self._login_with_cookies()

    def _login_with_cookies(self):
        # Try mbasic first
        self.driver.get("https://mbasic.facebook.com")
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
        
        # Refresh to apply cookies
        self.driver.get("https://mbasic.facebook.com")
        time.sleep(4)

    def detect_facebook_layout(self, url):
        """Detect which Facebook layout we're dealing with"""
        if "mbasic.facebook.com" in url:
            return "mbasic"
        elif "m.facebook.com" in url:
            return "mobile"
        elif "www.facebook.com" in url:
            return "www"
        else:
            return "unknown"

    def load_post(self, post_url):
        print(f"Loading post: {post_url}")
        
        # Try mbasic first
        if "mbasic.facebook.com" not in post_url:
            mbasic_url = post_url.replace("www.facebook.com", "mbasic.facebook.com").replace("m.facebook.com", "mbasic.facebook.com")
            print(f"Trying mbasic URL: {mbasic_url}")
            
            try:
                self.driver.get(mbasic_url)
                time.sleep(6)
                
                current_url = self.driver.current_url
                self.facebook_layout = self.detect_facebook_layout(current_url)
                print(f"Detected layout: {self.facebook_layout}")
                print(f"Final URL: {current_url}")
                
                # Check if login is required
                page_title = self.driver.title.lower()
                if any(keyword in page_title for keyword in ["log in", "login", "đăng nhập"]):
                    print("❌ Not logged in!")
                    return False
                
                # Check if we can see any content
                if self.facebook_layout == "mobile":
                    print("📱 Redirected to mobile layout - adjusting selectors")
                elif self.facebook_layout == "mbasic":
                    print("📄 Using mbasic layout")
                
                return True
                
            except Exception as e:
                print(f"Error loading post: {e}")
                return False
        else:
            # Direct mbasic URL
            try:
                self.driver.get(post_url)
                time.sleep(6)
                self.facebook_layout = self.detect_facebook_layout(self.driver.current_url)
                return True
            except:
                return False

    def get_layout_specific_selectors(self):
        """Get selectors based on detected Facebook layout"""
        if self.facebook_layout == "mobile":
            # m.facebook.com selectors
            return {
                'expand_links': [
                    "//a[contains(text(),'View more comments')]",
                    "//a[contains(text(),'View previous comments')]",
                    "//a[contains(text(),'View more replies')]",
                    "//a[contains(text(),'Show more')]",
                    "//a[contains(text(),'See more')]",
                    "//a[contains(text(),'Xem thêm')]",
                    "//a[contains(text(),'Hiển thị thêm')]",
                    "//div[@role='button' and contains(text(),'more')]",
                    "//span[contains(text(),'View') and contains(text(),'more')]/ancestor::a[1]",
                    "//span[contains(text(),'Xem') and contains(text(),'thêm')]/ancestor::a[1]"
                ],
                'comment_containers': [
                    # Mobile-specific comment selectors
                    "//div[@data-sigil='comment']",
                    "//div[contains(@class, 'story_body_container')]//div[.//a[contains(@href, 'profile.php')]]",
                    "//div[contains(@id, 'comment_')]",
                    "//article//div[.//a[contains(@href, 'profile.php')]]",
                    "//div[@role='article']//div[.//a[contains(@href, 'profile.php')]]",
                    "//div[.//h3/a[contains(@href, 'profile.php')]]",
                    "//div[.//strong/a[contains(@href, 'profile.php')]]",
                    "//div[.//a[contains(@href, 'profile.php')] and string-length(normalize-space(text())) > 30]",
                    "//div[contains(@class, 'async_like')]",
                    "//div[contains(@data-ft, 'comment')]"
                ]
            }
        else:
            # mbasic.facebook.com selectors
            return {
                'expand_links': [
                    "//a[contains(text(),'View more comments')]",
                    "//a[contains(text(),'View previous comments')]",
                    "//a[contains(text(),'View more replies')]",
                    "//a[contains(text(),'Show more')]",
                    "//a[contains(text(),'See more')]",
                    "//a[contains(text(),'Xem thêm')]",
                    "//a[contains(text(),'Hiển thị thêm')]",
                    "//a[contains(@href,'comment') and contains(text(),'more')]",
                    "//a[contains(@href,'reply') and contains(text(),'more')]"
                ],
                'comment_containers': [
                    # mbasic-specific comment selectors
                    "//div[@data-ft and contains(@data-ft, 'comment')]",
                    "//div[contains(@id, 'comment_')]",
                    "//div[.//a[contains(@href, 'profile.php?id=')]]",
                    "//div[.//a[contains(@href, 'user.php?id=')]]",
                    "//div[.//h3/a[contains(@href, 'profile.php')]]",
                    "//div[.//strong/a[contains(@href, 'profile.php')]]",
                    "//table//div[.//a[contains(@href, 'profile.php')]]",
                    "//div[.//a[contains(@href, 'facebook.com/')] and string-length(normalize-space(text())) > 25]"
                ]
            }

    def smart_expand_all(self, max_iterations=100):
        """Smart expansion that adapts to layout"""
        print(f"=== SMART EXPANSION for {self.facebook_layout} layout ===")
        
        selectors = self.get_layout_specific_selectors()
        expand_selectors = selectors['expand_links']
        
        iteration = 0
        no_expansion_count = 0
        total_expanded = 0
        
        while iteration < max_iterations and no_expansion_count < 6:
            if self._stop_flag:
                break
                
            iteration += 1
            expanded_this_round = 0
            
            print(f"[Iteration {iteration}] Searching for expand opportunities...")
            
            # Scroll to load more content
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(1.5, 2.5))
            
            # Find all expandable links
            all_expandable = []
            for selector in expand_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for elem in elements:
                        try:
                            if elem.is_displayed() and elem.is_enabled():
                                elem_text = elem.text.strip().lower()
                                # Validate that this is actually an expand link
                                if any(keyword in elem_text for keyword in 
                                      ['view', 'more', 'show', 'see', 'xem', 'thêm', 'hiển thị']):
                                    if elem not in all_expandable:
                                        all_expandable.append(elem)
                        except:
                            continue
                except:
                    continue
            
            print(f"  Found {len(all_expandable)} expandable elements")
            
            # Click each expandable element
            for i, elem in enumerate(all_expandable):
                if self._stop_flag:
                    break
                    
                try:
                    elem_text = elem.text.strip()
                    print(f"    Clicking {i+1}/{len(all_expandable)}: '{elem_text}'")
                    
                    # Scroll into view
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", elem)
                    time.sleep(1)
                    
                    # Try clicking
                    try:
                        elem.click()
                        expanded_this_round += 1
                        print(f"    ✓ Success")
                    except:
                        # Fallback to JavaScript click
                        self.driver.execute_script("arguments[0].click();", elem)
                        expanded_this_round += 1
                        print(f"    ✓ JS Success")
                    
                    time.sleep(random.uniform(2, 4))
                    
                except Exception as e:
                    print(f"    ✗ Failed: {e}")
                    continue
            
            total_expanded += expanded_this_round
            
            if expanded_this_round > 0:
                print(f"✓ Expanded {expanded_this_round} elements in iteration {iteration}")
                no_expansion_count = 0
            else:
                no_expansion_count += 1
                print(f"✗ No expansion in iteration {iteration} (consecutive: {no_expansion_count})")
        
        print(f"=== EXPANSION COMPLETE: {total_expanded} total expansions ===")

    def extract_comments_by_layout(self):
        """Extract comments using layout-specific logic"""
        print(f"=== EXTRACTING COMMENTS for {self.facebook_layout} layout ===")
        
        # Save page for debugging
        try:
            with open(f"debug_{self.facebook_layout}_page.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            print(f"Saved page source to debug_{self.facebook_layout}_page.html")
        except:
            pass
        
        selectors = self.get_layout_specific_selectors()
        comment_selectors = selectors['comment_containers']
        
        all_comment_elements = []
        
        # Collect all potential comment elements
        for i, selector in enumerate(comment_selectors):
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
                print(f"Selector {i+1}: Found {len(elements)} elements")
                
                for elem in elements:
                    if elem not in all_comment_elements:
                        all_comment_elements.append(elem)
                        
            except Exception as e:
                print(f"Selector {i+1} failed: {e}")
                continue

        print(f"Total unique comment elements: {len(all_comment_elements)}")
        
        if len(all_comment_elements) == 0:
            # Fallback: try very broad selectors
            print("⚠️ No comments found with standard selectors, trying fallback...")
            fallback_selectors = [
                "//div[.//a[contains(@href, 'facebook.com/')] and string-length(normalize-space(text())) > 20]",
                "//div[string-length(normalize-space(text())) > 50]",
                "//span[string-length(normalize-space(text())) > 30]/ancestor::div[1]",
                "//*[contains(text(), 'Like') or contains(text(), 'Reply')]/ancestor::div[string-length(text()) > 30][1]"
            ]
            
            for selector in fallback_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    print(f"Fallback selector: Found {len(elements)} elements")
                    for elem in elements:
                        if elem not in all_comment_elements:
                            all_comment_elements.append(elem)
                except:
                    continue
        
        # Sort by position
        try:
            all_comment_elements.sort(key=lambda x: (x.location['y'], x.location['x']))
        except:
            pass
        
        comments = []
        seen_content = set()
        
        # Process each element
        for i, element in enumerate(all_comment_elements):
            if self._stop_flag:
                break
                
            try:
                print(f"\n--- Processing element {i+1}/{len(all_comment_elements)} ---")
                
                comment_data = self.extract_comment_data(element, i)
                
                if not comment_data:
                    continue
                
                # Deduplication
                content_key = comment_data['Content'][:50]
                if content_key in seen_content:
                    print("  ✗ Skipped: duplicate content")
                    continue
                seen_content.add(content_key)
                
                # Determine type based on layout
                comment_type = self.determine_comment_type_by_layout(element, all_comment_elements, i)
                comment_data['Type'] = comment_type
                
                comments.append(comment_data)
                print(f"  ✓ Added {comment_type}: {comment_data['Name']} - {comment_data['Content'][:60]}...")
                
            except Exception as e:
                print(f"  Error processing element {i}: {e}")
                continue
        
        # Final organization
        comments = self.organize_comments(comments)
        
        print(f"\n=== EXTRACTION COMPLETE ===")
        main_count = len([c for c in comments if c['Type'] == 'Comment'])
        reply_count = len([c for c in comments if c['Type'] == 'Reply'])
        print(f"Results: {main_count} main comments + {reply_count} replies = {len(comments)} total")
        
        return comments

    def extract_comment_data(self, element, index):
        """Extract name, content, and metadata from comment element"""
        try:
            full_text = element.text.strip()
            if len(full_text) < 5:
                return None
            
            print(f"  Full text: '{full_text[:100]}...'")
            
            # Find profile links
            profile_links = element.find_elements(By.XPATH, ".//a[contains(@href, 'profile.php') or contains(@href, 'user.php') or contains(@href, '/profile/')]")
            
            username = "Unknown"
            profile_href = ""
            uid = "Unknown"
            
            # Extract name from profile links
            for link in profile_links[:3]:
                try:
                    link_text = link.text.strip()
                    link_href = link.get_attribute("href") or ""
                    
                    # Validate name
                    if (link_text and 
                        3 <= len(link_text) <= 100 and 
                        not link_text.startswith('http') and
                        not link_text.isdigit() and
                        not re.match(r'^\d+\s*(min|hour|day)', link_text, re.IGNORECASE)):
                        
                        username = link_text
                        profile_href = link_href
                        
                        # Extract UID
                        uid_match = re.search(r'profile\.php\?id=(\d+)', link_href)
                        if uid_match:
                            uid = uid_match.group(1)
                        break
                except:
                    continue
            
            # Extract content using layout-specific logic
            content = self.extract_content_by_layout(element, username, full_text)
            
            if not content or len(content) < 8 or self.is_ui_only(content):
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
            print(f"Error extracting comment data: {e}")
            return None

    def extract_content_by_layout(self, element, username, full_text):
        """Extract content using layout-specific strategies"""
        content_strategies = []
        
        # Strategy 1: Remove username from full text
        content = full_text
        if username != "Unknown":
            if content.startswith(username):
                content = content[len(username):].strip()
            content = re.sub(rf'\b{re.escape(username)}\b', '', content, count=1).strip()
        content_strategies.append(content)
        
        if self.facebook_layout == "mobile":
            # Mobile-specific content extraction
            try:
                # Look for div with data-sigil="comment-body"
                comment_body = element.find_elements(By.XPATH, ".//div[@data-sigil='comment-body']")
                for body in comment_body:
                    body_text = body.text.strip()
                    if body_text and body_text != username:
                        content_strategies.append(body_text)
            except:
                pass
            
            try:
                # Look for spans without links (pure content)
                content_spans = element.find_elements(By.XPATH, ".//span[not(.//a) and string-length(normalize-space(text())) > 15]")
                for span in content_spans:
                    span_text = span.text.strip()
                    if span_text and span_text != username:
                        content_strategies.append(span_text)
            except:
                pass
        
        else:
            # mbasic-specific content extraction
            try:
                # Look for div with dir="auto"
                dir_auto = element.find_elements(By.XPATH, ".//div[@dir='auto']")
                for div in dir_auto:
                    div_text = div.text.strip()
                    if div_text and div_text != username:
                        content_strategies.append(div_text)
            except:
                pass
        
        # Common strategies for both layouts
        try:
            # Look for text in divs without links
            text_divs = element.find_elements(By.XPATH, ".//div[not(.//a) and string-length(normalize-space(text())) > 15]")
            for div in text_divs:
                div_text = div.text.strip()
                if div_text and div_text != username:
                    content_strategies.append(div_text)
        except:
            pass
        
        # Choose best content
        valid_contents = []
        for strategy_content in content_strategies:
            cleaned = clean_text(strategy_content)
            if cleaned and len(cleaned) >= 8 and not self.is_ui_only(cleaned):
                valid_contents.append(cleaned)
        
        if not valid_contents:
            return ""
        
        # Return the longest valid content
        best_content = max(valid_contents, key=len)
        return best_content

    def determine_comment_type_by_layout(self, element, all_elements, index):
        """Determine comment type based on layout"""
        try:
            if self.facebook_layout == "mobile":
                # Mobile layout logic
                
                # Check data-sigil attribute
                data_sigil = element.get_attribute("data-sigil") or ""
                if "reply" in data_sigil.lower():
                    return "Reply"
                
                # Check for reply indicators in classes
                class_attr = element.get_attribute("class") or ""
                if any(indicator in class_attr.lower() for indicator in ["reply", "nested", "sub"]):
                    return "Reply"
                
                # Position-based detection for mobile
                try:
                    elem_location = element.location
                    
                    # Check previous elements for indentation comparison
                    for prev_index in range(max(0, index-5), index):
                        if prev_index < len(all_elements):
                            prev_elem = all_elements[prev_index]
                            try:
                                prev_location = prev_elem.location
                                # If significantly more indented than previous elements
                                if elem_location['x'] > prev_location['x'] + 25:
                                    return "Reply"
                            except:
                                continue
                except:
                    pass
            
            else:
                # mbasic layout logic
                
                # Check for table-based nesting (mbasic uses tables)
                try:
                    table_ancestors = element.find_elements(By.XPATH, "./ancestor::table")
                    nested_tables = element.find_elements(By.XPATH, ".//table")
                    
                    # If element is in a nested table structure, likely a reply
                    if len(table_ancestors) > 1 or len(nested_tables) > 0:
                        return "Reply"
                except:
                    pass
                
                # Check for indentation in mbasic
                try:
                    style = element.get_attribute("style") or ""
                    if "margin-left" in style or "padding-left" in style:
                        margin_match = re.search(r'margin-left:\s*(\d+)', style)
                        if margin_match and int(margin_match.group(1)) > 20:
                            return "Reply"
                except:
                    pass
            
            # Common logic for both layouts
            
            # Check DOM nesting depth
            try:
                comment_ancestors = element.find_elements(By.XPATH, 
                    "./ancestor::div[.//a[contains(@href,'profile.php')] and string-length(normalize-space(text())) > 30]")
                if len(comment_ancestors) > 0:
                    return "Reply"
            except:
                pass
            
            # Check for reply keywords in text
            try:
                elem_text = element.text.lower()
                reply_keywords = ['replied to', 'replying to', 'in reply to', 'trả lời', 'phản hồi', '@']
                if any(keyword in elem_text for keyword in reply_keywords):
                    return "Reply"
            except:
                pass
            
            # Default to main comment
            return "Comment"
            
        except Exception as e:
            print(f"Error determining comment type: {e}")
            return "Comment"

    def is_ui_only(self, text):
        """Check if text is just UI elements"""
        if not text or len(text.strip()) < 5:
            return True
        
        text_clean = text.lower().strip()
        
        # UI-only patterns
        ui_patterns = [
            r'^(like|reply|share|comment|translate|hide|report|block|thích|trả lời|chia sẻ)(\s+\d+)?\s*$',
            r'^\d+\s*(min|minutes?|hours?|days?|phút|giờ|ngày)\s*(ago|trước)?\s*$',
            r'^(top fan|most relevant|newest|all comments|view more|see more|xem thêm)\s*$',
            r'^\d+\s*(like|love|reaction|thích|yêu)\s*$',
            r'^(see translation|xem bản dịch)\s*$'
        ]
        
        for pattern in ui_patterns:
            if re.match(pattern, text_clean):
                return True
        
        # Just numbers or punctuation
        if re.match(r'^[\s\d\.\,\!\?\-\+\=\(\)]+$', text_clean):
            return True
        
        return False

    def organize_comments(self, comments):
        """Final organization and cleanup"""
        print("=== ORGANIZING COMMENTS ===")
        
        # Remove duplicates more aggressively
        unique_comments = []
        seen_combinations = set()
        
        for comment in comments:
            # Create multiple keys for deduplication
            keys = [
                f"{comment['Name']}_{comment['Content'][:30]}",
                f"{comment['Content'][:50]}",
                f"{comment['UID']}_{comment['Content'][:20]}" if comment['UID'] != "Unknown" else None
            ]
            
            is_duplicate = any(key in seen_combinations for key in keys if key)
            
            if not is_duplicate:
                unique_comments.append(comment)
                for key in keys:
                    if key:
                        seen_combinations.add(key)
        
        # Sort: Comments first, then replies, then by original order
        unique_comments.sort(key=lambda x: (
            x['Type'] == 'Reply',  # Comments first
            x.get('ElementIndex', 999)  # Then by order
        ))
        
        print(f"Organized: {len(unique_comments)} unique comments")
        return unique_comments

    def scrape_all_comments(self, limit=0, resolve_uid=True, progress_callback=None):
        """Main scraping method"""
        print(f"=== STARTING HYBRID SCRAPING for {self.facebook_layout} ===")
        
        # Step 1: Smart expansion
        self.smart_expand_all()
        
        if self._stop_flag:
            return []
        
        # Step 2: Extract comments
        comments = self.extract_comments_by_layout()
        
        # Step 3: Apply limit
        if limit > 0:
            comments = comments[:limit]
        
        # Step 4: Progress callback
        if progress_callback:
            progress_callback(len(comments))
        
        return comments

    def close(self):
        try: 
            self.driver.quit()
        except: 
            pass

# ----------------------------
# Enhanced GUI with Layout Detection
# ----------------------------
class FBCommentAppGUI:
    def __init__(self, root):
        self.root = root
        root.title("🔥 FB Hybrid Comment Scraper (mbasic + mobile)")
        root.geometry("1000x850")
        root.configure(bg="#f8f9fa")

        # Main frame
        main_frame = tk.Frame(root, bg="#f8f9fa")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # Title
        title_label = tk.Label(main_frame, text="🔥 Facebook Hybrid Comment Scraper", 
                              font=("Arial", 18, "bold"), bg="#f8f9fa", fg="#1877f2")
        title_label.pack(pady=(0,10))
        
        subtitle_label = tk.Label(main_frame, text="✨ Hỗ trợ cả mbasic.facebook.com và m.facebook.com", 
                                 font=("Arial", 10), bg="#f8f9fa", fg="#6c757d")
        subtitle_label.pack(pady=(0,20))

        # Input section
        input_frame = tk.LabelFrame(main_frame, text="📝 Thông tin đầu vào", font=("Arial", 12, "bold"), 
                                   bg="#f8f9fa", relief="groove", bd=2)
        input_frame.pack(fill="x", pady=(0,15))

        tk.Label(input_frame, text="🔗 Link bài viết Facebook:", bg="#f8f9fa", font=("Arial", 10)).pack(anchor="w", padx=15, pady=(15,5))
        self.entry_url = tk.Entry(input_frame, width=100, font=("Arial", 9))
        self.entry_url.pack(fill="x", padx=15, pady=(0,10))

        tk.Label(input_frame, text="🍪 Cookie (để đăng nhập):", bg="#f8f9fa", font=("Arial", 10)).pack(anchor="w", padx=15, pady=(5,5))
        self.txt_cookie = tk.Text(input_frame, height=4, font=("Arial", 8))
        self.txt_cookie.pack(fill="x", padx=15, pady=(0,15))

        # Options section
        options_frame = tk.LabelFrame(main_frame, text="⚙️ Tùy chọn", font=("Arial", 12, "bold"), 
                                     bg="#f8f9fa", relief="groove", bd=2)
        options_frame.pack(fill="x", pady=(0,15))
        
        opt_grid = tk.Frame(options_frame, bg="#f8f9fa")
        opt_grid.pack(fill="x", padx=15, pady=15)
        
        # Row 1
        tk.Label(opt_grid, text="📊 Giới hạn số lượng:", bg="#f8f9fa").grid(row=0, column=0, sticky="w")
        self.entry_limit = tk.Entry(opt_grid, width=10)
        self.entry_limit.insert(0, "0")
        self.entry_limit.grid(row=0, column=1, sticky="w", padx=(10,30))
        
        tk.Label(opt_grid, text="(0 = lấy tất cả)", bg="#f8f9fa", fg="#6c757d").grid(row=0, column=2, sticky="w")

        # Row 2
        self.headless_var = tk.BooleanVar(value=True)
        tk.Checkbutton(opt_grid, text="👻 Chạy ẩn (headless)", variable=self.headless_var, 
                      bg="#f8f9fa", font=("Arial", 9)).grid(row=1, column=0, sticky="w", pady=(10,0))

        self.resolve_uid_var = tk.BooleanVar(value=False)
        tk.Checkbutton(opt_grid, text="🆔 Lấy UID (chậm hơn)", variable=self.resolve_uid_var, 
                      bg="#f8f9fa", font=("Arial", 9)).grid(row=1, column=1, sticky="w", pady=(10,0))

        # File output section
        file_frame = tk.LabelFrame(main_frame, text="💾 File xuất kết quả", font=("Arial", 12, "bold"), 
                                  bg="#f8f9fa", relief="groove", bd=2)
        file_frame.pack(fill="x", pady=(0,15))
        
        file_row = tk.Frame(file_frame, bg="#f8f9fa")
        file_row.pack(fill="x", padx=15, pady=15)
        
        self.entry_file = tk.Entry(file_row, width=70, font=("Arial", 9))
        self.entry_file.insert(0, "facebook_comments_hybrid.xlsx")
        self.entry_file.pack(side="left", fill="x", expand=True)
        
        tk.Button(file_row, text="📁 Chọn file", command=self.choose_file, 
                 bg="#17a2b8", fg="white", font=("Arial", 9)).pack(side="right", padx=(10,0))

        # Status section
        status_frame = tk.LabelFrame(main_frame, text="📊 Trạng thái & Tiến độ", font=("Arial", 12, "bold"), 
                                    bg="#f8f9fa", relief="groove", bd=2)
        status_frame.pack(fill="x", pady=(0,15))
        
        self.lbl_status = tk.Label(status_frame, text="✅ Sẵn sàng để bắt đầu", fg="#28a745", 
                                  wraplength=900, justify="left", font=("Arial", 10), bg="#f8f9fa")
        self.lbl_status.pack(anchor="w", padx=15, pady=(15,5))

        self.lbl_progress_detail = tk.Label(status_frame, text="💡 Nhập link và cookie, sau đó nhấn 'Bắt đầu'. Scraper sẽ tự động detect layout Facebook.", 
                                          fg="#6c757d", wraplength=900, justify="left", font=("Arial", 9), bg="#f8f9fa")
        self.lbl_progress_detail.pack(anchor="w", padx=15, pady=(0,10))

        # Progress bar
        self.progress_bar = ttk.Progressbar(status_frame, mode='indeterminate')
        self.progress_bar.pack(fill="x", padx=15, pady=(0,15))

        # Control buttons
        button_frame = tk.Frame(main_frame, bg="#f8f9fa")
        button_frame.pack(fill="x", pady=20)
        
        self.btn_start = tk.Button(button_frame, text="🚀 Bắt đầu lấy dữ liệu", bg="#28a745", fg="white", 
                                  font=("Arial", 14, "bold"), command=self.start_scrape_thread, 
                                  pady=10, padx=30)
        self.btn_start.pack(side="left")

        self.btn_stop = tk.Button(button_frame, text="⏹️ Dừng lại", bg="#dc3545", fg="white", 
                                 font=("Arial", 14, "bold"), command=self.stop_scrape, 
                                 state=tk.DISABLED, pady=10, padx=30)
        self.btn_stop.pack(side="left", padx=(20,0))

        self.progress_var = tk.IntVar(value=0)
        self.progress_label = tk.Label(button_frame, textvariable=self.progress_var, fg="#28a745", 
                                     font=("Arial", 16, "bold"), bg="#f8f9fa")
        self.progress_label.pack(side="right")

        self._scrape_thread = None
        self._stop_flag = False
        self.scraper = None

    def choose_file(self):
        f = filedialog.asksaveasfilename(
            defaultextension=".xlsx", 
            filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv")],
            title="Chọn vị trí lưu file kết quả"
        )
        if f:
            self.entry_file.delete(0, tk.END)
            self.entry_file.insert(0, f)

    def start_scrape_thread(self):
        url = self.entry_url.get().strip()
        cookie_str = self.txt_cookie.get("1.0", tk.END).strip()
        file_out = self.entry_file.get().strip() or "facebook_comments_hybrid.xlsx"
        
        if not url:
            messagebox.showerror("❌ Lỗi", "Vui lòng nhập link bài viết Facebook.")
            return
        
        try: 
            limit = int(self.entry_limit.get().strip())
        except: 
            limit = 0

        self._stop_flag = False
        self.progress_var.set(0)
        self.progress_bar.start()
        self.lbl_status.config(text="🔄 Đang khởi động hybrid scraper...", fg="#fd7e14")
        self.lbl_progress_detail.config(text="⏳ Đang chuẩn bị trình duyệt và detect layout Facebook...")
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
        self.lbl_status.config(text="⏹️ Đang dừng quá trình...", fg="#dc3545")
        self.btn_stop.config(state=tk.DISABLED)

    def _progress_cb(self, count):
        self.progress_var.set(count)
        self.lbl_status.config(text=f"📈 Đang xử lý... Đã lấy được {count} comment/reply", fg="#28a745")
        self.root.update_idletasks()

    def _scrape_worker(self, url, cookie_str, file_out, limit, headless, resolve_uid):
        try:
            # Initialize
            self.lbl_status.config(text="🌐 Khởi tạo hybrid scraper...", fg="#fd7e14")
            self.scraper = FacebookHybridScraper(cookie_str, headless=headless)
            
            if self._stop_flag: return
            
            # Load post
            self.lbl_status.config(text="📄 Đang tải bài viết và detect layout...", fg="#fd7e14")
            self.lbl_progress_detail.config(text="⏳ Đang kết nối và phân tích layout Facebook...")
            success = self.scraper.load_post(url)
            
            if not success:
                self.lbl_status.config(text="❌ Không thể tải bài viết", fg="#dc3545")
                self.lbl_progress_detail.config(text="💡 Kiểm tra: Cookie có hợp lệ? Link có public? Thử tắt headless để debug")
                return
            
            # Show detected layout
            layout = self.scraper.facebook_layout
            self.lbl_progress_detail.config(text=f"🎯 Detected layout: {layout} - Đang tối ưu selectors...")
                
            if self._stop_flag: return
            
            # Scrape comments
            self.lbl_status.config(text=f"🔍 Đang lấy comment từ {layout} layout...", fg="#fd7e14")
            self.lbl_progress_detail.config(text="⏳ Đang mở rộng và phân tích comment structure...")
            
            comments = self.scraper.scrape_all_comments(limit=limit, resolve_uid=resolve_uid, 
                                                       progress_callback=self._progress_cb)
            
            if self._stop_flag: return
            
            # Save results
            self.lbl_status.config(text="💾 Đang lưu kết quả...", fg="#fd7e14")
            
            if comments:
                df = pd.DataFrame(comments)
                
                # Add helpful columns
                df.insert(0, 'STT', range(1, len(df) + 1))
                df['Layout'] = layout
                
                # Ensure proper file extension
                if not file_out.lower().endswith((".xlsx", ".csv")):
                    file_out += ".xlsx"
                
                # Save to file
                if file_out.lower().endswith(".csv"):
                    df.to_csv(file_out, index=False, encoding="utf-8-sig")
                else:
                    df.to_excel(file_out, index=False, engine="openpyxl")
                
                # Statistics
                comments_count = len([c for c in comments if c['Type'] == 'Comment'])
                replies_count = len([c for c in comments if c['Type'] == 'Reply'])
                unique_users = len(set(c['Name'] for c in comments if c['Name'] != 'Unknown'))
                avg_length = sum(len(c['Content']) for c in comments) // len(comments) if comments else 0
                
                self.lbl_status.config(text=f"🎉 THÀNH CÔNG! Đã lưu {len(comments)} comment/reply", fg="#28a745")
                self.lbl_progress_detail.config(text=f"📊 {comments_count} comment chính + {replies_count} reply | {unique_users} users | Layout: {layout} | Lưu: {file_out}")
                
            else:
                self.lbl_status.config(text="⚠️ Không tìm thấy comment", fg="#ffc107")
                self.lbl_progress_detail.config(text=f"💡 Layout detected: {layout} | Kiểm tra debug_{layout}_page.html | Thử tắt headless hoặc đổi cookie")
                
        except Exception as e:
            error_msg = str(e)[:100]
            self.lbl_status.config(text=f"❌ Lỗi: {error_msg}...", fg="#dc3545")
            self.lbl_progress_detail.config(text="🔍 Xem console để biết chi tiết lỗi")
            print(f"Detailed error: {e}")
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
    app = FBCommentAppGUI(root)
    root.mainloop()