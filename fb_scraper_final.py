# fb_scraper_final.py - Final version with "Cmt" column and enhanced name/link extraction
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

def parse_cookies_to_dict(cookie_str):
    d = {}
    for pair in cookie_str.split(';'):
        pair = pair.strip()
        if '=' in pair:
            name, value = pair.split('=', 1)
            d[name.strip()] = value.strip()
    return d

def clean_text(text):
    """Advanced text cleaning"""
    if not text:
        return ""
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove UI elements more precisely
    ui_removals = [
        r'\b(Like|Reply|Share|Comment|Translate|Hide|Report|Block)\b',
        r'\b(Thích|Trả lời|Chia sẻ|Bình luận|Dịch|Ẩn|Báo cáo|Chặn)\b',
        r'\b\d+\s*(min|minutes?|hours?|days?|seconds?|phút|giờ|ngày|giây)\s*(ago|trước)?\b',
        r'\b(Top fan|Most relevant|Newest|All comments|Bình luận hàng đầu)\b',
        r'\b\d+\s*(like|love|reaction|thích|yêu thích|cảm xúc)\b',
        r'\b(See translation|Xem bản dịch|Translate|Dịch)\b'
    ]
    
    for pattern in ui_removals:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # Remove extra spaces after cleaning
    text = re.sub(r'\s+', ' ', text.strip())
    
    return text

def is_valid_facebook_name(name_text, profile_href=""):
    """Validate if text looks like a real Facebook name"""
    if not name_text:
        return False
    
    name_text = name_text.strip()
    
    # Length check
    if len(name_text) < 2 or len(name_text) > 100:
        return False
    
    # Should not be URL
    if name_text.startswith('http'):
        return False
    
    # Should not be just numbers
    if name_text.isdigit():
        return False
    
    # Should not be UI elements
    ui_keywords = ['like', 'reply', 'share', 'comment', 'view', 'more', 'see', 'show', 'ago', 'min', 'hour', 'day',
                   'thích', 'trả lời', 'chia sẻ', 'bình luận', 'xem', 'thêm', 'hiển thị', 'trước', 'phút', 'giờ', 'ngày']
    if any(keyword in name_text.lower() for keyword in ui_keywords):
        return False
    
    # Should not be timestamp
    if re.match(r'^\d+\s*(min|hour|day|phút|giờ|ngày)', name_text, re.IGNORECASE):
        return False
    
    # Should contain letters
    if not re.search(r'[a-zA-ZÀ-ỹ]', name_text):
        return False
    
    # If we have profile href, it should be a Facebook profile
    if profile_href and not any(indicator in profile_href for indicator in ['profile.php', 'user.php', '/profile/', 'facebook.com']):
        return False
    
    return True

