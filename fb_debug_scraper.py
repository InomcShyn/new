# fb_debug_scraper.py - Debug version to analyze Facebook structure
import time, random, threading, re, requests, pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
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
# Debug Facebook Scraper
# ----------------------------
class FacebookDebugScraper:
    def __init__(self, cookie_str, headless=False):  # Default to visible for debugging
        options = Options()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # Try different user agents
        options.add_argument("user-agent=Mozilla/5.0 (Android 10; Mobile; rv:109.0) Gecko/111.0 Firefox/109.0")
        options.add_argument("window-size=414,896")
        
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        self.cookie_str = cookie_str or ""
        self.cookies_list = parse_cookies_to_list(self.cookie_str)
        self._stop_flag = False
        
        if self.cookies_list:
            self._login_with_cookies()

    def _login_with_cookies(self):
        print("=== LOGGING IN WITH COOKIES ===")
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
                print(f"Added cookie: {c['name']}")
            except Exception as e:
                print(f"Failed to add cookie {c['name']}: {e}")
        
        self.driver.get("https://m.facebook.com")
        time.sleep(4)
        print("Login complete")

    def load_and_analyze_post(self, post_url):
        """Load post and perform deep analysis"""
        print(f"=== LOADING AND ANALYZING POST ===")
        print(f"Original URL: {post_url}")
        
        # Try multiple URL variants
        url_variants = [
            post_url,
            post_url.replace("mbasic.facebook.com", "m.facebook.com"),
            post_url.replace("www.facebook.com", "m.facebook.com"),
            post_url.replace("m.facebook.com", "mbasic.facebook.com"),
            post_url.replace("www.facebook.com", "mbasic.facebook.com")
        ]
        
        # Remove duplicates while preserving order
        unique_urls = []
        for url in url_variants:
            if url not in unique_urls:
                unique_urls.append(url)
        
        successful_url = None
        
        for i, url in enumerate(unique_urls):
            try:
                print(f"\n--- Trying URL variant {i+1}: {url} ---")
                self.driver.get(url)
                time.sleep(6)
                
                current_url = self.driver.current_url
                page_title = self.driver.title
                
                print(f"Current URL: {current_url}")
                print(f"Page title: {page_title}")
                
                # Check if we can access the page
                if "Log in" not in page_title and "Login" not in page_title:
                    print("✅ Successfully loaded page")
                    successful_url = url
                    break
                else:
                    print("❌ Login required")
                    
            except Exception as e:
                print(f"❌ Failed to load {url}: {e}")
                continue
        
        if not successful_url:
            print("❌ Failed to load any URL variant")
            return False
        
        print(f"\n=== ANALYZING PAGE STRUCTURE ===")
        
        # Save full page source
        try:
            with open("debug_full_page.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            print("✅ Saved full page to debug_full_page.html")
        except:
            pass
        
        # Analyze page structure
        self.analyze_page_structure()
        
        return True

    def analyze_page_structure(self):
        """Perform deep analysis of page structure"""
        print("\n=== DEEP PAGE STRUCTURE ANALYSIS ===")
        
        analysis_results = {
            "total_divs": 0,
            "total_spans": 0,
            "total_links": 0,
            "profile_links": 0,
            "elements_with_text": 0,
            "potential_comments": [],
            "expand_candidates": [],
            "layout_indicators": []
        }
        
        # Count basic elements
        try:
            all_divs = self.driver.find_elements(By.TAG_NAME, "div")
            all_spans = self.driver.find_elements(By.TAG_NAME, "span") 
            all_links = self.driver.find_elements(By.TAG_NAME, "a")
            
            analysis_results["total_divs"] = len(all_divs)
            analysis_results["total_spans"] = len(all_spans)
            analysis_results["total_links"] = len(all_links)
            
            print(f"📊 Basic elements: {len(all_divs)} divs, {len(all_spans)} spans, {len(all_links)} links")
        except:
            pass
        
        # Find profile links
        try:
            profile_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'profile.php') or contains(@href, 'user.php') or contains(@href, '/profile/')]")
            analysis_results["profile_links"] = len(profile_links)
            print(f"👤 Profile links: {len(profile_links)}")
            
            # Sample some profile links
            for i, link in enumerate(profile_links[:5]):
                try:
                    link_text = link.text.strip()
                    link_href = link.get_attribute("href")
                    print(f"  Profile {i+1}: '{link_text}' -> {link_href}")
                except:
                    continue
                    
        except:
            pass
        
        # Find elements with substantial text
        try:
            text_elements = self.driver.find_elements(By.XPATH, "//*[string-length(normalize-space(text())) > 30]")
            analysis_results["elements_with_text"] = len(text_elements)
            print(f"📝 Elements with text (>30 chars): {len(text_elements)}")
            
            # Sample some text elements
            for i, elem in enumerate(text_elements[:10]):
                try:
                    elem_text = elem.text.strip()
                    elem_tag = elem.tag_name
                    elem_class = elem.get_attribute("class") or ""
                    elem_id = elem.get_attribute("id") or ""
                    
                    if len(elem_text) > 50:  # Potential comment
                        analysis_results["potential_comments"].append({
                            "index": i,
                            "tag": elem_tag,
                            "class": elem_class[:50],
                            "id": elem_id[:50],
                            "text": elem_text[:100],
                            "text_length": len(elem_text)
                        })
                        print(f"  💬 Potential comment {i+1}: [{elem_tag}] '{elem_text[:80]}...'")
                        
                except:
                    continue
                    
        except:
            pass
        
        # Look for expand/more links
        try:
            expand_keywords = ['more', 'view', 'show', 'see', 'thêm', 'xem', 'hiển thị']
            for keyword in expand_keywords:
                try:
                    expand_elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{keyword}')]")
                    for elem in expand_elements:
                        try:
                            elem_text = elem.text.strip()
                            elem_tag = elem.tag_name
                            elem_href = elem.get_attribute("href") if elem_tag == "a" else ""
                            
                            if len(elem_text) < 100:  # Not too long
                                analysis_results["expand_candidates"].append({
                                    "keyword": keyword,
                                    "tag": elem_tag,
                                    "text": elem_text,
                                    "href": elem_href[:100] if elem_href else ""
                                })
                                print(f"  🔗 Expand candidate: [{elem_tag}] '{elem_text}' -> {elem_href[:50]}")
                        except:
                            continue
                except:
                    continue
        except:
            pass
        
        # Detect layout indicators
        try:
            layout_indicators = [
                ("mbasic", "mbasic" in self.driver.current_url),
                ("mobile", "m.facebook.com" in self.driver.current_url),
                ("www", "www.facebook.com" in self.driver.current_url),
                ("has_tables", len(self.driver.find_elements(By.TAG_NAME, "table")) > 0),
                ("has_articles", len(self.driver.find_elements(By.TAG_NAME, "article")) > 0),
                ("has_data_ft", len(self.driver.find_elements(By.XPATH, "//*[@data-ft]")) > 0),
                ("has_data_sigil", len(self.driver.find_elements(By.XPATH, "//*[@data-sigil]")) > 0),
                ("has_role_article", len(self.driver.find_elements(By.XPATH, "//*[@role='article']")) > 0)
            ]
            
            for indicator, value in layout_indicators:
                analysis_results["layout_indicators"].append({"indicator": indicator, "value": value})
                print(f"  🎯 {indicator}: {value}")
                
        except:
            pass
        
        # Save analysis results
        try:
            with open("debug_analysis.json", "w", encoding="utf-8") as f:
                json.dump(analysis_results, f, indent=2, ensure_ascii=False)
            print("✅ Saved analysis to debug_analysis.json")
        except:
            pass
        
        # Try emergency broad search
        print(f"\n=== EMERGENCY BROAD SEARCH ===")
        self.emergency_search()
        
        return analysis_results

    def emergency_search(self):
        """Emergency search with extremely broad selectors"""
        print("Trying emergency broad selectors...")
        
        emergency_selectors = [
            # Extremely broad selectors
            "//*[string-length(normalize-space(text())) > 20]",
            "//div",
            "//span", 
            "//p",
            "//td",
            "//li",
            # Text-based
            "//*[contains(text(), 'comment') or contains(text(), 'bình luận')]",
            "//*[contains(text(), 'reply') or contains(text(), 'trả lời')]",
            "//*[contains(text(), 'like') or contains(text(), 'thích')]",
            # Attribute-based
            "//*[@data-ft]",
            "//*[@data-sigil]",
            "//*[@role]",
            "//*[@class]",
            "//*[@id]"
        ]
        
        emergency_results = []
        
        for i, selector in enumerate(emergency_selectors):
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
                print(f"Emergency selector {i+1}: Found {len(elements)} elements")
                
                # Sample first few elements
                for j, elem in enumerate(elements[:5]):
                    try:
                        elem_text = elem.text.strip()
                        elem_tag = elem.tag_name
                        elem_class = elem.get_attribute("class") or ""
                        elem_id = elem.get_attribute("id") or ""
                        elem_data_ft = elem.get_attribute("data-ft") or ""
                        elem_data_sigil = elem.get_attribute("data-sigil") or ""
                        
                        if len(elem_text) > 30:  # Potential content
                            emergency_results.append({
                                "selector_index": i,
                                "element_index": j,
                                "tag": elem_tag,
                                "class": elem_class[:100],
                                "id": elem_id[:50],
                                "data_ft": elem_data_ft[:100],
                                "data_sigil": elem_data_sigil[:50],
                                "text": elem_text[:150],
                                "text_length": len(elem_text)
                            })
                            
                            print(f"    Element {j+1}: [{elem_tag}] class='{elem_class[:30]}' id='{elem_id[:20]}' text='{elem_text[:60]}...'")
                    except:
                        continue
                
                # If we found substantial content, focus on this selector
                if len([e for e in emergency_results if e["selector_index"] == i]) > 3:
                    print(f"🎯 Selector {i+1} looks promising!")
                    break
                    
            except Exception as e:
                print(f"Emergency selector {i+1} failed: {e}")
                continue
        
        # Save emergency results
        try:
            with open("debug_emergency_results.json", "w", encoding="utf-8") as f:
                json.dump(emergency_results, f, indent=2, ensure_ascii=False)
            print("✅ Saved emergency results to debug_emergency_results.json")
        except:
            pass
        
        return emergency_results

    def extract_everything_possible(self):
        """Extract everything that could possibly be a comment"""
        print("\n=== EXTRACTING EVERYTHING POSSIBLE ===")
        
        all_possible_comments = []
        
        # Super broad selectors - get everything with text
        super_broad_selectors = [
            "//*[string-length(normalize-space(text())) > 25 and string-length(normalize-space(text())) < 1000]",
            "//div[string-length(normalize-space(text())) > 20]",
            "//span[string-length(normalize-space(text())) > 20]",
            "//p[string-length(normalize-space(text())) > 20]",
            "//td[string-length(normalize-space(text())) > 20]"
        ]
        
        for selector in super_broad_selectors:
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
                print(f"Super broad selector: Found {len(elements)} elements")
                
                for elem in elements:
                    try:
                        elem_text = elem.text.strip()
                        
                        # Basic filtering
                        if (len(elem_text) >= 25 and 
                            len(elem_text) <= 1000 and
                            not elem_text.startswith('http') and
                            elem not in [item['element'] for item in all_possible_comments]):
                            
                            # Check if it looks like user-generated content
                            has_profile_link = len(elem.find_elements(By.XPATH, ".//a[contains(@href, 'profile.php') or contains(@href, 'user.php')]")) > 0
                            has_meaningful_text = not re.match(r'^[\s\d\.\,\!\?\-\+\=\(\)]+$', elem_text)
                            
                            if has_meaningful_text:
                                all_possible_comments.append({
                                    'element': elem,
                                    'text': elem_text,
                                    'has_profile_link': has_profile_link,
                                    'tag': elem.tag_name,
                                    'class': elem.get_attribute("class") or "",
                                    'id': elem.get_attribute("id") or "",
                                    'data_ft': elem.get_attribute("data-ft") or "",
                                    'data_sigil': elem.get_attribute("data-sigil") or ""
                                })
                    except:
                        continue
                        
            except:
                continue
        
        print(f"Found {len(all_possible_comments)} possible comment elements")
        
        # Sort by likelihood of being a comment
        all_possible_comments.sort(key=lambda x: (
            -1 if x['has_profile_link'] else 0,  # Profile links first
            -len(x['text']),  # Longer text first
            -1 if x['data_ft'] else 0,  # data-ft elements first
            -1 if x['data_sigil'] else 0  # data-sigil elements first
        ))
        
        # Extract data from most promising elements
        extracted_comments = []
        
        for i, item in enumerate(all_possible_comments[:50]):  # Top 50 most promising
            try:
                print(f"\n--- Extracting from element {i+1} ---")
                print(f"Tag: {item['tag']}, Class: {item['class'][:50]}, ID: {item['id'][:30]}")
                print(f"Data-ft: {item['data_ft'][:50]}")
                print(f"Data-sigil: {item['data_sigil'][:30]}")
                print(f"Text: {item['text'][:100]}...")
                
                # Try to extract name and content
                extracted = self.extract_from_element(item['element'], item['text'])
                if extracted:
                    extracted['source_info'] = {
                        'tag': item['tag'],
                        'class': item['class'][:100],
                        'id': item['id'][:50],
                        'data_ft': item['data_ft'][:100],
                        'data_sigil': item['data_sigil'][:50],
                        'has_profile_link': item['has_profile_link']
                    }
                    extracted_comments.append(extracted)
                    print(f"  ✅ Extracted: {extracted['Name']} - {extracted['Content'][:50]}...")
                else:
                    print(f"  ❌ Could not extract meaningful data")
                    
            except Exception as e:
                print(f"  ❌ Error extracting from element {i+1}: {e}")
                continue
        
        # Save extracted comments for analysis
        try:
            with open("debug_extracted_comments.json", "w", encoding="utf-8") as f:
                json.dump(extracted_comments, f, indent=2, ensure_ascii=False, default=str)
            print(f"✅ Saved {len(extracted_comments)} extracted comments to debug_extracted_comments.json")
        except:
            pass
        
        return extracted_comments

    def extract_from_element(self, element, full_text):
        """Try to extract name and content from any element"""
        try:
            # Find any links that could be names
            links = element.find_elements(By.XPATH, ".//a")
            
            username = "Unknown"
            profile_href = ""
            
            for link in links[:3]:
                try:
                    link_text = link.text.strip()
                    link_href = link.get_attribute("href") or ""
                    
                    # Very loose name validation
                    if (link_text and 
                        2 <= len(link_text) <= 100 and 
                        not link_text.startswith('http') and
                        'facebook.com' in link_href):
                        
                        username = link_text
                        profile_href = link_href
                        break
                except:
                    continue
            
            # Extract content
            content = full_text
            if username != "Unknown":
                # Remove username from content
                if content.startswith(username):
                    content = content[len(username):].strip()
                content = content.replace(username, "").strip()
            
            # Basic content cleaning
            content = re.sub(r'\s+', ' ', content)
            content = re.sub(r'^(Like|Reply|Share|Comment|Thích|Trả lời|Chia sẻ|Bình luận)\s*', '', content)
            
            if len(content) >= 10:
                return {
                    "Name": username,
                    "Content": content,
                    "ProfileLink": profile_href,
                    "ContentLength": len(content)
                }
            
            return None
            
        except Exception as e:
            print(f"Error in extract_from_element: {e}")
            return None

    def run_complete_analysis(self, post_url):
        """Run complete analysis and extraction"""
        print("=== STARTING COMPLETE ANALYSIS ===")
        
        # Load and analyze
        success = self.load_and_analyze_post(post_url)
        if not success:
            return []
        
        # Extract everything possible
        comments = self.extract_everything_possible()
        
        print(f"\n=== ANALYSIS COMPLETE ===")
        print(f"Total extracted: {len(comments)}")
        
        return comments

    def close(self):
        try: 
            self.driver.quit()
        except: 
            pass

