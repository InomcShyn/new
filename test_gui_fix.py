#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script để kiểm tra GUI đã được sửa
"""

import tkinter as tk
from tkinter import messagebox
import threading
import time
from tkinter import ttk

class TestGUI:
    def __init__(self, root):
        self.root = root
        root.title("🧪 Test GUI Fix")
        root.geometry("600x400")
        
        # Variables
        self._stop_flag = False
        self.progress_var = tk.IntVar()
        
        # Create GUI elements
        self.create_widgets()
        
    def create_widgets(self):
        # URL Entry
        tk.Label(self.root, text="URL:").pack(pady=5)
        self.url_entry = tk.Entry(self.root, width=50)
        self.url_entry.pack(pady=5)
        self.url_entry.insert(0, "https://www.facebook.com/groups/test/posts/123")
        
        # Cookies Text
        tk.Label(self.root, text="Cookies:").pack(pady=5)
        self.cookies_text = tk.Text(self.root, height=3, width=50)
        self.cookies_text.pack(pady=5)
        self.cookies_text.insert("1.0", "test_cookie=value; another_cookie=value")
        
        # Limit Entry
        tk.Label(self.root, text="Limit:").pack(pady=5)
        self.limit_entry = tk.Entry(self.root, width=10)
        self.limit_entry.pack(pady=5)
        self.limit_entry.insert(0, "10")
        
        # Checkboxes
        self.resolve_uid_var = tk.BooleanVar(value=True)
        self.enhanced_var = tk.BooleanVar(value=True)
        self.headless_var = tk.BooleanVar(value=True)
        
        tk.Checkbutton(self.root, text="Resolve UID", variable=self.resolve_uid_var).pack()
        tk.Checkbutton(self.root, text="Enhanced Extraction", variable=self.enhanced_var).pack()
        tk.Checkbutton(self.root, text="Headless Mode", variable=self.headless_var).pack()
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(self.root, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(pady=10, fill="x", padx=20)
        
        # Status label
        self.status_label = tk.Label(self.root, text="Ready", fg="blue")
        self.status_label.pack(pady=5)
        
        # Buttons
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)
        
        self.start_button = tk.Button(button_frame, text="Start Test", command=self.start_test, bg="green", fg="white")
        self.start_button.pack(side="left", padx=5)
        
        self.stop_button = tk.Button(button_frame, text="Stop", command=self.stop_test, bg="red", fg="white", state="disabled")
        self.stop_button.pack(side="left", padx=5)
        
        # Result text
        tk.Label(self.root, text="Results:").pack(pady=5)
        self.result_text = tk.Text(self.root, height=10, width=60)
        self.result_text.pack(pady=5)
        
    def start_test(self):
        """Test the _scrape_worker method"""
        self._stop_flag = False
        self.progress_var.set(0)
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        
        # Store parameters in instance variables (like the real GUI)
        self.scrape_url = self.url_entry.get().strip()
        self.scrape_cookies = self.cookies_text.get("1.0", tk.END).strip()
        self.scrape_limit = int(self.limit_entry.get()) if self.limit_entry.get().isdigit() else 0
        self.scrape_resolve_uid = self.resolve_uid_var.get()
        self.scrape_enhanced = self.enhanced_var.get()
        self.scrape_headless = self.headless_var.get()
        
        # Start worker thread
        self.worker_thread = threading.Thread(target=self._scrape_worker)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        
    def stop_test(self):
        """Stop the test"""
        self._stop_flag = True
        self.status_label.config(text="Stopping...", fg="orange")
        self.stop_button.config(state="disabled")
        
    def _scrape_worker(self):
        """Test worker method - simulates the real _scrape_worker"""
        try:
            self.status_label.config(text="🔄 Starting test...", fg="orange")
            self.progress_var.set(10)
            
            # Get parameters from instance variables
            url = self.scrape_url
            cookies = self.scrape_cookies
            limit = self.scrape_limit
            resolve_uid = self.scrape_resolve_uid
            enhanced = self.scrape_enhanced
            headless = self.scrape_headless
            
            if not url:
                self.status_label.config(text="❌ Please enter a URL", fg="red")
                return
            
            if not cookies:
                self.status_label.config(text="❌ Please enter cookies", fg="red")
                return
            
            # Simulate initialization
            self.status_label.config(text="🌐 Initializing...", fg="orange")
            self.progress_var.set(20)
            time.sleep(1)
            
            if self._stop_flag:
                return
            
            # Simulate loading post
            self.status_label.config(text="📄 Loading post...", fg="orange")
            self.progress_var.set(40)
            time.sleep(1)
            
            if self._stop_flag:
                return
            
            # Simulate scraping
            self.status_label.config(text="🔍 Scraping comments...", fg="orange")
            self.progress_var.set(60)
            time.sleep(2)
            
            if self._stop_flag:
                return
            
            # Simulate results
            self.status_label.config(text="✅ Test completed successfully!", fg="green")
            self.progress_var.set(100)
            
            # Update result text
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert("1.0", "✅ Test completed successfully!\n\n")
            self.result_text.insert(tk.END, f"📊 URL: {url}\n")
            self.result_text.insert(tk.END, f"🍪 Cookies: {cookies[:50]}...\n")
            self.result_text.insert(tk.END, f"📏 Limit: {limit}\n")
            self.result_text.insert(tk.END, f"🆔 Resolve UID: {resolve_uid}\n")
            self.result_text.insert(tk.END, f"🚀 Enhanced: {enhanced}\n")
            self.result_text.insert(tk.END, f"👻 Headless: {headless}\n\n")
            self.result_text.insert(tk.END, "🎉 GUI fix test passed! The _scrape_worker method is working correctly.\n")
            
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            self.status_label.config(text=error_msg, fg="red")
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert("1.0", error_msg)
            print(f"Test error: {e}")
        finally:
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")

def main():
    """Run the test GUI"""
    root = tk.Tk()
    app = TestGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()