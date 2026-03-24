"""
Scrape Canton Featured App Requests from lists.sync.global
- Uses API with pagination to get ALL topics
- Parses data inline from the list page (full details are embedded in each topic row)
- Extracts: Project Name, App Name, App URL, Category/Description
- Saves results to CSV and JSON
"""

import requests
import re
import json
import time
import csv
import datetime
from bs4 import BeautifulSoup

COOKIE_VAL = "v1:1280x720|Win32|Asia/Saigon|12|8:1774177567:05fa9fd0f83f2e68856b256a0d80076856ab5270ecf3e0c6fa2c9890f8197d9b"

HEADERS = {
    "accept": "*/*",
    "accept-language": "en,vi;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,ja;q=0.5",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "referer": "https://lists.sync.global/g/tokenomics/topics?sidebar=true",
    "hx-history-restore-request": "true",
    "sec-ch-ua-mobile": "?0",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
}

session = requests.Session()
session.cookies.set("g._", COOKIE_VAL, domain="lists.sync.global")
session.headers.update(HEADERS)


def get_topics_page(page_num=1, after_id=None):
    """Get a page of topics."""
    if page_num == 1:
        url = "https://lists.sync.global/g/tokenomics/topics?sidebar=true"
    else:
        url = f"https://lists.sync.global/g/tokenomics/topics?page={page_num}&after={after_id}&sidebar=true"
    
    for attempt in range(3):
        try:
            resp = session.get(url, timeout=30)
            return resp.text
        except requests.exceptions.RequestException as e:
            print(f"  [Error] Request failed on attempt {attempt+1}: {e}")
            time.sleep(5)
            
    print("  [Error] Failed to fetch page after 3 retries.")
    return ""


def extract_field(text, field_name):
    """Extract a field value from the description text."""
    # Try pattern: "Field Name: value" or "Field Name value"
    patterns = [
        rf'{field_name}\s*[:\-]\s*(.+?)(?=\s*(?:Disclaimer|Email|Name of applying|Summary of Company|URL of the applying|Product Website|Party ID|Link to Brand|Demo Video|Provide a summary|Describe the expected|How will your|Describe how your|Describe the activities|Does this activity|On a per user|Under what conditions|How do you expect|What is your anticipated|Who will be your|$))',
        rf'{field_name}\s+(.+?)(?=\s+(?:Disclaimer|Email|Name of applying|URL of|Product Website|Party ID))',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1).strip()
    return ""


def parse_topics_from_html(html_content):
    """Parse all topic data from the HTML page."""
    soup = BeautifulSoup(html_content, "html.parser")
    topics = []
    
    # Find all topic rows - they have links with href containing /topic/
    subject_links = soup.select("a.subject[href*='/topic/']")
    
    for link in subject_links:
        href = link.get("href", "")
        title = link.get_text(strip=True)
        
        # Skip non-Featured App Request topics
        if "Featured App Request" not in title:
            continue
        
        # Parse topic ID from href
        match = re.search(r'/topic/([^/]+)/(\d+)', href)
        if not match:
            continue
        
        topic_type = match.group(1)
        topic_id = match.group(2)
        
        # Parse title: "Featured App Request: CompanyName - AppName"
        title_match = re.search(r'Featured App Request:\s*(.+?)(?:\s*-\s*(.+))?$', title)
        project_name = ""
        app_name = ""
        if title_match:
            project_name = title_match.group(1).strip()
            if title_match.group(2):
                app_name = title_match.group(2).strip()
            else:
                app_name = project_name
        
        # Get the full description from the truncated div
        tr = link.find_parent("tr")
        description_text = ""
        if tr:
            truncate_div = tr.find("div", class_="truncate-one-line")
            if truncate_div:
                description_text = truncate_div.get_text(strip=True)
        
        # Extract key fields from description
        app_url = ""
        institution_url = ""
        product_website = ""
        summary = ""
        
        # Product Website
        pw_match = re.search(r'Product Website\s+(https?://[^\s]+)', description_text)
        if pw_match:
            product_website = pw_match.group(1).strip()
        
        # URL of the applying institution
        iu_match = re.search(r'URL of the applying institution\s+(https?://[^\s]+)', description_text)
        if iu_match:
            institution_url = iu_match.group(1).strip()
        
        # Use product website first, then institution URL
        app_url = product_website or institution_url
        
        # Application name from form (may differ from title)
        form_app_name_match = re.search(r'Name of the application:\s*(.+?)(?:\s+Disclaimer|\s+URL|\s+Email)', description_text)
        if form_app_name_match:
            form_app_name = form_app_name_match.group(1).strip()
            if form_app_name:
                app_name = form_app_name
        
        # Company/Institution name from form
        inst_name_match = re.search(r'Name of applying institution\s+(.+?)(?:\s+Summary of Company)', description_text)
        if inst_name_match:
            project_name = inst_name_match.group(1).strip()
        
        # Get summary of what app does
        summary_match = re.search(r'Provide a summary of what your application will do:\s*(.+?)(?:\s*Describe the expected users)', description_text, re.DOTALL)
        if summary_match:
            summary = summary_match.group(1).strip()
        
        # Expected users
        expected_users = ""
        eu_match = re.search(r'Describe the expected users[^.]*?[.:]\s*(.+?)(?:\s*How will your app)', description_text, re.DOTALL)
        if eu_match:
            expected_users = eu_match.group(1).strip()
        
        # Reward activities (IMPORTANT)
        reward_activities = ""
        ra_match = re.search(r'Describe the activities that your application will earn application rewards from[.:]?\s*(.+?)(?:\s*Does this activity use Canton Coin)', description_text, re.DOTALL)
        if ra_match:
            reward_activities = ra_match.group(1).strip()
        
        # Canton Coin or Activity Markers (IMPORTANT)
        reward_type = ""
        rt_match = re.search(r'Does this activity use Canton Coin or Activity Markers to generate rewards\??\s*(.+?)(?:\s*On a per user)', description_text, re.DOTALL)
        if rt_match:
            reward_type = rt_match.group(1).strip()
        
        # Daily transactions per user
        daily_transactions = ""
        dt_match = re.search(r'On a per user basis,?\s*what is your expected daily number of transactions[?]?\s*(.+?)(?:\s*Under what conditions)', description_text, re.DOTALL)
        if dt_match:
            daily_transactions = dt_match.group(1).strip()
        
        # Launch date
        launch_date = ""
        ld_match = re.search(r'What is your anticipated launch date on MainNet\??\s*(.+?)(?:\s*Who will be your)', description_text, re.DOTALL)
        if ld_match:
            launch_date = ld_match.group(1).strip()
        
        # Entry ID
        entry_id = ""
        entry_match = re.search(r'Entry ID:\s*(\d+)', description_text)
        if entry_match:
            entry_id = entry_match.group(1)
        
        topics.append({
            "topic_id": topic_id,
            "entry_id": entry_id,
            "project_name": project_name,
            "app_name": app_name,
            "app_url": app_url,
            "institution_url": institution_url,
            "product_website": product_website,
            "summary": summary,
            "expected_users": expected_users,
            "reward_activities": reward_activities,
            "reward_type": reward_type,
            "daily_transactions": daily_transactions,
            "launch_date": launch_date,
            "title": title,
        })
    
    # Find pagination - next page link
    next_page = None
    next_after = None
    pag_links = soup.select("a[rel='next']")
    for pl in pag_links:
        href = pl.get("href", "")
        page_match = re.search(r'page=(\d+)&after=(\d+)', href)
        if page_match:
            next_page = int(page_match.group(1))
            next_after = page_match.group(2)
    
    # Get total count
    total_match = re.search(r'(\d+)\s*-\s*(\d+)\s+of\s+(\d+)', html_content)
    total = 0
    if total_match:
        total = int(total_match.group(3))
    
    return topics, next_page, next_after, total


