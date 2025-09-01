# fb_comment_scraper_ultimate.py
import time, random, threading, re, requests, pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
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

def try_resolve_numeric_uid(profile_href, cookies_dict, timeout=6):
    if not profile_href:
        return None
    try:
        href = profile_href.replace("www.facebook.com", "mbasic.facebook.com")
        r = requests.get(href, cookies=cookies_dict, timeout=timeout, allow_redirects=True)
        html = r.text
        m = re.search(r"profile\.php\?id=(\d+)", html)
        if m: return m.group(1)
        m2 = re.search(r'"entity_id":"(\d+)"', html)
        if m2: return m2.group(1)
        parts = profile_href.rstrip('/').split('/')
        if parts: return parts[-1]
    except:
        return None
    return None

def clean_text(text):
    """Clean and normalize text content"""
    if not text:
        return ""
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text.strip())
    # Remove Facebook-specific UI elements
    text = re.sub(r'\b(Like|Reply|Share|Comment|Translate|See translation|Hide|Report|Block)\b', '', text)
    text = re.sub(r'\b(\d+\s*(minutes?|hours?|days?|seconds?|phút|giờ|ngày|giây)\s*(ago|trước)?)\b', '', text)
    text = re.sub(r'\b(Top fan|Most relevant|Newest|All comments|Bình luận hàng đầu)\b', '', text)
    # Remove reaction counts
    text = re.sub(r'\b\d+\s*(likes?|loves?|reactions?|thích|yêu thích)\b', '', text, flags=re.IGNORECASE)
    return text.strip()

