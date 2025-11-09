#!/usr/bin/env python3
# Google Books API Scraper with CSS Styling

import requests
import json
import time
import csv
from datetime import datetime
import argparse
import html as html_module

def fetch_books(query, limit=10, api_key=None, langRestrict=None):
    books = []
    max_books = min(limit, 40)
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {
        "q": query,
        "maxResults": min(max_books, 40),
        "printType": "books"
    }
    if langRestrict:
        params["langRestrict"] = langRestrict
    if api_key:
        params["key"] = api_key
    try:
        print(f"Searching Google Books: {query}")
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if 'items' not in data:
            return []
        for item in data['items'][:limit]:
            info = item.get('volumeInfo', {})
            sale = item.get('saleInfo', {})
            b = {
                "title": info.get("title", ""),
                "subtitle": info.get("subtitle", ""),
                "authors": info.get("authors", []),
                "publisher": info.get("publisher"),
                "publishedDate": info.get("publishedDate"),
                "pageCount": info.get("pageCount"),
                "categories": info.get("categories", []),
                "description": info.get("description", ""),
                "language": info.get("language"),
                "isbn_10": None,
                "isbn_13": None,
                "other_ids": [],
                "previewLink": info.get("previewLink"),
                "infoLink": info.get("infoLink"),
                "image_url": info.get("imageLinks", {}).get("thumbnail"),
                "avg_rating": info.get("averageRating"),
                "ratings_count": info.get("ratingsCount"),
                "saleability": sale.get("saleability"),
                "price": None,
            }
            if "industryIdentifiers" in info:
                for id_type in info["industryIdentifiers"]:
                    if id_type["type"] == "ISBN_13":
                        b["isbn_13"] = id_type["identifier"]
                    elif id_type["type"] == "ISBN_10":
                        b["isbn_10"] = id_type["identifier"]
                    else:
                        b["other_ids"].append(id_type["identifier"])
            if "retailPrice" in sale and "amount" in sale["retailPrice"]:
                b["price"] = sale["retailPrice"]["amount"]
            books.append(b)
        time.sleep(0.3)
        return books
    except Exception as e:
        print(f"Error: {e}")
        return []

def calculate_popularity(book):
    score = 0
    if book["avg_rating"]:
        score += (min(book["avg_rating"], 5) / 5) * 50
    if book["ratings_count"]:
        score += min(book["ratings_count"] / 10, 30)
    if book["pageCount"]:
        score += min(book["pageCount"] / 100, 10)
    if book["categories"]:
        score += 10
    return round(score, 2)

def make_css():
    return """
body {font-family:Arial,sans-serif;background:linear-gradient(135deg,#f5f7fa 0%,#c3cfe2 100%);padding:20px;}
.container {max-width:1200px;margin:0 auto;}
.header {background:white;padding:20px;border-radius:10px;text-align:center;margin-bottom:20px;}
.grid {display:grid;grid-template-columns:repeat(auto-fit,minmax(350px,1fr));gap:20px;}
.card {background:white;padding:20px;border-radius:10px;box-shadow:0 4px 6px rgba(0,0,0,0.1);position:relative;}
.card h2 {color:#2c3e50;font-size:1.2em;margin-bottom:4px;}
.card p {color:#555;margin:6px 0;}
.score {position:absolute;top:10px;right:10px;background:#e67e22;color:white;padding:7px 14px;border-radius:18px;font-weight:bold;}
.cover {text-align:center;margin:10px 0;}
.cover img {max-width:100px;border-radius:6px;box-shadow:0 2px 4px rgba(0,0,0,0.18);}
.no-cover {width:100px;height:150px;background:#95a5a6;display:inline-flex;align-items:center;justify-content:center;border-radius:5px;color:white;font-weight:bold;}
.meta {font-size:0.95em;color:#888;}
.chips {margin-top:7px;}
.chip {background:#d1eaff;color:#2c3e50;padding:4px 9px;border-radius:12px;font-size:0.85em;margin-right:7px;display:inline-block;}
a.link {color:#337ab7;text-decoration:none;}
a.link:hover {text-decoration: underline;}
"""

