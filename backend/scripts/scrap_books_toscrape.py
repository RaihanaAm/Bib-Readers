"""
Scrape books.toscrape.com (list via Selenium; details via HTTP+BS4),
clean data, save to CSV, and optionally upsert into PostgreSQL (FastAPI models).

USAGE (from backend/):
  # Sanity run: 1 page, fetch all 20 descriptions
  python scripts/scrap_books_toscrape.py --csv data/livres_bruts.csv --max-pages 1 --desc-timeout 8 --desc-limit-per-page 20

  # Full run WITH DB upsert (update existing rows too)
  python scripts/scrap_books_toscrape.py --csv data/livres_bruts.csv --load-db --update-existing --max-pages 1 --desc-timeout 8 --desc-limit-per-page 20

  # Fast run (skip descriptions)
  python scripts/scrap_books_toscrape.py --csv data/livres_bruts.csv --no-desc --max-pages 5
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import time
from typing import Dict, List, Tuple, Iterable
from urllib.parse import urljoin

# ------------- Make 'app' importable (so we can use DB models if requested) ---
THIS_FILE = os.path.abspath(__file__)
SCRIPTS_DIR = os.path.dirname(THIS_FILE)                         # .../backend/scripts
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))  # .../backend
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ---------------- Optional DB imports (used only if --load-db) -----------------
try:
    import asyncio
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.db.session import SessionLocal
    from app.models.livre import Livre
except Exception:
    # If DB not configured yet, keep these None; DB path remains optional.
    Livre = None
    SessionLocal = None

# -------------------- Selenium for listing & pagination -----------------------
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# -------------------- HTTP details fetch (descriptions) -----------------------
import requests
from bs4 import BeautifulSoup

BASE_URL = "http://books.toscrape.com/"
CATALOGUE_URL = urljoin(BASE_URL, "catalogue/")
START_PAGE = urljoin(CATALOGUE_URL, "page-1.html")

CSV_FIELDS = ["title", "author", "description", "price", "stock", "rating", "image_url", "product_url"]


# ============================== Parsing helpers ===============================

def rating_text_to_int(rating_text: str) -> int:
    """Map star-rating text to integer."""
    mapping = {"Zero": 0, "One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
    return mapping.get((rating_text or "").strip(), 0)


def parse_price(price_text: str) -> float:
    """Extract float from '£51.77' style text."""
    m = re.search(r"(\d+(?:\.\d+)?)", price_text or "")
    return float(m.group(1)) if m else 0.0


def parse_availability(avail_text: str) -> int:
    """Extract available stock from 'In stock (22 available)' style text."""
    m = re.search(r"(\d+)", avail_text or "")
    return int(m.group(1)) if m else 0


def clean_row(raw: Dict[str, str]) -> Dict[str, object]:
    """Normalize scraped strings to clean typed fields."""
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
    try:
        page_url = START_PAGE
        page_idx = 1

        while True:
            if not _load_catalog_page(driver, page_url, tries=3):
                print(f"[ERROR] Could not load page after retries: {page_url}. Stopping.")
                break

            cards = driver.find_elements(By.CSS_SELECTOR, "ol.row li")
            print(f"[Page {page_idx}] found {len(cards)} cards")

            page_rows: List[Dict[str, str]] = []
            desc_done = 0

            for i, card in enumerate(cards, start=1):
                try:
                    a = card.find_element(By.CSS_SELECTOR, "h3 a")
                    title = a.get_attribute("title").strip()
                    product_href = a.get_attribute("href")
                    product_url = product_href if product_href.startswith("http") else urljoin(CATALOGUE_URL, product_href)

                    price_text = card.find_element(By.CSS_SELECTOR, ".price_color").text
                    avail_text = card.find_element(By.CSS_SELECTOR, ".availability").text

                    rating_el = card.find_element(By.CSS_SELECTOR, "p.star-rating")
                    classes = rating_el.get_attribute("class").split()
                    rating_text = [c for c in classes if c != "star-rating"][-1] if len(classes) > 1 else "Zero"

                    img = card.find_element(By.CSS_SELECTOR, "img")
                    img_src = img.get_attribute("src")
                    image_url = img_src if img_src.startswith("http") else urljoin(BASE_URL, img_src)

                    # Description via HTTP fetch (fast & reliable)
                    description = ""
                    if fetch_descriptions and desc_done < desc_limit_per_page:
                        description = get_full_description_http(product_url, timeout=desc_timeout)
                        desc_done += 1

                    page_rows.append(
                        {
                            "title": title,
                            "author": "Unknown",
                            "price_text": price_text,
                            "availability_text": avail_text,
                            "rating_text": rating_text,
                            "image_url": image_url,
                            "description": description,
                            "product_url": product_url,
                        }
                    )

                    if i % 5 == 0:
                        print(f"  - processed {i}/{len(cards)} cards (descriptions fetched: {desc_done})")

                    time.sleep(0.02)  # tiny polite delay

                except Exception:
                    # Skip any problematic card
                    continue

            yield page_idx, page_rows

            if max_pages and page_idx >= max_pages:
                break

            next_links = driver.find_elements(By.CSS_SELECTOR, "li.next a")
            if next_links:
                next_href = next_links[0].get_attribute("href")
                page_url = next_href if next_href.startswith("http") else urljoin(CATALOGUE_URL, next_href)
                page_idx += 1
                time.sleep(0.2)
            else:
                break

    finally:
        driver.quit()


# ============================== CSV saving ====================================

def save_csv(rows: List[Dict[str, object]], csv_path: str) -> None:
    """
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


# ================================== CLI =======================================

def main():
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


if __name__ == "__main__":
    main()