# ----------------------------
# Debug GUI
# ----------------------------
class FBDebugAppGUI:
    def __init__(self, root):
        self.root = root
        root.title("🔍 FB Debug Analyzer")
        root.geometry("900x700")
        root.configure(bg="#fff3cd")

        main_frame = tk.Frame(root, bg="#fff3cd")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # Title
        title_label = tk.Label(main_frame, text="🔍 Facebook Structure Debug Analyzer", 
                              font=("Arial", 18, "bold"), bg="#fff3cd", fg="#856404")
        title_label.pack(pady=(0,20))

        # Input
        input_frame = tk.LabelFrame(main_frame, text="🔗 Debug Input", font=("Arial", 12, "bold"), 
                                   bg="#fff3cd", fg="#856404")
        input_frame.pack(fill="x", pady=(0,15))

        tk.Label(input_frame, text="Facebook Post/Groups URL:", bg="#fff3cd").pack(anchor="w", padx=15, pady=(15,5))
        self.entry_url = tk.Entry(input_frame, width=90, font=("Arial", 9))
        self.entry_url.pack(fill="x", padx=15, pady=(0,10))

        tk.Label(input_frame, text="Cookie:", bg="#fff3cd").pack(anchor="w", padx=15, pady=(5,5))
        self.txt_cookie = tk.Text(input_frame, height=3, font=("Arial", 8))
        self.txt_cookie.pack(fill="x", padx=15, pady=(0,15))

        # Options
        self.headless_var = tk.BooleanVar(value=False)
        tk.Checkbutton(input_frame, text="Run headless (khuyến nghị tắt để debug)", 
                      variable=self.headless_var, bg="#fff3cd").pack(anchor="w", padx=15, pady=(0,15))

        # Status
        self.lbl_status = tk.Label(main_frame, text="Ready to analyze Facebook structure", 
                                  fg="#856404", wraplength=800, justify="left", font=("Arial", 10), bg="#fff3cd")
        self.lbl_status.pack(pady=15)

        # Buttons
        button_frame = tk.Frame(main_frame, bg="#fff3cd")
        button_frame.pack(pady=20)
        
        self.btn_analyze = tk.Button(button_frame, text="🔍 Analyze Structure", bg="#ffc107", fg="black", 
                                    font=("Arial", 12, "bold"), command=self.start_analysis)
        self.btn_analyze.pack(side="left", padx=(0,20))

        self.btn_extract = tk.Button(button_frame, text="📊 Extract Everything", bg="#28a745", fg="white", 
                                    font=("Arial", 12, "bold"), command=self.start_extraction)
        self.btn_extract.pack(side="left")

        self.scraper = None

    def start_analysis(self):
        url = self.entry_url.get().strip()
        cookie_str = self.txt_cookie.get("1.0", tk.END).strip()
        
        if not url:
            messagebox.showerror("Error", "Please enter URL")
            return
        
        self.lbl_status.config(text="🔍 Analyzing Facebook page structure...", fg="#fd7e14")
        self.btn_analyze.config(state=tk.DISABLED)
        
        def analyze_worker():
            try:
                self.scraper = FacebookDebugScraper(cookie_str, headless=self.headless_var.get())
                analysis = self.scraper.run_complete_analysis(url)
                
                self.lbl_status.config(text=f"✅ Analysis complete! Found {len(analysis)} potential comments. Check debug files.", fg="#28a745")
                
            except Exception as e:
                self.lbl_status.config(text=f"❌ Analysis failed: {e}", fg="#dc3545")
                print(f"Analysis error: {e}")
            finally:
                if self.scraper:
                    self.scraper.close()
                self.btn_analyze.config(state=tk.NORMAL)
        
        threading.Thread(target=analyze_worker, daemon=True).start()

    def start_extraction(self):
        url = self.entry_url.get().strip()
        cookie_str = self.txt_cookie.get("1.0", tk.END).strip()
        
        if not url:
            messagebox.showerror("Error", "Please enter URL")
            return
        
        self.lbl_status.config(text="📊 Extracting all possible content...", fg="#fd7e14")
        self.btn_extract.config(state=tk.DISABLED)
        
        def extract_worker():
            try:
                self.scraper = FacebookDebugScraper(cookie_str, headless=self.headless_var.get())
                comments = self.scraper.run_complete_analysis(url)
                
                if comments:
                    # Save to Excel for review
                    df = pd.DataFrame(comments)
                    df.to_excel("debug_extracted_data.xlsx", index=False, engine="openpyxl")
                    
                    self.lbl_status.config(text=f"✅ Extracted {len(comments)} items! Saved to debug_extracted_data.xlsx", fg="#28a745")
                else:
                    self.lbl_status.config(text="⚠️ No content extracted. Check debug files for analysis.", fg="#ffc107")
                
            except Exception as e:
                self.lbl_status.config(text=f"❌ Extraction failed: {e}", fg="#dc3545")
                print(f"Extraction error: {e}")
            finally:
                if self.scraper:
                    self.scraper.close()
                self.btn_extract.config(state=tk.NORMAL)
        
        threading.Thread(target=extract_worker, daemon=True).start()

# ----------------------------
# Run debug app
# ----------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = FBDebugAppGUI(root)
    root.mainloop()