"""
<<<<<<< HEAD
Scrape books.toscrape.com with Selenium, clean data, save to CSV,
and optionally insert into PostgreSQL using your FastAPI project's models.

USAGE (run from backend/):
  python scripts/scrap_books_toscrape.py --csv data/livres_bruts.csv
  python scripts/scrap_books_toscrape.py --csv data/livres_bruts.csv --load-db
  python scripts/scrap_books_toscrape.py --csv data/livres_bruts.csv --no-desc

Notes:
- Selenium Manager (built into selenium>=4.10) auto-fetches the right ChromeDriver.
- We keep dependencies minimal (standard csv module; no pandas).
- If you pass --load-db, we insert into the 'livres' table using your app's async SQLAlchemy setup.
=======
Scrape books.toscrape.com (list via Selenium; details via HTTP+BS4),
clean data, save to CSV, and optionally upsert into PostgreSQL (FastAPI models).

USAGE (from backend/):
  # Sanity run: 1 page, fetch all 20 descriptions
  python scripts/scrap_books_toscrape.py --csv data/livres_bruts.csv --max-pages 1 --desc-timeout 8 --desc-limit-per-page 20

  # Full run WITH DB upsert (update existing rows too)
  python scripts/scrap_books_toscrape.py --csv data/livres_bruts.csv --load-db --update-existing --max-pages 1 --desc-timeout 8 --desc-limit-per-page 20

  # Fast run (skip descriptions)
  python scripts/scrap_books_toscrape.py --csv data/livres_bruts.csv --no-desc --max-pages 5
>>>>>>> main
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import time
<<<<<<< HEAD
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

# ------------------ Make the project 'app' importable when run from backend/ ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))          # .../backend/scripts
BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))   # .../backend
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

# ------------------ Optional DB imports (used only when --load-db) -------------
=======
from typing import Dict, List, Tuple, Iterable
from urllib.parse import urljoin

# ------------- Make 'app' importable (so we can use DB models if requested) ---
THIS_FILE = os.path.abspath(__file__)
SCRIPTS_DIR = os.path.dirname(THIS_FILE)                         # .../backend/scripts
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))  # .../backend
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ---------------- Optional DB imports (used only if --load-db) -----------------
>>>>>>> main
try:
    import asyncio
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.db.session import SessionLocal
    from app.models.livre import Livre
except Exception:
<<<<<<< HEAD
    # DB is optional; we'll handle None checks later
    Livre = None
    SessionLocal = None

# ------------------ Selenium imports ------------------------------------------
=======
    # If DB not configured yet, keep these None; DB path remains optional.
    Livre = None
    SessionLocal = None

# -------------------- Selenium for listing & pagination -----------------------
>>>>>>> main
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
<<<<<<< HEAD

=======
from selenium.common.exceptions import TimeoutException

# -------------------- HTTP details fetch (descriptions) -----------------------
import requests
from bs4 import BeautifulSoup
>>>>>>> main

BASE_URL = "http://books.toscrape.com/"
CATALOGUE_URL = urljoin(BASE_URL, "catalogue/")
START_PAGE = urljoin(CATALOGUE_URL, "page-1.html")

<<<<<<< HEAD

# ============================== Helpers (parsing) ==============================

def rating_text_to_int(rating_text: str) -> int:
    """
    Convert star rating text ('Zero','One','Two','Three','Four','Five') -> int 0..5.
    """
=======
CSV_FIELDS = ["title", "author", "description", "price", "stock", "rating", "image_url", "product_url"]


# ============================== Parsing helpers ===============================

def rating_text_to_int(rating_text: str) -> int:
    """Map star-rating text to integer."""
>>>>>>> main
    mapping = {"Zero": 0, "One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
    return mapping.get((rating_text or "").strip(), 0)


def parse_price(price_text: str) -> float:
<<<<<<< HEAD
    """
    Price text looks like '£51.77'. Extract the float (51.77).
    """
    match = re.search(r"(\d+(?:\.\d+)?)", price_text or "")
    return float(match.group(1)) if match else 0.0


def parse_availability(avail_text: str) -> int:
    """
    Availability often like: 'In stock (19 available)' or 'In stock'.
    Extract the first integer found, else 0 if not found.
    """
    match = re.search(r"(\d+)", avail_text or "")
    return int(match.group(1)) if match else 0


def clean_row(raw: Dict[str, str]) -> Dict[str, object]:
    """
    Convert raw scraped strings into clean, typed fields for CSV/DB.
    """
=======
    """Extract float from '£51.77' style text."""
    m = re.search(r"(\d+(?:\.\d+)?)", price_text or "")
    return float(m.group(1)) if m else 0.0


def parse_availability(avail_text: str) -> int:
    """Extract available stock from 'In stock (22 available)' style text."""
    m = re.search(r"(\d+)", avail_text or "")
    return int(m.group(1)) if m else 0


def clean_row(raw: Dict[str, str]) -> Dict[str, object]:
    """Normalize scraped strings to clean typed fields."""
>>>>>>> main
    return {
        "title": (raw.get("title") or "").strip() or "Untitled",
        "author": (raw.get("author") or "Unknown").strip() or "Unknown",
        "description": (raw.get("description") or "").strip(),
        "price": parse_price(raw.get("price_text", "")),
        "stock": parse_availability(raw.get("availability_text", "")),
        "rating": rating_text_to_int(raw.get("rating_text", "")),
        "image_url": (raw.get("image_url") or "").strip(),
        "product_url": (raw.get("product_url") or "").strip(),
    }


<<<<<<< HEAD
# ========================= Product-page description ===========================

def get_full_description_newtab(driver: webdriver.Chrome, product_url: str, timeout: int = 10) -> str:
    """
    Open product_url in a NEW TAB, scrape description, then close and return to the listing tab.
    Prevents losing the listing context and avoids stale element issues.
    """
    original_window = driver.current_window_handle
    try:
        # Open product in a new tab
        driver.execute_script("window.open(arguments[0], '_blank');", product_url)
        WebDriverWait(driver, timeout).until(EC.number_of_windows_to_be(2))

        # Switch to the new tab (last handle)
        driver.switch_to.window(driver.window_handles[-1])

        # Wait for product page layout
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.product_page"))
        )

        # The description is usually under #product_description followed by a <p>
        hdr = driver.find_elements(By.ID, "product_description")
        if not hdr:
            return ""
        p_tags = driver.find_elements(By.CSS_SELECTOR, "#product_description ~ p")
        return p_tags[0].text.strip() if p_tags else ""
    except Exception:
        return ""
    finally:
        # Close product tab and switch back
        try:
            if len(driver.window_handles) > 1:
                driver.close()
                driver.switch_to.window(original_window)
        except Exception:
            # Fallback: ensure we are on some valid window
            handles = driver.window_handles
            driver.switch_to.window(handles[0])


# ============================== Scraping core =================================

def build_driver() -> webdriver.Chrome:
    """
    Build a Chrome WebDriver with reasonable defaults.
    - Headed (visible) by default to debug easily. Switch to headless if you want.
    """
    options = ChromeOptions()
    # Uncomment for headless scraping:
    # options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=options)  # Selenium Manager handles chromedriver


def scrape_all_books(fetch_descriptions: bool = True) -> List[Dict[str, str]]:
    """
    Navigate all catalogue pages, extract card info (title, price, availability, rating, image),
    and optionally open each product page for full description.
    Returns a list of dicts (raw fields).
    """
    rows: List[Dict[str, str]] = []
    driver = build_driver()

=======
# ===================== Product-page description via HTTP ======================

def get_full_description_http(product_url: str, timeout: int = 8) -> str:
    """
    Fetch a product page over HTTP and parse description with BeautifulSoup.
    Reliable and fast even in headless environments.
    Includes encoding fix for proper accents.
    """
    try:
        resp = requests.get(product_url, timeout=timeout)
        # --- Encoding fix: prefer server header; fallback to apparent encoding
        if not resp.encoding or resp.encoding.lower() in ("iso-8859-1", "latin-1"):
            resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")

        # Canonical layout: <div id="product_description"></div><p>DESCRIPTION</p>
        hdr = soup.select_one("#product_description")
        if hdr:
            p = hdr.find_next("p")
            if p:
                txt = p.get_text(strip=True)
                if txt:
                    return txt

        # Fallback 1: choose the longest reasonable <p> inside product page
        article = soup.select_one("article.product_page") or soup.select_one("div.product_page")
        if article:
            best = ""
            for p in article.find_all("p"):
                txt = p.get_text(strip=True)
                # skip common non-description bits
                if len(txt) > len(best) and not re.search(r"(UPC|£|In stock|Tax)", txt, re.I):
                    best = txt
            if best:
                return best

        # Fallback 2: any longer paragraph in content
        for p in soup.select("#content_inner p"):
            txt = p.get_text(strip=True)
            if len(txt) >= 20:
                return txt

        return ""
    except Exception:
        return ""


# ============================== WebDriver setup ===============================

def build_driver() -> webdriver.Chrome:
    """
    Headless Chrome set up for reliability in Windows environments.
    Selenium Manager handles ChromeDriver automatically.
    """
    options = ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--use-angle=swiftshader")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)
    return driver


def _load_catalog_page(driver: webdriver.Chrome, url: str, tries: int = 3) -> bool:
    """
    Load a catalogue page and wait for its list. Retry a few times on timeouts.
    """
    for attempt in range(1, tries + 1):
        try:
            driver.get(url)
            WebDriverWait(driver, 25).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ol.row li"))
            )
            return True
        except TimeoutException:
            print(f"[WARN] Timeout loading page (try {attempt}/{tries}): {url}")
            time.sleep(1.0)
            try:
                driver.refresh()
            except Exception:
                pass
    return False


# ============================== Scraping (stream) =============================

def scrape_all_books_stream(
    fetch_descriptions: bool,
    max_pages: int,
    desc_timeout: int,
    desc_limit_per_page: int
) -> Iterable[Tuple[int, List[Dict[str, str]]]]:
    """
    Iterate pages and yield (page_index, raw_rows).

    - fetch_descriptions: if True, fetch up to desc_limit_per_page descriptions
      per list page using HTTP (requests + BeautifulSoup).
    - max_pages: stop after N pages (0 = all).
    """
    driver = build_driver()
>>>>>>> main
    try:
        page_url = START_PAGE
        page_idx = 1

        while True:
<<<<<<< HEAD
            driver.get(page_url)

            # Wait for the list of books on the page
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ol.row li"))
            )
=======
            if not _load_catalog_page(driver, page_url, tries=3):
                print(f"[ERROR] Could not load page after retries: {page_url}. Stopping.")
                break
>>>>>>> main

            cards = driver.find_elements(By.CSS_SELECTOR, "ol.row li")
            print(f"[Page {page_idx}] found {len(cards)} cards")

<<<<<<< HEAD
            for card in cards:
                try:
                    # Title & product link
=======
            page_rows: List[Dict[str, str]] = []
            desc_done = 0

            for i, card in enumerate(cards, start=1):
                try:
>>>>>>> main
                    a = card.find_element(By.CSS_SELECTOR, "h3 a")
                    title = a.get_attribute("title").strip()
                    product_href = a.get_attribute("href")
                    product_url = product_href if product_href.startswith("http") else urljoin(CATALOGUE_URL, product_href)

<<<<<<< HEAD
                    # Price & availability
                    price_text = card.find_element(By.CSS_SELECTOR, ".price_color").text
                    avail_text = card.find_element(By.CSS_SELECTOR, ".availability").text

                    # Rating from class "star-rating Three" etc.
=======
                    price_text = card.find_element(By.CSS_SELECTOR, ".price_color").text
                    avail_text = card.find_element(By.CSS_SELECTOR, ".availability").text

>>>>>>> main
                    rating_el = card.find_element(By.CSS_SELECTOR, "p.star-rating")
                    classes = rating_el.get_attribute("class").split()
                    rating_text = [c for c in classes if c != "star-rating"][-1] if len(classes) > 1 else "Zero"

<<<<<<< HEAD
                    # Image URL (absolute)
=======
>>>>>>> main
                    img = card.find_element(By.CSS_SELECTOR, "img")
                    img_src = img.get_attribute("src")
                    image_url = img_src if img_src.startswith("http") else urljoin(BASE_URL, img_src)

<<<<<<< HEAD
                    # Description via product page (optional)
                    description = ""
                    if fetch_descriptions:
                        description = get_full_description_newtab(driver, product_url)

                    rows.append(
                        {
                            "title": title,
                            "author": "Unknown",  # site doesn't expose author; keep Unknown
=======
                    # Description via HTTP fetch (fast & reliable)
                    description = ""
                    if fetch_descriptions and desc_done < desc_limit_per_page:
                        description = get_full_description_http(product_url, timeout=desc_timeout)
                        desc_done += 1

                    page_rows.append(
                        {
                            "title": title,
                            "author": "Unknown",
>>>>>>> main
                            "price_text": price_text,
                            "availability_text": avail_text,
                            "rating_text": rating_text,
                            "image_url": image_url,
                            "description": description,
                            "product_url": product_url,
                        }
                    )

<<<<<<< HEAD
                    # Polite delay to reduce flakiness (adjust as you wish)
                    time.sleep(0.05)

                except Exception:
                    # Skip any broken card; continue with the rest
                    continue

            # Next page?
=======
                    if i % 5 == 0:
                        print(f"  - processed {i}/{len(cards)} cards (descriptions fetched: {desc_done})")

                    time.sleep(0.02)  # tiny polite delay

                except Exception:
                    # Skip any problematic card
                    continue

            yield page_idx, page_rows

            if max_pages and page_idx >= max_pages:
                break

>>>>>>> main
            next_links = driver.find_elements(By.CSS_SELECTOR, "li.next a")
            if next_links:
                next_href = next_links[0].get_attribute("href")
                page_url = next_href if next_href.startswith("http") else urljoin(CATALOGUE_URL, next_href)
                page_idx += 1
<<<<<<< HEAD
                time.sleep(0.3)  # polite delay between pages
=======
                time.sleep(0.2)
>>>>>>> main
            else:
                break

    finally:
        driver.quit()

<<<<<<< HEAD
    return rows

=======
>>>>>>> main

# ============================== CSV saving ====================================

def save_csv(rows: List[Dict[str, object]], csv_path: str) -> None:
    """
