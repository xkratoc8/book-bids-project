#!/usr/bin/env python3
# Open Library Book Scraper with CSS Styling

import requests
import json
import time
import csv
import html as html_module
from typing import Dict, List, Optional, Any
from datetime import datetime
import argparse

class OpenLibraryBookScraper:
    def __init__(self):
        self.base_url = "https://openlibrary.org/search.json"
        self.covers_url = "https://covers.openlibrary.org/b"
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'OpenLibraryBookScraper/1.0'})

        self.available_fields = [
            'key', 'title', 'subtitle', 'author_name', 'author_key',
            'cover_i', 'first_publish_year', 'publish_year', 'publisher',
            'isbn', 'isbn13', 'subject', 'language', 'number_of_pages_median',
            'ratings_average', 'ratings_count', 'want_to_read_count',
            'currently_reading_count', 'already_read_count', 'readinglog_count',
            'edition_count', 'lc_classifications', 'dewey_decimal_class',
            'ia', 'has_fulltext', 'public_scan_b', 'lending_edition_s'
        ]

    def search_books(self, query="", author="", title="", subject="", limit=10, language=""):
        params = {
            'limit': min(limit, 100),
            'fields': ','.join(self.available_fields)
        }

        query_parts = []
        if query: query_parts.append(query)
        if author: query_parts.append(f'author:"{author}"')
        if title: query_parts.append(f'title:"{title}"')
        if subject: query_parts.append(f'subject:"{subject}"')
        if language: query_parts.append(f'language:{language}')

        params['q'] = ' AND '.join(query_parts) if query_parts else '*'

        try:
            print(f"Searching: {params['q']}")
            response = self.session.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            time.sleep(0.5)
            return response.json()
        except Exception as e:
            print(f"Error: {e}")
            return {"docs": [], "numFound": 0}

    def get_cover_url(self, cover_id, size="M"):
        return f"{self.covers_url}/id/{cover_id}-{size}.jpg" if cover_id else None

    def calculate_popularity(self, book):
        score = 0.0
        if book.get('ratings_average') and book.get('ratings_count'):
            score += (book['ratings_average'] / 5.0) * 20
            score += min(book['ratings_count'] / 100, 20)

        reading = sum([
            book.get('want_to_read_count', 0),
            book.get('currently_reading_count', 0),
            book.get('already_read_count', 0)
        ])
        score += min(reading / 50, 30)
        score += min(book.get('edition_count', 0) * 2, 20)

        if book.get('has_fulltext'): score += 5
        if book.get('lending_edition_s'): score += 5

        return round(score, 2)

    def get_availability(self, book):
        if book.get('has_fulltext'): return "Full Text Available"
        if book.get('lending_edition_s'): return "Available for Lending"
        if book.get('public_scan_b'): return "Public Scan Available"
        if book.get('ia'): return "Archive.org Available"
        return "Metadata Only"

    def get_reading_level(self, book):
        pages = book.get('number_of_pages_median', 0)
        if pages > 800: return "Advanced"
        if pages > 400: return "Intermediate"
        return "Beginner"

    def format_book(self, book):
        return {
            'key': book.get('key', ''),
            'url': f"https://openlibrary.org{book.get('key', '')}",
            'title': book.get('title', 'Unknown'),
            'subtitle': book.get('subtitle', ''),
            'authors': book.get('author_name', []),
            'first_year': book.get('first_publish_year'),
            'publishers': book.get('publisher', []),
            'pages': book.get('number_of_pages_median'),
            'isbn': book.get('isbn', []),
            'subjects': book.get('subject', []),
            'cover_url': self.get_cover_url(book.get('cover_i')),
            'rating': book.get('ratings_average'),
            'rating_count': book.get('ratings_count'),
            'want_read': book.get('want_to_read_count', 0),
            'reading_now': book.get('currently_reading_count', 0),
            'have_read': book.get('already_read_count', 0),
            'editions': book.get('edition_count', 0),
            'popularity': self.calculate_popularity(book),
            'availability': self.get_availability(book),
            'level': self.get_reading_level(book)
        }

    def generate_html(self, books, query="", total=0):
        cards_html = ""
        for book in books:
            authors = ', '.join(book['authors']) if book['authors'] else 'Unknown'
            cover_html = f'<img src="{book["cover_url"]}">' if book["cover_url"] else '<div class="no-cover">No Cover</div>'
            subjects_html = ', '.join(book['subjects'][:5]) if book['subjects'] else 'None'

            cards_html += f'''
            <div class="card">
                <div class="score">{book["popularity"]}</div>
                <h2>{html_module.escape(book["title"])}</h2>
                <p>by {html_module.escape(authors)}</p>
                <div class="cover">{cover_html}</div>
                <div class="info">
                    <p><strong>Year:</strong> {book["first_year"] or "Unknown"}</p>
                    <p><strong>Pages:</strong> {book["pages"] or "Unknown"}</p>
                    <p><strong>Rating:</strong> {book["rating"] or "N/A"} ({book["rating_count"] or 0} ratings)</p>
                    <p><strong>Editions:</strong> {book["editions"]}</p>
                    <p><strong>Level:</strong> {book["level"]}</p>
                    <p><strong>Status:</strong> {book["availability"]}</p>
                    <p><strong>Want to Read:</strong> {book["want_read"]}</p>
                    <p><strong>Subjects:</strong> {html_module.escape(subjects_html)}</p>
                </div>
                <a href="{book["url"]}" target="_blank">View on Open Library</a>
            </div>
            '''

        html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Open Library Books</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 20px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
        }}
        .card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            position: relative;
        }}
        .card:hover {{ transform: translateY(-5px); transition: 0.3s; }}
        .score {{
            position: absolute;
            top: 10px;
            right: 10px;
            background: #e74c3c;
            color: white;
            padding: 8px 12px;
            border-radius: 20px;
            font-weight: bold;
        }}
        .card h2 {{ color: #2c3e50; font-size: 1.3em; margin-bottom: 5px; }}
        .card p {{ margin: 8px 0; color: #555; }}
        .cover {{ text-align: center; margin: 15px 0; }}
        .cover img {{ max-width: 100px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }}
        .no-cover {{
            width: 100px;
            height: 150px;
            background: #95a5a6;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 5px;
            color: white;
            font-weight: bold;
        }}
        .card a {{
            display: inline-block;
            margin-top: 10px;
            padding: 8px 15px;
            background: #3498db;
            color: white;
            text-decoration: none;
            border-radius: 5px;
        }}
        .card a:hover {{ background: #2980b9; }}
        .info {{ margin-top: 10px; }}
        strong {{ color: #2c3e50; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📚 Open Library Books</h1>
            <p>Query: {html_module.escape(query) if query else "All Books"}</p>
            <p>Found {total} books | Showing {len(books)}</p>
            <p style="font-size: 0.9em; color: #777;">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
        </div>
        <div class="grid">
            {cards_html}
        </div>
    </div>
</body>
</html>'''
        return html

    def save_csv(self, books, filename="books.csv"):
        if not books: return

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            fields = ['title', 'authors', 'first_year', 'publishers', 'pages',
                     'rating', 'popularity', 'availability', 'level', 'url']
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()

            for book in books:
                row = {
                    'title': book['title'],
                    'authors': '; '.join(book['authors']),
                    'first_year': book['first_year'],
                    'publishers': '; '.join(book['publishers'][:2]),
                    'pages': book['pages'],
                    'rating': book['rating'],
                    'popularity': book['popularity'],
                    'availability': book['availability'],
                    'level': book['level'],
                    'url': book['url']
                }
                writer.writerow(row)
        print(f"✅ CSV saved: {filename}")

    def run_interactive(self):
        print("\n" + "="*60)
        print("📚 OPEN LIBRARY BOOK SCRAPER")
        print("="*60)
        query = input("\nSearch query: ").strip()
        author = input("Author: ").strip()
        title = input("Title: ").strip()
        subject = input("Subject: ").strip()

        try:
            limit = int(input("How many books (default 10): ").strip() or "10")
        except:
            limit = 10

        print("\n🔍 Searching...")
        results = self.search_books(query, author, title, subject, limit)

        if not results['docs']:
            print("❌ No books found!")
            return

        books = [self.format_book(b) for b in results['docs']]
        search_query = ' '.join(filter(None, [query, author, title, subject]))

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        html_file = f"books_{timestamp}.html"
        csv_file = f"books_{timestamp}.csv"

        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(self.generate_html(books, search_query, results['numFound']))

        self.save_csv(books, csv_file)

        print(f"\n✅ HTML: {html_file}")
        print(f"✅ CSV: {csv_file}")
        print(f"📚 Found {len(books)} books")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--query', '-q', help='Search query')
    parser.add_argument('--author', '-a', help='Author')
    parser.add_argument('--title', '-t', help='Title')
    parser.add_argument('--limit', '-l', type=int, default=10)
    parser.add_argument('--interactive', '-i', action='store_true')

    args = parser.parse_args()
    scraper = OpenLibraryBookScraper()

    if args.interactive or not args.query:
        scraper.run_interactive()
    else:
        results = scraper.search_books(args.query, args.author or "", args.title or "", "", args.limit)
        if results['docs']:
            books = [scraper.format_book(b) for b in results['docs']]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            with open(f"books_{timestamp}.html", 'w', encoding='utf-8') as f:
                f.write(scraper.generate_html(books, args.query, results['numFound']))
            scraper.save_csv(books, f"books_{timestamp}.csv")
            print(f"✅ Done! Found {len(books)} books")

if __name__ == "__main__":
    main()
