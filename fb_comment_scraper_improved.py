# fb_comment_scraper_improved.py - Fixed name extraction and comment links
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
    """Clean comment text"""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text.strip())
    # Remove UI elements
    text = re.sub(r'\b(Like|Reply|Share|Comment|Translate|Hide|Report|Block|Thích|Trả lời|Chia sẻ|Bình luận)\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b\d+\s*(min|minutes?|hours?|days?|seconds?|phút|giờ|ngày|giây)\s*(ago|trước)?\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(Top fan|Most relevant|Newest|All comments|Bình luận hàng đầu)\b', '', text, flags=re.IGNORECASE)
    return text.strip()

def extract_comment_id_from_url(current_url):
    """Extract comment ID from current page URL for building comment links"""
    try:
        # Look for comment ID patterns in URL
        patterns = [
            r'comment_id=(\d+)',
            r'ctoken=(\w+)',
            r'posts/(\d+)',
            r'fbid=(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, current_url)
            if match:
                return match.group(1)
        
        return None
    except:
        return None

# ----------------------------
# Improved Comment Scraper with Name & Link Extraction
# ----------------------------
class FacebookImprovedScraper:
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
        
        # Mobile user agent
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
        self.base_post_url = None
        
        if self.cookies_list:
            self._login_with_cookies()

    def _login_with_cookies(self):
        print("=== LOGGING IN ===")
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
        """Load post and detect layout"""
        print(f"=== LOADING POST ===")
        self.base_post_url = post_url
        
        # Try multiple URL variants
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
                
                if "Log in" not in page_title and "Login" not in page_title:
                    print(f"✅ Successfully loaded with {self.current_layout} layout")
                    return True
                    
            except Exception as e:
                print(f"Failed to load {url}: {e}")
                continue
        
        return False

    def extract_names_and_links_with_javascript(self):
        """Use JavaScript to extract names and comment links more accurately"""
        
        js_script = """
        function extractCommentsWithNamesAndLinks() {
            console.log('🔥 Extracting comments with names and links...');
            
            let comments = [];
            let processedTexts = new Set();
            
            // Get current page URL for building comment links
            let currentUrl = window.location.href;
            let baseUrl = currentUrl.split('?')[0];
            
            // Find all potential comment elements
            let allElements = document.querySelectorAll('*');
            let commentElements = [];
            
            // First pass: find elements that look like comments
            for (let elem of allElements) {
                try {
                    let text = (elem.innerText || elem.textContent || '').trim();
                    
                    // Must have substantial text
                    if (text.length >= 20 && text.length <= 2000) {
                        // Must have profile links nearby
                        let hasProfileLink = elem.querySelector('a[href*="profile.php"], a[href*="user.php"], a[href*="/profile/"]') ||
                                           elem.parentElement?.querySelector('a[href*="profile.php"], a[href*="user.php"], a[href*="/profile/"]') ||
                                           elem.parentElement?.parentElement?.querySelector('a[href*="profile.php"], a[href*="user.php"], a[href*="/profile/"]');
                        
                        if (hasProfileLink) {
                            commentElements.push({
                                element: elem,
                                text: text
                            });
                        }
                    }
                } catch (e) {
                    continue;
                }
            }
            
            console.log('Found', commentElements.length, 'potential comment elements');
            
            // Second pass: extract data from comment elements
            for (let i = 0; i < commentElements.length; i++) {
                try {
                    let item = commentElements[i];
                    let elem = item.element;
                    let text = item.text;
                    
                    // Skip if already processed similar text
                    let textKey = text.substring(0, 60);
                    if (processedTexts.has(textKey)) {
                        continue;
                    }
                    
                    // Skip UI-only content
                    if (isUIOnly(text)) {
                        continue;
                    }
                    
                    // Extract name and profile link
                    let nameData = extractNameAndProfile(elem);
                    let username = nameData.name;
                    let profileHref = nameData.profileHref;
                    let profileId = nameData.profileId;
                    
                    // Extract clean comment content
                    let content = extractCleanContent(text, username);
                    
                    if (content.length >= 10) {
                        // Build comment link
                        let commentLink = buildCommentLink(elem, baseUrl, currentUrl);
                        
                        // Determine comment type
                        let commentType = determineCommentType(elem, i);
                        
                        let commentData = {
                            Type: commentType,
                            UID: profileId,
                            Name: username,
                            Cmt: content,  // Changed from "Content" to "Cmt"
                            ProfileLink: profileHref,
                            CommentLink: commentLink,
                            CmtLength: content.length,
                            Position: elem.getBoundingClientRect().left + ',' + elem.getBoundingClientRect().top
                        };
                        
                        comments.push(commentData);
                        processedTexts.add(textKey);
                        
                        console.log('✅ Extracted:', username, '-', content.substring(0, 50) + '...');
                    }
                    
                } catch (e) {
                    console.log('Error processing element', i, ':', e);
                    continue;
                }
            }
            
            // Helper functions
            function extractNameAndProfile(elem) {
                let username = 'Unknown';
                let profileHref = '';
                let profileId = 'Unknown';
                
                // Search in element and ancestors
                let searchElements = [elem];
                if (elem.parentElement) searchElements.push(elem.parentElement);
                if (elem.parentElement?.parentElement) searchElements.push(elem.parentElement.parentElement);
                
                for (let searchElem of searchElements) {
                    // Look for profile links
                    let profileLinks = searchElem.querySelectorAll('a[href*="facebook.com"]');
                    
                    for (let link of profileLinks) {
                        try {
                            let linkText = (link.innerText || link.textContent || '').trim();
                            let linkHref = link.href || '';
                            
                            // Validate that this looks like a name
                            if (linkText && 
                                linkText.length >= 2 && 
                                linkText.length <= 100 && 
                                !linkText.startsWith('http') && 
                                !linkText.match(/^\\d+$/) &&
                                !linkText.match(/^(like|reply|share|comment|thích|trả lời)$/i) &&
                                (linkHref.includes('profile.php') || linkHref.includes('user.php') || linkHref.includes('/profile/'))) {
                                
                                username = linkText;
                                profileHref = linkHref;
                                
                                // Extract profile ID
                                let idMatch = linkHref.match(/profile\\.php\\?id=(\\d+)/);
                                if (idMatch) {
                                    profileId = idMatch[1];
                                } else {
                                    // Try to extract from username-based URLs
                                    let usernameMatch = linkHref.match(/facebook\\.com\\/([^/?]+)/);
                                    if (usernameMatch) {
                                        profileId = usernameMatch[1];
                                    }
                                }
                                
                                break;
                            }
                        } catch (e) {
                            continue;
                        }
                    }
                    
                    if (username !== 'Unknown') break;
                }
                
                return {name: username, profileHref: profileHref, profileId: profileId};
            }
            
            function extractCleanContent(text, username) {
                let content = text;
                
                // Remove username from content
                if (username !== 'Unknown') {
                    // Remove from beginning
                    if (content.startsWith(username)) {
                        content = content.substring(username.length).trim();
                    }
                    
                    // Remove with regex
                    let usernameRegex = new RegExp('\\\\b' + username.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&') + '\\\\b', 'g');
                    content = content.replace(usernameRegex, '').trim();
                }
                
                // Clean UI elements
                content = content.replace(/\\b(Like|Reply|Share|Comment|Translate|Hide|Report|Block|Thích|Trả lời|Chia sẻ|Bình luận)\\b/gi, '');
                content = content.replace(/\\b\\d+\\s*(min|minutes?|hours?|days?|phút|giờ|ngày)\\s*(ago|trước)?\\b/gi, '');
                content = content.replace(/\\b(Top fan|Most relevant|Newest|All comments)\\b/gi, '');
                content = content.replace(/\\s+/g, ' ').trim();
                
                // Remove leading/trailing UI text
                content = content.replace(/^(Like|Reply|Share|Comment|Thích|Trả lời|Chia sẻ|Bình luận)\\s*/i, '');
                content = content.replace(/\\s*(Like|Reply|Share|Comment|Thích|Trả lời|Chia sẻ|Bình luận)$/i, '');
                
                return content.trim();
            }
            
            function buildCommentLink(elem, baseUrl, currentUrl) {
                try {
                    // Method 1: Look for direct comment link in element
                    let commentLinks = elem.querySelectorAll('a[href*="comment"], a[href*="reply"]');
                    for (let link of commentLinks) {
                        let href = link.href;
                        if (href && href.includes('facebook.com')) {
                            return href;
                        }
                    }
                    
                    // Method 2: Look for data attributes that might contain comment ID
                    let dataFt = elem.getAttribute('data-ft');
                    if (dataFt) {
                        try {
                            let ftData = JSON.parse(dataFt);
                            if (ftData.comment_id) {
                                return baseUrl + '?comment_id=' + ftData.comment_id;
                            }
                        } catch (e) {
                            // Try regex extraction from data-ft
                            let commentIdMatch = dataFt.match(/"comment_id":"(\\d+)"/);
                            if (commentIdMatch) {
                                return baseUrl + '?comment_id=' + commentIdMatch[1];
                            }
                        }
                    }
                    
                    // Method 3: Look for comment ID in nearby elements
                    let parent = elem.parentElement;
                    while (parent && parent !== document.body) {
                        let parentDataFt = parent.getAttribute('data-ft');
                        if (parentDataFt && parentDataFt.includes('comment_id')) {
                            try {
                                let commentIdMatch = parentDataFt.match(/"comment_id":"(\\d+)"/);
                                if (commentIdMatch) {
                                    return baseUrl + '?comment_id=' + commentIdMatch[1];
                                }
                            } catch (e) {
                                // continue
                            }
                        }
                        parent = parent.parentElement;
                    }
                    
                    // Method 4: Look for ID in element attributes
                    let elemId = elem.id;
                    if (elemId && elemId.includes('comment')) {
                        return baseUrl + '#' + elemId;
                    }
                    
                    // Method 5: Generate approximate link based on position
                    let rect = elem.getBoundingClientRect();
                    return currentUrl + '#comment_pos_' + Math.round(rect.top);
                    
                } catch (e) {
                    return currentUrl + '#comment_unknown';
                }
            }
            
            function determineCommentType(elem, index) {
                try {
                    // Check indentation
                    let rect = elem.getBoundingClientRect();
                    if (rect.left > 60) {
                        return 'Reply';
                    }
                    
                    // Check for reply indicators in text
                    let text = (elem.innerText || elem.textContent || '').toLowerCase();
                    if (text.includes('replied to') || text.includes('trả lời') || text.includes('@')) {
                        return 'Reply';
                    }
                    
                    // Check DOM nesting
                    let commentAncestors = 0;
                    let parent = elem.parentElement;
                    while (parent && commentAncestors < 10) {
                        if (parent.querySelector && parent.querySelector('a[href*="profile.php"]')) {
                            commentAncestors++;
                        }
                        parent = parent.parentElement;
                    }
                    
                    if (commentAncestors > 1) {
                        return 'Reply';
                    }
                    
                    return 'Comment';
                } catch (e) {
                    return 'Comment';
                }
            }
            
            function isUIOnly(text) {
                if (!text || text.length < 8) return true;
                
                let textLower = text.toLowerCase().trim();
                
                let uiPatterns = [
                    /^(like|reply|share|comment|translate|hide|report|block)(\\s+\\d+)?\\s*$/,
                    /^(thích|trả lời|chia sẻ|bình luận|dịch|ẩn|báo cáo|chặn)(\\s+\\d+)?\\s*$/,
                    /^\\d+\\s*(min|minutes?|hours?|days?|phút|giờ|ngày)\\s*(ago|trước)?\\s*$/,
                    /^(view more|see more|show more|xem thêm|hiển thị thêm)\\s*$/,
                    /^\\d+\\s*(like|love|reaction|thích|yêu)\\s*$/
                ];
                
                for (let pattern of uiPatterns) {
                    if (pattern.test(textLower)) {
                        return true;
                    }
                }
                
                // Must contain letters
                if (!/[a-zA-ZÀ-ỹ]/.test(text)) {
                    return true;
                }
                
                return false;
            }
            
            console.log('🎉 JavaScript extraction complete. Found', comments.length, 'comments');
            return comments;
        }
        
        return extractCommentsWithNamesAndLinks();
        """
        
        try:
            print("🔥 Executing JavaScript extraction...")
            result = self.driver.execute_script(js_script)
            print(f"JavaScript found {len(result)} comments with names and links")
            return result
        except Exception as e:
            print(f"JavaScript extraction failed: {e}")
            return []

    def enhanced_selenium_extraction(self):
        """Enhanced Selenium extraction focusing on names and links"""
        print("=== ENHANCED SELENIUM EXTRACTION ===")
        
        comments = []
        seen_content = set()
        
        # Save page for debugging
        try:
            with open(f"debug_enhanced_{self.current_layout}.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            print(f"✅ Saved page to debug_enhanced_{self.current_layout}.html")
        except:
            pass
        
        # Comprehensive selectors for different layouts
        if self.current_layout == "mobile":
            selectors = [
                # Mobile-specific
                "//div[@data-sigil='comment']",
                "//div[@data-sigil='comment-body']",
                "//div[contains(@data-ft, 'comment')]",
                "//article//div[.//a[contains(@href, 'profile.php')]]",
                "//div[@role='article']//div[.//a[contains(@href, 'profile.php')]]",
                "//div[.//strong/a[contains(@href, 'profile.php')]]",
                "//div[.//h3/a[contains(@href, 'profile.php')]]",
                "//div[.//span/a[contains(@href, 'profile.php')]]",
                # Broader mobile selectors
                "//div[.//a[contains(@href, 'facebook.com/')] and string-length(normalize-space(text())) > 25]"
            ]
        else:
            selectors = [
                # mbasic-specific
                "//div[@data-ft and contains(@data-ft, 'comment')]",
                "//div[contains(@id, 'comment_')]",
                "//table//div[.//a[contains(@href, 'profile.php')]]",
                "//div[.//a[contains(@href, 'profile.php?id=')]]",
                "//div[.//h3/a[contains(@href, 'profile.php')]]"
            ]
        
        # Emergency fallback selectors
        emergency_selectors = [
            "//div[.//a[contains(@href, 'facebook.com/')] and string-length(normalize-space(text())) > 20]",
            "//div[string-length(normalize-space(text())) > 30]",
            "//*[contains(text(), 'Like') or contains(text(), 'Thích')]/ancestor::div[string-length(text()) > 30][1]",
            "//a[contains(@href,'profile.php')]/ancestor::div[string-length(text()) > 25][1]"
        ]
        
        all_selectors = selectors + emergency_selectors
        all_elements = []
        
        # Collect elements
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
        
        # Process elements
        for i, elem in enumerate(all_elements):
            if self._stop_flag:
                break
                
            try:
                print(f"\n--- Processing element {i+1}/{len(all_elements)} ---")
                
                full_text = elem.text.strip()
                if len(full_text) < 20:
                    print("  ✗ Too short")
                    continue
                
                print(f"  Text: '{full_text[:100]}...'")
                
                # Enhanced name extraction
                username, profile_href, uid = self.extract_name_enhanced(elem)
                print(f"  Name: '{username}' | Profile: {profile_href[:50]}...")
                
                # Enhanced content extraction
                content = self.extract_content_enhanced(elem, username, full_text)
                print(f"  Content: '{content[:80]}...'")
                
                if not content or len(content) < 10:
                    print("  ✗ No valid content")
                    continue
                
                # Check for duplicates
                content_key = f"{username}_{content[:50]}"
                if content_key in seen_content:
                    print("  ✗ Duplicate")
                    continue
                seen_content.add(content_key)
                
                # Build comment link
                comment_link = self.build_comment_link(elem)
                
                # Determine type
                comment_type = self.determine_comment_type_enhanced(elem, i)
                
                comment_data = {
                    "Type": comment_type,
                    "UID": uid,
                    "Name": username,
                    "Cmt": content,  # Changed from "Content" to "Cmt"
                    "ProfileLink": profile_href,
                    "CommentLink": comment_link,
                    "CmtLength": len(content)
                }
                
                comments.append(comment_data)
                print(f"  ✅ Added {comment_type}: {username}")
                
            except Exception as e:
                print(f"  ✗ Error processing element {i}: {e}")
                continue
        
        print(f"\n=== SELENIUM EXTRACTION COMPLETE ===")
        print(f"Extracted {len(comments)} comments with enhanced name/link detection")
        
        return comments

    def extract_name_enhanced(self, element):
        """Enhanced name extraction with multiple strategies"""
        username = "Unknown"
        profile_href = ""
        uid = "Unknown"
        
        # Strategy 1: Direct profile links in element
        try:
            profile_links = element.find_elements(By.XPATH, ".//a[contains(@href, 'profile.php') or contains(@href, 'user.php') or contains(@href, '/profile/')]")
            
            for link in profile_links:
                try:
                    link_text = link.text.strip()
                    link_href = link.get_attribute("href") or ""
                    
                    if self.is_valid_name(link_text, link_href):
                        username = link_text
                        profile_href = link_href
                        uid = self.extract_uid_from_href(link_href)
                        print(f"    ✅ Found name via direct link: {username}")
                        return username, profile_href, uid
                except:
                    continue
        except:
            pass
        
        # Strategy 2: Look in parent elements
        try:
            parent = element.find_element(By.XPATH, "./..")
            parent_links = parent.find_elements(By.XPATH, ".//a[contains(@href, 'facebook.com')]")
            
            for link in parent_links[:3]:
                try:
                    link_text = link.text.strip()
                    link_href = link.get_attribute("href") or ""
                    
                    if self.is_valid_name(link_text, link_href):
                        username = link_text
                        profile_href = link_href
                        uid = self.extract_uid_from_href(link_href)
                        print(f"    ✅ Found name via parent: {username}")
                        return username, profile_href, uid
                except:
                    continue
        except:
            pass
        
        # Strategy 3: Look for strong/h3 tags with links
        try:
            name_elements = element.find_elements(By.XPATH, ".//strong/a | .//h3/a | .//b/a")
            for name_elem in name_elements:
                try:
                    name_text = name_elem.text.strip()
                    name_href = name_elem.get_attribute("href") or ""
                    
                    if self.is_valid_name(name_text, name_href):
                        username = name_text
                        profile_href = name_href
                        uid = self.extract_uid_from_href(name_href)
                        print(f"    ✅ Found name via strong/h3: {username}")
                        return username, profile_href, uid
                except:
                    continue
        except:
            pass
        
        # Strategy 4: Text-based name extraction
        try:
            full_text = element.text.strip()
            lines = full_text.split('\n')
            
            for line in lines[:3]:  # Check first 3 lines
                line = line.strip()
                if (line and 
                    len(line) >= 3 and 
                    len(line) <= 80 and
                    not line.startswith('http') and
                    not line.isdigit() and
                    not any(ui in line.lower() for ui in ['like', 'reply', 'share', 'comment', 'ago', 'min', 'hour'])):
                    
                    # This might be a name
                    username = line
                    print(f"    ⚠️ Guessed name from text: {username}")
                    break
        except:
            pass
        
        print(f"    ❌ Could not extract name reliably")
        return username, profile_href, uid

    def is_valid_name(self, text, href):
        """Check if text/href combination looks like a valid name"""
        if not text or not href:
            return False
        
        # Text validation
        if (len(text) < 2 or 
            len(text) > 100 or
            text.startswith('http') or
            text.isdigit() or
            any(ui in text.lower() for ui in ['like', 'reply', 'share', 'comment', 'thích', 'trả lời'])):
            return False
        
        # Href validation
        if not any(indicator in href for indicator in ['profile.php', 'user.php', '/profile/', 'facebook.com/']):
            return False
        
        return True

    def extract_uid_from_href(self, href):
        """Extract UID from profile href"""
        try:
            # Direct ID in URL
            uid_match = re.search(r'profile\.php\?id=(\d+)', href)
            if uid_match:
                return uid_match.group(1)
            
            # Username-based profile
            username_match = re.search(r'facebook\.com/([^/?]+)', href)
            if username_match:
                return username_match.group(1)
            
            return "Unknown"
        except:
            return "Unknown"

    def extract_content_enhanced(self, element, username, full_text):
        """Enhanced content extraction"""
        content_candidates = []
        
        # Strategy 1: Remove username from full text
        content = full_text
        if username != "Unknown":
            if content.startswith(username):
                content = content[len(username):].strip()
            content = re.sub(rf'\b{re.escape(username)}\b', '', content, count=1).strip()
        content_candidates.append(content)
        
        # Strategy 2: Look for content-specific elements
        try:
            # Look for elements that don't contain links (pure content)
            content_elements = element.find_elements(By.XPATH, ".//div[not(.//a) and string-length(normalize-space(text())) > 15] | .//span[not(.//a) and string-length(normalize-space(text())) > 15]")
            
            for content_elem in content_elements:
                try:
                    content_text = content_elem.text.strip()
                    if content_text and content_text != username:
                        content_candidates.append(content_text)
                except:
                    continue
        except:
            pass
        
        # Strategy 3: Look for dir="auto" elements (often comment content)
        try:
            dir_auto_elements = element.find_elements(By.XPATH, ".//*[@dir='auto' and string-length(normalize-space(text())) > 10]")
            for dir_elem in dir_auto_elements:
                try:
                    dir_text = dir_elem.text.strip()
                    if dir_text and dir_text != username:
                        content_candidates.append(dir_text)
                except:
                    continue
        except:
            pass
        
        # Choose best content
        valid_contents = []
        for candidate in content_candidates:
            cleaned = clean_text(candidate)
            if cleaned and len(cleaned) >= 10 and not self.is_ui_only_element(cleaned):
                valid_contents.append(cleaned)
        
        if not valid_contents:
            return ""
        
        # Return longest valid content
        best_content = max(valid_contents, key=len)
        return best_content

    def build_comment_link(self, element):
        """Build direct link to comment"""
        try:
            current_url = self.driver.current_url
            base_url = current_url.split('?')[0]
            
            # Method 1: Look for data-ft with comment_id
            data_ft = element.get_attribute("data-ft")
            if data_ft:
                try:
                    # Try JSON parse
                    ft_data = json.loads(data_ft)
                    if 'comment_id' in ft_data:
                        return f"{base_url}?comment_id={ft_data['comment_id']}"
                except:
                    # Try regex
                    comment_id_match = re.search(r'"comment_id":"(\d+)"', data_ft)
                    if comment_id_match:
                        return f"{base_url}?comment_id={comment_id_match.group(1)}"
            
            # Method 2: Look for comment links in element
            comment_links = element.find_elements(By.XPATH, ".//a[contains(@href, 'comment') or contains(@href, 'reply')]")
            for link in comment_links:
                href = link.get_attribute("href")
                if href and 'facebook.com' in href:
                    return href
            
            # Method 3: Look for element ID
            elem_id = element.get_attribute("id")
            if elem_id and 'comment' in elem_id:
                return f"{current_url}#{elem_id}"
            
            # Method 4: Generate approximate link
            try:
                location = element.location
                return f"{current_url}#comment_pos_{location['y']}"
            except:
                return current_url
                
        except:
            return self.driver.current_url

    def determine_comment_type_enhanced(self, element, index):
        """Enhanced comment type determination"""
        try:
            # Check indentation
            location = element.location
            if location['x'] > 50:
                return "Reply"
            
            # Check for reply indicators
            text = element.text.lower()
            if any(indicator in text for indicator in ['replied to', 'trả lời', '@', 'phản hồi']):
                return "Reply"
            
            # Check DOM nesting
            try:
                ancestors = element.find_elements(By.XPATH, "./ancestor::div[.//a[contains(@href,'profile.php')]]")
                if len(ancestors) > 1:
                    return "Reply"
            except:
                pass
            
            return "Comment"
        except:
            return "Comment"

    def is_ui_only_element(self, text):
        """Check if element is UI-only"""
        if not text or len(text.strip()) < 8:
            return True
        
        text_lower = text.lower().strip()
        
        ui_patterns = [
            r'^(like|reply|share|comment|translate|hide|report|block)(\s+\d+)?\s*$',
            r'^(thích|trả lời|chia sẻ|bình luận|dịch|ẩn|báo cáo|chặn)(\s+\d+)?\s*$',
            r'^\d+\s*(min|minutes?|hours?|days?|phút|giờ|ngày)\s*(ago|trước)?\s*$',
            r'^(view more|see more|show more|xem thêm|hiển thị thêm)\s*$'
        ]
        
        for pattern in ui_patterns:
            if re.match(pattern, text_lower):
                return True
        
        return False

    def scrape_all_comments(self, limit=0, progress_callback=None):
        """Main scraping method with enhanced name and link extraction"""
        print("=== STARTING ENHANCED SCRAPING ===")
        
        # Try JavaScript extraction first
        comments = self.extract_names_and_links_with_javascript()
        
        # If JavaScript fails, use enhanced Selenium
        if not comments:
            print("JavaScript extraction failed, trying enhanced Selenium...")
            comments = self.enhanced_selenium_extraction()
        
        # Apply limit
        if limit > 0:
            comments = comments[:limit]
        
        # Final organization
        comments = self.organize_final_comments(comments)
        
        # Progress callback
        if progress_callback:
            progress_callback(len(comments))
        
        return comments

    def organize_final_comments(self, comments):
        """Final organization and deduplication"""
        print("=== ORGANIZING FINAL COMMENTS ===")
        
        # Remove duplicates
        unique_comments = []
        seen_combinations = set()
        
        for comment in comments:
            # Create multiple deduplication keys
            keys = [
                f"{comment['Name']}_{comment['Cmt'][:40]}",
                comment['Cmt'][:60] if len(comment['Cmt']) > 60 else comment['Cmt'],
                f"{comment['UID']}_{comment['Cmt'][:30]}" if comment['UID'] != "Unknown" else None
            ]
            
            is_duplicate = any(key in seen_combinations for key in keys if key)
            
            if not is_duplicate:
                unique_comments.append(comment)
                for key in keys:
                    if key:
                        seen_combinations.add(key)
        
        # Sort: Comments first, then replies
        unique_comments.sort(key=lambda x: (x['Type'] == 'Reply', x.get('Position', '0,0')))
        
        print(f"Final organized comments: {len(unique_comments)}")
        return unique_comments

    def close(self):
        try: 
            self.driver.quit()
        except: 
            pass

# ----------------------------
# Improved GUI with better column naming
# ----------------------------
class FBImprovedAppGUI:
    def __init__(self, root):
        self.root = root
        root.title("🔥 FB Comment Scraper - Enhanced Name & Link Extraction")
        root.geometry("1050x850")
        root.configure(bg="#f0f8ff")

        main_frame = tk.Frame(root, bg="#f0f8ff")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # Title
        title_label = tk.Label(main_frame, text="🔥 FB Enhanced Comment Scraper", 
                              font=("Arial", 20, "bold"), bg="#f0f8ff", fg="#0066cc")
        title_label.pack(pady=(0,10))
        
        subtitle_label = tk.Label(main_frame, text="✨ Cải thiện extraction tên người viết và link comment", 
                                 font=("Arial", 12), bg="#f0f8ff", fg="#0066cc")
        subtitle_label.pack(pady=(0,20))

        # Input section
        input_frame = tk.LabelFrame(main_frame, text="📝 Thông tin đầu vào", font=("Arial", 12, "bold"), 
                                   bg="#f0f8ff", fg="#0066cc", relief="groove", bd=2)
        input_frame.pack(fill="x", pady=(0,15))

        tk.Label(input_frame, text="🔗 Link Facebook (Groups/Posts):", bg="#f0f8ff", font=("Arial", 10)).pack(anchor="w", padx=15, pady=(15,5))
        self.entry_url = tk.Entry(input_frame, width=100, font=("Arial", 9))
        self.entry_url.pack(fill="x", padx=15, pady=(0,10))

        tk.Label(input_frame, text="🍪 Cookie Facebook:", bg="#f0f8ff", font=("Arial", 10)).pack(anchor="w", padx=15, pady=(5,5))
        self.txt_cookie = tk.Text(input_frame, height=4, font=("Arial", 8))
        self.txt_cookie.pack(fill="x", padx=15, pady=(0,15))

        # Options section
        options_frame = tk.LabelFrame(main_frame, text="⚙️ Tùy chọn", font=("Arial", 12, "bold"), 
                                     bg="#f0f8ff", fg="#0066cc", relief="groove", bd=2)
        options_frame.pack(fill="x", pady=(0,15))
        
        opt_grid = tk.Frame(options_frame, bg="#f0f8ff")
        opt_grid.pack(fill="x", padx=15, pady=15)
        
        tk.Label(opt_grid, text="📊 Số lượng comment:", bg="#f0f8ff").grid(row=0, column=0, sticky="w")
        self.entry_limit = tk.Entry(opt_grid, width=10)
        self.entry_limit.insert(0, "0")
        self.entry_limit.grid(row=0, column=1, sticky="w", padx=(10,30))
        tk.Label(opt_grid, text="(0 = tất cả)", bg="#f0f8ff", fg="#6c757d").grid(row=0, column=2, sticky="w")

        self.headless_var = tk.BooleanVar(value=False)  # Default to visible for debugging
        tk.Checkbutton(opt_grid, text="👻 Chạy ẩn (headless)", variable=self.headless_var, 
                      bg="#f0f8ff", font=("Arial", 9)).grid(row=1, column=0, sticky="w", pady=(10,0))

        # File output section
        file_frame = tk.LabelFrame(main_frame, text="💾 File xuất kết quả", font=("Arial", 12, "bold"), 
                                  bg="#f0f8ff", fg="#0066cc", relief="groove", bd=2)
        file_frame.pack(fill="x", pady=(0,15))
        
        file_row = tk.Frame(file_frame, bg="#f0f8ff")
        file_row.pack(fill="x", padx=15, pady=15)
        
        self.entry_file = tk.Entry(file_row, width=70, font=("Arial", 9))
        self.entry_file.insert(0, "facebook_comments_enhanced.xlsx")
        self.entry_file.pack(side="left", fill="x", expand=True)
        
        tk.Button(file_row, text="📁 Chọn file", command=self.choose_file, 
                 bg="#17a2b8", fg="white", font=("Arial", 9)).pack(side="right", padx=(10,0))

        # Preview section
        preview_frame = tk.LabelFrame(main_frame, text="📋 Cấu trúc dữ liệu xuất", font=("Arial", 12, "bold"), 
                                     bg="#f0f8ff", fg="#0066cc", relief="groove", bd=2)
        preview_frame.pack(fill="x", pady=(0,15))
        
        preview_text = """📊 Các cột sẽ được xuất:
• STT - Số thứ tự
• Type - Loại (Comment/Reply)  
• UID - ID người dùng
• Name - Tên người viết comment ✨
• Cmt - Nội dung comment ✨ (đã đổi từ Content)
• ProfileLink - Link profile người viết ✨
• CommentLink - Link trực tiếp đến comment ✨ (MỚI)
• CmtLength - Độ dài comment"""
        
        tk.Label(preview_frame, text=preview_text, bg="#f0f8ff", fg="#2d5a2d", 
                justify="left", font=("Arial", 9)).pack(anchor="w", padx=15, pady=15)

        # Status section
        status_frame = tk.LabelFrame(main_frame, text="📊 Trạng thái", font=("Arial", 12, "bold"), 
                                    bg="#f0f8ff", fg="#0066cc", relief="groove", bd=2)
        status_frame.pack(fill="x", pady=(0,15))
        
        self.lbl_status = tk.Label(status_frame, text="✅ Sẵn sàng - Enhanced scraper với name & link extraction", fg="#28a745", 
                                  wraplength=950, justify="left", font=("Arial", 11), bg="#f0f8ff")
        self.lbl_status.pack(anchor="w", padx=15, pady=(15,5))

        self.lbl_progress_detail = tk.Label(status_frame, text="💡 Scraper này sẽ tự động detect layout, extract tên chính xác và tạo link trực tiếp đến comment", 
                                          fg="#6c757d", wraplength=950, justify="left", font=("Arial", 9), bg="#f0f8ff")
        self.lbl_progress_detail.pack(anchor="w", padx=15, pady=(0,10))

        # Progress bar
        self.progress_bar = ttk.Progressbar(status_frame, mode='indeterminate')
        self.progress_bar.pack(fill="x", padx=15, pady=(0,15))

        # Control buttons
        button_frame = tk.Frame(main_frame, bg="#f0f8ff")
        button_frame.pack(fill="x", pady=20)
        
        self.btn_start = tk.Button(button_frame, text="🚀 Bắt đầu Enhanced Scraping", bg="#28a745", fg="white", 
                                  font=("Arial", 14, "bold"), command=self.start_scrape_thread, 
                                  pady=12, padx=40)
        self.btn_start.pack(side="left")

        self.btn_stop = tk.Button(button_frame, text="⏹️ Dừng lại", bg="#dc3545", fg="white", 
                                 font=("Arial", 14, "bold"), command=self.stop_scrape, 
                                 state=tk.DISABLED, pady=12, padx=40)
        self.btn_stop.pack(side="left", padx=(25,0))

        self.progress_var = tk.IntVar(value=0)
        self.progress_label = tk.Label(button_frame, textvariable=self.progress_var, fg="#28a745", 
                                     font=("Arial", 18, "bold"), bg="#f0f8ff")
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
        file_out = self.entry_file.get().strip() or "facebook_comments_enhanced.xlsx"
        
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
        self.lbl_status.config(text="🔄 Đang khởi động enhanced scraper...", fg="#fd7e14")
        self.lbl_progress_detail.config(text="⏳ Đang chuẩn bị extraction tên và link comment...")
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
        self.lbl_status.config(text="⏹️ Đang dừng...", fg="#dc3545")
        self.btn_stop.config(state=tk.DISABLED)

    def _progress_cb(self, count):
        self.progress_var.set(count)
        self.lbl_status.config(text=f"📈 Đang extract... Đã lấy {count} comment với tên & link", fg="#28a745")
        self.root.update_idletasks()

    def _scrape_worker(self, url, cookie_str, file_out, limit, headless):
        try:
            # Initialize
            self.lbl_status.config(text="🌐 Khởi tạo enhanced scraper...", fg="#fd7e14")
            self.scraper = FacebookImprovedScraper(cookie_str, headless=headless)
            
            if self._stop_flag: return
            
            # Load post
            self.lbl_status.config(text="📄 Đang tải và phân tích trang...", fg="#fd7e14")
            self.lbl_progress_detail.config(text="⏳ Đang load page và detect layout...")
            success = self.scraper.load_post(url)
            
            if not success:
                self.lbl_status.config(text="❌ Không thể tải trang", fg="#dc3545")
                self.lbl_progress_detail.config(text="💡 Kiểm tra: Cookie có hợp lệ? Link có đúng? Thử tắt headless")
                return
            
            layout = getattr(self.scraper, 'current_layout', 'unknown')
            self.lbl_progress_detail.config(text=f"🎯 Detected layout: {layout} - Optimizing extraction...")
                
            if self._stop_flag: return
            
            # Scrape with enhanced extraction
            self.lbl_status.config(text="🔍 Đang extract tên, comment và link...", fg="#fd7e14")
            self.lbl_progress_detail.config(text="⏳ Sử dụng JavaScript + Selenium để extract chính xác...")
            
            comments = self.scraper.scrape_all_comments(limit=limit, progress_callback=self._progress_cb)
            
            if self._stop_flag: return
            
            # Save results
            self.lbl_status.config(text="💾 Đang lưu kết quả...", fg="#fd7e14")
            
            if comments:
                df = pd.DataFrame(comments)
                
                # Add useful metadata
                df.insert(0, 'STT', range(1, len(df) + 1))
                df['Layout'] = layout
                df['ExtractedAt'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Reorder columns for better display
                column_order = ['STT', 'Type', 'Name', 'Cmt', 'UID', 'ProfileLink', 'CommentLink', 'CmtLength', 'Layout', 'ExtractedAt']
                df = df.reindex(columns=[col for col in column_order if col in df.columns])
                
                # Save file
                if not file_out.lower().endswith((".xlsx", ".csv")):
                    file_out += ".xlsx"
                
                if file_out.lower().endswith(".csv"):
                    df.to_csv(file_out, index=False, encoding="utf-8-sig")
                else:
                    df.to_excel(file_out, index=False, engine="openpyxl")
                
                # Calculate statistics
                comments_count = len([c for c in comments if c['Type'] == 'Comment'])
                replies_count = len([c for c in comments if c['Type'] == 'Reply'])
                named_comments = len([c for c in comments if c['Name'] != 'Unknown'])
                with_links = len([c for c in comments if c.get('CommentLink', '').startswith('http')])
                
                self.lbl_status.config(text=f"🎉 HOÀN THÀNH! Đã lưu {len(comments)} comment/reply", fg="#28a745")
                self.lbl_progress_detail.config(text=f"📊 {comments_count} comments + {replies_count} replies | {named_comments} có tên | {with_links} có link | Layout: {layout} | File: {file_out}")
                
            else:
                self.lbl_status.config(text="⚠️ Không extract được comment nào", fg="#ffc107")
                self.lbl_progress_detail.config(text=f"💡 Layout: {layout} | Kiểm tra debug files hoặc thử scraper khác")
                
        except Exception as e:
            error_msg = str(e)[:120]
            self.lbl_status.config(text=f"❌ Lỗi: {error_msg}...", fg="#dc3545")
            self.lbl_progress_detail.config(text="🔍 Xem console để biết chi tiết lỗi")
            print(f"Enhanced scraping error: {e}")
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
    app = FBImprovedAppGUI(root)
    root.mainloop()