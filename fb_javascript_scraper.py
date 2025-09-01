# fb_javascript_scraper.py - Use JavaScript injection to extract comments
import time, threading, re, pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import json

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

# ----------------------------
# JavaScript-based Facebook Scraper
# ----------------------------
class FacebookJavaScriptScraper:
    def __init__(self, cookie_str, headless=True):
        options = Options()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # Android user agent for better mobile compatibility
        options.add_argument("user-agent=Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36")
        
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        self.cookie_str = cookie_str or ""
        self.cookies_list = parse_cookies_to_list(self.cookie_str)
        self._stop_flag = False
        
        if self.cookies_list:
            self._login_with_cookies()

    def _login_with_cookies(self):
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
        """Load post with multiple URL attempts"""
        print(f"=== LOADING POST WITH JAVASCRIPT ===")
        
        url_variants = [
            post_url.replace("mbasic.facebook.com", "m.facebook.com"),
            post_url.replace("www.facebook.com", "m.facebook.com"),
            post_url,
            post_url.replace("m.facebook.com", "mbasic.facebook.com")
        ]
        
        for url in url_variants:
            try:
                print(f"Trying: {url}")
                self.driver.get(url)
                time.sleep(8)
                
                if "Log in" not in self.driver.title:
                    print(f"✅ Successfully loaded: {self.driver.current_url}")
                    return True
            except:
                continue
        
        return False

    def inject_comment_extractor_script(self):
        """Inject JavaScript to extract comments directly from DOM"""
        
        js_script = """
        // JavaScript Comment Extractor for Facebook
        function extractFacebookComments() {
            console.log('🔥 Starting JavaScript comment extraction...');
            
            let results = {
                comments: [],
                debug_info: {
                    total_elements: 0,
                    profile_links: 0,
                    text_elements: 0,
                    layout_type: 'unknown'
                }
            };
            
            // Detect layout
            if (window.location.href.includes('mbasic.facebook.com')) {
                results.debug_info.layout_type = 'mbasic';
            } else if (window.location.href.includes('m.facebook.com')) {
                results.debug_info.layout_type = 'mobile';
            } else {
                results.debug_info.layout_type = 'www';
            }
            
            console.log('Layout detected:', results.debug_info.layout_type);
            
            // Get all elements with text
            let allElements = document.querySelectorAll('*');
            results.debug_info.total_elements = allElements.length;
            
            console.log('Total elements:', allElements.length);
            
            // Find elements with substantial text
            let textElements = [];
            for (let elem of allElements) {
                try {
                    let text = elem.innerText || elem.textContent || '';
                    text = text.trim();
                    
                    if (text.length >= 20 && text.length <= 2000) {
                        textElements.push({
                            element: elem,
                            text: text,
                            tagName: elem.tagName,
                            className: elem.className || '',
                            id: elem.id || '',
                            dataFt: elem.getAttribute('data-ft') || '',
                            dataSigil: elem.getAttribute('data-sigil') || ''
                        });
                    }
                } catch (e) {
                    continue;
                }
            }
            
            results.debug_info.text_elements = textElements.length;
            console.log('Text elements found:', textElements.length);
            
            // Find profile links
            let profileLinks = document.querySelectorAll('a[href*="profile.php"], a[href*="user.php"], a[href*="/profile/"]');
            results.debug_info.profile_links = profileLinks.length;
            console.log('Profile links found:', profileLinks.length);
            
            // Extract potential comments
            let processedTexts = new Set();
            
            for (let item of textElements) {
                try {
                    let text = item.text;
                    
                    // Skip if already processed similar text
                    let textKey = text.substring(0, 50);
                    if (processedTexts.has(textKey)) {
                        continue;
                    }
                    
                    // Check if this looks like comment content
                    if (!isLikelyCommentContent(text)) {
                        continue;
                    }
                    
                    // Try to find associated name
                    let username = 'Unknown';
                    let profileHref = '';
                    
                    // Look for profile links in this element and nearby elements
                    let searchElements = [item.element];
                    if (item.element.parentElement) searchElements.push(item.element.parentElement);
                    if (item.element.parentElement && item.element.parentElement.parentElement) {
                        searchElements.push(item.element.parentElement.parentElement);
                    }
                    
                    for (let searchElem of searchElements) {
                        let links = searchElem.querySelectorAll('a[href*="facebook.com"]');
                        for (let link of links) {
                            let linkText = (link.innerText || link.textContent || '').trim();
                            let linkHref = link.href || '';
                            
                            if (linkText && linkText.length >= 3 && linkText.length <= 80 && 
                                !linkText.startsWith('http') && !linkText.match(/^\\d+$/)) {
                                username = linkText;
                                profileHref = linkHref;
                                break;
                            }
                        }
                        if (username !== 'Unknown') break;
                    }
                    
                    // Clean content
                    let content = text;
                    if (username !== 'Unknown') {
                        content = content.replace(username, '').trim();
                        content = content.replace(new RegExp('^.*?' + username.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&') + '\\\\s*'), '').trim();
                    }
                    
                    // Remove UI elements
                    content = content.replace(/\\b(Like|Reply|Share|Comment|Translate|Hide|Report|Block|Thích|Trả lời|Chia sẻ|Bình luận)\\b/g, '');
                    content = content.replace(/\\b\\d+\\s*(min|minutes?|hours?|days?|phút|giờ|ngày)\\s*(ago|trước)?\\b/g, '');
                    content = content.replace(/\\s+/g, ' ').trim();
                    
                    if (content.length >= 10) {
                        // Determine comment type based on element position/structure
                        let commentType = 'Comment';
                        
                        // Check indentation
                        let rect = item.element.getBoundingClientRect();
                        if (rect.left > 50) {
                            commentType = 'Reply';
                        }
                        
                        // Check for reply indicators
                        if (text.toLowerCase().includes('replied to') || 
                            text.toLowerCase().includes('trả lời') || 
                            text.toLowerCase().includes('@')) {
                            commentType = 'Reply';
                        }
                        
                        // Check DOM nesting
                        let commentAncestors = 0;
                        let parent = item.element.parentElement;
                        while (parent && commentAncestors < 20) {
                            if (parent.querySelector && parent.querySelector('a[href*="profile.php"]')) {
                                commentAncestors++;
                            }
                            parent = parent.parentElement;
                        }
                        
                        if (commentAncestors > 1) {
                            commentType = 'Reply';
                        }
                        
                        let commentData = {
                            Type: commentType,
                            UID: 'Unknown',
                            Name: username,
                            Content: content,
                            ProfileLink: profileHref,
                            ContentLength: content.length,
                            ElementInfo: {
                                tag: item.tagName,
                                className: item.className.substring(0, 100),
                                id: item.id.substring(0, 50),
                                dataFt: item.dataFt.substring(0, 100),
                                dataSigil: item.dataSigil.substring(0, 50),
                                position: rect.left + ',' + rect.top
                            }
                        };
                        
                        results.comments.push(commentData);
                        processedTexts.add(textKey);
                        
                        console.log('✅ Extracted:', username, '-', content.substring(0, 50) + '...');
                    }
                    
                } catch (e) {
                    console.log('Error processing element:', e);
                    continue;
                }
            }
            
            // Helper function to check if text looks like comment content
            function isLikelyCommentContent(text) {
                if (!text || text.length < 15) return false;
                
                let textLower = text.toLowerCase().trim();
                
                // Skip UI-only patterns
                let uiPatterns = [
                    /^(like|reply|share|comment|translate|hide|report|block)(\\s+\\d+)?\\s*$/,
                    /^(thích|trả lời|chia sẻ|bình luận|dịch|ẩn|báo cáo|chặn)(\\s+\\d+)?\\s*$/,
                    /^\\d+\\s*(min|minutes?|hours?|days?|phút|giờ|ngày)\\s*(ago|trước)?\\s*$/,
                    /^(view more|see more|show more|xem thêm|hiển thị thêm)\\s*$/,
                    /^\\d+\\s*(like|love|reaction|thích|yêu)\\s*$/,
                    /^(top fan|most relevant|newest|all comments)\\s*$/
                ];
                
                for (let pattern of uiPatterns) {
                    if (pattern.test(textLower)) {
                        return false;
                    }
                }
                
                // Must contain letters
                if (!/[a-zA-ZÀ-ỹ]/.test(text)) {
                    return false;
                }
                
                // Skip if just punctuation/numbers
                if (/^[\\s\\d\\.\\,\\!\\?\\-\\+\\=\\(\\)\\[\\]]+$/.test(textLower)) {
                    return false;
                }
                
                return true;
            }
            
            console.log('🎉 JavaScript extraction complete. Found', results.comments.length, 'comments');
            return results;
        }
        
        // Execute the extraction
        return extractFacebookComments();
        """
        
        try:
            print("🔥 Injecting JavaScript comment extractor...")
            result = self.driver.execute_script(js_script)
            
            print(f"JavaScript execution complete!")
            print(f"Debug info: {result.get('debug_info', {})}")
            
            comments = result.get('comments', [])
            print(f"JavaScript found {len(comments)} comments")
            
            return comments
            
        except Exception as e:
            print(f"JavaScript injection failed: {e}")
            return []

    def javascript_expand_all(self):
        """Use JavaScript to expand all comments"""
        
        expand_script = """
        // JavaScript to expand all comments
        function expandAllComments() {
            console.log('🔄 Starting JavaScript expansion...');
            
            let expandCount = 0;
            let maxAttempts = 100;
            let attempt = 0;
            
            function findAndClickExpandLinks() {
                // Find all potential expand links
                let expandSelectors = [
                    'a[href*="comment"]',
                    'a[href*="reply"]',
                    '*[role="button"]',
                    'a',
                    'div[role="button"]',
                    'span[role="button"]'
                ];
                
                let clickedSomething = false;
                
                for (let selector of expandSelectors) {
                    try {
                        let elements = document.querySelectorAll(selector);
                        
                        for (let elem of elements) {
                            try {
                                let text = (elem.innerText || elem.textContent || '').toLowerCase();
                                
                                // Check for expand keywords
                                let expandKeywords = [
                                    'view more', 'show more', 'see more', 'more comments', 'more replies',
                                    'xem thêm', 'hiển thị thêm', 'thêm bình luận', 'thêm phản hồi',
                                    'view previous', 'previous comments'
                                ];
                                
                                let hasExpandKeyword = expandKeywords.some(keyword => text.includes(keyword));
                                
                                if (hasExpandKeyword && elem.offsetParent !== null) {
                                    // Element is visible, try to click
                                    try {
                                        elem.scrollIntoView({behavior: 'smooth', block: 'center'});
                                        setTimeout(() => {
                                            elem.click();
                                            expandCount++;
                                            clickedSomething = true;
                                            console.log('✅ Clicked expand element:', text.substring(0, 50));
                                        }, 500);
                                    } catch (e) {
                                        console.log('Failed to click element:', e);
                                    }
                                }
                            } catch (e) {
                                continue;
                            }
                        }
                    } catch (e) {
                        continue;
                    }
                }
                
                return clickedSomething;
            }
            
            // Expansion loop
            function expandLoop() {
                if (attempt >= maxAttempts) {
                    console.log('🎯 JavaScript expansion complete. Total expansions:', expandCount);
                    return;
                }
                
                attempt++;
                console.log('Expansion attempt', attempt);
                
                // Scroll to bottom
                window.scrollTo(0, document.body.scrollHeight);
                
                setTimeout(() => {
                    let expanded = findAndClickExpandLinks();
                    
                    if (expanded) {
                        // If we expanded something, wait and try again
                        setTimeout(expandLoop, 3000);
                    } else {
                        // No expansion, try a few more times then stop
                        if (attempt < maxAttempts - 5) {
                            setTimeout(expandLoop, 2000);
                        } else {
                            console.log('🎯 JavaScript expansion complete. Total expansions:', expandCount);
                        }
                    }
                }, 2000);
            }
            
            // Start expansion
            expandLoop();
            
            return expandCount;
        }
        
        return expandAllComments();
        """
        
        try:
            print("🔄 Starting JavaScript expansion...")
            self.driver.execute_script(expand_script)
            
            # Wait for expansion to complete
            time.sleep(30)  # Give it time to expand
            
            print("✅ JavaScript expansion phase complete")
            
        except Exception as e:
            print(f"JavaScript expansion failed: {e}")

    def scrape_with_javascript(self, post_url, limit=0, progress_callback=None):
        """Main JavaScript-based scraping method"""
        print("=== STARTING JAVASCRIPT SCRAPING ===")
        
        # Load post
        success = self.load_post(post_url)
        if not success:
            print("❌ Failed to load post")
            return []
        
        # JavaScript expansion
        self.javascript_expand_all()
        
        if self._stop_flag:
            return []
        
        # JavaScript extraction
        comments = self.inject_comment_extractor_script()
        
        if not comments:
            print("⚠️ JavaScript extraction returned no results, trying fallback...")
            comments = self.fallback_extraction()
        
        # Apply limit
        if limit > 0:
            comments = comments[:limit]
        
        # Progress callback
        if progress_callback:
            progress_callback(len(comments))
        
        return comments

    def fallback_extraction(self):
        """Fallback extraction using Selenium if JavaScript fails"""
        print("=== FALLBACK EXTRACTION ===")
        
        comments = []
        
        # Get all elements with text
        try:
            all_elements = self.driver.find_elements(By.XPATH, "//*[string-length(normalize-space(text())) > 20]")
            print(f"Fallback: Found {len(all_elements)} elements with text")
            
            for i, elem in enumerate(all_elements):
                try:
                    elem_text = elem.text.strip()
                    
                    if len(elem_text) >= 20 and self.is_likely_comment(elem_text):
                        # Find name
                        username = "Unknown"
                        profile_href = ""
                        
                        # Look for profile links in element and parents
                        search_elements = [elem]
                        try:
                            search_elements.append(elem.find_element(By.XPATH, "./.."))
                            search_elements.append(elem.find_element(By.XPATH, "./../.."))
                        except:
                            pass
                        
                        for search_elem in search_elements:
                            try:
                                links = search_elem.find_elements(By.XPATH, ".//a[contains(@href, 'facebook.com')]")
                                for link in links[:2]:
                                    link_text = link.text.strip()
                                    link_href = link.get_attribute("href")
                                    
                                    if (link_text and 3 <= len(link_text) <= 80 and 
                                        'profile' in link_href and not link_text.startswith('http')):
                                        username = link_text
                                        profile_href = link_href
                                        break
                                
                                if username != "Unknown":
                                    break
                            except:
                                continue
                        
                        # Clean content
                        content = elem_text
                        if username != "Unknown":
                            content = content.replace(username, "").strip()
                        
                        content = re.sub(r'\\s+', ' ', content)
                        content = re.sub(r'^(Like|Reply|Share|Comment|Thích|Trả lời|Chia sẻ|Bình luận)\\s*', '', content)
                        
                        if len(content) >= 10:
                            # Guess comment type
                            comment_type = "Reply" if elem.location['x'] > 50 else "Comment"
                            
                            comments.append({
                                "Type": comment_type,
                                "UID": "Unknown",
                                "Name": username,
                                "Content": content,
                                "ProfileLink": profile_href,
                                "ContentLength": len(content)
                            })
                            
                            print(f"  ✅ Fallback extracted: {username} - {content[:50]}...")
                
                except Exception as e:
                    continue
        
        except Exception as e:
            print(f"Fallback extraction error: {e}")
        
        print(f"Fallback extraction complete: {len(comments)} comments")
        return comments

    def is_likely_comment(self, text):
        """Check if text is likely a comment"""
        text_lower = text.lower().strip()
        
        # UI-only patterns
        ui_patterns = [
            r'^(like|reply|share|comment)(\s+\d+)?\s*$',
            r'^(thích|trả lời|chia sẻ|bình luận)(\s+\d+)?\s*$',
            r'^\d+\s*(min|hour|day|phút|giờ|ngày)\s*(ago|trước)?\s*$',
            r'^(view more|see more|xem thêm)\s*$'
        ]
        
        for pattern in ui_patterns:
            if re.match(pattern, text_lower):
                return False
        
        # Must have meaningful content
        if len(text) < 15 or not re.search(r'[a-zA-ZÀ-ỹ]', text):
            return False
        
        return True

    def close(self):
        try: 
            self.driver.quit()
        except: 
            pass

