# fb_comment_scraper_fixed.py
import time, random, threading, re, requests, pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

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
    text = re.sub(r'\b(\d+\s*(minutes?|hours?|days?|seconds?)\s*ago)\b', '', text)
    text = re.sub(r'\b(Top fan|Most relevant|Newest|All comments)\b', '', text)
    return text.strip()

# ----------------------------
# Fixed Advanced Comment Scraper
# ----------------------------
class FacebookAdvancedScraper:
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
        self.cookie_str = cookie_str or ""
        self.cookies_list = parse_cookies_to_list(self.cookie_str)
        self.cookies_dict = parse_cookies_to_dict(self.cookie_str)
        self.is_mobile_version = False
        
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
            
            # Detect Facebook version
            if "m.facebook.com" in current_url:
                print("On mobile version (m.facebook.com)")
                self.is_mobile_version = True
            elif "mbasic.facebook.com" in current_url:
                print("On mbasic version")
                self.is_mobile_version = False
            
            # Check accessibility
            page_title = self.driver.title
            print(f"Page title: {page_title}")
            
            if "Log in" in page_title or "Login" in page_title:
                print("ERROR: Not logged in! Check your cookies.")
                return False
            
            return True
                
        except Exception as e:
            print(f"Error loading post: {e}")
            return False

    def expand_all_comments_and_replies(self, max_attempts=100):
        print("=== EXPANDING COMMENTS & REPLIES ===")
        attempts = 0
        while attempts < max_attempts:
            expanded = False
            attempts += 1
            print(f"[Attempt {attempts}] scrolling and checking for expand links...")

            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(2, 3))

            # Tìm tất cả các link expand khác nhau
            expand_selectors = [
                "//a[contains(text(),'View more comments')]",
                "//a[contains(text(),'View previous comments')]", 
                "//a[contains(text(),'View more replies')]",
                "//a[contains(text(),'Show more')]",
                "//a[contains(text(),'See more')]",
                "//a[contains(text(),'Xem thêm')]",
                "//a[contains(text(),'Xem bình luận')]",
                "//a[contains(text(),'Xem phản hồi')]",
                "//div[contains(text(),'See more')]/parent::*",
                "//span[contains(text(),'View') and contains(text(),'more')]/ancestor::a[1]"
            ]

            all_expand_links = []
            for selector in expand_selectors:
                try:
                    links = self.driver.find_elements(By.XPATH, selector)
                    all_expand_links.extend(links)
                except:
                    continue

            # Remove duplicates
            unique_links = []
            for link in all_expand_links:
                if link not in unique_links:
                    unique_links.append(link)

            for link in unique_links:
                try:
                    if link.is_displayed() and link.is_enabled():
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", link)
                        time.sleep(0.5)
                        self.driver.execute_script("arguments[0].click();", link)
                        print(f"✓ Clicked expand link: {link.text.strip()}")
                        expanded = True
                        time.sleep(random.uniform(2, 4))
                except Exception as e:
                    print(f"Failed to click link: {e}")
                    continue

            if not expanded:
                print("No more expand links found.")
                break

        print("=== EXPANSION DONE ===")
    
        # Final scroll to make sure everything is loaded
        for i in range(5):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

    def extract_comment_details(self, element):
        """Improved extraction with better comment/reply detection"""
        try:
            # Get all text first
            full_text = element.text.strip()
            if not full_text or len(full_text) < 3:
                return None
                
            print(f"  Processing element with text: '{full_text[:100]}...'")
            
            # Find name links (profile links)
            name_links = element.find_elements(By.XPATH, ".//a[contains(@href, 'profile.php') or contains(@href, 'user.php') or contains(@href, '/profile/')]")
            
            username = "Unknown"
            profile_href = ""
            uid = "Unknown"
            
            # Get the first valid name link
            for link in name_links[:2]:  # Check first 2 links
                try:
                    link_text = link.text.strip()
                    link_href = link.get_attribute("href") or ""
                    
                    if link_text and len(link_text) < 100 and len(link_text) > 1:
                        # This looks like a valid name
                        username = link_text
                        profile_href = link_href
                        
                        # Try to extract UID from href
                        uid_match = re.search(r'profile\.php\?id=(\d+)', link_href)
                        if uid_match:
                            uid = uid_match.group(1)
                        else:
                            # Try to resolve UID
                            try:
                                uid = try_resolve_numeric_uid(profile_href, self.cookies_dict) or "Unknown"
                            except:
                                uid = "Unknown"
                        break
                except:
                    continue
            
            # Extract content by removing name and UI elements
            content = full_text
            
            # Remove username from content
            if username != "Unknown" and username in content:
                content = content.replace(username, "", 1).strip()
            
            # Clean content
            content = clean_text(content)
            
            # Skip if no meaningful content
            if not content or len(content) < 5:
                return None
                
            # Skip UI-only elements
            ui_patterns = [
                r'^(Like|Reply|Share|Comment|Translate)(\s+\d+)?\s*$',
                r'^\d+\s*(min|minutes?|hours?|days?|giây|phút|giờ|ngày)\s*(ago|trước)\s*$',
                r'^(Top fan|Most relevant|Newest|All comments)\s*$'
            ]
            
            for pattern in ui_patterns:
                if re.match(pattern, content, re.IGNORECASE):
                    return None
            
            # Determine if this is a main comment or reply
            comment_type = self.determine_comment_type(element)
            
            return {
                "Type": comment_type,
                "UID": uid,
                "Name": username,
                "Content": content,
                "ProfileLink": profile_href,
                "ContentLength": len(content)
            }
            
        except Exception as e:
            print(f"  Error extracting comment details: {e}")
            return None

    def determine_comment_type(self, element):
        """Determine if element is a main comment or reply based on structure"""
        try:
            # Method 1: Check indentation/margin styles
            style = element.get_attribute("style") or ""
            if "margin-left" in style or "padding-left" in style:
                # Extract margin/padding value
                margin_match = re.search(r'margin-left:\s*(\d+)', style)
                padding_match = re.search(r'padding-left:\s*(\d+)', style)
                
                if margin_match and int(margin_match.group(1)) > 20:
                    return "Reply"
                if padding_match and int(padding_match.group(1)) > 20:
                    return "Reply"
            
            # Method 2: Check CSS classes that indicate replies
            class_attr = element.get_attribute("class") or ""
            reply_indicators = ["reply", "nested", "indent", "sub"]
            if any(indicator in class_attr.lower() for indicator in reply_indicators):
                return "Reply"
            
            # Method 3: Check DOM structure depth
            # Count parent elements with comment-like characteristics
            try:
                comment_ancestors = element.find_elements(By.XPATH, 
                    "./ancestor::div[contains(@class,'comment') or contains(@data-ft,'comment') or .//a[contains(@href,'profile.php')]]")
                
                if len(comment_ancestors) > 1:  # If nested inside another comment structure
                    return "Reply"
            except:
                pass
            
            # Method 4: Check if element is within a "replies" container
            try:
                reply_containers = element.find_elements(By.XPATH, 
                    "./ancestor::div[contains(text(),'repl') or contains(@class,'repl') or contains(@id,'repl')]")
                if reply_containers:
                    return "Reply"
            except:
                pass
            
            # Method 5: Position-based detection
            try:
                # Get element's position
                location = element.location
                size = element.size
                
                # Check if there are comments above this one at a similar or less indented position
                all_comments_above = self.driver.find_elements(By.XPATH, 
                    f"//div[position() < position() and .//a[contains(@href,'profile.php')]]")
                
                for above_comment in all_comments_above[-5:]:  # Check last 5 comments above
                    try:
                        above_location = above_comment.location
                        # If this element is significantly more to the right, it's likely a reply
                        if location['x'] > above_location['x'] + 30:
                            return "Reply"
                    except:
                        continue
                        
            except:
                pass
            
            # Default to main comment
            return "Comment"
            
        except Exception as e:
            print(f"Error determining comment type: {e}")
            return "Comment"

    def scrape_all_comments(self, limit=0, resolve_uid=True, progress_callback=None):
        print("=== STARTING IMPROVED COMMENT SCRAPING ===")
        
        # First expand all comments and replies
        self.expand_all_comments_and_replies()
        
        comments = []
        seen = set()
        
        # Save page source for debugging
        try:
            with open("debug_expanded_page.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            print("Saved expanded page source to debug_expanded_page.html")
        except:
            pass

        # Improved selectors targeting Facebook's comment structure
        comment_selectors = [
            # Primary selectors for mbasic Facebook
            "//div[@data-ft and contains(@data-ft, 'comment')]",
            "//div[.//a[contains(@href, 'profile.php?id=')]]",
            "//div[.//a[contains(@href, 'user.php?id=')]]",
            
            # Secondary selectors for different layouts
            "//div[@role='article']",
            "//article",
            "//div[h3//a[contains(@href, 'profile.php')]]",
            "//div[h3//a[contains(@href, 'user.php')]]",
            
            # Content-based selectors
            "//div[.//a[contains(@href, 'facebook.com/')] and string-length(normalize-space(text())) > 30]",
            "//div[contains(@class, 'comment') or contains(@id, 'comment')]",
            
            # Fallback selectors
            "//div[string-length(normalize-space(text())) > 50 and .//a[contains(@href, 'profile')]]",
            "//span[string-length(normalize-space(text())) > 30]/ancestor::div[.//a[contains(@href, 'profile')]][1]"
        ]

        all_potential_elements = []
        
        # Collect all potential comment elements
        for i, selector in enumerate(comment_selectors):
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
                print(f"Selector {i+1}: Found {len(elements)} elements")
                
                # Add unique elements only
                for elem in elements:
                    # Check if element is already in the list
                    is_duplicate = False
                    for existing_elem in all_potential_elements:
                        try:
                            if elem == existing_elem:
                                is_duplicate = True
                                break
                        except:
                            continue
                    
                    if not is_duplicate:
                        all_potential_elements.append(elem)
                        
            except Exception as e:
                print(f"Selector {i+1} failed: {e}")
                continue

        print(f"Total unique potential comment elements: {len(all_potential_elements)}")

        # Sort elements by their position on page (top to bottom, left to right)
        try:
            all_potential_elements.sort(key=lambda elem: (elem.location['y'], elem.location['x']))
        except:
            pass

        # Process each potential comment element
        for i, element in enumerate(all_potential_elements):
            try:
                if limit and len(comments) >= limit:
                    break
                    
                if self._stop_flag if hasattr(self, '_stop_flag') else False:
                    break

                print(f"\n--- Processing element {i+1}/{len(all_potential_elements)} ---")
                
                # Extract comment details
                comment_data = self.extract_comment_details(element)
                
                if not comment_data:
                    print("  Skipping: no valid comment data")
                    continue
                
                # Deduplication based on name + content
                dedupe_key = f"{comment_data['Name'][:30]}_{comment_data['Content'][:50]}"
                if dedupe_key in seen:
                    print("  Skipping: duplicate")
                    continue
                seen.add(dedupe_key)
                
                # Additional validation
                if len(comment_data['Content']) < 8:
                    print(f"  Skipping: content too short ({len(comment_data['Content'])} chars)")
                    continue
                
                comments.append(comment_data)
                print(f"  ✓ ADDED {comment_data['Type'].upper()} #{len(comments)}")
                print(f"    Name: {comment_data['Name']}")
                print(f"    Content: {comment_data['Content'][:80]}...")
                
                if progress_callback:
                    progress_callback(len(comments))
                    
            except Exception as e:
                print(f"  Error processing element {i}: {e}")
                continue

        print(f"\n=== SCRAPING COMPLETE ===")
        print(f"Total comments and replies extracted: {len(comments)}")
        
        # Count and display statistics
        comments_count = len([c for c in comments if c['Type'] == 'Comment'])
        replies_count = len([c for c in comments if c['Type'] == 'Reply'])
        print(f"Main Comments: {comments_count}")
        print(f"Replies: {replies_count}")
        
        # Sort comments: main comments first, then replies
        comments.sort(key=lambda x: (x['Type'] == 'Reply', x['Name']))
        
        return comments

    def close(self):
        try: 
            self.driver.quit()
        except: 
            pass

# ----------------------------
# Enhanced GUI with better feedback
# ----------------------------
class FBCommentAppGUI:
    def __init__(self, root):
        self.root = root
        root.title("FB Advanced Comment & Reply Scraper (Fixed)")
        root.geometry("900x700")

        frame = tk.Frame(root)
        frame.pack(padx=12, pady=8, fill=tk.BOTH, expand=True)

        tk.Label(frame, text="Link bài viết:").grid(row=0, column=0, sticky="w")
        self.entry_url = tk.Entry(frame, width=90)
        self.entry_url.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0,5))

        tk.Label(frame, text="Cookie:").grid(row=2, column=0, sticky="w")
        self.txt_cookie = tk.Text(frame, height=4, width=90)
        self.txt_cookie.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0,8))

        # Options frame
        options_frame = tk.Frame(frame)
        options_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0,8))
        
        tk.Label(options_frame, text="Số lượng comment (0 = all):").grid(row=0, column=0, sticky="w")
        self.entry_limit = tk.Entry(options_frame, width=12)
        self.entry_limit.insert(0, "0")
        self.entry_limit.grid(row=0, column=1, sticky="w", padx=(5,20))

        self.headless_var = tk.BooleanVar(value=False)
        tk.Checkbutton(options_frame, text="Chạy headless", variable=self.headless_var).grid(row=0, column=2, sticky="w")

        self.resolve_uid_var = tk.BooleanVar(value=True)
        tk.Checkbutton(options_frame, text="Resolve UID", variable=self.resolve_uid_var).grid(row=0, column=3, sticky="w")

        tk.Label(frame, text="File lưu (Excel):").grid(row=5, column=0, sticky="w")
        file_frame = tk.Frame(frame)
        file_frame.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(0,8))
        
        self.entry_file = tk.Entry(file_frame, width=70)
        self.entry_file.grid(row=0, column=0, sticky="ew")
        tk.Button(file_frame, text="Chọn...", command=self.choose_file).grid(row=0, column=1, sticky="w", padx=(5,0))
        
        file_frame.columnconfigure(0, weight=1)

        # Status and progress display
        self.lbl_status = tk.Label(frame, text="Status: Ready", fg="blue", wraplength=800, justify="left")
        self.lbl_status.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(8,4))

        # Progress details
        self.lbl_progress_detail = tk.Label(frame, text="", fg="green", wraplength=800, justify="left")
        self.lbl_progress_detail.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(0,4))

        # Buttons and progress
        button_frame = tk.Frame(frame)
        button_frame.grid(row=9, column=0, columnspan=3, sticky="ew", pady=8)
        
        self.btn_start = tk.Button(button_frame, text="Start Scrape", bg="#28a745", fg="white", 
                                  command=self.start_scrape_thread)
        self.btn_start.grid(row=0, column=0, sticky="w")

        self.btn_stop = tk.Button(button_frame, text="Stop", bg="#dc3545", fg="white", 
                                 command=self.stop_scrape, state=tk.DISABLED)
        self.btn_stop.grid(row=0, column=1, padx=(10,0), sticky="w")

        self.progress_var = tk.IntVar(value=0)
        self.progress_label = tk.Label(button_frame, textvariable=self.progress_var, fg="green")
        self.progress_label.grid(row=0, column=2, padx=(20,0), sticky="e")
        
        button_frame.columnconfigure(2, weight=1)
        frame.columnconfigure(0, weight=1)

        self._scrape_thread = None
        self._stop_flag = False
        self.scraper = None

    def choose_file(self):
        f = filedialog.asksaveasfilename(defaultextension=".xlsx", 
                                       filetypes=[("Excel files", "*.xlsx")])
        if f:
            self.entry_file.delete(0, tk.END)
            self.entry_file.insert(0, f)

    def start_scrape_thread(self):
        url = self.entry_url.get().strip()
        cookie_str = self.txt_cookie.get("1.0", tk.END).strip()
        file_out = self.entry_file.get().strip() or "fb_comments_fixed.xlsx"
        
        if not url:
            messagebox.showerror("Missing input", "Vui lòng nhập link bài viết.")
            return
        
        try: 
            limit = int(self.entry_limit.get().strip())
        except: 
            limit = 0

        self._stop_flag = False
        self.progress_var.set(0)
        self.lbl_status.config(text="Starting improved scraper...", fg="orange")
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
        self.lbl_status.config(text="Stopping...", fg="red")
        self.btn_stop.config(state=tk.DISABLED)

    def _progress_cb(self, count):
        self.progress_var.set(count)
        self.lbl_status.config(text=f"Đã lấy {count} comment/reply...", fg="green")
        self.root.update_idletasks()

    def _scrape_worker(self, url, cookie_str, file_out, limit, headless, resolve_uid):
        try:
            self.lbl_status.config(text="Khởi tạo trình duyệt...", fg="orange")
            self.scraper = FacebookAdvancedScraper(cookie_str, headless=headless)
            self.scraper._stop_flag = False
            
            if self._stop_flag: return
            
            self.lbl_status.config(text="Tải bài viết...", fg="orange")
            success = self.scraper.load_post(url)
            
            if not success:
                self.lbl_status.config(text="Lỗi: Không thể tải bài viết hoặc chưa đăng nhập", fg="red")
                return
                
            if self._stop_flag: return
            
            self.lbl_status.config(text="Mở rộng tất cả comment và reply...", fg="orange")
            comments = self.scraper.scrape_all_comments(limit=limit, resolve_uid=resolve_uid, 
                                                       progress_callback=self._progress_cb)
            
            if self._stop_flag: return
            
            self.lbl_status.config(text="Lưu dữ liệu...", fg="orange")
            
            if comments:
                df = pd.DataFrame(comments)
                if not file_out.lower().endswith(".xlsx"):
                    file_out += ".xlsx"
                    
                # Sort by Type (Comments first, then Replies) and then by order
                df = df.sort_values(['Type', 'Name'])
                df.to_excel(file_out, index=False, engine="openpyxl")
                
                comments_count = len([c for c in comments if c['Type'] == 'Comment'])
                replies_count = len([c for c in comments if c['Type'] == 'Reply'])
                
                self.lbl_status.config(text=f"THÀNH CÔNG! Lưu vào {file_out}", fg="green")
                self.lbl_progress_detail.config(text=f"📊 Kết quả: {comments_count} comment chính + {replies_count} reply")
            else:
                self.lbl_status.config(text="Không tìm thấy comment. Kiểm tra debug_expanded_page.html", fg="red")
                self.lbl_progress_detail.config(text="💡 Thử: 1) Kiểm tra cookie, 2) Thử link khác, 3) Tắt headless mode")
                
        except Exception as e:
            self.lbl_status.config(text=f"Lỗi: {e}", fg="red")
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