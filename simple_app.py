# fb_comment_scraper_www.py
import time
import threading
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    StaleElementReferenceException,
    WebDriverException
)
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

# ----------------------------
# Scraper (WWW layout)
# ----------------------------
class FacebookWWWScraper:
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
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
        options.add_argument("--log-level=3")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)

        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        self.driver.set_window_size(1200, 900)

        self.cookie_str = cookie_str or ""
        self.cookies_list = parse_cookies_to_list(self.cookie_str)
        self.cookies_dict = parse_cookies_to_dict(self.cookie_str)

        if self.cookies_list:
            self._login_with_cookies()

    def _login_with_cookies(self):
        self.driver.get("https://www.facebook.com")
        time.sleep(2)
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
        self.driver.get("https://www.facebook.com")
        time.sleep(3)

    def load_post(self, post_url):
        self.post_url = post_url
        self.driver.get(self.post_url)
        time.sleep(3)

    def expand_all_comments(self, limit=0, max_clicks=500):
        """Click tất cả nút xem thêm comment/reply trên post."""
        clicks = 0
        while clicks < max_clicks:
            try:
                btns = self.driver.find_elements(By.XPATH,
                    "//div[contains(text(),'Xem thêm bình luận') or contains(text(),'View more comments')]/ancestor::div[@role='button']")
                if not btns:
                    break
                for btn in btns:
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                        time.sleep(0.3)
                        btn.click()
                        time.sleep(1)
                    except:
                        continue
                clicks += 1

                # Nếu giới hạn comment được đặt, dừng khi đủ
                if limit:
                    total_comments = len(self.driver.find_elements(By.CSS_SELECTOR, "div.xdj266r.x14z9mp.xat24cr.x1lziwak.xexx8yu.x18d9i69.x1g0dm76.xpdmqnj.x1n2onr6"))
                    if total_comments >= limit:
                        break
            except:
                break

    def scrape_comments(self, limit=0, progress_callback=None):
        comments = []
        seen = set()

        # Lấy tất cả khung comment hiện tại
        comment_blocks = self.driver.find_elements(By.CSS_SELECTOR,
            "div.xdj266r.x14z9mp.xat24cr.x1lziwak.xexx8yu.x18d9i69.x1g0dm76.xpdmqnj.x1n2onr6")

        for block in comment_blocks:
            try:
                # Lấy tên & profile
                try:
                    username_elem = block.find_element(By.TAG_NAME, "a")
                    username = username_elem.text.strip()
                    profile_href = username_elem.get_attribute("href")
                except:
                    username = "Unknown"
                    profile_href = ""

                # Lấy nội dung comment
                try:
                    content_elem = block.find_element(By.CSS_SELECTOR, "div[dir='auto'][style*='text-align']")
                    content = content_elem.text.strip()
                except:
                    content = ""

                if not content:
                    continue

                dedupe = f"{username}_{content[:50]}"
                if dedupe in seen:
                    continue
                seen.add(dedupe)

                comments.append({
                    "Name": username,
                    "Content": content,
                    "ProfileLink": profile_href
                })

                if progress_callback:
                    progress_callback(len(comments))

                if limit and len(comments) >= limit:
                    break
            except:
                continue

        return comments

    def close(self):
        try:
            self.driver.quit()
        except:
            pass

