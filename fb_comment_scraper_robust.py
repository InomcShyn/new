# fb_comment_scraper_robust.py - Version with robust comment/reply detection
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

def ensure_mbasic_url(url):
    if "mbasic.facebook.com" in url:
        return url
    url = url.replace("www.facebook.com", "mbasic.facebook.com")
    url = url.replace("m.facebook.com", "mbasic.facebook.com")
    return url

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text.strip())
    # Remove UI elements but be more conservative
    ui_keywords = ['Like', 'Reply', 'Share', 'Comment', 'Translate', 'Hide', 'Report', 'Block']
    for keyword in ui_keywords:
        # Only remove if it's a standalone word, not part of actual content
        text = re.sub(rf'\b{keyword}\b(?=\s|$)', '', text)
    
    # Remove timestamps
    text = re.sub(r'\b\d+\s*(min|minutes?|hours?|days?|seconds?|phút|giờ|ngày|giây)\s*(ago|trước)?\b', '', text, flags=re.IGNORECASE)
    return text.strip()

# ----------------------------
# Robust Comment Scraper
# ----------------------------
class FacebookRobustScraper:
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
        
        # Use mobile user agent for better mbasic compatibility
        options.add_argument("user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) "
                             "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1")
        options.add_argument("window-size=414,896")
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        self.wait = WebDriverWait(self.driver, 10)
        self.cookie_str = cookie_str or ""
        self.cookies_list = parse_cookies_to_list(self.cookie_str)
        self.cookies_dict = parse_cookies_to_dict(self.cookie_str)
        self._stop_flag = False
        
        if self.cookies_list:
            self._login_with_cookies()

    def _login_with_cookies(self):
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
            except: pass
        self.driver.get("https://mbasic.facebook.com")
        time.sleep(4)

    def load_post(self, post_url):
        self.post_url = ensure_mbasic_url(post_url)
        print(f"Loading post: {self.post_url}")
        
        try:
            self.driver.get(self.post_url)
            time.sleep(6)
            
            page_title = self.driver.title
            print(f"Page title: {page_title}")
            
            if any(keyword in page_title.lower() for keyword in ["log in", "login", "đăng nhập"]):
                print("ERROR: Not logged in!")
                return False
            
            # Check if we can see any comment-like content
            try:
                comment_indicators = self.driver.find_elements(By.XPATH, 
                    "//div[contains(text(),'comment') or contains(text(),'bình luận') or .//a[contains(@href,'profile.php')]]")
                if comment_indicators:
                    print(f"✓ Found {len(comment_indicators)} comment indicators on page")
                    return True
                else:
                    print("⚠️ No comment indicators found, but proceeding...")
                    return True
            except:
                return True
                
        except Exception as e:
            print(f"Error loading post: {e}")
            return False

    def smart_expand_comments(self, max_iterations=200):
        """Smart expansion that handles both comments and replies"""
        print("=== SMART COMMENT EXPANSION ===")
        
        iteration = 0
        no_expansion_count = 0
        
        while iteration < max_iterations and no_expansion_count < 8:
            if self._stop_flag:
                break
                
            iteration += 1
            expanded_this_round = False
            
            print(f"[Iteration {iteration}] Searching for expand opportunities...")
            
            # Scroll to bottom to load more content
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(1, 2))
            
            # Comprehensive search for expandable elements
            expand_patterns = [
                # Direct text matches
                "//a[contains(text(),'View more comments')]",
                "//a[contains(text(),'View previous comments')]",
                "//a[contains(text(),'View more replies')]", 
                "//a[contains(text(),'Show more comments')]",
                "//a[contains(text(),'Show more replies')]",
                "//a[contains(text(),'See more')]",
                
                # Vietnamese
                "//a[contains(text(),'Xem thêm bình luận')]",
                "//a[contains(text(),'Xem thêm phản hồi')]",
                "//a[contains(text(),'Hiển thị thêm')]",
                "//a[contains(text(),'Xem thêm')]",
                
                # Pattern-based
                "//a[contains(@href,'comment') and (contains(text(),'more') or contains(text(),'thêm') or contains(text(),'View'))]",
                "//a[contains(@href,'reply') and (contains(text(),'more') or contains(text(),'thêm') or contains(text(),'View'))]",
                
                # Fallback patterns
                "//*[self::a or @role='button'][contains(text(),'View') and (contains(text(),'more') or contains(text(),'comment') or contains(text(),'repl'))]",
                "//*[self::a or @role='button'][contains(text(),'Xem') and contains(text(),'thêm')]"
            ]
            
            all_expandable = []
            for pattern in expand_patterns:
                try:
                    elements = self.driver.find_elements(By.XPATH, pattern)
                    for elem in elements:
                        if elem not in all_expandable and elem.is_displayed() and elem.is_enabled():
                            all_expandable.append(elem)
                except:
                    continue
            
            print(f"  Found {len(all_expandable)} expandable elements")
            
            # Click each expandable element
            successful_clicks = 0
            for i, elem in enumerate(all_expandable):
                if self._stop_flag:
                    break
                    
                try:
                    elem_text = elem.text.strip()
                    print(f"    Attempting to click {i+1}/{len(all_expandable)}: '{elem_text}'")
                    
                    # Scroll element into view
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", elem)
                    time.sleep(0.8)
                    
                    # Try clicking
                    try:
                        elem.click()
                        successful_clicks += 1
                        expanded_this_round = True
                        print(f"    ✓ Clicked successfully")
                    except:
                        # Fallback to JavaScript click
                        self.driver.execute_script("arguments[0].click();", elem)
                        successful_clicks += 1
                        expanded_this_round = True
                        print(f"    ✓ JS clicked successfully")
                    
                    # Wait between clicks
                    time.sleep(random.uniform(1.5, 3))
                    
                except Exception as e:
                    print(f"    ✗ Failed to click: {e}")
                    continue
            
            if expanded_this_round:
                print(f"✓ Successfully expanded {successful_clicks} elements in iteration {iteration}")
                no_expansion_count = 0
            else:
                no_expansion_count += 1
                print(f"✗ No expansion in iteration {iteration} (consecutive: {no_expansion_count})")
            
            # Break if we haven't found anything to expand for several iterations
            if no_expansion_count >= 8:
                print("No expansion opportunities found for several iterations. Stopping.")
                break
        
        print(f"=== EXPANSION COMPLETE after {iteration} iterations ===")

    def parse_comment_hierarchy(self):
        """Parse comments into a proper hierarchy"""
        print("=== PARSING COMMENT HIERARCHY ===")
        
        # Save page source for debugging
        try:
            with open("debug_hierarchy_page.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            print("Saved page source to debug_hierarchy_page.html")
        except:
            pass
        
        comments = []
        processed_elements = set()
        
        # Find all potential comment containers
        # Strategy: Look for elements that contain profile links and substantial text
        comment_containers = []
        
        selectors_to_try = [
            # Most specific first
            "//div[@data-ft and contains(@data-ft, 'comment')]",
            "//div[contains(@class, 'comment')]",
            "//div[contains(@id, 'comment')]",
            
            # Profile-link based
            "//div[.//a[contains(@href, 'profile.php?id=')]]",
            "//div[.//a[contains(@href, 'user.php?id=')]]",
            "//div[.//h3/a[contains(@href, 'profile.php')]]",
            
            # Content-based fallback
            "//div[.//a[contains(@href, 'facebook.com/')] and string-length(normalize-space(text())) > 25]"
        ]
        
        for selector in selectors_to_try:
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
                for elem in elements:
                    if elem not in comment_containers:
                        comment_containers.append(elem)
            except:
                continue
        
        print(f"Found {len(comment_containers)} potential comment containers")
        
        # Sort by position (top to bottom)
        try:
            comment_containers.sort(key=lambda x: (x.location['y'], x.location['x']))
        except:
            pass
        
        # Process each container
        for i, container in enumerate(comment_containers):
            if self._stop_flag:
                break
                
            try:
                # Skip if already processed
                if id(container) in processed_elements:
                    continue
                
                print(f"\n--- Container {i+1}/{len(comment_containers)} ---")
                
                # Extract comment data
                comment_data = self.extract_comment_from_container(container)
                
                if not comment_data:
                    continue
                
                # Determine if this is a main comment or reply
                comment_type = self.determine_comment_type_advanced(container, comment_containers)
                comment_data['Type'] = comment_type
                comment_data['ContainerIndex'] = i
                
                # Check for duplicates
                is_duplicate = any(
                    existing['Name'] == comment_data['Name'] and 
                    existing['Content'] == comment_data['Content']
                    for existing in comments
                )
                
                if not is_duplicate:
                    comments.append(comment_data)
                    processed_elements.add(id(container))
                    print(f"  ✓ Added {comment_type}: {comment_data['Name']} - {comment_data['Content'][:60]}...")
                else:
                    print(f"  ✗ Skipped duplicate")
                    
            except Exception as e:
                print(f"  Error processing container {i}: {e}")
                continue
        
        # Post-processing: Final cleanup and organization
        cleaned_comments = self.post_process_comments(comments)
        
        print(f"\n=== HIERARCHY PARSING COMPLETE ===")
        main_count = len([c for c in cleaned_comments if c['Type'] == 'Comment'])
        reply_count = len([c for c in cleaned_comments if c['Type'] == 'Reply'])
        print(f"Final result: {main_count} main comments + {reply_count} replies = {len(cleaned_comments)} total")
        
        return cleaned_comments

    def extract_comment_from_container(self, container):
        """Extract clean comment data from a container element"""
        try:
            full_text = container.text.strip()
            if len(full_text) < 5:
                return None
            
            # Find profile links
            profile_links = container.find_elements(By.XPATH, ".//a[contains(@href, 'profile.php') or contains(@href, 'user.php')]")
            
            username = "Unknown"
            profile_href = ""
            uid = "Unknown"
            
            # Get the best profile link (usually the first one)
            for link in profile_links[:2]:
                try:
                    link_text = link.text.strip()
                    link_href = link.get_attribute("href") or ""
                    
                    # Validate name
                    if (link_text and 
                        2 <= len(link_text) <= 80 and 
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
            
            # Extract content using multiple strategies
            content = self.extract_content_smart(container, username, full_text)
            
            if not content or len(content) < 5 or self.is_ui_only_element(content):
                return None
            
            return {
                "UID": uid,
                "Name": username,
                "Content": content,
                "ProfileLink": profile_href,
                "ContentLength": len(content),
                "FullText": full_text[:200]  # For debugging
            }
            
        except Exception as e:
            print(f"Error extracting from container: {e}")
            return None

    def extract_content_smart(self, container, username, full_text):
        """Smart content extraction with multiple fallback strategies"""
        content_candidates = []
        
        # Strategy 1: Remove username and common prefixes
        content = full_text
        if username != "Unknown":
            # Remove username from start
            if content.startswith(username):
                content = content[len(username):].strip()
            # Remove username anywhere with word boundaries
            content = re.sub(rf'\b{re.escape(username)}\b', '', content, count=1).strip()
        
        content_candidates.append(content)
        
        # Strategy 2: Look for text nodes that don't contain links
        try:
            text_divs = container.find_elements(By.XPATH, ".//div[not(.//a) and string-length(normalize-space(text())) > 10]")
            for div in text_divs:
                div_text = div.text.strip()
                if div_text and div_text != username:
                    content_candidates.append(div_text)
        except:
            pass
        
        # Strategy 3: Look for spans with meaningful content
        try:
            text_spans = container.find_elements(By.XPATH, ".//span[string-length(normalize-space(text())) > 15 and not(.//a)]")
            for span in text_spans:
                span_text = span.text.strip()
                if span_text and span_text != username:
                    content_candidates.append(span_text)
        except:
            pass
        
        # Strategy 4: Look for elements with dir="auto" (often comment content)
        try:
            dir_auto_elements = container.find_elements(By.XPATH, ".//*[@dir='auto' and string-length(normalize-space(text())) > 10]")
            for elem in dir_auto_elements:
                elem_text = elem.text.strip()
                if elem_text and elem_text != username:
                    content_candidates.append(elem_text)
        except:
            pass
        
        # Choose the best content
        if not content_candidates:
            return ""
        
        # Filter and rank candidates
        valid_candidates = []
        for candidate in content_candidates:
            cleaned = clean_text(candidate)
            if cleaned and len(cleaned) >= 5 and not self.is_ui_only_element(cleaned):
                valid_candidates.append(cleaned)
        
        if not valid_candidates:
            return ""
        
        # Return the longest valid candidate (usually the most complete)
        best_content = max(valid_candidates, key=len)
        return best_content

    def determine_comment_type_advanced(self, container, all_containers):
        """Advanced logic to determine if element is main comment or reply"""
        try:
            container_location = container.location
            container_size = container.size
            
            # Method 1: Check indentation/positioning
            # Replies are typically indented (more to the right)
            base_x_positions = []
            for other_container in all_containers[:20]:  # Sample first 20
                try:
                    if other_container != container:
                        base_x_positions.append(other_container.location['x'])
                except:
                    continue
            
            if base_x_positions:
                min_x = min(base_x_positions)
                avg_x = sum(base_x_positions) / len(base_x_positions)
                
                # If this element is significantly more indented, it's likely a reply
                if container_location['x'] > avg_x + 20:
                    return "Reply"
                if container_location['x'] > min_x + 30:
                    return "Reply"
            
            # Method 2: Check DOM nesting level
            try:
                # Count how many comment-like ancestors this element has
                comment_ancestors = container.find_elements(By.XPATH, 
                    "./ancestor::div[.//a[contains(@href,'profile.php')] and string-length(normalize-space(text())) > 30]")
                
                if len(comment_ancestors) > 0:
                    return "Reply"
            except:
                pass
            
            # Method 3: Check for reply-specific indicators in nearby text
            try:
                container_text = container.text.lower()
                reply_indicators = ['replied to', 'replying to', 'in reply to', 'trả lời', 'phản hồi']
                if any(indicator in container_text for indicator in reply_indicators):
                    return "Reply"
            except:
                pass
            
            # Method 4: Size-based heuristic (replies are often shorter)
            try:
                if container_size['width'] < 300:  # Narrow elements might be replies
                    return "Reply"
            except:
                pass
            
            # Default to main comment
            return "Comment"
            
        except Exception as e:
            print(f"Error determining comment type: {e}")
            return "Comment"

    def is_ui_only_element(self, text):
        """Check if text represents only UI elements"""
        if not text or len(text.strip()) < 3:
            return True
        
        text_clean = text.lower().strip()
        
        # Exact UI matches
        ui_exact = [
            'like', 'reply', 'share', 'comment', 'translate', 'hide', 'report', 'block',
            'thích', 'trả lời', 'chia sẻ', 'bình luận', 'dịch', 'ẩn', 'báo cáo', 'chặn',
            'top fan', 'most relevant', 'newest', 'all comments',
            'see translation', 'xem bản dịch', 'view more', 'xem thêm'
        ]
        
        if text_clean in ui_exact:
            return True
        
        # Pattern matches
        ui_patterns = [
            r'^\d+\s*(like|thích|love|yêu)\s*$',
            r'^\d+\s*(min|minutes?|hours?|days?|phút|giờ|ngày)\s*(ago|trước)?\s*$',
            r'^(like|reply|share|comment)(\s+\d+)?\s*$',
            r'^view\s+(more|previous)\s+(comment|reply)',
            r'^xem\s+thêm\s+(bình luận|phản hồi)'
        ]
        
        for pattern in ui_patterns:
            if re.match(pattern, text_clean):
                return True
        
        # Too short or just punctuation
        if len(text_clean) < 8 or re.match(r'^[\s\d\.\,\!\?\-\+\(\)]+$', text_clean):
            return True
        
        return False

    def post_process_comments(self, comments):
        """Final cleanup and organization of comments"""
        print("=== POST-PROCESSING COMMENTS ===")
        
        cleaned_comments = []
        seen_combinations = set()
        
        for comment in comments:
            # Create a unique key for deduplication
            dedupe_key = f"{comment['Name'][:20]}_{comment['Content'][:30]}"
            
            if dedupe_key in seen_combinations:
                continue
            seen_combinations.add(dedupe_key)
            
            # Final content validation
            if (comment['Content'] and 
                len(comment['Content']) >= 8 and 
                not self.is_ui_only_element(comment['Content'])):
                
                cleaned_comments.append(comment)
        
        # Sort: main comments first, then replies, then by position
        cleaned_comments.sort(key=lambda x: (
            x['Type'] == 'Reply',  # Comments first, then replies
            x.get('ContainerIndex', 999)  # Then by original order
        ))
        
        print(f"Post-processing complete: {len(cleaned_comments)} final comments")
        return cleaned_comments

    def scrape_all_comments(self, limit=0, resolve_uid=True, progress_callback=None):
        """Main scraping orchestrator"""
        print("=== STARTING ROBUST COMMENT SCRAPING ===")
        
        # Step 1: Expand all content
        self.smart_expand_comments()
        
        if self._stop_flag:
            return []
        
        # Step 2: Parse hierarchy
        comments = self.parse_comment_hierarchy()
        
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
# Enhanced GUI
# ----------------------------
class FBCommentAppGUI:
    def __init__(self, root):
        self.root = root
        root.title("🔥 FB Robust Comment & Reply Scraper")
        root.geometry("1000x800")
        root.configure(bg="#f0f0f0")

        # Main frame with padding
        main_frame = tk.Frame(root, bg="#f0f0f0")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # Title
        title_label = tk.Label(main_frame, text="🔥 Facebook Comment & Reply Scraper", 
                              font=("Arial", 16, "bold"), bg="#f0f0f0", fg="#1877f2")
        title_label.pack(pady=(0,20))

        # Input section
        input_frame = tk.LabelFrame(main_frame, text="📝 Thông tin đầu vào", font=("Arial", 11, "bold"), bg="#f0f0f0")
        input_frame.pack(fill="x", pady=(0,15))

        tk.Label(input_frame, text="🔗 Link bài viết Facebook:", bg="#f0f0f0").pack(anchor="w", padx=10, pady=(10,5))
        self.entry_url = tk.Entry(input_frame, width=100, font=("Arial", 9))
        self.entry_url.pack(fill="x", padx=10, pady=(0,10))

        tk.Label(input_frame, text="🍪 Cookie (để đăng nhập):", bg="#f0f0f0").pack(anchor="w", padx=10, pady=(5,5))
        self.txt_cookie = tk.Text(input_frame, height=4, font=("Arial", 8))
        self.txt_cookie.pack(fill="x", padx=10, pady=(0,15))

        # Options section
        options_frame = tk.LabelFrame(main_frame, text="⚙️ Tùy chọn", font=("Arial", 11, "bold"), bg="#f0f0f0")
        options_frame.pack(fill="x", pady=(0,15))
        
        opt_row1 = tk.Frame(options_frame, bg="#f0f0f0")
        opt_row1.pack(fill="x", padx=10, pady=10)
        
        tk.Label(opt_row1, text="Giới hạn số lượng (0 = tất cả):", bg="#f0f0f0").pack(side="left")
        self.entry_limit = tk.Entry(opt_row1, width=10)
        self.entry_limit.insert(0, "0")
        self.entry_limit.pack(side="left", padx=(10,30))

        self.headless_var = tk.BooleanVar(value=True)
        tk.Checkbutton(opt_row1, text="Chạy ẩn (nhanh hơn)", variable=self.headless_var, bg="#f0f0f0").pack(side="left", padx=(0,20))

        self.resolve_uid_var = tk.BooleanVar(value=False)
        tk.Checkbutton(opt_row1, text="Lấy UID (chậm hơn)", variable=self.resolve_uid_var, bg="#f0f0f0").pack(side="left")

        # File output section
        file_frame = tk.LabelFrame(main_frame, text="💾 File xuất", font=("Arial", 11, "bold"), bg="#f0f0f0")
        file_frame.pack(fill="x", pady=(0,15))
        
        file_row = tk.Frame(file_frame, bg="#f0f0f0")
        file_row.pack(fill="x", padx=10, pady=10)
        
        self.entry_file = tk.Entry(file_row, width=70, font=("Arial", 9))
        self.entry_file.insert(0, "facebook_comments_robust.xlsx")
        self.entry_file.pack(side="left", fill="x", expand=True)
        
        tk.Button(file_row, text="📁 Chọn file", command=self.choose_file, 
                 bg="#17a2b8", fg="white").pack(side="right", padx=(10,0))

        # Status section
        status_frame = tk.LabelFrame(main_frame, text="📊 Trạng thái & Tiến độ", font=("Arial", 11, "bold"), bg="#f0f0f0")
        status_frame.pack(fill="x", pady=(0,15))
        
        self.lbl_status = tk.Label(status_frame, text="✅ Sẵn sàng để bắt đầu", fg="#28a745", 
                                  wraplength=900, justify="left", font=("Arial", 10), bg="#f0f0f0")
        self.lbl_status.pack(anchor="w", padx=15, pady=(10,5))

        self.lbl_progress_detail = tk.Label(status_frame, text="💡 Nhập link và cookie, sau đó nhấn 'Bắt đầu'", 
                                          fg="#6c757d", wraplength=900, justify="left", font=("Arial", 9), bg="#f0f0f0")
        self.lbl_progress_detail.pack(anchor="w", padx=15, pady=(0,10))

        # Progress bar
        self.progress_bar = ttk.Progressbar(status_frame, mode='indeterminate')
        self.progress_bar.pack(fill="x", padx=15, pady=(0,10))

        # Control buttons
        button_frame = tk.Frame(main_frame, bg="#f0f0f0")
        button_frame.pack(fill="x", pady=15)
        
        self.btn_start = tk.Button(button_frame, text="🚀 Bắt đầu lấy dữ liệu", bg="#28a745", fg="white", 
                                  font=("Arial", 12, "bold"), command=self.start_scrape_thread, 
                                  pady=8, padx=20)
        self.btn_start.pack(side="left")

        self.btn_stop = tk.Button(button_frame, text="⏹️ Dừng lại", bg="#dc3545", fg="white", 
                                 font=("Arial", 12, "bold"), command=self.stop_scrape, 
                                 state=tk.DISABLED, pady=8, padx=20)
        self.btn_stop.pack(side="left", padx=(20,0))

        self.progress_var = tk.IntVar(value=0)
        self.progress_label = tk.Label(button_frame, textvariable=self.progress_var, fg="#28a745", 
                                     font=("Arial", 14, "bold"), bg="#f0f0f0")
        self.progress_label.pack(side="right")

        self._scrape_thread = None
        self._stop_flag = False
        self.scraper = None

    def choose_file(self):
        f = filedialog.asksaveasfilename(
            defaultextension=".xlsx", 
            filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv")],
            title="Chọn vị trí lưu file"
        )
        if f:
            self.entry_file.delete(0, tk.END)
            self.entry_file.insert(0, f)

    def start_scrape_thread(self):
        url = self.entry_url.get().strip()
        cookie_str = self.txt_cookie.get("1.0", tk.END).strip()
        file_out = self.entry_file.get().strip() or "facebook_comments_robust.xlsx"
        
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
        self.lbl_status.config(text="🔄 Đang khởi động scraper...", fg="#fd7e14")
        self.lbl_progress_detail.config(text="⏳ Đang chuẩn bị trình duyệt và đăng nhập...")
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
            self.lbl_status.config(text="🌐 Khởi tạo trình duyệt...", fg="#fd7e14")
            self.scraper = FacebookRobustScraper(cookie_str, headless=headless)
            
            if self._stop_flag: return
            
            # Load post
            self.lbl_status.config(text="📄 Đang tải bài viết Facebook...", fg="#fd7e14")
            self.lbl_progress_detail.config(text="⏳ Đang kết nối và tải nội dung bài viết...")
            success = self.scraper.load_post(url)
            
            if not success:
                self.lbl_status.config(text="❌ Không thể tải bài viết", fg="#dc3545")
                self.lbl_progress_detail.config(text="💡 Kiểm tra: Cookie có đúng? Link có public? Tài khoản có bị khóa?")
                return
                
            if self._stop_flag: return
            
            # Scrape comments
            self.lbl_status.config(text="🔍 Đang lấy tất cả comment và reply...", fg="#fd7e14")
            self.lbl_progress_detail.config(text="⏳ Đang mở rộng và phân tích cấu trúc comment... Quá trình này có thể mất vài phút.")
            
            comments = self.scraper.scrape_all_comments(limit=limit, resolve_uid=resolve_uid, 
                                                       progress_callback=self._progress_cb)
            
            if self._stop_flag: return
            
            # Save results
            self.lbl_status.config(text="💾 Đang lưu kết quả...", fg="#fd7e14")
            
            if comments:
                df = pd.DataFrame(comments)
                
                # Add index column for easier tracking
                df.insert(0, 'STT', range(1, len(df) + 1))
                
                # Ensure proper file extension
                if not file_out.lower().endswith((".xlsx", ".csv")):
                    file_out += ".xlsx"
                
                # Save to file
                if file_out.lower().endswith(".csv"):
                    df.to_csv(file_out, index=False, encoding="utf-8-sig")
                else:
                    df.to_excel(file_out, index=False, engine="openpyxl")
                
                # Calculate and display statistics
                comments_count = len([c for c in comments if c['Type'] == 'Comment'])
                replies_count = len([c for c in comments if c['Type'] == 'Reply'])
                total_chars = sum(len(c['Content']) for c in comments)
                avg_length = total_chars // len(comments) if comments else 0
                unique_users = len(set(c['Name'] for c in comments))
                
                self.lbl_status.config(text=f"🎉 HOÀN THÀNH! Đã lưu {len(comments)} comment/reply vào {file_out}", fg="#28a745")
                self.lbl_progress_detail.config(text=f"📊 Chi tiết: {comments_count} comment chính + {replies_count} reply | {unique_users} người dùng | TB: {avg_length} ký tự/comment")
                
            else:
                self.lbl_status.config(text="⚠️ Không tìm thấy comment nào", fg="#ffc107")
                self.lbl_progress_detail.config(text="💡 Có thể do: Bài viết không có comment, không có quyền truy cập, hoặc cấu trúc trang đã thay đổi")
                
        except Exception as e:
            error_msg = str(e)[:150]
            self.lbl_status.config(text=f"❌ Lỗi: {error_msg}...", fg="#dc3545")
            self.lbl_progress_detail.config(text="🔍 Xem console/terminal để biết chi tiết lỗi")
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