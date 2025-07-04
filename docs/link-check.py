#!/usr/bin/env python3
"""
Link checker for SparkSneeze documentation.
Validates all internal and external links in the built HTML documentation.
"""

import os
import sys
import requests
from pathlib import Path
from bs4 import BeautifulSoup
import argparse
from typing import Set, List, Tuple


class LinkChecker:
    def __init__(self, html_dir: Path, base_url: str = ""):
        self.html_dir = Path(html_dir)
        self.base_url = base_url
        self.internal_links: Set[str] = set()
        self.external_links: Set[str] = set()
        self.broken_links: List[Tuple[str, str, str]] = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SparkSneeze-Docs-LinkChecker/1.0'
        })
        
    def find_all_links(self) -> None:
        """Find all links in HTML files."""
        html_files = list(self.html_dir.glob("**/*.html"))
        
        for html_file in html_files:
            with open(html_file, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
                
            # Find all anchor tags with href
            for link in soup.find_all('a', href=True):
                href = link['href']
                self._categorize_link(href, str(html_file))
                
    def _categorize_link(self, href: str, source_file: str) -> None:
        """Categorize link as internal or external."""
        # Skip anchors and special links
        if href.startswith(('#', 'mailto:', 'javascript:', 'tel:')):
            return
            
        # Check if external URL
        if href.startswith(('http://', 'https://')):
            self.external_links.add((href, source_file))
        else:
            # Internal link - resolve relative to current file
            self.internal_links.add((href, source_file))
            
    def check_internal_links(self) -> None:
        """Check all internal links exist."""
        for link, source_file in self.internal_links:
            # Remove fragment identifier
            clean_link = link.split('#')[0]
            if not clean_link:  # Pure fragment link
                continue
                
            # Resolve path relative to source file
            source_dir = Path(source_file).parent
            target_path = source_dir / clean_link
            
            # Normalize path
            try:
                target_path = target_path.resolve()
            except OSError:
                self.broken_links.append((link, source_file, "Invalid path"))
                continue
                
            # Check if file exists
            if not target_path.exists():
                # Try with .html extension if missing
                if not target_path.suffix and not (target_path.with_suffix('.html')).exists():
                    self.broken_links.append((link, source_file, "File not found"))
                elif target_path.suffix and not target_path.exists():
                    self.broken_links.append((link, source_file, "File not found"))
                    
    def check_external_links(self, timeout: int = 10) -> None:
        """Check external links are accessible."""
        for link, source_file in self.external_links:
            try:
                response = self.session.head(link, timeout=timeout, allow_redirects=True)
                if response.status_code >= 400:
                    self.broken_links.append((link, source_file, f"HTTP {response.status_code}"))
            except requests.RequestException as e:
                self.broken_links.append((link, source_file, f"Request failed: {str(e)}"))
                
    def generate_report(self) -> str:
        """Generate a report of the link checking results."""
        report = []
        report.append("SparkSneeze Documentation Link Check Report")
        report.append("=" * 50)
        report.append(f"Internal links found: {len(self.internal_links)}")
        report.append(f"External links found: {len(self.external_links)}")
        report.append(f"Broken links found: {len(self.broken_links)}")
        report.append("")
        
        if self.broken_links:
            report.append("BROKEN LINKS:")
            report.append("-" * 20)
            for link, source_file, error in self.broken_links:
                rel_source = os.path.relpath(source_file, self.html_dir)
                report.append(f"❌ {link}")
                report.append(f"   Source: {rel_source}")
                report.append(f"   Error: {error}")
                report.append("")
        else:
            report.append("✅ All links are working correctly!")
            
        return "\n".join(report)
        
    def run_check(self, check_external: bool = True, timeout: int = 10) -> bool:
        """Run the complete link check process."""
        print("Finding links in documentation...")
        self.find_all_links()
        
        print(f"Checking {len(self.internal_links)} internal links...")
        self.check_internal_links()
        
        if check_external:
            print(f"Checking {len(self.external_links)} external links...")
            self.check_external_links(timeout)
        
        return len(self.broken_links) == 0


def main():
    parser = argparse.ArgumentParser(description="Check links in SparkSneeze documentation")
    parser.add_argument("html_dir", help="Path to built HTML documentation")
    parser.add_argument("--no-external", action="store_true", 
                      help="Skip checking external links")
    parser.add_argument("--timeout", type=int, default=10,
                      help="Timeout for external link checks (seconds)")
    parser.add_argument("--output", help="Output report to file")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.html_dir):
        print(f"Error: HTML directory '{args.html_dir}' does not exist")
        sys.exit(1)
        
    checker = LinkChecker(args.html_dir)
    success = checker.run_check(
        check_external=not args.no_external,
        timeout=args.timeout
    )
    
    report = checker.generate_report()
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"Report written to {args.output}")
    else:
        print(report)
        
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()