# ----------------------------
# Tkinter App
# ----------------------------
class FBCommentAppGUI:
    def __init__(self, root):
        self.root = root
        root.title("FB Comment Scraper - WWW Layout")
        root.geometry("760x520")

        frame = tk.Frame(root)
        frame.pack(padx=12, pady=8, fill=tk.BOTH, expand=True)

        tk.Label(frame, text="Link bài viết:").grid(row=0, column=0, sticky="w")
        self.entry_url = tk.Entry(frame, width=90)
        self.entry_url.grid(row=1, column=0, columnspan=3, sticky="w")

        tk.Label(frame, text="Cookie:").grid(row=2, column=0, sticky="w")
        self.txt_cookie = tk.Text(frame, height=5, width=90)
        self.txt_cookie.grid(row=3, column=0, columnspan=3, pady=(4,8))

        tk.Label(frame, text="Số lượng comment muốn lấy (0 = all):").grid(row=4, column=0, sticky="w")
        self.entry_limit = tk.Entry(frame, width=12)
        self.entry_limit.insert(0, "0")
        self.entry_limit.grid(row=5, column=0, sticky="w", pady=(4,8))

        self.headless_var = tk.BooleanVar(value=False)
        tk.Checkbutton(frame, text="Chạy headless (ẩn trình duyệt)", variable=self.headless_var).grid(row=5, column=1, sticky="w")

        tk.Label(frame, text="File lưu (Excel):").grid(row=6, column=0, sticky="w")
        self.entry_file = tk.Entry(frame, width=60)
        self.entry_file.grid(row=7, column=0, sticky="w")
        tk.Button(frame, text="Chọn...", command=self.choose_file).grid(row=7, column=1, sticky="w")

        self.lbl_status = tk.Label(frame, text="Status: Ready", fg="blue")
        self.lbl_status.grid(row=8, column=0, columnspan=3, sticky="w", pady=(8,4))

        self.btn_start = tk.Button(frame, text="Start Scrape", bg="#28a745", fg="white", command=self.start_scrape_thread)
        self.btn_start.grid(row=9, column=0, pady=8, sticky="w")

        self.btn_stop = tk.Button(frame, text="Stop", bg="#dc3545", fg="white", command=self.stop_scrape, state=tk.DISABLED)
        self.btn_stop.grid(row=9, column=1, padx=6, pady=8, sticky="w")

        self.progress_var = tk.IntVar(value=0)
        self.progress_label = tk.Label(frame, textvariable=self.progress_var)
        self.progress_label.grid(row=9, column=2, sticky="e")

        self._scrape_thread = None
        self._stop_flag = False
        self.scraper = None

    def choose_file(self):
        f = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
        if f:
            self.entry_file.delete(0, tk.END)
            self.entry_file.insert(0, f)

    def start_scrape_thread(self):
        url = self.entry_url.get().strip()
        cookie_str = self.txt_cookie.get("1.0", tk.END).strip()
        file_out = self.entry_file.get().strip() or "comments.xlsx"
        if not url or not cookie_str:
            messagebox.showerror("Missing input", "Vui lòng nhập link bài viết và cookie.")
            return
        try:
            limit = int(self.entry_limit.get().strip())
        except:
            limit = 0

        self._stop_flag = False
        self.progress_var.set(0)
        self.lbl_status.config(text="Status: Starting...", fg="orange")
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)

        self._scrape_thread = threading.Thread(target=self._scrape_worker, args=(url, cookie_str, file_out, limit, self.headless_var.get()))
        self._scrape_thread.daemon = True
        self._scrape_thread.start()

    def stop_scrape(self):
        self._stop_flag = True
        self.lbl_status.config(text="Stopping...", fg="red")
        self.btn_stop.config(state=tk.DISABLED)

    def _progress_cb(self, count):
        self.progress_var.set(count)
        self.lbl_status.config(text=f"Đã lấy {count} bình luận...", fg="green")
        self.root.update_idletasks()

    def _scrape_worker(self, url, cookie_str, file_out, limit, headless):
        try:
            self.lbl_status.config(text="Khởi tạo trình duyệt...", fg="orange")
            self.scraper = FacebookWWWScraper(cookie_str, headless=headless)
            if self._stop_flag:
                return
            self.lbl_status.config(text="Đang tải bài viết...", fg="orange")
            self.scraper.load_post(url)
            if self._stop_flag:
                return
            self.lbl_status.config(text="Đang mở rộng bình luận...", fg="orange")
            self.scraper.expand_all_comments(limit=limit)
            if self._stop_flag:
                return
            self.lbl_status.config(text="Đang lấy dữ liệu...", fg="orange")
            comments = self.scraper.scrape_comments(limit=limit, progress_callback=self._progress_cb)
            self.lbl_status.config(text="Đang lưu file...", fg="orange")
            if comments:
                df = pd.DataFrame(comments)
                if not file_out.lower().endswith(".xlsx"):
                    file_out += ".xlsx"
                df.to_excel(file_out, index=False, engine="openpyxl")
                self.lbl_status.config(text=f"Done! Lưu {len(comments)} bình luận vào {file_out}", fg="green")
            else:
                self.lbl_status.config(text="Không tìm thấy bình luận.", fg="red")
        except Exception as e:
            self.lbl_status.config(text=f"Lỗi: {e}", fg="red")
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
