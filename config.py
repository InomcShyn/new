#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration file for Enhanced Facebook Groups Comment Scraper
"""

# ============================================================================
# SCRAPER CONFIGURATION
# ============================================================================

# Browser settings
BROWSER_CONFIG = {
    'headless': False,  # Set to True for headless mode
    'window_size': '414,896',  # Mobile viewport
    'user_agent': 'Mozilla/5.0 (Android 10; Mobile; rv:109.0) Gecko/111.0 Firefox/109.0',
    'timeout': 15,  # WebDriverWait timeout
    'page_load_timeout': 30,
}

# Scraping settings
SCRAPING_CONFIG = {
    'max_expansion_iterations': 120,  # Maximum iterations for expanding comments
    'consecutive_failure_limit': 8,   # Stop after N consecutive failures
    'scroll_delay': (2, 3),           # Random delay range for scrolling
    'click_delay': (2, 4),            # Random delay range for clicking
    'expansion_delay': (1.5, 2),      # Delay between expansions
}

# Content processing settings
CONTENT_CONFIG = {
    'min_content_length': 8,          # Minimum content length to consider valid
    'max_content_length': 500,        # Maximum content length (to avoid UI elements)
    'min_username_length': 2,         # Minimum username length
    'max_username_length': 50,        # Maximum username length
    'enable_enhanced_extraction': True,  # Use enhanced extraction methods
    'enable_user_verification': True,    # Detect verified users
    'enable_display_name': True,         # Extract display names
}

# ============================================================================
# SELECTORS CONFIGURATION
# ============================================================================

# Mobile layout selectors
MOBILE_SELECTORS = {
    'expand_links': [
        "//a[contains(text(),'View more comments')]",
        "//a[contains(text(),'View previous comments')]",
        "//a[contains(text(),'View more replies')]",
        "//a[contains(text(),'Show more')]",
        "//a[contains(text(),'See more')]",
        "//a[contains(text(),'Xem thêm')]",
        "//a[contains(text(),'Hiển thị thêm')]",
        "//div[@role='button' and (contains(text(),'more') or contains(text(),'thêm'))]",
        "//span[contains(text(),'View') and contains(text(),'more')]/ancestor::*[@role='button' or self::a][1]",
        "//div[@data-sigil='more' or @data-sigil='expand']",
        "//*[contains(@data-sigil,'comment')]//*[contains(text(),'more') or contains(text(),'thêm')]"
    ],
    'comment_containers': [
        "//div[@data-sigil='comment']",
        "//div[@data-sigil='comment-body']", 
        "//div[contains(@data-ft, 'comment')]",
        "//div[contains(@id, 'comment_')]",
        "//article//div[.//a[contains(@href, 'profile.php')]]",
        "//div[@role='article']//div[.//a[contains(@href, 'profile.php')]]",
        "//div[contains(@class, 'story_body_container')]//div[.//a[contains(@href, 'profile.php')]]",
        "//div[.//strong/a[contains(@href, 'profile.php')]]",
        "//div[.//h3/a[contains(@href, 'profile.php')]]",
        "//div[.//span/a[contains(@href, 'profile.php')]]",
        "//div[.//a[contains(@href, 'facebook.com/')] and string-length(normalize-space(text())) > 25]",
        "//div[string-length(normalize-space(text())) > 40 and .//a[contains(@href, 'profile')]]"
    ],
    'profile_links': [
        ".//a[contains(@href, 'profile.php')]",
        ".//a[contains(@href, 'user.php')]",
        ".//a[contains(@href, '/profile/')]",
        ".//strong/a[contains(@href, 'facebook.com/')]",
        ".//h3/a[contains(@href, 'facebook.com/')]",
        ".//span/a[contains(@href, 'facebook.com/')]",
        ".//div[@role='link']/a[contains(@href, 'facebook.com/')]",
        ".//a[contains(@data-sigil, 'profile')]"
    ],
    'comment_bodies': [
        ".//div[@data-sigil='comment-body']",
        ".//span[@data-sigil='comment-body']",
        ".//div[contains(@class, 'comment-body')]",
        ".//div[contains(@class, 'comment-text')]",
        ".//div[contains(@class, 'story_body')]",
        ".//div[contains(@data-ft, 'comment')]//div[not(.//a[contains(@href, 'profile.php')])]"
    ]
}

# Mbasic layout selectors
MBASIC_SELECTORS = {
    'expand_links': [
        "//a[contains(text(),'View more comments')]",
        "//a[contains(text(),'View previous comments')]",
        "//a[contains(text(),'View more replies')]", 
        "//a[contains(text(),'Show more')]",
        "//a[contains(text(),'See more')]",
        "//a[contains(text(),'Xem thêm')]",
        "//a[contains(@href,'comment') and contains(text(),'more')]",
        "//a[contains(@href,'reply') and contains(text(),'more')]"
    ],
    'comment_containers': [
        "//div[@data-ft and contains(@data-ft, 'comment')]",
        "//div[contains(@id, 'comment_')]",
        "//table//div[.//a[contains(@href, 'profile.php')]]",
        "//div[.//a[contains(@href, 'profile.php?id=')]]",
        "//div[.//a[contains(@href, 'user.php?id=')]]",
        "//div[.//h3/a[contains(@href, 'profile.php')]]"
    ]
}

# ============================================================================
# PATTERNS CONFIGURATION
# ============================================================================

# UI patterns to remove
UI_PATTERNS = [
    r'\b(Like|Reply|Share|Comment|Translate|Hide|Report|Block)\b',
    r'\b(Thích|Trả lời|Chia sẻ|Bình luận|Dịch|Ẩn|Báo cáo|Chặn)\b',
    r'\b\d+\s*(min|minutes?|hours?|days?|seconds?|phút|giờ|ngày|giây)\s*(ago|trước)?\b',
    r'\b(Top fan|Most relevant|Newest|All comments|Bình luận hàng đầu)\b',
    r'\b(View more|See more|Show more|Xem thêm|Hiển thị thêm)\b',
    r'\b(Write a comment|Viết bình luận)\b',
    r'^\d+\s*(like|love|reaction|thích|yêu|cảm xúc)\s*$',
    r'^(See translation|Xem bản dịch|Translate|Dịch)\s*$'
]

# UI-only content patterns
UI_ONLY_PATTERNS = [
    r'^(like|reply|share|comment|translate|hide|report|block)(\s+\d+)?\s*$',
    r'^(thích|trả lời|chia sẻ|bình luận|dịch|ẩn|báo cáo|chặn)(\s+\d+)?\s*$',
    r'^\d+\s*(min|minutes?|hours?|days?|phút|giờ|ngày)\s*(ago|trước)?\s*$',
    r'^(top fan|most relevant|newest|all comments|view more|see more)\s*$',
    r'^(bình luận hàng đầu|xem thêm|hiển thị thêm)\s*$',
    r'^\d+\s*(like|love|reaction|thích|yêu|cảm xúc)\s*$',
    r'^(see translation|xem bản dịch|translate|dịch)\s*$',
    r'^(write a comment|viết bình luận|comment|bình luận)\s*$',
    r'^(group|nhóm|groups|các nhóm)\s*$',
    r'^[^\wÀ-ỹ]*$',  # Only punctuation/symbols
    r'^\d+$',  # Only numbers
    r'^[a-z]{1,3}\s*$'  # Very short text
]

# Invalid username patterns
INVALID_USERNAME_PATTERNS = [
    'like', 'reply', 'share', 'comment', 'translate', 'hide', 'report', 'block',
    'thích', 'trả lời', 'chia sẻ', 'bình luận', 'dịch', 'ẩn', 'báo cáo', 'chặn'
]

# Reply indicators
REPLY_INDICATORS = [
    'replied to', 'replying to', 'in reply to', 
    'trả lời', 'phản hồi', 'đáp lại',
    '@', 'reply:', 'phản hồi:', 'đáp:'
]

# ============================================================================
# OUTPUT CONFIGURATION
# ============================================================================

# Default output settings
OUTPUT_CONFIG = {
    'default_filename': 'enhanced_facebook_groups_comments.xlsx',
    'encoding': 'utf-8-sig',
    'include_metadata': True,
    'include_timestamp': True,
    'include_source': True,
    'include_enhanced_flag': True,
}

# Excel formatting
EXCEL_CONFIG = {
    'sheet_name': 'Facebook Groups Comments',
    'auto_filter': True,
    'freeze_panes': 'A2',
    'column_widths': {
        'A': 8,   # STT
        'B': 15,  # UID
        'C': 25,  # Name
        'D': 25,  # DisplayName
        'E': 50,  # Content
        'F': 40,  # ProfileLink
        'G': 10,  # Verified
        'H': 12,  # Type
        'I': 12,  # Layout
        'J': 15,  # ContentLength
        'K': 20,  # Source
        'L': 20,  # ScrapedAt
        'M': 20,  # EnhancedExtraction
    }
}

# ============================================================================
# DEBUG CONFIGURATION
# ============================================================================

# Debug settings
DEBUG_CONFIG = {
    'save_html_debug': True,
    'debug_filename_prefix': 'debug_groups_',
    'verbose_logging': True,
    'print_progress': True,
    'show_element_details': False,
}

# ============================================================================
# VALIDATION CONFIGURATION
# ============================================================================

# Validation settings
VALIDATION_CONFIG = {
    'validate_usernames': True,
    'validate_content': True,
    'check_duplicates': True,
    'remove_ui_only': True,
    'min_confidence_score': 0.7,
}

# ============================================================================
# PERFORMANCE CONFIGURATION
# ============================================================================

# Performance settings
PERFORMANCE_CONFIG = {
    'enable_caching': True,
    'cache_size': 1000,
    'parallel_processing': False,
    'max_workers': 4,
    'chunk_size': 100,
}

# ============================================================================
# ERROR HANDLING CONFIGURATION
# ============================================================================

# Error handling settings
ERROR_CONFIG = {
    'max_retries': 3,
    'retry_delay': 2,
    'continue_on_error': True,
    'log_errors': True,
    'save_error_log': True,
}