#!/usr/bin/env python3
"""
Generate skill template from a GitHub repository.
Analyzes repository structure and creates boilerplate for a Claude Skill.
"""

import argparse
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: requests is required. Install with: pip install requests")
    sys.exit(1)


def fetch_repo_contents(owner, repo, github_token=None):
    """Fetch repository contents from GitHub API."""
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/"

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "github-to-skill"
    }

    if github_token:
        headers["Authorization"] = f"token {github_token}"

    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching repository contents: {e}", file=sys.stderr)
        return None


def fetch_file_content(owner, repo, path, github_token=None):
    """Fetch file content from GitHub repository."""
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "github-to-skill"
    }

    if github_token:
        headers["Authorization"] = f"token {github_token}"

    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Decode base64 content
        import base64
        content = base64.b64decode(data['content']).decode('utf-8')
        return content
    except requests.exceptions.RequestException as e:
        print(f"Error fetching file content: {e}", file=sys.stderr)
        return None


def generate_skill_frontmatter(skill_name, description):
    """Generate YAML frontmatter for SKILL.md."""
    return f"""---
name: {skill_name}
description: "{description}"
---
"""


def generate_skill_md_content(skill_name, repo_url, core_features):
    """Generate body content for SKILL.md."""
    return f"""# {skill_name.replace('-', ' ').title()}

## Overview

[TODO: 1-2 sentences explaining what this skill enables]

This skill is based on [{repo_url}]({repo_url}).

## Core Features

{chr(10).join(f"- {feature}" for feature in core_features)}

## Quick Start

### Installation

Install required dependencies:

```bash
# [TODO: Add installation commands]
pip install <package-name>
```

### Basic Usage

```python
# [TODO: Add usage example]
import {skill_name.replace('-', '_')}
```

## Configuration

[TODO: Describe any configuration options, environment variables, or setup steps]

## API Reference

[TODO: Document main functions, parameters, and return types]

## Examples

[TODO: Add real-world usage examples]

## Resources

- Original repository: {repo_url}
- Documentation: [TODO: Add docs link]
- Issues/Bugs: [TODO: Add issues link]
"""


def generate_skill_template(skill_name, repo_url, features, output_dir):
    """Generate complete skill directory structure."""
    skill_dir = Path(output_dir) / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)

    # Generate SKILL.md
    frontmatter = generate_skill_frontmatter(
        skill_name,
        f"Skill generated from {repo_url}"
    )
    body = generate_skill_md_content(skill_name, repo_url, features)

    skill_md = skill_dir / "SKILL.md"
    with open(skill_md, 'w', encoding='utf-8') as f:
        f.write(frontmatter + "\n" + body)

    # Create subdirectories
    (skill_dir / "scripts").mkdir(exist_ok=True)
    (skill_dir / "references").mkdir(exist_ok=True)

    # Create example script
    example_script = skill_dir / "scripts" / "example.py"
    with open(example_script, 'w', encoding='utf-8') as f:
        f.write(f'''#!/usr/bin/env python3
"""
Example script for {skill_name}.
[TODO: Add description]
"""

import sys

def main():
    """[TODO: Implement main function]"""
    print("Hello from {skill_name}!")
    return 0

if __name__ == '__main__':
    sys.exit(main())
''')

    print(f"✅ Generated skill template at: {skill_dir}")
    print(f"   - SKILL.md")
    print(f"   - scripts/example.py")
    print(f"   - references/")

    return skill_dir


def analyze_repo_and_generate(full_repo_name, output_dir=".", github_token=None):
    """Analyze GitHub repository and generate skill template."""
    try:
        owner, repo = full_repo_name.split('/')
    except ValueError:
        print(f"Error: Invalid repository format '{full_repo_name}'. Use 'owner/repo' format.", file=sys.stderr)
        sys.exit(1)

    print(f"🔍 Analyzing {full_repo_name}...")

    # Fetch repository info
    contents = fetch_repo_contents(owner, repo, github_token)
    if not contents:
        print("❌ Failed to fetch repository contents", file=sys.stderr)
        sys.exit(1)

    # Extract basic information
    skill_name = repo.lower().replace('_', '-')

    # Identify potential features
    features = [
        "Core functionality from original repository",
        "Integration with Claude AI",
        "Automated workflows"
    ]

    # Look for README to extract more info
    for item in contents:
        if item['name'].lower().startswith('readme'):
            readme_content = fetch_file_content(owner, repo, item['name'], github_token)
            if readme_content:
                # Could parse README for more features
                print(f"📖 Found README: {item['name']}")
                features.append(f"Based on documentation from {item['name']}")
                break

    repo_url = f"https://github.com/{full_repo_name}"

    # Generate template
    skill_dir = generate_skill_template(skill_name, repo_url, features, output_dir)

    print(f"\n💡 Next steps:")
    print(f"   1. Review SKILL.md and customize the description")
    print(f"   2. Implement core functionality in scripts/")
    print(f"   3. Add documentation to references/")
    print(f"   4. Test the skill and package it")

    return skill_dir


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description='Generate Claude Skill template from GitHub repository',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate skill from a repository
  %(prog)s owner/repository

  # Specify custom output directory
  %(prog)s owner/repository --output ./my-skills

  # Use GitHub token for private repositories
  %(prog)s owner/repository --token YOUR_TOKEN
        """
    )

    parser.add_argument(
        'repository',
        help='GitHub repository in "owner/repo" format'
    )

    parser.add_argument(
        '--output', '-o',
        default='.',
        help='Output directory for generated skill (default: current directory)'
    )

    parser.add_argument(
        '--token', '-t',
        help='GitHub personal access token (for private repos)'
    )

    args = parser.parse_args()

    # Get GitHub token from environment if not provided
    github_token = args.token or os.environ.get('GITHUB_TOKEN')

    # Generate skill template
    analyze_repo_and_generate(
        args.repository,
        args.output,
        github_token
    )


if __name__ == '__main__':
    main()
