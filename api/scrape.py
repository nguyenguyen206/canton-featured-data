"""
Vercel Serverless Function - Live scrape Canton Featured Apps
Scrapes data directly from lists.sync.global API on each request.
Uses Cache-Control for CDN caching (1 hour) to avoid overloading the source.
"""

import json
import re
import time
from http.server import BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from html.parser import HTMLParser


# ============================================================
# Lightweight HTML parser (no BeautifulSoup dependency needed)
# ============================================================

class TopicParser(HTMLParser):
    """Parse topics from the list page HTML."""
    
    def __init__(self):
        super().__init__()
        self.topics = []
        self.next_page = None
        self.next_after = None
        self.total = 0
        
        self._in_subject_link = False
        self._current_href = ""
        self._current_title = ""
        self._in_truncate = False
        self._current_desc = ""
        self._in_pagination_info = False
        self._pagination_text = ""
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        
        # Subject links: <a class="showvisited subject" href="/g/tokenomics/topic/...">
        if tag == "a":
            cls = attrs_dict.get("class", "")
            href = attrs_dict.get("href", "")
            if "subject" in cls and "/topic/" in href:
                self._in_subject_link = True
                self._current_href = href
                self._current_title = ""
            # Pagination next: <a rel="next" href="...?page=2&after=123">
            rel = attrs_dict.get("rel", "")
            if rel == "next":
                m = re.search(r'page=(\d+)&after=(\d+)', href)
                if m:
                    self.next_page = int(m.group(1))
                    self.next_after = m.group(2)
        
        # Truncated description div
        if tag == "div":
            cls = attrs_dict.get("class", "")
            if "truncate-one-line" in cls:
                self._in_truncate = True
                self._current_desc = ""
    
    def handle_endtag(self, tag):
        if tag == "a" and self._in_subject_link:
            self._in_subject_link = False
            if "Featured App Request" in self._current_title:
                self.topics.append({
                    "href": self._current_href,
                    "title": self._current_title.strip(),
                    "desc": "",
                })
        
        if tag == "div" and self._in_truncate:
            self._in_truncate = False
            # Attach desc to the last topic
            if self.topics and not self.topics[-1]["desc"]:
                self.topics[-1]["desc"] = self._current_desc.strip()
    
    def handle_data(self, data):
        if self._in_subject_link:
            self._current_title += data
        if self._in_truncate:
            self._current_desc += data


def fetch_page(url, cookie_val):
    """Fetch a page from the API."""
    headers = {
        "Accept": "*/*",
        "Accept-Language": "en,vi;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Referer": "https://lists.sync.global/g/tokenomics/topics?sidebar=true",
        "Hx-History-Restore-Request": "true",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
        "Cookie": f"g._={cookie_val}",
    }
    req = Request(url, headers=headers)
    with urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")


def extract_app_info(title, desc):
    """Extract structured app info from title and description."""
    # Parse title
    title_match = re.search(r'Featured App Request:\s*(.+?)(?:\s*-\s*(.+))?$', title)
    project_name = ""
    app_name = ""
    if title_match:
        project_name = title_match.group(1).strip()
        app_name = title_match.group(2).strip() if title_match.group(2) else project_name
    
    # Extract from description
    # Institution name
    inst_match = re.search(r'Name of applying institution\s+(.+?)(?:\s+Summary of Company)', desc)
    if inst_match:
        project_name = inst_match.group(1).strip()
    
    # App name from form
    form_app_match = re.search(r'Name of the application:\s*(.+?)(?:\s+Disclaimer|\s+URL|\s+Email)', desc)
    if form_app_match:
        app_name = form_app_match.group(1).strip()
    
    # Product Website
    app_url = ""
    pw_match = re.search(r'Product Website\s+(https?://[^\s]+)', desc)
    if pw_match:
        app_url = pw_match.group(1).strip()
    
    if not app_url:
        iu_match = re.search(r'URL of the applying institution\s+(https?://[^\s]+)', desc)
        if iu_match:
            app_url = iu_match.group(1).strip()
    
    # Institution URL
    institution_url = ""
    iu_match2 = re.search(r'URL of the applying institution\s+(https?://[^\s]+)', desc)
    if iu_match2:
        institution_url = iu_match2.group(1).strip()
    
    # Summary
    summary = ""
    sum_match = re.search(r'Provide a summary of what your application will do:\s*(.+?)(?:\s*Describe the expected users)', desc, re.DOTALL)
    if sum_match:
        summary = sum_match.group(1).strip()[:300]
    
    # Entry ID
    entry_id = ""
    eid_match = re.search(r'Entry ID:\s*(\d+)', desc)
    if eid_match:
        entry_id = eid_match.group(1)
    
    # Topic ID from href
    topic_id = ""
    
    return {
        "entry_id": entry_id,
        "project_name": project_name,
        "app_name": app_name,
        "app_url": app_url,
        "institution_url": institution_url,
        "product_website": app_url,
        "summary": summary,
        "title": title,
    }


def scrape_all():
    """Scrape all featured app topics."""
    cookie_val = "v1:1280x720|Win32|Asia/Saigon|12|8:1774177567:05fa9fd0f83f2e68856b256a0d80076856ab5270ecf3e0c6fa2c9890f8197d9b"
    
    all_apps = []
    page_num = 1
    after_id = None
    
    for _ in range(40):  # Max 40 pages safety
        if page_num == 1:
            url = "https://lists.sync.global/g/tokenomics/topics?sidebar=true"
        else:
            url = f"https://lists.sync.global/g/tokenomics/topics?page={page_num}&after={after_id}&sidebar=true"
        
        try:
            html = fetch_page(url, cookie_val)
        except Exception as e:
            print(f"Error fetching page {page_num}: {e}")
            break
        
        parser = TopicParser()
        parser.feed(html)
        
        if not parser.topics:
            break
        
        for topic in parser.topics:
            info = extract_app_info(topic["title"], topic["desc"])
            # Extract topic_id from href
            m = re.search(r'/topic/[^/]+/(\d+)', topic["href"])
            if m:
                info["topic_id"] = m.group(1)
            all_apps.append(info)
        
        if parser.next_page and parser.next_after:
            page_num = parser.next_page
            after_id = parser.next_after
            time.sleep(0.1)  # Minimal delay
        else:
            break
    
    # Deduplicate
    seen = set()
    unique = []
    for app in all_apps:
        tid = app.get("topic_id", app["title"])
        if tid not in seen:
            seen.add(tid)
            unique.append(app)
    
    return unique


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            apps = scrape_all()
            result = {
                "count": len(apps),
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "apps": apps,
            }
            body = json.dumps(result, ensure_ascii=False).encode("utf-8")
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            # Cache for 1 hour on Vercel CDN, serve stale for 24h while revalidating
            self.send_header("Cache-Control", "s-maxage=3600, stale-while-revalidate=86400")
            self.end_headers()
            self.wfile.write(body)
            
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