# ----------------------------
# Final Facebook Scraper with All Improvements
# ----------------------------
class FacebookFinalScraper:
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
        
        # Android user agent for best compatibility
        options.add_argument("user-agent=Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36")
        options.add_argument("window-size=414,896")
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        self.cookie_str = cookie_str or ""
        self.cookies_list = parse_cookies_to_list(self.cookie_str)
        self.cookies_dict = parse_cookies_to_dict(self.cookie_str)
        self._stop_flag = False
        self.current_layout = None
        self.current_url = None
        
        if self.cookies_list:
            self._login_with_cookies()

    def _login_with_cookies(self):
        print("=== ENHANCED LOGIN ===")
        
        # Try multiple entry points
        entry_points = ["https://m.facebook.com", "https://mbasic.facebook.com"]
        
        for entry_point in entry_points:
            try:
                print(f"Trying login via: {entry_point}")
                self.driver.get(entry_point)
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
                
                self.driver.get(entry_point)
                time.sleep(4)
                
                if "Log in" not in self.driver.title:
                    print(f"✅ Login successful via {entry_point}")
                    return True
            except:
                continue
        
        print("⚠️ Login may have issues, but proceeding...")
        return True

    def load_post_smart(self, post_url):
        """Smart post loading with multiple attempts"""
        print(f"=== SMART POST LOADING ===")
        self.current_url = post_url
        
        # Generate URL variants
        url_variants = []
        
        # Mobile variants
        mobile_url = post_url.replace("mbasic.facebook.com", "m.facebook.com").replace("www.facebook.com", "m.facebook.com")
        url_variants.append(mobile_url)
        
        # mbasic variants  
        mbasic_url = post_url.replace("m.facebook.com", "mbasic.facebook.com").replace("www.facebook.com", "mbasic.facebook.com")
        url_variants.append(mbasic_url)
        
        # Original URL
        url_variants.append(post_url)
        
        # Remove duplicates while preserving order
        unique_urls = []
        for url in url_variants:
            if url not in unique_urls:
                unique_urls.append(url)
        
        for i, url in enumerate(unique_urls):
            try:
                print(f"\n--- Attempt {i+1}: {url} ---")
                self.driver.get(url)
                time.sleep(8)  # Longer wait for Groups
                
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
                    print("❌ Login required")
                    continue
                
                # Check if page has content
                body_text = self.driver.find_element(By.TAG_NAME, "body").text
                if len(body_text) > 200:
                    print(f"✅ Page loaded successfully ({len(body_text)} chars)")
                    self.current_url = current_url  # Update to actual URL
                    return True
                else:
                    print("❌ Page seems empty")
                    continue
                    
            except Exception as e:
                print(f"❌ Failed to load {url}: {e}")
                continue
        
        print("❌ Could not load post with any URL variant")
        return False

    def massive_expand_attempt(self):
        """Massive expansion attempt with all possible methods"""
        print(f"=== MASSIVE EXPAND ATTEMPT ({self.current_layout}) ===")
        
        total_clicks = 0
        max_rounds = 80
        
        for round_num in range(max_rounds):
            if self._stop_flag:
                break
                
            print(f"[Round {round_num + 1}] Searching for expand opportunities...")
            
            # Scroll to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Scroll up a bit and back down to trigger lazy loading
            if round_num % 4 == 0:
                self.driver.execute_script("window.scrollBy(0, -300);")
                time.sleep(1)
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            
            # Comprehensive expand selectors
            expand_selectors = [
                # Text-based
                "//*[contains(text(), 'View more comments')]",
                "//*[contains(text(), 'View previous comments')]",
                "//*[contains(text(), 'View more replies')]",
                "//*[contains(text(), 'Show more')]",
                "//*[contains(text(), 'See more')]",
                "//*[contains(text(), 'More comments')]",
                "//*[contains(text(), 'More replies')]",
                "//*[contains(text(), 'Xem thêm')]",
                "//*[contains(text(), 'Hiển thị thêm')]",
                "//*[contains(text(), 'Xem bình luận')]",
                "//*[contains(text(), 'Xem phản hồi')]",
                
                # Attribute-based
                "//*[contains(@href, 'comment')]",
                "//*[contains(@href, 'reply')]",
                "//*[@data-sigil='more']",
                "//*[@data-sigil='expand']",
                "//*[contains(@data-sigil, 'comment')]",
                
                # Role-based
                "//*[@role='button' and (contains(text(), 'more') or contains(text(), 'thêm'))]",
                
                # Generic clickable with expand keywords
                "//a[contains(text(), 'more') or contains(text(), 'view') or contains(text(), 'show') or contains(text(), 'thêm') or contains(text(), 'xem')]",
                "//div[@role='button' and (contains(text(), 'more') or contains(text(), 'view') or contains(text(), 'thêm') or contains(text(), 'xem'))]",
                "//span[contains(text(), 'more') or contains(text(), 'view') or contains(text(), 'thêm')]/ancestor::*[@role='button' or self::a][1]"
            ]
            
            all_expandables = []
            for selector in expand_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for elem in elements:
                        try:
                            if elem.is_displayed() and elem.is_enabled() and elem not in all_expandables:
                                elem_text = elem.text.strip().lower()
                                # Validate expand keywords
                                expand_keywords = ['more', 'view', 'show', 'see', 'thêm', 'xem', 'hiển thị', 'comment', 'reply', 'bình luận', 'phản hồi']
                                if any(keyword in elem_text for keyword in expand_keywords) and len(elem_text) < 200:
                                    all_expandables.append(elem)
                        except:
                            continue
                except:
                    continue
            
            print(f"  Found {len(all_expandables)} expandable elements")
            
            clicks_this_round = 0
            for elem in all_expandables:
                if self._stop_flag:
                    break
                    
                try:
                    elem_text = elem.text.strip()
                    print(f"    Clicking: '{elem_text[:50]}'")
                    
                    # Scroll and click
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", elem)
                    time.sleep(1)
                    
                    # Try multiple click methods
                    success = False
                    try:
                        elem.click()
                        success = True
                    except:
                        try:
                            self.driver.execute_script("arguments[0].click();", elem)
                            success = True
                        except:
                            pass
                    
                    if success:
                        clicks_this_round += 1
                        total_clicks += 1
                        print(f"    ✅ Success")
                        time.sleep(random.uniform(2, 4))
                    else:
                        print(f"    ❌ Failed")
                        
                except Exception as e:
                    print(f"    ❌ Error: {e}")
                    continue
            
            if clicks_this_round == 0:
                print(f"No clicks in round {round_num + 1}")
                if round_num > 5:  # Stop if no clicks for several rounds
                    break
            else:
                print(f"✅ Round {round_num + 1}: {clicks_this_round} clicks")
        
        print(f"=== EXPANSION COMPLETE: {total_clicks} total clicks ===")

    def extract_with_advanced_javascript(self):
        """Advanced JavaScript extraction focusing on names and comment links"""
        
        js_script = """
        function advancedCommentExtraction() {
            console.log('🔥 Advanced JavaScript Comment Extraction Started...');
            
            let results = [];
            let processed = new Set();
            let currentUrl = window.location.href;
            let baseUrl = currentUrl.split('?')[0];
            
            // Find all elements with meaningful text
            let allElements = Array.from(document.querySelectorAll('*')).filter(elem => {
                let text = (elem.innerText || elem.textContent || '').trim();
                return text.length >= 20 && text.length <= 2000;
            });
            
            console.log('Found', allElements.length, 'elements with text');
            
            // Process each element
            for (let i = 0; i < allElements.length; i++) {
                try {
                    let elem = allElements[i];
                    let fullText = (elem.innerText || elem.textContent || '').trim();
                    
                    // Skip if already processed similar content
                    let textKey = fullText.substring(0, 50);
                    if (processed.has(textKey)) continue;
                    
                    // Skip UI-only content
                    if (isUIOnlyContent(fullText)) continue;
                    
                    // Enhanced name extraction
                    let nameData = extractNameAdvanced(elem);
                    let username = nameData.name;
                    let profileHref = nameData.href;
                    let uid = nameData.uid;
                    
                    // Enhanced content extraction
                    let content = extractContentAdvanced(elem, username, fullText);
                    
                    if (content.length >= 10) {
                        // Build comment link
                        let commentLink = buildCommentLink(elem, baseUrl, currentUrl);
                        
                        // Determine comment type
                        let commentType = determineCommentType(elem, i);
                        
                        let commentData = {
                            Type: commentType,
                            UID: uid,
                            Name: username,
                            Cmt: content,  // Changed from Content to Cmt
                            ProfileLink: profileHref,
                            CommentLink: commentLink,
                            CmtLength: content.length,
                            ExtractionMethod: 'JavaScript',
                            Position: elem.getBoundingClientRect().left + ',' + elem.getBoundingClientRect().top
                        };
                        
                        results.push(commentData);
                        processed.add(textKey);
                        
                        console.log('✅', commentType + ':', username, '-', content.substring(0, 60) + '...');
                    }
                    
                } catch (e) {
                    console.log('Error processing element', i, ':', e);
                    continue;
                }
            }
            
            // Helper functions
            function extractNameAdvanced(elem) {
                let name = 'Unknown';
                let href = '';
                let uid = 'Unknown';
                
                // Strategy 1: Look for profile links in element and ancestors
                let searchElements = [elem];
                if (elem.parentElement) searchElements.push(elem.parentElement);
                if (elem.parentElement?.parentElement) searchElements.push(elem.parentElement.parentElement);
                
                for (let searchElem of searchElements) {
                    // Find profile links
                    let profileLinks = searchElem.querySelectorAll('a[href*="facebook.com"]');
                    
                    for (let link of profileLinks) {
                        let linkText = (link.innerText || link.textContent || '').trim();
                        let linkHref = link.href || '';
                        
                        // Enhanced name validation
                        if (isValidName(linkText, linkHref)) {
                            name = linkText;
                            href = linkHref;
                            
                            // Extract UID
                            let uidMatch = linkHref.match(/profile\\.php\\?id=(\\d+)/);
                            if (uidMatch) {
                                uid = uidMatch[1];
                            } else {
                                let usernameMatch = linkHref.match(/facebook\\.com\\/([^\\/?#]+)/);
                                if (usernameMatch && usernameMatch[1] !== 'profile') {
                                    uid = usernameMatch[1];
                                }
                            }
                            
                            return {name: name, href: href, uid: uid};
                        }
                    }
                }
                
                // Strategy 2: Look for strong/h3/b tags with potential names
                let nameElements = searchElem.querySelectorAll('strong, h3, b, .author, .commenter');
                for (let nameElem of nameElements) {
                    let nameText = (nameElem.innerText || nameElem.textContent || '').trim();
                    if (isValidName(nameText, '')) {
                        name = nameText;
                        break;
                    }
                }
                
                if (name !== 'Unknown') break;
                
                return {name: name, href: href, uid: uid};
            }
            
            function extractContentAdvanced(elem, username, fullText) {
                let content = fullText;
                
                // Remove username from content
                if (username !== 'Unknown') {
                    // Remove from beginning
                    if (content.startsWith(username)) {
                        content = content.substring(username.length).trim();
                    }
                    
                    // Remove with word boundaries
                    let usernameRegex = new RegExp('\\\\b' + username.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&') + '\\\\b', 'g');
                    content = content.replace(usernameRegex, '').trim();
                }
                
                // Look for pure content elements
                let contentElements = elem.querySelectorAll('div:not(:has(a)), span:not(:has(a)), p:not(:has(a))');
                let contentCandidates = [content];
                
                for (let contentElem of contentElements) {
                    let contentText = (contentElem.innerText || contentElem.textContent || '').trim();
                    if (contentText && contentText !== username && contentText.length > 15) {
                        contentCandidates.push(contentText);
                    }
                }
                
                // Choose best content (longest valid one)
                let bestContent = '';
                for (let candidate of contentCandidates) {
                    let cleaned = cleanContent(candidate);
                    if (cleaned.length > bestContent.length && !isUIOnlyContent(cleaned)) {
                        bestContent = cleaned;
                    }
                }
                
                return bestContent;
            }
            
            function buildCommentLink(elem, baseUrl, currentUrl) {
                try {
                    // Method 1: data-ft comment_id
                    let dataFt = elem.getAttribute('data-ft');
                    if (dataFt) {
                        let commentIdMatch = dataFt.match(/"comment_id":"(\\d+)"/);
                        if (commentIdMatch) {
                            return baseUrl + '?comment_id=' + commentIdMatch[1];
                        }
                    }
                    
                    // Method 2: Look for comment links
                    let commentLinks = elem.querySelectorAll('a[href*="comment"], a[href*="reply"]');
                    for (let link of commentLinks) {
                        if (link.href && link.href.includes('facebook.com')) {
                            return link.href;
                        }
                    }
                    
                    // Method 3: Element ID
                    if (elem.id && elem.id.includes('comment')) {
                        return currentUrl + '#' + elem.id;
                    }
                    
                    // Method 4: Parent data-ft
                    let parent = elem.parentElement;
                    while (parent && parent !== document.body) {
                        let parentDataFt = parent.getAttribute('data-ft');
                        if (parentDataFt) {
                            let commentIdMatch = parentDataFt.match(/"comment_id":"(\\d+)"/);
                            if (commentIdMatch) {
                                return baseUrl + '?comment_id=' + commentIdMatch[1];
                            }
                        }
                        parent = parent.parentElement;
                    }
                    
                    // Method 5: Position-based
                    let rect = elem.getBoundingClientRect();
                    return currentUrl + '#pos_' + Math.round(rect.top) + '_' + Math.round(rect.left);
                    
                } catch (e) {
                    return currentUrl + '#unknown';
                }
            }
            
            function determineCommentType(elem, index) {
                try {
                    // Indentation check
                    let rect = elem.getBoundingClientRect();
                    if (rect.left > 60) return 'Reply';
                    
                    // Text indicators
                    let text = (elem.innerText || elem.textContent || '').toLowerCase();
                    if (text.includes('@') || text.includes('replied') || text.includes('trả lời')) {
                        return 'Reply';
                    }
                    
                    // DOM nesting
                    let commentAncestors = 0;
                    let parent = elem.parentElement;
                    while (parent && commentAncestors < 8) {
                        if (parent.querySelector && parent.querySelector('a[href*="profile.php"]')) {
                            commentAncestors++;
                        }
                        parent = parent.parentElement;
                    }
                    
                    return commentAncestors > 1 ? 'Reply' : 'Comment';
                } catch (e) {
                    return 'Comment';
                }
            }
            
            function isValidName(text, href) {
                if (!text || text.length < 2 || text.length > 100) return false;
                if (text.startsWith('http') || /^\\d+$/.test(text)) return false;
                
                let uiKeywords = ['like', 'reply', 'share', 'comment', 'view', 'more', 'see', 'ago', 'min', 'hour', 'day',
                                 'thích', 'trả lời', 'chia sẻ', 'bình luận', 'xem', 'thêm', 'trước', 'phút', 'giờ'];
                if (uiKeywords.some(keyword => text.toLowerCase().includes(keyword))) return false;
                
                if (!/[a-zA-ZÀ-ỹ]/.test(text)) return false;
                
                if (href && !href.includes('facebook.com')) return false;
                
                return true;
            }
            
            function cleanContent(text) {
                if (!text) return '';
                
                // Remove UI elements
                text = text.replace(/\\b(Like|Reply|Share|Comment|Translate|Hide|Report|Block|Thích|Trả lời|Chia sẻ|Bình luận)\\b/gi, '');
                text = text.replace(/\\b\\d+\\s*(min|minutes?|hours?|days?|phút|giờ|ngày)\\s*(ago|trước)?\\b/gi, '');
                text = text.replace(/\\b(Top fan|Most relevant|Newest|All comments)\\b/gi, '');
                text = text.replace(/\\s+/g, ' ').trim();
                
                return text;
            }
            
            function isUIOnlyContent(text) {
                if (!text || text.length < 8) return true;
                
                let textLower = text.toLowerCase().trim();
                let uiPatterns = [
                    /^(like|reply|share|comment|translate|hide|report|block)(\\s+\\d+)?\\s*$/,
                    /^(thích|trả lời|chia sẻ|bình luận|dịch|ẩn|báo cáo|chặn)(\\s+\\d+)?\\s*$/,
                    /^\\d+\\s*(min|minutes?|hours?|days?|phút|giờ|ngày)\\s*(ago|trước)?\\s*$/,
                    /^(view more|see more|show more|xem thêm|hiển thị thêm)\\s*$/
                ];
                
                return uiPatterns.some(pattern => pattern.test(textLower));
            }
            
            console.log('🎉 Advanced JavaScript extraction complete:', results.length, 'comments');
            return results;
        }
        
        return advancedCommentExtraction();
        """
        
        try:
            print("🔥 Executing advanced JavaScript extraction...")
            result = self.driver.execute_script(js_script)
            print(f"JavaScript found {len(result)} comments")
            return result
        except Exception as e:
            print(f"JavaScript extraction failed: {e}")
            return []

    def selenium_fallback_extraction(self):
        """Selenium fallback with enhanced name detection"""
        print("=== SELENIUM FALLBACK EXTRACTION ===")
        
        comments = []
        seen_content = set()
        
        # Save page for debugging
        try:
            with open(f"debug_final_{self.current_layout}.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            print(f"✅ Saved debug page to debug_final_{self.current_layout}.html")
        except:
            pass
        
        # Ultra-comprehensive selectors
        all_selectors = [
            # Standard comment selectors
            "//div[@data-ft and contains(@data-ft, 'comment')]",
            "//div[@data-sigil='comment']",
            "//div[contains(@id, 'comment_')]",
            
            # Profile-link based
            "//div[.//a[contains(@href, 'profile.php')]]",
            "//div[.//a[contains(@href, 'user.php')]]",
            "//div[.//h3/a[contains(@href, 'facebook.com')]]",
            "//div[.//strong/a[contains(@href, 'facebook.com')]]",
            "//div[.//span/a[contains(@href, 'facebook.com')]]",
            
            # Content-based
            "//div[string-length(normalize-space(text())) > 30 and .//a[contains(@href, 'facebook.com')]]",
            "//article//div[string-length(normalize-space(text())) > 25]",
            "//div[@role='article']//div[string-length(normalize-space(text())) > 25]",
            
            # Emergency broad selectors
            "//div[string-length(normalize-space(text())) > 40]",
            "//span[string-length(normalize-space(text())) > 30]",
            "//p[string-length(normalize-space(text())) > 25]",
            "//td[string-length(normalize-space(text())) > 25]",
            
            # UI-indicator based
            "//*[contains(text(), 'Like') or contains(text(), 'Thích')]/ancestor::div[string-length(text()) > 30][1]",
            "//*[contains(text(), 'Reply') or contains(text(), 'Trả lời')]/ancestor::div[string-length(text()) > 30][1]"
        ]
        
        all_elements = []
        
        # Collect all potential elements
        for i, selector in enumerate(all_selectors):
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
                print(f"Selector {i+1}: Found {len(elements)} elements")
                
                for elem in elements:
                    if elem not in all_elements:
                        all_elements.append(elem)
                        
            except Exception as e:
                print(f"Selector {i+1} failed: {e}")
                continue
        
        print(f"Total unique elements: {len(all_elements)}")
        
        # Sort by position
        try:
            all_elements.sort(key=lambda x: (x.location['y'], x.location['x']))
        except:
            pass
        
        # Process each element with enhanced extraction
        for i, elem in enumerate(all_elements):
            if self._stop_flag:
                break
                
            try:
                print(f"\n--- Processing element {i+1}/{len(all_elements)} ---")
                
                full_text = elem.text.strip()
                if len(full_text) < 20:
                    print("  ✗ Too short")
                    continue
                
                print(f"  Text: '{full_text[:80]}...'")
                
                # Enhanced name extraction
                username, profile_href, uid = self.extract_name_super_enhanced(elem)
                print(f"  Name: '{username}' | UID: {uid}")
                
                # Enhanced content extraction
                content = self.extract_content_super_enhanced(elem, username, full_text)
                print(f"  Content: '{content[:60]}...'")
                
                if not content or len(content) < 10 or self.is_ui_only(content):
                    print("  ✗ Invalid content")
                    continue
                
                # Deduplication
                content_key = f"{username}_{content[:40]}"
                if content_key in seen_content:
                    print("  ✗ Duplicate")
                    continue
                seen_content.add(content_key)
                
                # Build comment link
                comment_link = self.build_comment_link_enhanced(elem)
                
                # Determine type
                comment_type = self.determine_type_enhanced(elem, i)
                
                comment_data = {
                    "Type": comment_type,
                    "UID": uid,
                    "Name": username,
                    "Cmt": content,  # Changed from Content to Cmt
                    "ProfileLink": profile_href,
                    "CommentLink": comment_link,
                    "CmtLength": len(content),
                    "ExtractionMethod": "Selenium"
                }
                
                comments.append(comment_data)
                print(f"  ✅ Added {comment_type}: {username}")
                
            except Exception as e:
                print(f"  ✗ Error: {e}")
                continue
        
        print(f"Selenium extraction complete: {len(comments)} comments")
        return comments

    def extract_name_super_enhanced(self, element):
        """Super enhanced name extraction with multiple fallback strategies"""
        
        # Strategy 1: Direct profile links
        profile_selectors = [
            ".//a[contains(@href, 'profile.php')]",
            ".//a[contains(@href, 'user.php')]", 
            ".//a[contains(@href, '/profile/')]",
            ".//strong/a[contains(@href, 'facebook.com')]",
            ".//h3/a[contains(@href, 'facebook.com')]",
            ".//b/a[contains(@href, 'facebook.com')]",
            ".//span/a[contains(@href, 'facebook.com')]"
        ]
        
        for selector in profile_selectors:
            try:
                links = element.find_elements(By.XPATH, selector)
                for link in links[:2]:  # Check first 2 links
                    try:
                        link_text = link.text.strip()
                        link_href = link.get_attribute("href") or ""
                        
                        if is_valid_facebook_name(link_text, link_href):
                            uid = self.extract_uid_from_link(link_href)
                            print(f"    ✅ Found name via {selector}: {link_text}")
                            return link_text, link_href, uid
                    except:
                        continue
            except:
                continue
        
        # Strategy 2: Look in parent elements
        try:
            parent = element.find_element(By.XPATH, "./..")
            grandparent = parent.find_element(By.XPATH, "./..")
            
            for ancestor in [parent, grandparent]:
                try:
                    ancestor_links = ancestor.find_elements(By.XPATH, ".//a[contains(@href, 'facebook.com')]")
                    for link in ancestor_links[:3]:
                        try:
                            link_text = link.text.strip()
                            link_href = link.get_attribute("href") or ""
                            
                            if is_valid_facebook_name(link_text, link_href):
                                uid = self.extract_uid_from_link(link_href)
                                print(f"    ✅ Found name via ancestor: {link_text}")
                                return link_text, link_href, uid
                        except:
                            continue
                except:
                    continue
        except:
            pass
        
        # Strategy 3: Text-based name extraction
        try:
            full_text = element.text.strip()
            lines = [line.strip() for line in full_text.split('\n') if line.strip()]
            
            for line in lines[:5]:  # Check first 5 lines
                if is_valid_facebook_name(line):
                    print(f"    ⚠️ Guessed name from text: {line}")
                    return line, "", "Unknown"
        except:
            pass
        
        # Strategy 4: Look for name-like elements by tag
        try:
            name_tags = element.find_elements(By.XPATH, ".//strong | .//h3 | .//b | .//*[@class*='author'] | .//*[@class*='name']")
            for tag in name_tags:
                try:
                    tag_text = tag.text.strip()
                    if is_valid_facebook_name(tag_text):
                        print(f"    ⚠️ Found name via tag: {tag_text}")
                        return tag_text, "", "Unknown"
                except:
                    continue
        except:
            pass
        
        print(f"    ❌ Could not extract name")
        return "Unknown", "", "Unknown"

    def extract_content_super_enhanced(self, element, username, full_text):
        """Super enhanced content extraction"""
        content_strategies = []
        
        # Strategy 1: Remove username and clean
        content = full_text
        if username != "Unknown":
            # Remove username from start
            if content.startswith(username):
                content = content[len(username):].strip()
            
            # Remove username with word boundaries
            content = re.sub(rf'\b{re.escape(username)}\b', '', content, count=1).strip()
            
            # Remove username anywhere in text
            content = content.replace(username, "").strip()
        
        content_strategies.append(content)
        
        # Strategy 2: Look for content-specific elements
        content_selectors = [
            ".//div[not(.//a) and string-length(normalize-space(text())) > 15]",
            ".//span[not(.//a) and string-length(normalize-space(text())) > 15]", 
            ".//p[string-length(normalize-space(text())) > 15]",
            ".//*[@dir='auto' and string-length(normalize-space(text())) > 10]",
            ".//*[contains(@class, 'content') and string-length(normalize-space(text())) > 10]",
            ".//*[contains(@class, 'text') and string-length(normalize-space(text())) > 10]"
        ]
        
        for selector in content_selectors:
            try:
                content_elements = element.find_elements(By.XPATH, selector)
                for content_elem in content_elements:
                    try:
                        content_text = content_elem.text.strip()
                        if content_text and content_text != username and len(content_text) > 10:
                            content_strategies.append(content_text)
                    except:
                        continue
            except:
                continue
        
        # Strategy 3: Line-based extraction
        try:
            lines = [line.strip() for line in full_text.split('\n') if line.strip()]
            
            # Skip first line if it's the username
            start_index = 0
            if lines and username != "Unknown" and lines[0].strip() == username:
                start_index = 1
            
            # Combine remaining lines
            if len(lines) > start_index:
                remaining_content = ' '.join(lines[start_index:])
                if remaining_content:
                    content_strategies.append(remaining_content)
        except:
            pass
        
        # Choose best content
        valid_contents = []
        for strategy_content in content_strategies:
            cleaned = clean_text(strategy_content)
            if cleaned and len(cleaned) >= 10 and not self.is_ui_only(cleaned):
                valid_contents.append(cleaned)
        
        if not valid_contents:
            return ""
        
        # Return longest valid content
        best_content = max(valid_contents, key=len)
        
        # Final cleaning
        best_content = re.sub(r'^(Like|Reply|Share|Comment|Thích|Trả lời|Chia sẻ|Bình luận)\s*', '', best_content, flags=re.IGNORECASE)
        best_content = re.sub(r'\s*(Like|Reply|Share|Comment|Thích|Trả lời|Chia sẻ|Bình luận)$', '', best_content, flags=re.IGNORECASE)
        
        return best_content.strip()

    def extract_uid_from_link(self, href):
        """Extract UID from profile link"""
        try:
            # Method 1: profile.php?id=123456
            uid_match = re.search(r'profile\.php\?id=(\d+)', href)
            if uid_match:
                return uid_match.group(1)
            
            # Method 2: facebook.com/username
            username_match = re.search(r'facebook\.com/([^/?#]+)', href)
            if username_match and username_match.group(1) not in ['profile', 'user', 'groups', 'pages']:
                return username_match.group(1)
            
            return "Unknown"
        except:
            return "Unknown"

    def build_comment_link_enhanced(self, element):
        """Build enhanced comment link"""
        try:
            current_url = self.current_url or self.driver.current_url
            base_url = current_url.split('?')[0]
            
            # Method 1: data-ft comment_id
            data_ft = element.get_attribute("data-ft")
            if data_ft:
                try:
                    ft_data = json.loads(data_ft)
                    if 'comment_id' in ft_data:
                        return f"{base_url}?comment_id={ft_data['comment_id']}"
                except:
                    comment_id_match = re.search(r'"comment_id":"(\d+)"', data_ft)
                    if comment_id_match:
                        return f"{base_url}?comment_id={comment_id_match.group(1)}"
            
            # Method 2: Look for comment/reply links in element
            comment_links = element.find_elements(By.XPATH, ".//a[contains(@href, 'comment') or contains(@href, 'reply')]")
            for link in comment_links:
                href = link.get_attribute("href")
                if href and 'facebook.com' in href:
                    return href
            
            # Method 3: Element ID
            elem_id = element.get_attribute("id")
            if elem_id and 'comment' in elem_id:
                return f"{current_url}#{elem_id}"
            
            # Method 4: Parent element data
            try:
                parent = element.find_element(By.XPATH, "./..")
                parent_data_ft = parent.get_attribute("data-ft")
                if parent_data_ft:
                    comment_id_match = re.search(r'"comment_id":"(\d+)"', parent_data_ft)
                    if comment_id_match:
                        return f"{base_url}?comment_id={comment_id_match.group(1)}"
            except:
                pass
            
            # Method 5: Position-based fallback
            try:
                location = element.location
                return f"{current_url}#comment_y{location['y']}_x{location['x']}"
            except:
                return current_url
                
        except:
            return self.driver.current_url

    def determine_type_enhanced(self, element, index):
        """Enhanced comment type determination"""
        try:
            # Check indentation (replies are usually indented)
            location = element.location
            if location['x'] > 60:
                return "Reply"
            
            # Check element width (replies often narrower)
            size = element.size
            if size['width'] < 300:
                return "Reply"
            
            # Check for reply text indicators
            text = element.text.lower()
            reply_indicators = ['@', 'replied to', 'replying to', 'in reply to', 'trả lời', 'phản hồi', 'đáp lại']
            if any(indicator in text for indicator in reply_indicators):
                return "Reply"
            
            # Check DOM nesting depth
            try:
                comment_ancestors = element.find_elements(By.XPATH, "./ancestor::div[.//a[contains(@href,'profile.php')]]")
                if len(comment_ancestors) > 1:
                    return "Reply"
            except:
                pass
            
            # Check data attributes
            data_sigil = element.get_attribute("data-sigil") or ""
            if "reply" in data_sigil.lower():
                return "Reply"
            
            return "Comment"
        except:
            return "Comment"

    def is_ui_only(self, text):
        """Check if text is UI-only"""
        if not text or len(text.strip()) < 8:
            return True
        
        text_lower = text.lower().strip()
        
        ui_patterns = [
            r'^(like|reply|share|comment|translate|hide|report|block)(\s+\d+)?\s*$',
            r'^(thích|trả lời|chia sẻ|bình luận|dịch|ẩn|báo cáo|chặn)(\s+\d+)?\s*$',
            r'^\d+\s*(min|minutes?|hours?|days?|phút|giờ|ngày)\s*(ago|trước)?\s*$',
            r'^(view more|see more|show more|xem thêm|hiển thị thêm)\s*$',
            r'^\d+\s*(like|love|reaction|thích|yêu)\s*$',
            r'^(see translation|xem bản dịch)\s*$'
        ]
        
        for pattern in ui_patterns:
            if re.match(pattern, text_lower):
                return True
        
        # Just punctuation/numbers
        if re.match(r'^[\s\d\.\,\!\?\-\+\=\(\)\[\]]+$', text_lower):
            return True
        
        return False

    def scrape_all_comments(self, limit=0, progress_callback=None):
        """Main scraping method with all enhancements"""
        print("=== STARTING FINAL ENHANCED SCRAPING ===")
        
        # Step 1: Massive expansion
        self.massive_expand_attempt()
        
        if self._stop_flag:
            return []
        
        # Step 2: Try JavaScript extraction first
        comments = self.extract_with_advanced_javascript()
        
        # Step 3: If JavaScript fails, use enhanced Selenium
        if not comments:
            print("JavaScript extraction yielded no results, trying Selenium fallback...")
            comments = self.selenium_fallback_extraction()
        
        # Step 4: Final processing
        comments = self.final_comment_processing(comments)
        
        # Step 5: Apply limit
        if limit > 0:
            comments = comments[:limit]
        
        # Step 6: Progress callback
        if progress_callback:
            progress_callback(len(comments))
        
        return comments

    def final_comment_processing(self, comments):
        """Final processing and organization"""
        print("=== FINAL COMMENT PROCESSING ===")
        
        # Enhanced deduplication
        unique_comments = []
        seen_signatures = set()
        
        for comment in comments:
            # Create multiple deduplication signatures
            signatures = [
                f"{comment['Name']}_{comment['Cmt'][:40]}",
                comment['Cmt'][:60] if len(comment['Cmt']) > 60 else comment['Cmt'],
                f"{comment['UID']}_{comment['Cmt'][:30]}" if comment['UID'] != "Unknown" else None,
                f"{comment['ProfileLink'][-20:]}_{comment['Cmt'][:20]}" if comment.get('ProfileLink') else None
            ]
            
            # Check for duplicates
            is_duplicate = any(sig in seen_signatures for sig in signatures if sig)
            
            if not is_duplicate and comment['Cmt'] and len(comment['Cmt']) >= 10:
                unique_comments.append(comment)
                for sig in signatures:
                    if sig:
                        seen_signatures.add(sig)
        
        # Sort: Comments first, then replies, then by position
        unique_comments.sort(key=lambda x: (
            x['Type'] == 'Reply',
            x.get('Position', '0,0'),
            x.get('ElementIndex', 999)
        ))
        
        print(f"Final processing complete: {len(unique_comments)} unique comments")
        return unique_comments

    def close(self):
        try: 
            self.driver.quit()
        except: 
            pass

# ----------------------------
# Final Enhanced GUI
# ----------------------------
class FBFinalAppGUI:
    def __init__(self, root):
        self.root = root
        root.title("🏆 FB Final Comment Scraper - Cmt Column & Enhanced Names")
        root.geometry("1100x900")
        root.configure(bg="#f8f9fa")

        main_frame = tk.Frame(root, bg="#f8f9fa")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=20)

        # Header
        header_frame = tk.Frame(main_frame, bg="#f8f9fa")
        header_frame.pack(fill="x", pady=(0,25))
        
        title_label = tk.Label(header_frame, text="🏆 Facebook Final Comment Scraper", 
                              font=("Arial", 22, "bold"), bg="#f8f9fa", fg="#0d6efd")
        title_label.pack()
        
        subtitle_label = tk.Label(header_frame, text="✨ Cột 'Cmt' + Extract tên chính xác + Link comment trực tiếp", 
                                 font=("Arial", 12), bg="#f8f9fa", fg="#6c757d")
        subtitle_label.pack(pady=(5,0))

        # Features highlight
        features_frame = tk.LabelFrame(main_frame, text="🎯 Tính năng nổi bật", font=("Arial", 11, "bold"), 
                                      bg="#f8f9fa", fg="#198754", relief="groove", bd=2)
        features_frame.pack(fill="x", pady=(0,20))
        
        features_text = """✅ Đổi cột 'Content' thành 'Cmt' như yêu cầu
✅ Enhanced name extraction - lấy chính xác tên người viết comment  
✅ CommentLink - link trực tiếp đến từng comment
✅ Support cả mobile (m.facebook.com) và mbasic layout
✅ JavaScript + Selenium hybrid approach
✅ Advanced comment/reply classification
✅ Comprehensive expansion algorithm"""
        
        tk.Label(features_frame, text=features_text, bg="#f8f9fa", fg="#198754", 
                justify="left", font=("Arial", 9)).pack(anchor="w", padx=15, pady=10)

        # Input section
        input_frame = tk.LabelFrame(main_frame, text="📝 Thông tin đầu vào", font=("Arial", 12, "bold"), 
                                   bg="#f8f9fa", fg="#0d6efd", relief="groove", bd=2)
        input_frame.pack(fill="x", pady=(0,15))

        tk.Label(input_frame, text="🔗 Link Facebook (Posts/Groups):", bg="#f8f9fa", font=("Arial", 10)).pack(anchor="w", padx=15, pady=(15,5))
        self.entry_url = tk.Entry(input_frame, width=100, font=("Arial", 9))
        self.entry_url.pack(fill="x", padx=15, pady=(0,10))

        tk.Label(input_frame, text="🍪 Cookie Facebook:", bg="#f8f9fa", font=("Arial", 10)).pack(anchor="w", padx=15, pady=(5,5))
        self.txt_cookie = tk.Text(input_frame, height=4, font=("Arial", 8))
        self.txt_cookie.pack(fill="x", padx=15, pady=(0,15))

        # Options section
        options_frame = tk.LabelFrame(main_frame, text="⚙️ Cấu hình", font=("Arial", 12, "bold"), 
                                     bg="#f8f9fa", fg="#0d6efd", relief="groove", bd=2)
        options_frame.pack(fill="x", pady=(0,15))
        
        opt_grid = tk.Frame(options_frame, bg="#f8f9fa")
        opt_grid.pack(fill="x", padx=15, pady=15)
        
        tk.Label(opt_grid, text="📊 Số lượng comment:", bg="#f8f9fa").grid(row=0, column=0, sticky="w")
        self.entry_limit = tk.Entry(opt_grid, width=10)
        self.entry_limit.insert(0, "0")
        self.entry_limit.grid(row=0, column=1, sticky="w", padx=(10,30))
        tk.Label(opt_grid, text="(0 = tất cả)", bg="#f8f9fa", fg="#6c757d").grid(row=0, column=2, sticky="w")

        self.headless_var = tk.BooleanVar(value=False)  # Default visible for debugging
        tk.Checkbutton(opt_grid, text="👻 Chạy ẩn", variable=self.headless_var, 
                      bg="#f8f9fa", font=("Arial", 9)).grid(row=1, column=0, sticky="w", pady=(10,0))

        # Output preview
        preview_frame = tk.LabelFrame(main_frame, text="📋 Cấu trúc dữ liệu xuất (đã cập nhật)", font=("Arial", 12, "bold"), 
                                     bg="#f8f9fa", fg="#198754", relief="groove", bd=2)
        preview_frame.pack(fill="x", pady=(0,15))
        
        preview_grid = tk.Frame(preview_frame, bg="#f8f9fa")
        preview_grid.pack(fill="x", padx=15, pady=10)
        
        columns_info = [
            ("STT", "Số thứ tự"),
            ("Type", "Comment/Reply"),
            ("Name", "Tên người viết 🆕"),
            ("Cmt", "Nội dung comment 🆕"),
            ("UID", "User ID"),
            ("ProfileLink", "Link profile 🆕"),
            ("CommentLink", "Link comment 🆕"),
            ("CmtLength", "Độ dài comment")
        ]
        
        for i, (col, desc) in enumerate(columns_info):
            row = i // 2
            col_pos = i % 2
            tk.Label(preview_grid, text=f"• {col}: {desc}", bg="#f8f9fa", fg="#198754", 
                    font=("Arial", 9)).grid(row=row, column=col_pos, sticky="w", padx=(0, 30), pady=2)

        # File output
        file_frame = tk.LabelFrame(main_frame, text="💾 File xuất", font=("Arial", 12, "bold"), 
                                  bg="#f8f9fa", fg="#0d6efd", relief="groove", bd=2)
        file_frame.pack(fill="x", pady=(0,15))
        
        file_row = tk.Frame(file_frame, bg="#f8f9fa")
        file_row.pack(fill="x", padx=15, pady=15)
        
        self.entry_file = tk.Entry(file_row, width=70, font=("Arial", 9))
        self.entry_file.insert(0, "facebook_comments_final.xlsx")
        self.entry_file.pack(side="left", fill="x", expand=True)
        
        tk.Button(file_row, text="📁 Chọn", command=self.choose_file, 
                 bg="#17a2b8", fg="white", font=("Arial", 9)).pack(side="right", padx=(10,0))

        # Status section
        status_frame = tk.LabelFrame(main_frame, text="📊 Trạng thái thực thi", font=("Arial", 12, "bold"), 
                                    bg="#f8f9fa", fg="#0d6efd", relief="groove", bd=2)
        status_frame.pack(fill="x", pady=(0,15))
        
        self.lbl_status = tk.Label(status_frame, text="🏆 Sẵn sàng - Final version với cột 'Cmt' và enhanced name extraction", fg="#198754", 
                                  wraplength=1000, justify="left", font=("Arial", 11), bg="#f8f9fa")
        self.lbl_status.pack(anchor="w", padx=15, pady=(15,5))

        self.lbl_progress_detail = tk.Label(status_frame, text="💡 Version này sẽ extract chính xác tên người viết, tạo link trực tiếp đến comment, và xuất với cột 'Cmt'", 
                                          fg="#6c757d", wraplength=1000, justify="left", font=("Arial", 9), bg="#f8f9fa")
        self.lbl_progress_detail.pack(anchor="w", padx=15, pady=(0,10))

        # Progress bar
        self.progress_bar = ttk.Progressbar(status_frame, mode='indeterminate')
        self.progress_bar.pack(fill="x", padx=15, pady=(0,15))

        # Control buttons
        button_frame = tk.Frame(main_frame, bg="#f8f9fa")
        button_frame.pack(fill="x", pady=25)
        
        self.btn_start = tk.Button(button_frame, text="🚀 Bắt đầu Final Scraping", bg="#198754", fg="white", 
                                  font=("Arial", 16, "bold"), command=self.start_scrape_thread, 
                                  pady=15, padx=50)
        self.btn_start.pack(side="left")

        self.btn_stop = tk.Button(button_frame, text="⏹️ Dừng", bg="#dc3545", fg="white", 
                                 font=("Arial", 16, "bold"), command=self.stop_scrape, 
                                 state=tk.DISABLED, pady=15, padx=50)
        self.btn_stop.pack(side="left", padx=(30,0))

        self.progress_var = tk.IntVar(value=0)
        self.progress_label = tk.Label(button_frame, textvariable=self.progress_var, fg="#198754", 
                                     font=("Arial", 20, "bold"), bg="#f8f9fa")
        self.progress_label.pack(side="right")

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
        file_out = self.entry_file.get().strip() or "facebook_comments_final.xlsx"
        
        if not url:
            messagebox.showerror("❌ Lỗi", "Vui lòng nhập link Facebook.")
            return
        
        try: 
            limit = int(self.entry_limit.get().strip())
        except: 
            limit = 0

        self._stop_flag = False
        self.progress_var.set(0)
        self.progress_bar.start()
        self.lbl_status.config(text="🔄 Đang khởi động Final Scraper...", fg="#fd7e14")
        self.lbl_progress_detail.config(text="⏳ Chuẩn bị JavaScript + Selenium hybrid extraction...")
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
        self.lbl_status.config(text="⏹️ Đang dừng Final Scraper...", fg="#dc3545")
        self.btn_stop.config(state=tk.DISABLED)

    def _progress_cb(self, count):
        self.progress_var.set(count)
        self.lbl_status.config(text=f"📈 Final extraction... Đã lấy {count} comment với tên & link", fg="#198754")
        self.root.update_idletasks()

    def _scrape_worker(self, url, cookie_str, file_out, limit, headless):
        try:
            # Initialize
            self.lbl_status.config(text="🌐 Khởi tạo Final Scraper...", fg="#fd7e14")
            self.scraper = FacebookFinalScraper(cookie_str, headless=headless)
            
            if self._stop_flag: return
            
            # Load post
            self.lbl_status.config(text="📄 Đang load và analyze post...", fg="#fd7e14")
            self.lbl_progress_detail.config(text="⏳ Smart loading với multiple URL attempts...")
            success = self.scraper.load_post_smart(url)
            
            if not success:
                self.lbl_status.config(text="❌ Không thể load post", fg="#dc3545")
                self.lbl_progress_detail.config(text="💡 Thử: 1) Kiểm tra cookie, 2) Kiểm tra link, 3) Tắt headless để debug")
                return
            
            layout = getattr(self.scraper, 'current_layout', 'unknown')
            self.lbl_progress_detail.config(text=f"🎯 Layout: {layout} - Optimizing extraction strategies...")
                
            if self._stop_flag: return
            
            # Scrape with all enhancements
            self.lbl_status.config(text="🔍 Đang extract với JavaScript + Selenium...", fg="#fd7e14")
            self.lbl_progress_detail.config(text="⏳ Massive expansion + Advanced name extraction + Comment links...")
            
            comments = self.scraper.scrape_all_comments(limit=limit, progress_callback=self._progress_cb)
            
            if self._stop_flag: return
            
            # Save results
            self.lbl_status.config(text="💾 Đang lưu kết quả Final...", fg="#fd7e14")
            
            if comments:
                df = pd.DataFrame(comments)
                
                # Add useful metadata
                df.insert(0, 'STT', range(1, len(df) + 1))
                df['Layout'] = layout
                df['ScrapedAt'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Ensure column order
                preferred_order = ['STT', 'Type', 'Name', 'Cmt', 'UID', 'ProfileLink', 'CommentLink', 'CmtLength', 'Layout', 'ExtractionMethod', 'ScrapedAt']
                existing_cols = [col for col in preferred_order if col in df.columns]
                other_cols = [col for col in df.columns if col not in preferred_order]
                df = df.reindex(columns=existing_cols + other_cols)
                
                # Save file
                if not file_out.lower().endswith((".xlsx", ".csv")):
                    file_out += ".xlsx"
                
                if file_out.lower().endswith(".csv"):
                    df.to_csv(file_out, index=False, encoding="utf-8-sig")
                else:
                    df.to_excel(file_out, index=False, engine="openpyxl")
                
                # Calculate detailed statistics
                comments_count = len([c for c in comments if c['Type'] == 'Comment'])
                replies_count = len([c for c in comments if c['Type'] == 'Reply'])
                named_comments = len([c for c in comments if c['Name'] != 'Unknown'])
                with_profile_links = len([c for c in comments if c.get('ProfileLink', '').startswith('http')])
                with_comment_links = len([c for c in comments if c.get('CommentLink', '').startswith('http')])
                js_extracted = len([c for c in comments if c.get('ExtractionMethod') == 'JavaScript'])
                
                self.lbl_status.config(text=f"🏆 FINAL SUCCESS! Đã lưu {len(comments)} comment/reply với cột 'Cmt'", fg="#198754")
                self.lbl_progress_detail.config(text=f"📊 {comments_count} comments + {replies_count} replies | {named_comments} có tên | {with_profile_links} profile links | {with_comment_links} comment links | {js_extracted} via JS | {layout}")
                
            else:
                self.lbl_status.config(text="⚠️ Final extraction không tìm thấy comment", fg="#ffc107")
                self.lbl_progress_detail.config(text=f"💡 Layout: {layout} | Kiểm tra debug files hoặc thử approach khác")
                
        except Exception as e:
            error_msg = str(e)[:150]
            self.lbl_status.config(text=f"❌ Final error: {error_msg}...", fg="#dc3545")
            self.lbl_progress_detail.config(text="🔍 Xem console để biết chi tiết lỗi")
            print(f"Final scraping error: {e}")
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
    app = FBFinalAppGUI(root)
    root.mainloop()