def main():
    print("=" * 70)
    print("  Canton Featured App Requests Scraper")
    print("=" * 70)
    
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{current_time}] Starting scrape cycle...")
    
    all_topics = []
    page_num = 1
    after_id = None
    total_count = 0
    
    cycle_success = False
    while True:
        print(f"\n[Page {page_num}] Fetching topics...")
        html = get_topics_page(page_num, after_id)
        
        if not html or len(html) < 500:
            print("  Empty response or session expired, stopping.")
            break
        
        topics, next_page, next_after, total = parse_topics_from_html(html)
        
        if total > 0 and total_count == 0:
            total_count = total
            print(f"  Total topics on forum: {total_count}")
        
        print(f"  Found {len(topics)} Featured App topics on this page")
        
        for t in topics:
            print(f"    [{t['entry_id']:>3}] {t['project_name'][:30]:<30} | {t['app_name'][:25]:<25} | {t['app_url'][:40]}")
        
        all_topics.extend(topics)
        
        if next_page and next_after:
            page_num = next_page
            after_id = next_after
            time.sleep(2)  # Increased sleep to prevent rate limiting connection errors
        else:
            print("\n  No more pages.")
            cycle_success = True
            break
    
    if not cycle_success:
        print("\n  WARNING: Scrape cycle did not finish successfully.")
        print("  Existing data files will NOT be overwritten to prevent data loss.")
    elif not all_topics:
        print("\n  WARNING: No data collected in this cycle. Session cookie may have expired.")
        print("  Existing data files will NOT be overwritten.")
    else:
        # Deduplicate by topic_id
        seen = set()
        unique = []
        for t in all_topics:
            if t["topic_id"] not in seen:
                seen.add(t["topic_id"])
                unique.append(t)
        
        print(f"\n{'=' * 70}")
        print(f"  Total unique Featured App Requests: {len(unique)}")
        print(f"{'=' * 70}")
        
        # Save as JSON
        with open("featured_apps.json", "w", encoding="utf-8") as f:
            json.dump(unique, f, indent=2, ensure_ascii=False)
        print(f"\n  Saved to featured_apps.json")
        
        # Save as CSV with updated field names for recently added fields
        fieldnames = [
            "entry_id", "project_name", "app_name", "app_url", "institution_url", 
            "product_website", "summary", "expected_users", "reward_activities", 
            "reward_type", "daily_transactions", "launch_date", "title", "topic_id"
        ]
        
        with open("featured_apps.csv", "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in unique:
                writer.writerow({k: r.get(k, "") for k in fieldnames})
        print(f"  Saved to featured_apps.csv")
        
        # Print summary table
        print(f"\n{'#':<4} {'Entry':<6} {'Project':<30} {'App Name':<25} {'URL':<45}")
        print("-" * 115)
        for i, r in enumerate(unique):
            proj = r.get("project_name", "")[:29]
            app = r.get("app_name", "")[:24]
            url = r.get("app_url", "")[:44]
            eid = r.get("entry_id", "")
            print(f"{i+1:<4} {eid:<6} {proj:<30} {app:<25} {url:<45}")
        
        print(f"\nTotal: {len(unique)} Featured App Requests")


if __name__ == "__main__":
    main()