def make_card(book):
    authors = ', '.join(book['authors']) if book['authors'] else 'Unknown'
    cats = ''.join(f'<span class="chip">{html_module.escape(c)}</span>' for c in book.get('categories', [])[:5])
    rating = f'{book["avg_rating"]}⭐ ({book["ratings_count"]})' if book["avg_rating"] else "No ratings"
    desc = book["description"][:300] + ("..." if book["description"] and len(book["description"]) > 300 else "")
    isbns = " / ".join(filter(None, [book["isbn_10"], book["isbn_13"]]))
    preview_link = f'<a class="link" href="{book["infoLink"] or book["previewLink"]}" target="_blank">View</a>'
    img = f'<img src="{book["image_url"]}" alt="Cover">' if book["image_url"] else "<div class='cover'>No Cover</div>"
    return f'''
    <div class="card">
      <div class="score">{calculate_popularity(book)}</div>
      <div class="cover">{img}</div>
      <h2>{html_module.escape(book["title"])}</h2>
      <div class="meta">{html_module.escape(authors)}, {html_module.escape(book.get("publisher") or "")} | {html_module.escape(str(book.get("publishedDate") or ""))}</div>
      <div>{preview_link}</div>
      <div class="chips">{cats}</div>
      <p class="meta">Pages: {book["pageCount"] or "?"} | {rating}</p>
      <p class="meta">ISBN(s): {isbns}</p>
      <p>{desc}</p>
    </div>
    '''

def save_csv(books, filename):
    fields = ['title','subtitle','authors','publisher','publishedDate','pageCount','categories','language','isbn_10','isbn_13','avg_rating','ratings_count','previewLink','infoLink','popularity']
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for b in books:
            row = {k:( '; '.join(b[k]) if isinstance(b[k],list) else b[k]) if k in b else "" for k in fields}
            row['popularity'] = calculate_popularity(b)
            w.writerow(row)
    print(f"✅ CSV saved: {filename}")

def save_html(books, q, total):
    cards = "".join(make_card(b) for b in books)
    s = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Google Books Results</title>
<style>{make_css()}</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>📚 Google Books Explorer</h1>
    <p>Query: <b>{html_module.escape(q)}</b></p>
    <p>Found {total} | Showing {len(books)}</p>
    <p style='font-size:.97em;color:#888;'>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
  </div>
  <div class="grid">{cards}</div>
</div>
</body></html>
"""
    fname = f"google_books_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(s)
    print(f"✅ HTML page saved: {fname}")

def run_interactive():
    print("\n" + "="*60)
    print("📚 GOOGLE BOOKS API SCRAPER")
    print("="*60)
    query = input("\nEnter search query: ").strip()
    if not query:
        print("❌ Query is required!")
        return
    try:
        limit = int(input("How many books (default 10, max 40): ").strip() or "10")
        limit = min(limit, 40)
    except:
        limit = 10
    lang = input("Language code (optional): ").strip()
    api_key = input("Google API key (optional): ").strip()
    print("\n🔍 Searching Google Books...\n")
    books = fetch_books(query, limit, api_key if api_key else None, lang if lang else None)
    if not books:
        print("❌ No books found!\n")
        return
    save_html(books, query, len(books))
    save_csv(books, f"google_books_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    print("\n✅ All done!\n")

def main():
    parser = argparse.ArgumentParser(description='Google Books API Scraper')
    parser.add_argument('--query', '-q', help='Search query')
    parser.add_argument('--limit', '-l', type=int, default=10, help='Max results (<=40)')
    parser.add_argument('--csv', help='CSV output')
    parser.add_argument('--lang', help='Language code (e.g., en, cs)')
    parser.add_argument('--apikey', help='Google Books API key (optional)')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    args = parser.parse_args()
    if args.interactive or not args.query:
        run_interactive()
        return
    books = fetch_books(args.query, args.limit, args.apikey, args.lang)
    if not books:
        print("No books found!")
        return
    save_html(books, args.query, len(books))
    if args.csv:
        save_csv(books, args.csv)

if __name__ == "__main__":
    main()
