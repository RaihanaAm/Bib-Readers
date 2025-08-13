"""
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
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

# ------------------ Make the project 'app' importable when run from backend/ ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))          # .../backend/scripts
BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))   # .../backend
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

# ------------------ Optional DB imports (used only when --load-db) -------------
try:
    import asyncio
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.db.session import SessionLocal
    from app.models.livre import Livre
except Exception:
    # DB is optional; we'll handle None checks later
    Livre = None
    SessionLocal = None

# ------------------ Selenium imports ------------------------------------------
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


BASE_URL = "http://books.toscrape.com/"
CATALOGUE_URL = urljoin(BASE_URL, "catalogue/")
START_PAGE = urljoin(CATALOGUE_URL, "page-1.html")


# ============================== Helpers (parsing) ==============================

def rating_text_to_int(rating_text: str) -> int:
    """
    Convert star rating text ('Zero','One','Two','Three','Four','Five') -> int 0..5.
    """
    mapping = {"Zero": 0, "One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
    return mapping.get((rating_text or "").strip(), 0)


def parse_price(price_text: str) -> float:
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

    try:
        page_url = START_PAGE
        page_idx = 1

        while True:
            driver.get(page_url)

            # Wait for the list of books on the page
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ol.row li"))
            )

            cards = driver.find_elements(By.CSS_SELECTOR, "ol.row li")
            print(f"[Page {page_idx}] found {len(cards)} cards")

            for card in cards:
                try:
                    # Title & product link
                    a = card.find_element(By.CSS_SELECTOR, "h3 a")
                    title = a.get_attribute("title").strip()
                    product_href = a.get_attribute("href")
                    product_url = product_href if product_href.startswith("http") else urljoin(CATALOGUE_URL, product_href)

                    # Price & availability
                    price_text = card.find_element(By.CSS_SELECTOR, ".price_color").text
                    avail_text = card.find_element(By.CSS_SELECTOR, ".availability").text

                    # Rating from class "star-rating Three" etc.
                    rating_el = card.find_element(By.CSS_SELECTOR, "p.star-rating")
                    classes = rating_el.get_attribute("class").split()
                    rating_text = [c for c in classes if c != "star-rating"][-1] if len(classes) > 1 else "Zero"

                    # Image URL (absolute)
                    img = card.find_element(By.CSS_SELECTOR, "img")
                    img_src = img.get_attribute("src")
                    image_url = img_src if img_src.startswith("http") else urljoin(BASE_URL, img_src)

                    # Description via product page (optional)
                    description = ""
                    if fetch_descriptions:
                        description = get_full_description_newtab(driver, product_url)

                    rows.append(
                        {
                            "title": title,
                            "author": "Unknown",  # site doesn't expose author; keep Unknown
                            "price_text": price_text,
                            "availability_text": avail_text,
                            "rating_text": rating_text,
                            "image_url": image_url,
                            "description": description,
                            "product_url": product_url,
                        }
                    )

                    # Polite delay to reduce flakiness (adjust as you wish)
                    time.sleep(0.05)

                except Exception:
                    # Skip any broken card; continue with the rest
                    continue

            # Next page?
            next_links = driver.find_elements(By.CSS_SELECTOR, "li.next a")
            if next_links:
                next_href = next_links[0].get_attribute("href")
                page_url = next_href if next_href.startswith("http") else urljoin(CATALOGUE_URL, next_href)
                page_idx += 1
                time.sleep(0.3)  # polite delay between pages
            else:
                break

    finally:
        driver.quit()

    return rows


# ============================== CSV saving ====================================

def save_csv(rows: List[Dict[str, object]], csv_path: str) -> None:
    """
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


# ================================== CLI =======================================

def main():
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


if __name__ == "__main__":
    main()