<<<<<<< HEAD
    Save cleaned rows as CSV at csv_path.
    """
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    fieldnames = ["title", "author", "description", "price", "stock", "rating", "image_url", "product_url"]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


# ============================== DB insertion ==================================

async def _fetch_existing_title_author(session: AsyncSession) -> set[Tuple[str, str]]:
    """
    Query existing (title, author) pairs to avoid duplicate inserts.
    """
    result = await session.execute(select(Livre.title, Livre.author))
    return set(result.all())


async def bulk_insert_books(clean_rows: List[Dict[str, object]]) -> int:
    """
    Insert books into the 'livres' table (async).
    - Skips simple duplicates based on (title, author).
    Returns number of inserted rows.
    """
    if Livre is None or SessionLocal is None:
        print("DB models/session not available; skipping DB insertion.")
        return 0

    inserted = 0
    async with SessionLocal() as session:  # reuse app's async session
        existing = await _fetch_existing_title_author(session)

        for r in clean_rows:
            key = (r["title"], r["author"])
            if key in existing:
                continue
            session.add(
                Livre(
                    title=r["title"],
                    author=r["author"],
                    description=r["description"],
                    price=r["price"],
                    stock=r["stock"],
                    rating=r["rating"],
                    image_url=r["image_url"],
                )
            )
            inserted += 1

        await session.commit()

    return inserted
=======
    Rewrite entire CSV each time so the file always contains all rows seen so far.
    """
    folder = os.path.dirname(csv_path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
        # Ensure data is flushed to disk
        f.flush()
        os.fsync(f.fileno())


# ============================== DB upsert =====================================

async def _fetch_existing_map(session: AsyncSession) -> dict[Tuple[str, str], Livre]:
    """
    Build {(title, author): Livre} for quick existence checks.
    """
    result = await session.execute(select(Livre))
    books = result.scalars().all()
    return {(b.title, b.author): b for b in books}


async def upsert_books(clean_rows: List[Dict[str, object]], update_existing: bool = False) -> int:
    """
    Upsert into 'livres':
      - Insert new rows.
      - If (title, author) exists:
          * if update_existing=True: update fields incl. description.
          * else: update only if new description exists and old is empty.
    """
    if Livre is None or SessionLocal is None:
        print("DB models/session not available; skipping DB upsert.")
        return 0

    changed = 0
    async with SessionLocal() as session:
        index = await _fetch_existing_map(session)

        for r in clean_rows:
            key = (r["title"], r["author"])
            if key in index:
                book = index[key]
                new_desc = (r["description"] or "").strip()
                has_new_desc = bool(new_desc)
                has_old_desc = bool((book.description or "").strip())

                should_update = update_existing or (has_new_desc and not has_old_desc)
                if should_update:
                    book.description = r["description"]
                    book.price = r["price"]
                    book.stock = r["stock"]
                    book.rating = r["rating"]
                    book.image_url = r["image_url"]
                    changed += 1
            else:
                session.add(
                    Livre(
                        title=r["title"],
                        author=r["author"],
                        description=r["description"],
                        price=r["price"],
                        stock=r["stock"],
                        rating=r["rating"],
                        image_url=r["image_url"],
                    )
                )
                changed += 1

        await session.commit()

    return changed
>>>>>>> main


# ================================== CLI =======================================

def main():
<<<<<<< HEAD
    parser = argparse.ArgumentParser(description="Scrape books.toscrape.com and save to CSV (optionally load DB).")
    parser.add_argument("--csv", required=True, help="Output CSV path, e.g., data/livres_bruts.csv")
    parser.add_argument("--load-db", action="store_true", help="Also insert into PostgreSQL 'livres' table.")
    parser.add_argument(
        "--no-desc",
        action="store_true",
        help="Skip opening product pages for descriptions (faster).",
    )
    args = parser.parse_args()

    print("Scraping list pages...")
    raw_rows = scrape_all_books(fetch_descriptions=not args.no_desc)
    print(f"Scraped {len(raw_rows)} raw rows.")

    # Clean rows
    clean_rows = [clean_row(r) for r in raw_rows]
    print(f"Cleaned {len(clean_rows)} rows.")

    # Save CSV
    save_csv(clean_rows, args.csv)
    print(f"Saved CSV to {args.csv}")

    # Optional DB load
    if args.load_db:
        if Livre is None or SessionLocal is None:
            print("DB not available; cannot insert. Did you run this from backend/ with your project installed?")
        else:
            try:
                inserted = asyncio.run(bulk_insert_books(clean_rows))
                print(f"Inserted {inserted} rows into DB.")
            except Exception as e:
                print(f"DB insertion failed: {e}")
=======
    parser = argparse.ArgumentParser(description="Scrape books.toscrape.com, save CSV, optionally upsert DB.")
    parser.add_argument("--csv", required=True, help="Output CSV path, e.g., data/livres_bruts.csv")
    parser.add_argument("--load-db", action="store_true", help="Insert/Update rows in PostgreSQL 'livres' table.")
    parser.add_argument("--update-existing", action="store_true", help="Update existing DB rows even if they already have descriptions.")
    parser.add_argument("--no-desc", action="store_true", help="Skip product descriptions (faster).")
    parser.add_argument("--max-pages", type=int, default=0, help="Stop after N pages (0 = all).")
    parser.add_argument("--desc-timeout", type=int, default=8, help="Seconds to wait for each HTTP product fetch.")
    parser.add_argument("--desc-limit-per-page", type=int, default=6, help="Max descriptions fetched per list page.")
    args = parser.parse_args()

    fetch_descriptions = not args.no_desc
    csv_path = args.csv
    all_clean_rows: List[Dict[str, object]] = []

    print("Scraping list pages...")

    for page_idx, raw_rows in scrape_all_books_stream(
        fetch_descriptions=fetch_descriptions,
        max_pages=args.max_pages,
        desc_timeout=args.desc_timeout,
        desc_limit_per_page=args.desc_limit_per_page,
    ):
        print(f"[Page {page_idx}] scraped {len(raw_rows)} rows")
        cleaned = [clean_row(r) for r in raw_rows]
        all_clean_rows.extend(cleaned)
        save_csv(all_clean_rows, csv_path)
        print(f"[Page {page_idx}] CSV updated → {csv_path} (total rows: {len(all_clean_rows)})")

    abs_csv = os.path.abspath(csv_path)
    print(f"Scraping finished. Total rows: {len(all_clean_rows)}")
    print(f"Final CSV at: {abs_csv}")

    # Optional DB upsert
    if args.load_db and all_clean_rows:
        if Livre is None or SessionLocal is None:
            print("DB not available; cannot insert/update. Did you run from backend/ with the project active?")
        else:
            try:
                changed = asyncio.run(upsert_books(all_clean_rows, update_existing=args.update_existing))
                print(f"Inserted/updated {changed} rows in DB.")
            except Exception as e:
                print(f"DB upsert failed: {e}")
>>>>>>> main


if __name__ == "__main__":
    main()
