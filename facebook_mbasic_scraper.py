import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time, re
import socket

# Test network connectivity
def test_network():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False

# ----------------------------
# Facebook MBASIC Scraper
# ----------------------------
class FacebookMBasicScraper:
    def __init__(self, cookie_str, headless=False):
        self.cookie_str = cookie_str
        self.headless = headless
        self._stop_flag = False
        self.setup_driver()

    def setup_driver(self):
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        
        # Network and DNS fixes
        options.add_argument("--dns-prefetch-disable")
        options.add_argument("--disable-dns-prefetch")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--ignore-ssl-errors")
        options.add_argument("--ignore-certificate-errors-spki-list")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        
        # GPU and WebGL related fixes
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-features=TranslateUI")
        options.add_argument("--disable-backgrounding-occluded-windows")
        
        # Additional stability options
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-translate")
        options.add_argument("--disable-logging")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-sync")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-component-update")
        options.add_argument("--disable-client-side-phishing-detection")
        options.add_argument("--disable-hang-monitor")
        options.add_argument("--disable-prompt-on-repost")
        
        # Proxy and network settings
        options.add_argument("--proxy-server='direct://'")
        options.add_argument("--proxy-bypass-list=*")
        
        # Logging level to suppress warnings
        options.add_argument("--log-level=3")
        options.add_argument("--silent")
        
        # Mobile User-Agent
        mobile_ua = "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Mobile Safari/537.36"
        options.add_argument(f"user-agent={mobile_ua}")
        
        # Experimental options to prevent crashes
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)
        
        try:
            # Set page load timeout
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(10)
            
            # Disable WebDriver detection
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
        except Exception as e:
            print(f"Error setting up driver: {e}")
            raise

    def load_post(self, url):
        try:
            # Test network connectivity first
            print("Testing network connectivity...")
            self.driver.get("https://www.google.com")
            time.sleep(2)
            print("Network test successful")
            
            # Convert URL to mbasic format
            original_url = url
            if "mbasic." not in url:
                if "www.facebook.com" in url:
                    url = url.replace("www.facebook.com", "mbasic.facebook.com")
                elif "m.facebook.com" in url:
                    url = url.replace("m.facebook.com", "mbasic.facebook.com")
                elif "facebook.com" in url:
                    url = url.replace("facebook.com", "mbasic.facebook.com")
            
            print(f"Original URL: {original_url}")
            print(f"Converted URL: {url}")
            
            # Navigate to mbasic Facebook first
            print("Navigating to mbasic.facebook.com...")
            self.driver.get("https://mbasic.facebook.com")
            time.sleep(3)
            
            # Check if we can access Facebook
            current_url = self.driver.current_url
            print(f"Current URL after navigation: {current_url}")
            
            if "facebook.com" not in current_url:
                print("Cannot access Facebook - possible network or cookie issue")
                return False
            
            # Set cookies on mbasic domain first
            print("Setting cookies on mbasic.facebook.com...")
            cookies_set = 0
            for cookie in self.cookie_str.split(";"):
                if "=" in cookie:
                    cookie_parts = cookie.strip().split("=", 1)
                    if len(cookie_parts) == 2:
                        name, value = cookie_parts
                        try:
                            self.driver.add_cookie({
                                "name": name.strip(), 
                                "value": value.strip(), 
                                "domain": "mbasic.facebook.com"
                            })
                            cookies_set += 1
                        except Exception as cookie_error:
                            print(f"Error adding cookie {name}: {cookie_error}")
                            continue
            
            print(f"Set {cookies_set} cookies on mbasic.facebook.com")
            
            # Also set cookies on .facebook.com domain for broader compatibility
            print("Setting cookies on .facebook.com domain...")
            for cookie in self.cookie_str.split(";"):
                if "=" in cookie:
                    cookie_parts = cookie.strip().split("=", 1)
                    if len(cookie_parts) == 2:
                        name, value = cookie_parts
                        try:
                            self.driver.add_cookie({
                                "name": name.strip(), 
                                "value": value.strip(), 
                                "domain": ".facebook.com"
                            })
                        except:
                            continue
            
            # Navigate to target URL
            print(f"Navigating to target URL: {url}")
            self.driver.get(url)
            time.sleep(5)
            
            # Check if we successfully loaded the post
            current_url = self.driver.current_url
            page_source = self.driver.page_source
            
            print(f"Final URL: {current_url}")
            
            # Check for error indicators - be more lenient
            if "login" in current_url.lower() and "checkpoint" in current_url.lower():
                print("Redirected to login/checkpoint - invalid cookies")
                return False
            
            # Check if we're still on Facebook (even if redirected to m.facebook.com)
            if "facebook.com" not in current_url:
                print("Redirected away from Facebook")
                return False
                
            # Check page content for actual errors
            if "error" in page_source.lower() and "not found" in page_source.lower():
                print("Page shows error or not found")
                return False
                
            # Check if we can see any content
            if len(page_source) < 1000:
                print("Page seems too short - possible error")
                return False
                
            print("Post loaded successfully")
            return True
            
        except Exception as e:
            print(f"Error loading post: {e}")
            # Try alternative approach
            try:
                print("Trying alternative approach...")
                # Try with www.facebook.com first
                self.driver.get("https://www.facebook.com")
                time.sleep(3)
                
                # Set cookies on www domain
                for cookie in self.cookie_str.split(";"):
                    if "=" in cookie:
                        cookie_parts = cookie.strip().split("=", 1)
                        if len(cookie_parts) == 2:
                            name, value = cookie_parts
                            try:
                                self.driver.add_cookie({
                                    "name": name.strip(), 
                                    "value": value.strip(), 
                                    "domain": ".facebook.com"
                                })
                            except:
                                continue
                
                # Now try mbasic
                if "mbasic." not in url:
                    url = url.replace("www.facebook.com", "mbasic.facebook.com")
                    url = url.replace("m.facebook.com", "mbasic.facebook.com")
                    url = url.replace("facebook.com", "mbasic.facebook.com")
                
                self.driver.get(url)
                time.sleep(5)
                return True
                
            except Exception as e2:
                print(f"Alternative approach also failed: {e2}")
                return False

    def expand_comments(self):
        try:
            max_attempts = 50  # Limit to prevent infinite loops
            attempts = 0
            
            while attempts < max_attempts:
                if self._stop_flag: 
                    break
                    
                # Look for "View more comments" buttons in multiple languages
                btns = self.driver.find_elements(By.XPATH, 
                    "//a[contains(text(),'Xem thêm bình luận')] | "
                    "//a[contains(text(),'View more comments')] | "
                    "//a[contains(text(),'Voir plus')] | "
                    "//a[contains(text(),'Ver más')] | "
                    "//a[contains(@href,'comment')]"
                )
                
                if not btns:
                    break
                    
                clicked_any = False
                for btn in btns:
                    if self._stop_flag:
                        break
                    try:
                        # Check if button is visible and clickable
                        if btn.is_displayed() and btn.is_enabled():
                            self.driver.execute_script("arguments[0].click();", btn)
                            clicked_any = True
                            time.sleep(2)  # Wait between clicks
                    except Exception as click_error:
                        print(f"Error clicking button: {click_error}")
                        continue
                
                if not clicked_any:
                    break
                    
                attempts += 1
                
        except Exception as e:
            print(f"Error expanding comments: {e}")

    def extract_comments(self):
        comments = []
        seen_profiles = set()

        try:
            time.sleep(3)

            # Selector chỉ lấy main comment (không lấy reply)
            comment_selectors = [
                "//div[starts-with(@id,'ufi_') and contains(@id,'comment')]",
                "//div[contains(@id,'comment_') and not(contains(@id,'reply'))]"
            ]

            all_comment_elements = []
            for selector in comment_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    all_comment_elements.extend(elements)
                except:
                    continue

            unique_elements = list(set(all_comment_elements))

            for div in unique_elements:
                try:
                    # Tìm link profile trong comment
                    a_tag = div.find_element(By.XPATH, ".//a[contains(@href,'/profile.php') or contains(@href,'facebook.com/')]")
                    profile = a_tag.get_attribute("href")
                    name = a_tag.text.strip()

                    # Bỏ qua ẩn danh
                    if not profile or "anonymous" in profile.lower():
                        continue

                    # Bỏ trùng
                    if profile in seen_profiles:
                        continue
                    seen_profiles.add(profile)

                    # Lấy link trực tiếp đến comment (nếu có)
                    try:
                        comment_link = div.find_element(By.XPATH, ".//a[contains(@href,'comment_id')]").get_attribute("href")
                    except:
                        comment_link = ""

                    comments.append({
                        "Name": name,
                        "ProfileLink": profile,
                        "CommentLink": comment_link
                    })

                except Exception as element_error:
                    print(f"Error processing element: {element_error}")
                    continue

        except Exception as e:
            print("Error extracting comments:", e)

        return comments

    def scrape_all(self, limit=0):
        try:
            self.expand_comments()
            if self._stop_flag:
                return []
                
            comments = self.extract_comments()
            
            if limit > 0 and len(comments) > limit:
                comments = comments[:limit]
                
            return comments
        except Exception as e:
            print(f"Error in scrape_all: {e}")
            return []

    def stop(self):
        self._stop_flag = True

    def close(self):
        try:
            if hasattr(self, 'driver'):
                self.driver.quit()
        except Exception as e:
            print(f"Error closing driver: {e}")

