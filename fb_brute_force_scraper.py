# fb_brute_force_scraper.py - Brute force approach for stubborn Facebook pages
import time, random, threading, re, requests, pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
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

def is_likely_comment_content(text):
    """Check if text looks like actual comment content"""
    if not text or len(text) < 8:
        return False
    
    text_lower = text.lower().strip()
    
    # Skip obvious UI elements
    ui_patterns = [
        r'^(like|reply|share|comment|translate|hide|report|block)(\s+\d+)?\s*$',
        r'^(thích|trả lời|chia sẻ|bình luận|dịch|ẩn|báo cáo|chặn)(\s+\d+)?\s*$',
        r'^\d+\s*(min|minutes?|hours?|days?|phút|giờ|ngày)\s*(ago|trước)?\s*$',
        r'^(view more|see more|show more|xem thêm|hiển thị thêm)\s*$',
        r'^\d+\s*(like|love|reaction|thích|yêu)\s*$',
        r'^(top fan|most relevant|newest)\s*$',
        r'^(write a comment|viết bình luận)\s*$'
    ]
    
    for pattern in ui_patterns:
        if re.match(pattern, text_lower):
            return False
    
    # Skip if just numbers/punctuation
    if re.match(r'^[\s\d\.\,\!\?\-\+\=\(\)\[\]]+$', text_lower):
        return False
    
    # Must have some letters
    if not re.search(r'[a-zA-ZÀ-ỹ]', text):
        return False
    
    # Prefer longer content
    if len(text) < 15:
        return False
    
    return True

def extract_name_from_nearby_links(element):
    """Extract name from nearby profile links"""
    try:
        # Look for profile links in current element and ancestors
        search_elements = [element]
        
        # Add parent elements
        try:
            parent = element.find_element(By.XPATH, "./..")
            search_elements.append(parent)
            grandparent = parent.find_element(By.XPATH, "./..")
            search_elements.append(grandparent)
        except:
            pass
        
        for search_elem in search_elements:
            try:
                profile_links = search_elem.find_elements(By.XPATH, ".//a[contains(@href, 'profile.php') or contains(@href, 'user.php') or contains(@href, '/profile/')]")
                
                for link in profile_links:
                    try:
                        link_text = link.text.strip()
                        link_href = link.get_attribute("href") or ""
                        
                        # Validate name
                        if (link_text and 
                            3 <= len(link_text) <= 80 and 
                            not link_text.startswith('http') and
                            not link_text.isdigit() and
                            not any(ui in link_text.lower() for ui in ['like', 'reply', 'share', 'comment'])):
                            
                            return link_text, link_href
                    except:
                        continue
            except:
                continue
        
        return "Unknown", ""
        
    except:
        return "Unknown", ""

