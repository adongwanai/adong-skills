#!/usr/bin/env python3
"""
Search GitHub repositories for skill creation.
Finds high-quality, active repositories suitable for Claude Skills.
"""

import argparse
import json
import os
import sys
from urllib.parse import urlencode

try:
    import requests
except ImportError:
    print("Error: requests is required. Install with: pip install requests")
    sys.exit(1)


# GitHub API base URL
GITHUB_API_URL = "https://api.github.com/search/repositories"


def search_github_repos(
    query,
    language=None,
    min_stars=100,
    sort="stars",
    per_page=10,
    github_token=None
):
    """
    Search GitHub repositories with filters.

    Args:
        query: Search query string
        language: Filter by programming language
        min_stars: Minimum number of stars
        sort: Sort by 'stars', 'forks', or 'updated'
        per_page: Number of results to return (max 100)
        github_token: GitHub personal access token for API rate limiting

    Returns:
        List of repository dictionaries
    """
    # Build search query
    search_terms = [query]

    if language:
        search_terms.append(f"language:{language}")

    if min_stars:
        search_terms.append(f"stars:>={min_stars}")

    full_query = " ".join(search_terms)

    # Build API request parameters
    params = {
        "q": full_query,
        "sort": sort,
        "order": "desc",
        "per_page": min(per_page, 100)
    }

    # Set up headers
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "github-to-skill"
    }

    if github_token:
        headers["Authorization"] = f"token {github_token}"

    try:
        # Make API request
        response = requests.get(
            GITHUB_API_URL,
            params=params,
            headers=headers,
            timeout=10
        )

        response.raise_for_status()
        data = response.json()

        return data.get("items", [])

    except requests.exceptions.RequestException as e:
        print(f"Error searching GitHub: {e}", file=sys.stderr)
        return []


def format_repo_table(repos):
    """
    Format repositories as a Markdown table.

    Args:
        repos: List of repository dictionaries

    Returns:
        Markdown formatted table string
    """
    if not repos:
        return "No repositories found."

    # Table header
    table = "| # | Repository | Stars | Updated | Language | Description | Recommendation |\n"
    table += "|---|-----------|-------|---------|----------|-------------|----------------|\n"

    # Table rows
    for idx, repo in enumerate(repos, 1):
        name = f"[{repo['full_name']}]({repo['html_url']})"
        stars = repo['stargazers_count']
        updated = repo['updated_at'][:10]  # YYYY-MM-DD
        language = repo.get('language', 'N/A')
        description = repo.get('description', 'No description')[:60] + ('...' if len(repo.get('description', '')) > 60 else '')

        # Generate recommendation reason
        reasons = []
        if stars >= 1000:
            reasons.append(f"⭐ {stars}+ stars")
        if language:
            reasons.append(f"💻 {language}")
        if repo.get('license'):
            reasons.append(f"📜 {repo['license']['key']}")
        recommendation = ", ".join(reasons) if reasons else "✓ Active"

        table += f"| {idx} | {name} | {stars} | {updated} | {language} | {description} | {recommendation} |\n"

    return table


def save_results(repos, output_file):
    """
    Save search results to JSON file.

    Args:
        repos: List of repository dictionaries
        output_file: Path to output JSON file
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(repos, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved {len(repos)} repositories to {output_file}")


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description='Search GitHub repositories for skill creation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for PDF processing libraries
  %(prog)s "PDF processing" --language python

  # Search with minimum stars and recent updates
  %(prog)s "image manipulation" --min-stars 500 --sort updated

  # Save results to file
  %(prog)s "REST API client" --output results.json
        """
    )

    parser.add_argument(
        'query',
        help='Search query string (e.g., "PDF processing", "image manipulation")'
    )

    parser.add_argument(
        '--language', '-l',
        help='Filter by programming language (e.g., python, javascript, go)'
    )

    parser.add_argument(
        '--min-stars', '-s',
        type=int,
        default=100,
        help='Minimum number of stars (default: 100)'
    )

    parser.add_argument(
        '--sort',
        choices=['stars', 'forks', 'updated'],
        default='stars',
        help='Sort results by (default: stars)'
    )

    parser.add_argument(
        '--results', '-r',
        type=int,
        default=10,
        help='Number of results to return (default: 10, max: 100)'
    )

    parser.add_argument(
        '--output', '-o',
        help='Save results to JSON file'
    )

    parser.add_argument(
        '--token', '-t',
        help='GitHub personal access token (optional, increases rate limit)'
    )

    parser.add_argument(
        '--format', '-f',
        choices=['table', 'json'],
        default='table',
        help='Output format (default: table)'
    )

    args = parser.parse_args()

    # Get GitHub token from environment if not provided
    github_token = args.token or os.environ.get('GITHUB_TOKEN')

    # Search repositories
    repos = search_github_repos(
        query=args.query,
        language=args.language,
        min_stars=args.min_stars,
        sort=args.sort,
        per_page=args.results,
        github_token=github_token
    )

    if not repos:
        print("❌ No repositories found matching your criteria.", file=sys.stderr)
        sys.exit(1)

    # Output results
    if args.format == 'json':
        print(json.dumps(repos, indent=2, ensure_ascii=False))
    else:
        print(f"\n🔍 Found {len(repos)} repositories:\n")
        print(format_repo_table(repos))
        print(f"\n💡 Tip: Use --output to save results for later analysis")

    # Save to file if requested
    if args.output:
        save_results(repos, args.output)


if __name__ == '__main__':
    main()