# ----------------------------
# GUI 
# ----------------------------
class FBMBasicAppGUI:
    def __init__(self, root):
        self.root = root
        self._stop_flag = False
        self.scraper = None
        
        root.title("📱 Facebook MBASIC Comment Scraper")
        root.geometry("1000x800")
        root.configure(bg="#e8f5e8")

        # Handle window close event
        root.protocol("WM_DELETE_WINDOW", self.on_closing)

        main_frame = tk.Frame(root, bg="#e8f5e8")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        tk.Label(main_frame, text="📱 Facebook MBASIC Comment Scraper", font=("Arial", 20, "bold"), bg="#e8f5e8", fg="#2d5a2d").pack(pady=(0,10))
        tk.Label(main_frame, text="✨ Chỉ lấy main comments từ MBASIC", font=("Arial", 11), bg="#e8f5e8", fg="#5a5a5a").pack(pady=(0,20))

        # Input
        input_frame = tk.LabelFrame(main_frame, text="📝 Thông tin bài viết", font=("Arial", 12, "bold"), bg="#e8f5e8", fg="#2d5a2d", relief="groove", bd=2)
        input_frame.pack(fill="x", pady=(0,15))
        tk.Label(input_frame, text="🔗 Link bài viết:", bg="#e8f5e8").pack(anchor="w", padx=15, pady=(15,5))
        self.entry_url = tk.Entry(input_frame, width=100)
        self.entry_url.pack(fill="x", padx=15, pady=(0,10))
        tk.Label(input_frame, text="🍪 Cookie Facebook:", bg="#e8f5e8").pack(anchor="w", padx=15, pady=(5,5))
        self.txt_cookie = tk.Text(input_frame, height=4)
        self.txt_cookie.pack(fill="x", padx=15, pady=(0,15))

        # Options
        options_frame = tk.LabelFrame(main_frame, text="⚙️ Cấu hình", font=("Arial", 12, "bold"), bg="#e8f5e8", fg="#2d5a2d", relief="groove", bd=2)
        options_frame.pack(fill="x", pady=(0,15))
        tk.Label(options_frame, text="📊 Số lượng comment (0 = tất cả):", bg="#e8f5e8").grid(row=0, column=0, sticky="w", padx=15, pady=10)
        self.entry_limit = tk.Entry(options_frame, width=10)
        self.entry_limit.insert(0, "0")
        self.entry_limit.grid(row=0, column=1, sticky="w")
        self.headless_var = tk.BooleanVar(value=False)
        tk.Checkbutton(options_frame, text="👻 Chạy ẩn (Headless)", variable=self.headless_var, bg="#e8f5e8").grid(row=1, column=0, sticky="w", padx=15)

        # File
        file_frame = tk.LabelFrame(main_frame, text="💾 Xuất kết quả", font=("Arial", 12, "bold"), bg="#e8f5e8", fg="#2d5a2d", relief="groove", bd=2)
        file_frame.pack(fill="x", pady=(0,15))
        file_row = tk.Frame(file_frame, bg="#e8f5e8")
        file_row.pack(fill="x", padx=15, pady=15)
        self.entry_file = tk.Entry(file_row, width=70)
        self.entry_file.insert(0, "facebook_mbasic_comments.xlsx")
        self.entry_file.pack(side="left", fill="x", expand=True)
        tk.Button(file_row, text="📁 Chọn", command=self.choose_file, bg="#17a2b8", fg="white").pack(side="right", padx=(10,0))

        # Status
        status_frame = tk.LabelFrame(main_frame, text="📊 Trạng thái", font=("Arial", 12, "bold"), bg="#e8f5e8", fg="#2d5a2d", relief="groove", bd=2)
        status_frame.pack(fill="x", pady=(0,15))
        self.lbl_status = tk.Label(status_frame, text="✅ Sẵn sàng scrape", fg="#28a745", wraplength=900, justify="left", bg="#e8f5e8")
        self.lbl_status.pack(anchor="w", padx=15, pady=(15,5))
        self.progress_bar = ttk.Progressbar(status_frame, mode='indeterminate')
        self.progress_bar.pack(fill="x", padx=15, pady=(0,15))

        # Buttons
        button_frame = tk.Frame(main_frame, bg="#e8f5e8")
        button_frame.pack(fill="x", pady=20)
        self.btn_start = tk.Button(button_frame, text="🚀 Bắt đầu", bg="#28a745", fg="white", font=("Arial", 14, "bold"), command=self.start_thread)
        self.btn_start.pack(side="left")
        self.btn_stop = tk.Button(button_frame, text="⏹️ Dừng", bg="#dc3545", fg="white", font=("Arial", 14, "bold"), command=self.stop_scrape, state=tk.DISABLED)
        self.btn_stop.pack(side="left", padx=(25,0))

    def choose_file(self):
        f = filedialog.asksaveasfilename(
            defaultextension=".xlsx", 
            filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv")]
        )
        if f:
            self.entry_file.delete(0, tk.END)
            self.entry_file.insert(0, f)

    def start_thread(self):
        # Check network connectivity first
        if not test_network():
            messagebox.showerror("❌ Lỗi mạng", "Không có kết nối internet. Kiểm tra kết nối mạng của bạn.")
            return
            
        url = self.entry_url.get().strip()
        cookie_str = self.txt_cookie.get("1.0", tk.END).strip()
        file_out = self.entry_file.get().strip()
        
        try: 
            limit = int(self.entry_limit.get().strip())
        except: 
            limit = 0
            
        if not url or not cookie_str:
            messagebox.showerror("❌ Lỗi", "Nhập link và cookie trước khi scrape.")
            return
            
        # Validate URL format
        if "facebook.com" not in url:
            messagebox.showerror("❌ Lỗi", "Link phải là từ Facebook.")
            return
            
        self._stop_flag = False
        self.progress_bar.start()
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        
        threading.Thread(
            target=self._scrape_worker, 
            args=(url, cookie_str, file_out, limit), 
            daemon=True
        ).start()

    def stop_scrape(self):
        self._stop_flag = True
        if self.scraper:
            self.scraper.stop()
        self.lbl_status.config(text="⏹️ Đang dừng scraper...", fg="#dc3545")

    def _scrape_worker(self, url, cookie_str, file_out, limit):
        try:
            self.lbl_status.config(text="🌐 Khởi tạo scraper...", fg="#fd7e14")
            self.root.update()
            
            self.scraper = FacebookMBasicScraper(cookie_str, headless=self.headless_var.get())
            
            if self._stop_flag: 
                return
                
            self.lbl_status.config(text="📄 Tải bài viết...", fg="#fd7e14")
            self.root.update()
            
            if not self.scraper.load_post(url):
                self.lbl_status.config(text="❌ Không thể tải bài viết. Kiểm tra:\n1. Kết nối mạng\n2. Link bài viết hợp lệ\n3. Cookie còn hiệu lực", fg="#dc3545")
                return
                
            if self._stop_flag: 
                return
                
            self.lbl_status.config(text="🔍 Đang lấy comments...", fg="#fd7e14")
            self.root.update()
            
            comments = self.scraper.scrape_all(limit)
            
            if self._stop_flag: 
                return
                
            if comments:
                # Create DataFrame and save
                df = pd.DataFrame(comments)
                df.insert(0, 'STT', range(1, len(df)+1))
                
                # Choose file format based on extension
                if file_out.endswith('.csv'):
                    df.to_csv(file_out, index=False, encoding='utf-8-sig')
                else:
                    df.to_excel(file_out, index=False, engine="openpyxl")
                
                self.lbl_status.config(
                    text=f"🎉 Hoàn thành! {len(comments)} comments đã lưu tại: {file_out}", 
                    fg="#28a745"
                )
            else:
                self.lbl_status.config(text="⚠️ Không tìm thấy comment nào", fg="#ffc107")
                
        except Exception as e:
            error_msg = str(e)
            if len(error_msg) > 100:
                error_msg = error_msg[:100] + "..."
            self.lbl_status.config(text=f"❌ Lỗi: {error_msg}", fg="#dc3545")
            print(f"Full error: {e}")
            
        finally:
            # Clean up
            if self.scraper:
                self.scraper.close()
                self.scraper = None
                
            self.progress_bar.stop()
            self.btn_start.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)
            self.root.update()

    def on_closing(self):
        """Handle window close event"""
        if self.scraper:
            self.scraper.close()
        self.root.destroy()

# ----------------------------
# Run App
# ----------------------------
if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = FBMBasicAppGUI(root)
        root.mainloop()
    except Exception as e:
        print(f"Application error: {e}")
        input("Press Enter to exit...")