# ----------------------------
# Brute Force Facebook Scraper
# ----------------------------
class FacebookBruteForceScraper:
    def __init__(self, cookie_str, headless=True):
        options = Options()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # Try Android user agent for better mobile compatibility
        options.add_argument("user-agent=Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36")
        options.add_argument("window-size=414,896")
        
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        self.cookie_str = cookie_str or ""
        self.cookies_list = parse_cookies_to_list(self.cookie_str)
        self._stop_flag = False
        
        if self.cookies_list:
            self._login_with_cookies()

    def _login_with_cookies(self):
        print("=== BRUTE FORCE LOGIN ===")
        
        # Try multiple Facebook entry points
        entry_points = [
            "https://m.facebook.com",
            "https://mbasic.facebook.com", 
            "https://www.facebook.com"
        ]
        
        for entry_point in entry_points:
            try:
                print(f"Trying login via: {entry_point}")
                self.driver.get(entry_point)
                time.sleep(3)
                
                # Add cookies
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
                
                # Test login
                self.driver.get(entry_point)
                time.sleep(3)
                
                if "Log in" not in self.driver.title:
                    print(f"✅ Successfully logged in via {entry_point}")
                    break
                    
            except Exception as e:
                print(f"Failed to login via {entry_point}: {e}")
                continue

    def load_post_brute_force(self, post_url):
        """Try loading post with multiple approaches"""
        print(f"=== BRUTE FORCE POST LOADING ===")
        
        # Generate all possible URL variants
        url_variants = [
            post_url,
            post_url.replace("mbasic.facebook.com", "m.facebook.com"),
            post_url.replace("www.facebook.com", "m.facebook.com"),
            post_url.replace("m.facebook.com", "mbasic.facebook.com"),
            post_url.replace("www.facebook.com", "mbasic.facebook.com"),
            post_url.replace("facebook.com", "m.facebook.com"),
            post_url.replace("facebook.com", "mbasic.facebook.com")
        ]
        
        # Remove duplicates
        unique_urls = list(dict.fromkeys(url_variants))
        
        for i, url in enumerate(unique_urls):
            try:
                print(f"\n--- Attempt {i+1}: {url} ---")
                self.driver.get(url)
                time.sleep(8)  # Longer wait
                
                current_url = self.driver.current_url
                page_title = self.driver.title
                
                print(f"Current URL: {current_url}")
                print(f"Page title: {page_title}")
                
                # Check accessibility
                if "Log in" in page_title or "Login" in page_title:
                    print("❌ Login required")
                    continue
                
                # Check if page has any content
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                if len(page_text) > 100:
                    print(f"✅ Page loaded successfully with {len(page_text)} characters")
                    
                    # Save page source immediately
                    try:
                        with open(f"debug_loaded_page_{i+1}.html", "w", encoding="utf-8") as f:
                            f.write(self.driver.page_source)
                        print(f"✅ Saved page source to debug_loaded_page_{i+1}.html")
                    except:
                        pass
                    
                    return True
                else:
                    print("❌ Page seems empty")
                    continue
                    
            except Exception as e:
                print(f"❌ Failed to load {url}: {e}")
                continue
        
        print("❌ Failed to load post with any URL variant")
        return False

    def brute_force_expand(self):
        """Brute force expansion - click everything that might expand content"""
        print("=== BRUTE FORCE EXPANSION ===")
        
        # Extremely broad expansion attempts
        expand_attempts = 0
        max_attempts = 50
        
        while expand_attempts < max_attempts:
            if self._stop_flag:
                break
                
            expand_attempts += 1
            expanded_something = False
            
            print(f"[Expand attempt {expand_attempts}]")
            
            # Scroll to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Find ALL clickable elements with relevant text
            clickable_selectors = [
                # Any element containing expand-like text
                "//*[contains(text(), 'more') or contains(text(), 'thêm')]",
                "//*[contains(text(), 'view') or contains(text(), 'xem')]", 
                "//*[contains(text(), 'show') or contains(text(), 'hiển thị')]",
                "//*[contains(text(), 'see') or contains(text(), 'xem')]",
                "//*[contains(text(), 'comment') or contains(text(), 'bình luận')]",
                "//*[contains(text(), 'reply') or contains(text(), 'trả lời')]",
                
                # Any clickable element
                "//a",
                "//button", 
                "//*[@role='button']",
                "//*[contains(@class, 'button')]",
                "//*[contains(@class, 'btn')]",
                "//*[@onclick]"
            ]
            
            all_clickables = []
            for selector in clickable_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for elem in elements:
                        try:
                            if elem.is_displayed() and elem.is_enabled():
                                elem_text = elem.text.strip().lower()
                                # Look for expand-related keywords
                                expand_keywords = ['more', 'view', 'show', 'see', 'comment', 'reply', 'thêm', 'xem', 'hiển thị', 'bình luận', 'trả lời']
                                if any(keyword in elem_text for keyword in expand_keywords):
                                    if elem not in all_clickables:
                                        all_clickables.append(elem)
                        except:
                            continue
                except:
                    continue
            
            print(f"  Found {len(all_clickables)} potentially clickable elements")
            
            # Try clicking each one
            for i, elem in enumerate(all_clickables[:20]):  # Limit to first 20 to avoid infinite loops
                if self._stop_flag:
                    break
                    
                try:
                    elem_text = elem.text.strip()
                    print(f"    Trying to click {i+1}: '{elem_text[:50]}'")
                    
                    # Scroll into view
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", elem)
                    time.sleep(1)
                    
                    # Try clicking
                    try:
                        elem.click()
                        expanded_something = True
                        print(f"    ✅ Clicked successfully")
                        time.sleep(random.uniform(2, 4))
                    except:
                        try:
                            self.driver.execute_script("arguments[0].click();", elem)
                            expanded_something = True
                            print(f"    ✅ JS clicked successfully")
                            time.sleep(random.uniform(2, 4))
                        except:
                            print(f"    ❌ Click failed")
                            continue
                            
                except Exception as e:
                    print(f"    ❌ Error clicking element {i}: {e}")
                    continue
            
            if not expanded_something:
                print("No successful expansions this round")
                break
            else:
                print(f"✅ Expanded some elements in attempt {expand_attempts}")
        
        print(f"=== BRUTE FORCE EXPANSION COMPLETE ===")

    def brute_force_extract_everything(self):
        """Extract everything that could possibly be a comment using brute force"""
        print("=== BRUTE FORCE EXTRACTION ===")
        
        # Save current page
        try:
            with open("debug_brute_force_page.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            print("✅ Saved page to debug_brute_force_page.html")
        except:
            pass
        
        # Get ALL text elements on the page
        all_text_elements = []
        
        # Super comprehensive element collection
        element_selectors = [
            "//div",
            "//span", 
            "//p",
            "//td",
            "//li",
            "//h1", "//h2", "//h3", "//h4", "//h5", "//h6",
            "//strong",
            "//em",
            "//b",
            "//i"
        ]
        
        for selector in element_selectors:
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
                print(f"Found {len(elements)} {selector.replace('//', '')} elements")
                
                for elem in elements:
                    try:
                        elem_text = elem.text.strip()
                        if len(elem_text) >= 15 and len(elem_text) <= 2000:  # Reasonable length
                            if elem not in all_text_elements:
                                all_text_elements.append(elem)
                    except:
                        continue
            except:
                continue
        
        print(f"Total text elements collected: {len(all_text_elements)}")
        
        # Filter for likely comment content
        potential_comments = []
        
        for i, elem in enumerate(all_text_elements):
            try:
                elem_text = elem.text.strip()
                
                # Check if this looks like comment content
                if is_likely_comment_content(elem_text):
                    
                    # Try to find associated name
                    username, profile_href = extract_name_from_nearby_links(elem)
                    
                    # Clean content
                    content = elem_text
                    if username != "Unknown":
                        # Remove username from content
                        content = content.replace(username, "").strip()
                        content = re.sub(rf'^.*?{re.escape(username)}\s*', '', content).strip()
                    
                    # Final content cleaning
                    content = re.sub(r'\s+', ' ', content)
                    content = re.sub(r'^(Like|Reply|Share|Comment|Thích|Trả lời|Chia sẻ|Bình luận)\s*', '', content)
                    content = re.sub(r'\s*(Like|Reply|Share|Comment|Thích|Trả lời|Chia sẻ|Bình luận)$', '', content)
                    
                    if len(content) >= 10:
                        # Determine if this is a comment or reply based on position/indentation
                        comment_type = self.guess_comment_type(elem, i)
                        
                        potential_comments.append({
                            "Type": comment_type,
                            "UID": "Unknown",
                            "Name": username,
                            "Content": content,
                            "ProfileLink": profile_href,
                            "ContentLength": len(content),
                            "ElementTag": elem.tag_name,
                            "ElementClass": elem.get_attribute("class") or "",
                            "ElementIndex": i
                        })
                        
                        print(f"  ✅ Found {comment_type}: {username} - {content[:60]}...")
                
            except Exception as e:
                print(f"Error processing element {i}: {e}")
                continue
        
        # Deduplication
        unique_comments = []
        seen_content = set()
        
        for comment in potential_comments:
            content_key = f"{comment['Name']}_{comment['Content'][:40]}"
            if content_key not in seen_content:
                unique_comments.append(comment)
                seen_content.add(content_key)
        
        # Sort: comments first, then replies
        unique_comments.sort(key=lambda x: (x['Type'] == 'Reply', x['ElementIndex']))
        
        print(f"\n=== BRUTE FORCE EXTRACTION COMPLETE ===")
        main_count = len([c for c in unique_comments if c['Type'] == 'Comment'])
        reply_count = len([c for c in unique_comments if c['Type'] == 'Reply'])
        print(f"Extracted: {main_count} comments + {reply_count} replies = {len(unique_comments)} total")
        
        return unique_comments

    def guess_comment_type(self, element, index):
        """Guess if element is comment or reply based on various factors"""
        try:
            # Method 1: Check indentation/position
            try:
                elem_location = element.location
                elem_x = elem_location['x']
                
                # If element is significantly indented, it's likely a reply
                if elem_x > 50:  # More than 50px from left
                    return "Reply"
            except:
                pass
            
            # Method 2: Check element size (replies often narrower)
            try:
                elem_size = element.size
                if elem_size['width'] < 300:
                    return "Reply"
            except:
                pass
            
            # Method 3: Check for reply indicators in text
            try:
                elem_text = element.text.lower()
                reply_indicators = ['@', 'replied to', 'replying to', 'trả lời', 'phản hồi']
                if any(indicator in elem_text for indicator in reply_indicators):
                    return "Reply"
            except:
                pass
            
            # Method 4: Check DOM depth (deeper = more likely reply)
            try:
                # Count ancestor divs
                ancestors = element.find_elements(By.XPATH, "./ancestor::div")
                if len(ancestors) > 10:  # Deeply nested
                    return "Reply"
            except:
                pass
            
            # Default to comment
            return "Comment"
            
        except:
            return "Comment"

    def run_brute_force_scraping(self, post_url, limit=0, progress_callback=None):
        """Main brute force scraping method"""
        print("=== STARTING BRUTE FORCE SCRAPING ===")
        
        # Step 1: Load post with multiple attempts
        success = self.load_post_brute_force(post_url)
        if not success:
            print("❌ Could not load post")
            return []
        
        # Step 2: Brute force expansion
        self.brute_force_expand()
        
        if self._stop_flag:
            return []
        
        # Step 3: Brute force extraction
        comments = self.brute_force_extract_everything()
        
        # Step 4: Apply limit
        if limit > 0:
            comments = comments[:limit]
        
        # Step 5: Progress callback
        if progress_callback:
            progress_callback(len(comments))
        
        return comments

    def close(self):
        try: 
            self.driver.quit()
        except: 
            pass

# ----------------------------
# Brute Force GUI
# ----------------------------
class FBBruteForceAppGUI:
    def __init__(self, root):
        self.root = root
        root.title("💪 FB Brute Force Comment Scraper")
        root.geometry("1000x800")
        root.configure(bg="#ffe6e6")

        main_frame = tk.Frame(root, bg="#ffe6e6")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # Title
        title_label = tk.Label(main_frame, text="💪 Facebook Brute Force Comment Scraper", 
                              font=("Arial", 18, "bold"), bg="#ffe6e6", fg="#721c24")
        title_label.pack(pady=(0,10))
        
        subtitle_label = tk.Label(main_frame, text="🔥 Khi các scraper khác không hoạt động - sử dụng brute force!", 
                                 font=("Arial", 11), bg="#ffe6e6", fg="#721c24")
        subtitle_label.pack(pady=(0,20))

        # Input section
        input_frame = tk.LabelFrame(main_frame, text="📝 Input", font=("Arial", 12, "bold"), 
                                   bg="#ffe6e6", fg="#721c24")
        input_frame.pack(fill="x", pady=(0,15))

        tk.Label(input_frame, text="🔗 Facebook URL (any format):", bg="#ffe6e6").pack(anchor="w", padx=15, pady=(15,5))
        self.entry_url = tk.Entry(input_frame, width=100, font=("Arial", 9))
        self.entry_url.pack(fill="x", padx=15, pady=(0,10))

        tk.Label(input_frame, text="🍪 Cookie:", bg="#ffe6e6").pack(anchor="w", padx=15, pady=(5,5))
        self.txt_cookie = tk.Text(input_frame, height=4, font=("Arial", 8))
        self.txt_cookie.pack(fill="x", padx=15, pady=(0,15))

        # Options
        options_frame = tk.LabelFrame(main_frame, text="⚙️ Brute Force Options", font=("Arial", 12, "bold"), 
                                     bg="#ffe6e6", fg="#721c24")
        options_frame.pack(fill="x", pady=(0,15))
        
        opt_row = tk.Frame(options_frame, bg="#ffe6e6")
        opt_row.pack(fill="x", padx=15, pady=15)
        
        tk.Label(opt_row, text="Limit:", bg="#ffe6e6").pack(side="left")
        self.entry_limit = tk.Entry(opt_row, width=10)
        self.entry_limit.insert(0, "0")
        self.entry_limit.pack(side="left", padx=(10,30))

        self.headless_var = tk.BooleanVar(value=False)
        tk.Checkbutton(opt_row, text="Headless (không khuyến nghị cho debug)", 
                      variable=self.headless_var, bg="#ffe6e6").pack(side="left")

        # File output
        file_frame = tk.Frame(main_frame, bg="#ffe6e6")
        file_frame.pack(fill="x", pady=(0,15))
        
        tk.Label(file_frame, text="💾 Output file:", bg="#ffe6e6").pack(anchor="w")
        file_row = tk.Frame(file_frame, bg="#ffe6e6")
        file_row.pack(fill="x", pady=(5,0))
        
        self.entry_file = tk.Entry(file_row, width=70, font=("Arial", 9))
        self.entry_file.insert(0, "brute_force_comments.xlsx")
        self.entry_file.pack(side="left", fill="x", expand=True)
        
        tk.Button(file_row, text="📁 Choose", command=self.choose_file, 
                 bg="#17a2b8", fg="white").pack(side="right", padx=(10,0))

        # Status
        status_frame = tk.LabelFrame(main_frame, text="📊 Status", font=("Arial", 12, "bold"), 
                                    bg="#ffe6e6", fg="#721c24")
        status_frame.pack(fill="x", pady=(0,15))
        
        self.lbl_status = tk.Label(status_frame, text="💪 Ready for brute force scraping", fg="#721c24", 
                                  wraplength=900, justify="left", font=("Arial", 11), bg="#ffe6e6")
        self.lbl_status.pack(anchor="w", padx=15, pady=(15,5))

        self.lbl_progress_detail = tk.Label(status_frame, text="🔥 Brute force sẽ thử mọi cách có thể để lấy comment - bao gồm cả emergency selectors", 
                                          fg="#6c757d", wraplength=900, justify="left", font=("Arial", 9), bg="#ffe6e6")
        self.lbl_progress_detail.pack(anchor="w", padx=15, pady=(0,15))

        # Buttons
        button_frame = tk.Frame(main_frame, bg="#ffe6e6")
        button_frame.pack(fill="x", pady=20)
        
        self.btn_start = tk.Button(button_frame, text="💪 BRUTE FORCE START", bg="#dc3545", fg="white", 
                                  font=("Arial", 14, "bold"), command=self.start_scrape_thread, 
                                  pady=12, padx=40)
        self.btn_start.pack(side="left")

        self.btn_stop = tk.Button(button_frame, text="⏹️ STOP", bg="#6c757d", fg="white", 
                                 font=("Arial", 14, "bold"), command=self.stop_scrape, 
                                 state=tk.DISABLED, pady=12, padx=40)
        self.btn_stop.pack(side="left", padx=(25,0))

        self.progress_var = tk.IntVar(value=0)
        self.progress_label = tk.Label(button_frame, textvariable=self.progress_var, fg="#721c24", 
                                     font=("Arial", 18, "bold"), bg="#ffe6e6")
        self.progress_label.pack(side="right")

        self._scrape_thread = None
        self._stop_flag = False
        self.scraper = None

    def choose_file(self):
        f = filedialog.asksaveasfilename(
            defaultextension=".xlsx", 
            filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv")],
            title="Choose output file"
        )
        if f:
            self.entry_file.delete(0, tk.END)
            self.entry_file.insert(0, f)

    def start_scrape_thread(self):
        url = self.entry_url.get().strip()
        cookie_str = self.txt_cookie.get("1.0", tk.END).strip()
        file_out = self.entry_file.get().strip() or "brute_force_comments.xlsx"
        
        if not url:
            messagebox.showerror("❌ Error", "Please enter Facebook URL")
            return
        
        try: 
            limit = int(self.entry_limit.get().strip())
        except: 
            limit = 0

        self._stop_flag = False
        self.progress_var.set(0)
        self.lbl_status.config(text="💪 Starting brute force scraper...", fg="#dc3545")
        self.lbl_progress_detail.config(text="🔥 Initializing brute force mode...")
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)

        self._scrape_thread = threading.Thread(target=self._scrape_worker, 
                                             args=(url, cookie_str, file_out, limit, self.headless_var.get()))
        self._scrape_thread.daemon = True
        self._scrape_thread.start()

    def stop_scrape(self):
        self._stop_flag = True
        if self.scraper:
            self.scraper._stop_flag = True
        self.lbl_status.config(text="⏹️ Stopping brute force...", fg="#dc3545")
        self.btn_stop.config(state=tk.DISABLED)

    def _progress_cb(self, count):
        self.progress_var.set(count)
        self.lbl_status.config(text=f"💪 Brute forcing... Found {count} comments/replies", fg="#28a745")
        self.root.update_idletasks()

    def _scrape_worker(self, url, cookie_str, file_out, limit, headless):
        try:
            # Initialize
            self.lbl_status.config(text="🌐 Initializing brute force scraper...", fg="#dc3545")
            self.scraper = FacebookBruteForceScraper(cookie_str, headless=headless)
            
            if self._stop_flag: return
            
            # Scrape with brute force
            self.lbl_status.config(text="💪 Running brute force extraction...", fg="#dc3545")
            self.lbl_progress_detail.config(text="🔥 Trying every possible method to extract comments...")
            
            comments = self.scraper.run_brute_force_scraping(url, limit=limit, progress_callback=self._progress_cb)
            
            if self._stop_flag: return
            
            # Save results
            self.lbl_status.config(text="💾 Saving brute force results...", fg="#dc3545")
            
            if comments:
                df = pd.DataFrame(comments)
                
                # Add metadata
                df.insert(0, 'STT', range(1, len(df) + 1))
                df['ExtractionMethod'] = 'Brute Force'
                df['Timestamp'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Save file
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
                
                self.lbl_status.config(text=f"💪 BRUTE FORCE SUCCESS! Saved {len(comments)} items", fg="#28a745")
                self.lbl_progress_detail.config(text=f"🎯 Results: {comments_count} comments + {replies_count} replies | {unique_users} users | File: {file_out}")
                
            else:
                self.lbl_status.config(text="💪 Brute force complete - no content found", fg="#ffc107")
                self.lbl_progress_detail.config(text="🔍 Check debug files: debug_brute_force_page.html and debug_loaded_page_*.html")
                
        except Exception as e:
            self.lbl_status.config(text=f"💥 Brute force error: {str(e)[:100]}...", fg="#dc3545")
            self.lbl_progress_detail.config(text="🔍 Check console for detailed error")
            print(f"Brute force error: {e}")
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
    app = FBBruteForceAppGUI(root)
    root.mainloop()