# ----------------------------
# JavaScript GUI
# ----------------------------
class FBJavaScriptAppGUI:
    def __init__(self, root):
        self.root = root
        root.title("🔥 FB JavaScript Comment Scraper")
        root.geometry("1000x750")
        root.configure(bg="#e6f3ff")

        main_frame = tk.Frame(root, bg="#e6f3ff")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # Title
        title_label = tk.Label(main_frame, text="🔥 Facebook JavaScript Comment Scraper", 
                              font=("Arial", 18, "bold"), bg="#e6f3ff", fg="#0066cc")
        title_label.pack(pady=(0,10))
        
        subtitle_label = tk.Label(main_frame, text="⚡ Sử dụng JavaScript injection để bypass Selenium limitations", 
                                 font=("Arial", 11), bg="#e6f3ff", fg="#0066cc")
        subtitle_label.pack(pady=(0,20))

        # Input section
        input_frame = tk.LabelFrame(main_frame, text="📝 Input", font=("Arial", 12, "bold"), 
                                   bg="#e6f3ff", fg="#0066cc")
        input_frame.pack(fill="x", pady=(0,15))

        tk.Label(input_frame, text="🔗 Facebook URL:", bg="#e6f3ff").pack(anchor="w", padx=15, pady=(15,5))
        self.entry_url = tk.Entry(input_frame, width=100, font=("Arial", 9))
        self.entry_url.pack(fill="x", padx=15, pady=(0,10))

        tk.Label(input_frame, text="🍪 Cookie:", bg="#e6f3ff").pack(anchor="w", padx=15, pady=(5,5))
        self.txt_cookie = tk.Text(input_frame, height=4, font=("Arial", 8))
        self.txt_cookie.pack(fill="x", padx=15, pady=(0,15))

        # Options
        options_frame = tk.LabelFrame(main_frame, text="⚙️ JavaScript Options", font=("Arial", 12, "bold"), 
                                     bg="#e6f3ff", fg="#0066cc")
        options_frame.pack(fill="x", pady=(0,15))
        
        opt_row = tk.Frame(options_frame, bg="#e6f3ff")
        opt_row.pack(fill="x", padx=15, pady=15)
        
        tk.Label(opt_row, text="Limit:", bg="#e6f3ff").pack(side="left")
        self.entry_limit = tk.Entry(opt_row, width=10)
        self.entry_limit.insert(0, "0")
        self.entry_limit.pack(side="left", padx=(10,30))

        self.headless_var = tk.BooleanVar(value=False)
        tk.Checkbutton(opt_row, text="Headless (không khuyến nghị cho debug)", 
                      variable=self.headless_var, bg="#e6f3ff").pack(side="left")

        # File output
        file_frame = tk.Frame(main_frame, bg="#e6f3ff")
        file_frame.pack(fill="x", pady=(0,15))
        
        tk.Label(file_frame, text="💾 Output file:", bg="#e6f3ff").pack(anchor="w")
        file_row = tk.Frame(file_frame, bg="#e6f3ff")
        file_row.pack(fill="x", pady=(5,0))
        
        self.entry_file = tk.Entry(file_row, width=70, font=("Arial", 9))
        self.entry_file.insert(0, "javascript_comments.xlsx")
        self.entry_file.pack(side="left", fill="x", expand=True)
        
        tk.Button(file_row, text="📁 Choose", command=self.choose_file, 
                 bg="#17a2b8", fg="white").pack(side="right", padx=(10,0))

        # Status
        status_frame = tk.LabelFrame(main_frame, text="📊 Status", font=("Arial", 12, "bold"), 
                                    bg="#e6f3ff", fg="#0066cc")
        status_frame.pack(fill="x", pady=(0,15))
        
        self.lbl_status = tk.Label(status_frame, text="⚡ Ready for JavaScript scraping", fg="#0066cc", 
                                  wraplength=900, justify="left", font=("Arial", 11), bg="#e6f3ff")
        self.lbl_status.pack(anchor="w", padx=15, pady=(15,5))

        self.lbl_progress_detail = tk.Label(status_frame, text="🔥 JavaScript sẽ inject code trực tiếp vào trang để extract comments", 
                                          fg="#6c757d", wraplength=900, justify="left", font=("Arial", 9), bg="#e6f3ff")
        self.lbl_progress_detail.pack(anchor="w", padx=15, pady=(0,15))

        # Buttons
        button_frame = tk.Frame(main_frame, bg="#e6f3ff")
        button_frame.pack(fill="x", pady=20)
        
        self.btn_start = tk.Button(button_frame, text="⚡ JAVASCRIPT SCRAPE", bg="#0066cc", fg="white", 
                                  font=("Arial", 14, "bold"), command=self.start_scrape_thread, 
                                  pady=12, padx=40)
        self.btn_start.pack(side="left")

        self.btn_stop = tk.Button(button_frame, text="⏹️ STOP", bg="#dc3545", fg="white", 
                                 font=("Arial", 14, "bold"), command=self.stop_scrape, 
                                 state=tk.DISABLED, pady=12, padx=40)
        self.btn_stop.pack(side="left", padx=(25,0))

        self.progress_var = tk.IntVar(value=0)
        self.progress_label = tk.Label(button_frame, textvariable=self.progress_var, fg="#0066cc", 
                                     font=("Arial", 18, "bold"), bg="#e6f3ff")
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
        file_out = self.entry_file.get().strip() or "javascript_comments.xlsx"
        
        if not url:
            messagebox.showerror("❌ Error", "Please enter Facebook URL")
            return
        
        try: 
            limit = int(self.entry_limit.get().strip())
        except: 
            limit = 0

        self._stop_flag = False
        self.progress_var.set(0)
        self.lbl_status.config(text="⚡ Starting JavaScript scraper...", fg="#fd7e14")
        self.lbl_progress_detail.config(text="🔥 Initializing JavaScript injection...")
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
        self.lbl_status.config(text="⏹️ Stopping JavaScript scraper...", fg="#dc3545")
        self.btn_stop.config(state=tk.DISABLED)

    def _progress_cb(self, count):
        self.progress_var.set(count)
        self.lbl_status.config(text=f"⚡ JavaScript working... Found {count} comments/replies", fg="#28a745")
        self.root.update_idletasks()

    def _scrape_worker(self, url, cookie_str, file_out, limit, headless):
        try:
            # Initialize
            self.lbl_status.config(text="🌐 Initializing JavaScript scraper...", fg="#fd7e14")
            self.scraper = FacebookJavaScriptScraper(cookie_str, headless=headless)
            
            if self._stop_flag: return
            
            # Scrape with JavaScript
            self.lbl_status.config(text="⚡ Running JavaScript extraction...", fg="#fd7e14")
            self.lbl_progress_detail.config(text="🔥 Injecting JavaScript code to extract comments...")
            
            comments = self.scraper.scrape_with_javascript(url, limit=limit, progress_callback=self._progress_cb)
            
            if self._stop_flag: return
            
            # Save results
            self.lbl_status.config(text="💾 Saving JavaScript results...", fg="#fd7e14")
            
            if comments:
                df = pd.DataFrame(comments)
                
                # Add metadata
                df.insert(0, 'STT', range(1, len(df) + 1))
                df['ExtractionMethod'] = 'JavaScript'
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
                
                self.lbl_status.config(text=f"⚡ JAVASCRIPT SUCCESS! Saved {len(comments)} items", fg="#28a745")
                self.lbl_progress_detail.config(text=f"🎯 Results: {comments_count} comments + {replies_count} replies | {unique_users} users | File: {file_out}")
                
            else:
                self.lbl_status.config(text="⚡ JavaScript complete - no content found", fg="#ffc107")
                self.lbl_progress_detail.config(text="🔍 Trang có thể không có comment hoặc cần quyền truy cập đặc biệt")
                
        except Exception as e:
            self.lbl_status.config(text=f"💥 JavaScript error: {str(e)[:100]}...", fg="#dc3545")
            self.lbl_progress_detail.config(text="🔍 Check console for detailed error")
            print(f"JavaScript scraping error: {e}")
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
    app = FBJavaScriptAppGUI(root)
    root.mainloop()