# ----------------------------
# Ultimate Comment Scraper with Fixed Logic
# ----------------------------
class FacebookUltimateScraper:
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
        options.add_argument("user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 16_4 like Mac OS X) "
                             "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Mobile/15E148 Safari/604.1")
        options.add_argument("window-size=375,812")
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
        time.sleep(2)
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
        time.sleep(3)

    def load_post(self, post_url):
        self.post_url = ensure_mbasic_url(post_url)
        print(f"Loading post: {self.post_url}")
        
        try:
            self.driver.get(self.post_url)
            time.sleep(5)
            
            current_url = self.driver.current_url
            print(f"Current URL after load: {current_url}")
            
            page_title = self.driver.title
            print(f"Page title: {page_title}")
            
            if "Log in" in page_title or "Login" in page_title:
                print("ERROR: Not logged in! Check your cookies.")
                return False
            
            return True
                
        except Exception as e:
            print(f"Error loading post: {e}")
            return False

    def expand_all_comments_and_replies(self, max_attempts=150):
        print("=== EXPANDING COMMENTS & REPLIES ===")
        attempts = 0
        consecutive_no_finds = 0
        
        while attempts < max_attempts and consecutive_no_finds < 5:
            if self._stop_flag:
                break
                
            expanded = False
            attempts += 1
            print(f"[Attempt {attempts}] Looking for expand links...")

            # Scroll to bottom first
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(1.5, 2.5))

            # Comprehensive expand link selectors for mbasic Facebook
            expand_selectors = [
                # English
                "//a[contains(text(),'View more comments')]",
                "//a[contains(text(),'View previous comments')]", 
                "//a[contains(text(),'View more replies')]",
                "//a[contains(text(),'Show more')]",
                "//a[contains(text(),'See more')]",
                "//a[contains(text(),'More comments')]",
                "//a[contains(text(),'More replies')]",
                
                # Vietnamese
                "//a[contains(text(),'Xem thêm bình luận')]",
                "//a[contains(text(),'Xem thêm phản hồi')]",
                "//a[contains(text(),'Xem thêm')]",
                "//a[contains(text(),'Hiển thị thêm')]",
                
                # Generic patterns
                "//a[contains(@href,'comment') and (contains(text(),'more') or contains(text(),'thêm'))]",
                "//a[contains(@href,'reply') and (contains(text(),'more') or contains(text(),'thêm'))]",
                
                # Fallback - any clickable element with expand-like text
                "//*[self::a or self::div[@role='button']][contains(text(),'View') and contains(text(),'more')]",
                "//*[self::a or self::div[@role='button']][contains(text(),'Xem') and contains(text(),'thêm')]"
            ]

            all_expand_links = []
            for selector in expand_selectors:
                try:
                    links = self.driver.find_elements(By.XPATH, selector)
                    all_expand_links.extend(links)
                except:
                    continue

            # Remove duplicates and filter
            unique_links = []
            for link in all_expand_links:
                try:
                    if link.is_displayed() and link.is_enabled():
                        link_text = link.text.strip().lower()
                        # Skip if it's not actually an expand link
                        if any(keyword in link_text for keyword in ['view', 'more', 'show', 'see', 'xem', 'thêm', 'hiển thị']):
                            if link not in unique_links:
                                unique_links.append(link)
                except:
                    continue

            print(f"Found {len(unique_links)} unique expand links")

            if not unique_links:
                consecutive_no_finds += 1
                print(f"No expand links found (consecutive: {consecutive_no_finds})")
            else:
                consecutive_no_finds = 0

            for i, link in enumerate(unique_links):
                if self._stop_flag:
                    break
                    
                try:
                    link_text = link.text.strip()
                    print(f"  Clicking link {i+1}: '{link_text}'")
                    
                    # Scroll into view
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", link)
                    time.sleep(1)
                    
                    # Try to click
                    try:
                        link.click()
                    except:
                        # Fallback to JavaScript click
                        self.driver.execute_script("arguments[0].click();", link)
                    
                    print(f"  ✓ Successfully clicked: {link_text}")
                    expanded = True
                    time.sleep(random.uniform(2, 4))
                    
                except Exception as e:
                    print(f"  ✗ Failed to click link: {e}")
                    continue

            if expanded:
                print(f"✓ Expanded {len(unique_links)} links in attempt {attempts}")
            
            # If no expansion happened for several attempts, we're probably done
            if consecutive_no_finds >= 5:
                print("No more expand links found for several attempts. Stopping expansion.")
                break

        print("=== EXPANSION COMPLETE ===")
        
        # Final scroll to ensure everything is loaded
        for i in range(3):
            if self._stop_flag:
                break
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

    def extract_structured_comments(self):
        """Extract comments with proper hierarchical structure"""
        print("=== EXTRACTING STRUCTURED COMMENTS ===")
        
        # Save current page for debugging
        try:
            with open("debug_final_page.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            print("Saved final page to debug_final_page.html")
        except:
            pass
        
        comments = []
        seen_content = set()
        
        # Strategy: Find comment containers in hierarchical order
        # 1. First find all main comment containers
        main_comment_selectors = [
            # mbasic Facebook main comment patterns
            "//div[@data-ft and contains(@data-ft, 'comment_id') and not(ancestor::div[@data-ft and contains(@data-ft, 'comment_id')])]",
            "//div[contains(@id, 'comment_') and not(ancestor::div[contains(@id, 'comment_')])]",
            
            # Look for top-level comment structures
            "//div[.//h3/a[contains(@href, 'profile.php')] and not(ancestor::div[.//h3/a[contains(@href, 'profile.php')]])]",
            
            # Fallback: any div with profile link that's not nested in another comment-like div
            "//div[.//a[contains(@href, 'profile.php')] and string-length(normalize-space(text())) > 30 and not(ancestor::div[.//a[contains(@href, 'profile.php')] and string-length(normalize-space(text())) > 30])]"
        ]
        
        main_elements = []
        for selector in main_comment_selectors:
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
                for elem in elements:
                    if elem not in main_elements:
                        main_elements.append(elem)
            except:
                continue
        
        print(f"Found {len(main_elements)} potential main comment containers")
        
        # Process each main comment container
        for i, main_elem in enumerate(main_elements):
            if self._stop_flag:
                break
                
            try:
                print(f"\n--- Processing main container {i+1}/{len(main_elements)} ---")
                
                # Extract main comment
                main_comment = self.extract_single_comment(main_elem, is_main_comment=True)
                if main_comment and main_comment['Content'] not in seen_content:
                    main_comment['Type'] = 'Comment'
                    main_comment['Level'] = 0
                    comments.append(main_comment)
                    seen_content.add(main_comment['Content'])
                    print(f"  ✓ Added main comment: {main_comment['Name']}")
                
                # Look for replies within this main comment container
                reply_selectors = [
                    ".//div[@data-ft and contains(@data-ft, 'comment_id')]",
                    ".//div[.//a[contains(@href, 'profile.php')] and string-length(normalize-space(text())) > 20]"
                ]
                
                reply_elements = []
                for selector in reply_selectors:
                    try:
                        replies = main_elem.find_elements(By.XPATH, selector)
                        for reply_elem in replies:
                            # Make sure it's not the main comment itself
                            if reply_elem != main_elem and reply_elem not in reply_elements:
                                reply_elements.append(reply_elem)
                    except:
                        continue
                
                print(f"  Found {len(reply_elements)} potential replies in this container")
                
                # Process replies
                for j, reply_elem in enumerate(reply_elements):
                    if self._stop_flag:
                        break
                        
                    try:
                        reply_comment = self.extract_single_comment(reply_elem, is_main_comment=False)
                        if reply_comment and reply_comment['Content'] not in seen_content:
                            # Additional validation for replies
                            if self.is_likely_reply(reply_elem, main_elem):
                                reply_comment['Type'] = 'Reply'
                                reply_comment['Level'] = 1
                                comments.append(reply_comment)
                                seen_content.add(reply_comment['Content'])
                                print(f"    ✓ Added reply {j+1}: {reply_comment['Name']}")
                            else:
                                print(f"    ✗ Skipped (not a valid reply): {reply_comment['Name']}")
                    except Exception as e:
                        print(f"    Error processing reply {j}: {e}")
                        continue
                        
            except Exception as e:
                print(f"Error processing main container {i}: {e}")
                continue
        
        print(f"\n=== EXTRACTION COMPLETE ===")
        print(f"Total extracted: {len(comments)}")
        
        # Final statistics
        main_comments = [c for c in comments if c['Type'] == 'Comment']
        replies = [c for c in comments if c['Type'] == 'Reply']
        print(f"Main comments: {len(main_comments)}")
        print(f"Replies: {len(replies)}")
        
        return comments

    def extract_single_comment(self, element, is_main_comment=True):
        """Extract name, content, and profile from a single comment element"""
        try:
            full_text = element.text.strip()
            if not full_text or len(full_text) < 3:
                return None
            
            # Find profile links
            profile_links = element.find_elements(By.XPATH, ".//a[contains(@href, 'profile.php') or contains(@href, 'user.php')]")
            
            username = "Unknown"
            profile_href = ""
            uid = "Unknown"
            
            # Get the first valid profile link (usually the commenter)
            for link in profile_links[:3]:
                try:
                    link_text = link.text.strip()
                    link_href = link.get_attribute("href") or ""
                    
                    # Validate that this looks like a real name
                    if (link_text and 
                        len(link_text) > 1 and 
                        len(link_text) < 100 and 
                        not link_text.startswith('http') and
                        not link_text.isdigit()):
                        
                        username = link_text
                        profile_href = link_href
                        
                        # Extract UID
                        uid_match = re.search(r'profile\.php\?id=(\d+)', link_href)
                        if uid_match:
                            uid = uid_match.group(1)
                        else:
                            # For username-based profiles, try to resolve
                            try:
                                uid = try_resolve_numeric_uid(profile_href, self.cookies_dict) or "Unknown"
                            except:
                                uid = "Unknown"
                        break
                except:
                    continue
            
            # Extract content
            content = self.extract_comment_content(element, username)
            
            if not content or len(content) < 5:
                return None
            
            # Skip obvious UI elements
            if self.is_ui_element(content):
                return None
            
            return {
                "UID": uid,
                "Name": username,
                "Content": content,
                "ProfileLink": profile_href,
                "ContentLength": len(content)
            }
            
        except Exception as e:
            print(f"Error extracting single comment: {e}")
            return None

    def extract_comment_content(self, element, username):
        """Extract clean comment content, removing name and UI elements"""
        try:
            full_text = element.text.strip()
            
            # Remove username from beginning
            if username != "Unknown" and full_text.startswith(username):
                content = full_text[len(username):].strip()
            else:
                content = full_text
            
            # Try to find content in specific sub-elements
            content_candidates = []
            
            # Look for text in divs that don't contain links (likely pure content)
            content_divs = element.find_elements(By.XPATH, ".//div[not(.//a) and string-length(normalize-space(text())) > 10]")
            for div in content_divs:
                try:
                    div_text = div.text.strip()
                    if div_text and div_text != username:
                        content_candidates.append(div_text)
                except:
                    continue
            
            # Look for spans with substantial text
            content_spans = element.find_elements(By.XPATH, ".//span[string-length(normalize-space(text())) > 15]")
            for span in content_spans:
                try:
                    span_text = span.text.strip()
                    if span_text and span_text != username and not span_text.startswith('http'):
                        content_candidates.append(span_text)
                except:
                    continue
            
            # Choose the best content
            if content_candidates:
                # Pick the longest meaningful content
                best_content = max(content_candidates, key=len)
                if len(best_content) > len(content):
                    content = best_content
            
            # Final cleaning
            content = clean_text(content)
            
            # Remove username again if it still appears
            if username != "Unknown":
                content = re.sub(rf'^.*?{re.escape(username)}\s*', '', content, count=1)
                content = content.replace(username, "").strip()
            
            return content
            
        except Exception as e:
            print(f"Error extracting content: {e}")
            return ""

    def is_likely_reply(self, reply_element, main_element):
        """Check if an element is likely a reply to the main comment"""
        try:
            # Check if reply element is spatially contained within main element
            main_location = main_element.location
            main_size = main_element.size
            reply_location = reply_element.location
            
            # Reply should be below and possibly indented
            if reply_location['y'] <= main_location['y']:
                return False
            
            # Reply should be within the main comment's horizontal bounds (with some tolerance)
            main_right = main_location['x'] + main_size['width']
            reply_right = reply_location['x'] + reply_element.size['width']
            
            # Check for indentation (reply should be more to the right)
            if reply_location['x'] > main_location['x'] + 10:  # At least 10px indentation
                return True
            
            # Check DOM hierarchy
            try:
                # If reply element is a descendant of main element
                ancestors = reply_element.find_elements(By.XPATH, "./ancestor::*")
                if main_element in ancestors:
                    return True
            except:
                pass
            
            return False
            
        except Exception as e:
            print(f"Error checking if reply: {e}")
            return False

    def is_ui_element(self, text):
        """Check if text is just a UI element, not actual comment content"""
        if not text:
            return True
            
        text_lower = text.lower().strip()
        
        # UI-only patterns
        ui_patterns = [
            r'^(like|reply|share|comment|translate|hide|report|block)(\s+\d+)?\s*$',
            r'^\d+\s*(min|minutes?|hours?|days?|seconds?|phút|giờ|ngày|giây)\s*(ago|trước)?\s*$',
            r'^(top fan|most relevant|newest|all comments|bình luận hàng đầu)\s*$',
            r'^\d+\s*(likes?|loves?|reactions?|thích|yêu thích)\s*$',
            r'^(see translation|xem bản dịch)\s*$',
            r'^(view more|show more|see more|xem thêm|hiển thị thêm)\s*$'
        ]
        
        for pattern in ui_patterns:
            if re.match(pattern, text_lower):
                return True
        
        # Too short to be meaningful
        if len(text) < 8:
            return True
            
        # Just numbers or special characters
        if re.match(r'^[\d\s\.\,\!\?\-\+\=\(\)]+$', text):
            return True
            
        return False

    def scrape_all_comments(self, limit=0, resolve_uid=True, progress_callback=None):
        """Main scraping method with improved logic"""
        print("=== STARTING ULTIMATE COMMENT SCRAPING ===")
        
        # Expand everything first
        self.expand_all_comments_and_replies()
        
        if self._stop_flag:
            return []
        
        # Extract with proper structure
        comments = self.extract_structured_comments()
        
        # Apply limit if specified
        if limit > 0:
            comments = comments[:limit]
        
        # Final validation and cleanup
        validated_comments = []
        for comment in comments:
            if (comment['Content'] and 
                len(comment['Content']) >= 5 and 
                not self.is_ui_element(comment['Content'])):
                validated_comments.append(comment)
                
                if progress_callback:
                    progress_callback(len(validated_comments))
        
        print(f"Final validated comments: {len(validated_comments)}")
        return validated_comments

    def close(self):
        try: 
            self.driver.quit()
        except: 
            pass

# ----------------------------
# Enhanced GUI with Better Status Display
# ----------------------------
class FBCommentAppGUI:
    def __init__(self, root):
        self.root = root
        root.title("FB Ultimate Comment & Reply Scraper")
        root.geometry("950x750")

        frame = tk.Frame(root)
        frame.pack(padx=15, pady=10, fill=tk.BOTH, expand=True)

        # URL input
        tk.Label(frame, text="🔗 Link bài viết:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w")
        self.entry_url = tk.Entry(frame, width=90, font=("Arial", 9))
        self.entry_url.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0,8))

        # Cookie input
        tk.Label(frame, text="🍪 Cookie:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="w")
        self.txt_cookie = tk.Text(frame, height=4, width=90, font=("Arial", 8))
        self.txt_cookie.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0,8))

        # Options frame
        options_frame = tk.LabelFrame(frame, text="⚙️ Tùy chọn", font=("Arial", 9, "bold"))
        options_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0,8), padx=5)
        
        tk.Label(options_frame, text="Giới hạn số lượng (0 = tất cả):").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.entry_limit = tk.Entry(options_frame, width=12)
        self.entry_limit.insert(0, "0")
        self.entry_limit.grid(row=0, column=1, sticky="w", padx=(5,20), pady=5)

        self.headless_var = tk.BooleanVar(value=False)
        tk.Checkbutton(options_frame, text="Chạy ẩn (headless)", variable=self.headless_var).grid(row=0, column=2, sticky="w", padx=5, pady=5)

        self.resolve_uid_var = tk.BooleanVar(value=True)
        tk.Checkbutton(options_frame, text="Lấy UID", variable=self.resolve_uid_var).grid(row=0, column=3, sticky="w", padx=5, pady=5)

        # File output
        tk.Label(frame, text="💾 File lưu kết quả:", font=("Arial", 10, "bold")).grid(row=5, column=0, sticky="w")
        file_frame = tk.Frame(frame)
        file_frame.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(0,8))
        
        self.entry_file = tk.Entry(file_frame, width=70, font=("Arial", 9))
        self.entry_file.insert(0, "facebook_comments_ultimate.xlsx")
        self.entry_file.grid(row=0, column=0, sticky="ew")
        tk.Button(file_frame, text="Chọn...", command=self.choose_file).grid(row=0, column=1, sticky="w", padx=(5,0))
        
        file_frame.columnconfigure(0, weight=1)

        # Status display
        status_frame = tk.LabelFrame(frame, text="📊 Trạng thái", font=("Arial", 9, "bold"))
        status_frame.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(8,0), padx=5)
        
        self.lbl_status = tk.Label(status_frame, text="Sẵn sàng để bắt đầu", fg="blue", 
                                  wraplength=800, justify="left", font=("Arial", 9))
        self.lbl_status.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        self.lbl_progress_detail = tk.Label(status_frame, text="", fg="green", 
                                          wraplength=800, justify="left", font=("Arial", 8))
        self.lbl_progress_detail.grid(row=1, column=0, sticky="ew", padx=10, pady=(0,5))

        # Control buttons
        button_frame = tk.Frame(frame)
        button_frame.grid(row=8, column=0, columnspan=3, sticky="ew", pady=15)
        
        self.btn_start = tk.Button(button_frame, text="🚀 Bắt đầu lấy dữ liệu", bg="#28a745", fg="white", 
                                  font=("Arial", 10, "bold"), command=self.start_scrape_thread)
        self.btn_start.grid(row=0, column=0, sticky="w")

        self.btn_stop = tk.Button(button_frame, text="⏹️ Dừng lại", bg="#dc3545", fg="white", 
                                 font=("Arial", 10, "bold"), command=self.stop_scrape, state=tk.DISABLED)
        self.btn_stop.grid(row=0, column=1, padx=(15,0), sticky="w")

        self.progress_var = tk.IntVar(value=0)
        self.progress_label = tk.Label(button_frame, textvariable=self.progress_var, fg="green", 
                                     font=("Arial", 12, "bold"))
        self.progress_label.grid(row=0, column=2, padx=(30,0), sticky="e")
        
        button_frame.columnconfigure(2, weight=1)
        frame.columnconfigure(0, weight=1)

        self._scrape_thread = None
        self._stop_flag = False
        self.scraper = None

    def choose_file(self):
        f = filedialog.asksaveasfilename(
            defaultextension=".xlsx", 
            filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv")],
            title="Chọn file để lưu kết quả"
        )
        if f:
            self.entry_file.delete(0, tk.END)
            self.entry_file.insert(0, f)

    def start_scrape_thread(self):
        url = self.entry_url.get().strip()
        cookie_str = self.txt_cookie.get("1.0", tk.END).strip()
        file_out = self.entry_file.get().strip() or "facebook_comments_ultimate.xlsx"
        
        if not url:
            messagebox.showerror("Thiếu thông tin", "Vui lòng nhập link bài viết.")
            return
        
        if not cookie_str:
            result = messagebox.askyesno("Thiếu cookie", 
                                       "Không có cookie. Bạn có muốn thử không dùng cookie không? (Có thể bị hạn chế)")
            if not result:
                return
        
        try: 
            limit = int(self.entry_limit.get().strip())
        except: 
            limit = 0

        self._stop_flag = False
        self.progress_var.set(0)
        self.lbl_status.config(text="🔄 Đang khởi động scraper nâng cao...", fg="orange")
        self.lbl_progress_detail.config(text="")
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
        self.lbl_status.config(text="⏹️ Đang dừng...", fg="red")
        self.btn_stop.config(state=tk.DISABLED)

    def _progress_cb(self, count):
        self.progress_var.set(count)
        self.lbl_status.config(text=f"📈 Đang xử lý... Đã lấy được {count} comment/reply", fg="green")
        self.root.update_idletasks()

    def _scrape_worker(self, url, cookie_str, file_out, limit, headless, resolve_uid):
        try:
            self.lbl_status.config(text="🌐 Khởi tạo trình duyệt...", fg="orange")
            self.scraper = FacebookUltimateScraper(cookie_str, headless=headless)
            
            if self._stop_flag: return
            
            self.lbl_status.config(text="📄 Đang tải bài viết...", fg="orange")
            success = self.scraper.load_post(url)
            
            if not success:
                self.lbl_status.config(text="❌ Lỗi: Không thể tải bài viết hoặc chưa đăng nhập", fg="red")
                self.lbl_progress_detail.config(text="💡 Kiểm tra: 1) Cookie có đúng không, 2) Link có hợp lệ không, 3) Tài khoản có bị khóa không")
                return
                
            if self._stop_flag: return
            
            self.lbl_status.config(text="🔄 Đang mở rộng tất cả comment và reply...", fg="orange")
            self.lbl_progress_detail.config(text="⏳ Quá trình này có thể mất vài phút tùy thuộc vào số lượng comment...")
            
            comments = self.scraper.scrape_all_comments(limit=limit, resolve_uid=resolve_uid, 
                                                       progress_callback=self._progress_cb)
            
            if self._stop_flag: return
            
            self.lbl_status.config(text="💾 Đang lưu dữ liệu...", fg="orange")
            
            if comments:
                df = pd.DataFrame(comments)
                
                # Ensure proper file extension
                if not file_out.lower().endswith((".xlsx", ".csv")):
                    file_out += ".xlsx"
                
                # Save to appropriate format
                if file_out.lower().endswith(".csv"):
                    df.to_csv(file_out, index=False, encoding="utf-8-sig")
                else:
                    df.to_excel(file_out, index=False, engine="openpyxl")
                
                # Calculate statistics
                comments_count = len([c for c in comments if c['Type'] == 'Comment'])
                replies_count = len([c for c in comments if c['Type'] == 'Reply'])
                total_chars = sum(len(c['Content']) for c in comments)
                avg_length = total_chars // len(comments) if comments else 0
                
                self.lbl_status.config(text=f"✅ HOÀN THÀNH! Đã lưu vào {file_out}", fg="green")
                self.lbl_progress_detail.config(text=f"📊 Kết quả: {comments_count} comment chính + {replies_count} reply | Độ dài TB: {avg_length} ký tự")
                
            else:
                self.lbl_status.config(text="⚠️ Không tìm thấy comment nào", fg="red")
                self.lbl_progress_detail.config(text="💡 Thử: 1) Kiểm tra link có public không, 2) Thử tắt headless, 3) Kiểm tra debug_final_page.html")
                
        except Exception as e:
            self.lbl_status.config(text=f"❌ Lỗi: {str(e)[:100]}...", fg="red")
            self.lbl_progress_detail.config(text="🔍 Xem console để biết chi tiết lỗi")
            print(f"Detailed error: {e}")
            import traceback
            traceback.print_exc()
        finally:
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