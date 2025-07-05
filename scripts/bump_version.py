#!/usr/bin/env python3
"""
Simple version bumping script for sparksneeze.

Usage:
    python scripts/bump_version.py [patch|minor|major] [--dry-run]
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


def get_current_version():
    """Get current version from pyproject.toml."""
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        raise FileNotFoundError("pyproject.toml not found")
    
    content = pyproject_path.read_text()
    match = re.search(r'version = "([^"]+)"', content)
    if not match:
        raise ValueError("Version not found in pyproject.toml")
    
    return match.group(1)


def parse_version(version_str):
    """Parse version string into (major, minor, patch) tuple."""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version_str)
    if not match:
        raise ValueError(f"Invalid version format: {version_str}")
    
    return tuple(map(int, match.groups()))


def bump_version(version_tuple, bump_type):
    """Bump version based on type."""
    major, minor, patch = version_tuple
    
    if bump_type == "major":
        return (major + 1, 0, 0)
    elif bump_type == "minor":
        return (major, minor + 1, 0)
    elif bump_type == "patch":
        return (major, minor, patch + 1)
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")


def format_version(version_tuple):
    """Format version tuple back to string."""
    return ".".join(map(str, version_tuple))


def update_pyproject_toml(old_version, new_version, dry_run=False):
    """Update version in pyproject.toml."""
    pyproject_path = Path("pyproject.toml")
    content = pyproject_path.read_text()
    
    new_content = content.replace(
        f'version = "{old_version}"',
        f'version = "{new_version}"'
    )
    
    if content == new_content:
        raise ValueError("Version not found or already updated in pyproject.toml")
    
    if not dry_run:
        pyproject_path.write_text(new_content)
    
    return new_content


def update_init_py(old_version, new_version, dry_run=False):
    """Update fallback version in __init__.py."""
    init_path = Path("src/sparksneeze/__init__.py")
    content = init_path.read_text()
    
    new_content = content.replace(
        f'__version__ = "{old_version}"',
        f'__version__ = "{new_version}"'
    )
    
    if content == new_content:
        raise ValueError("Version not found or already updated in __init__.py")
    
    if not dry_run:
        init_path.write_text(new_content)
    
    return new_content


def update_docs_conf(old_version, new_version, dry_run=False):
    """Update version in docs/conf.py."""
    conf_path = Path("docs/conf.py")
    if not conf_path.exists():
        return None
    
    content = conf_path.read_text()
    
    new_content = content.replace(
        f"release = '{old_version}'",
        f"release = '{new_version}'"
    )
    
    if content == new_content:
        raise ValueError("Version not found or already updated in docs/conf.py")
    
    if not dry_run:
        conf_path.write_text(new_content)
    
    return new_content


def update_docs_metadata_rst(old_version, new_version, dry_run=False):
    """Update version in docs/metadata.rst example."""
    rst_path = Path("docs/metadata.rst")
    if not rst_path.exists():
        return None
    
    content = rst_path.read_text()
    
    new_content = content.replace(
        f'"sparksneeze_version": "{old_version}"',
        f'"sparksneeze_version": "{new_version}"'
    )
    
    if content == new_content:
        raise ValueError("Version not found or already updated in docs/metadata.rst")
    
    if not dry_run:
        rst_path.write_text(new_content)
    
    return new_content


def create_git_commit(old_version, new_version, dry_run=False):
    """Create git commit with version bump."""
    commit_message = f"Bump version from {old_version} to {new_version}"
    
    if dry_run:
        print(f"Would create commit: {commit_message}")
        return
    
    # Add changed files
    files_to_add = [
        "pyproject.toml", 
        "src/sparksneeze/__init__.py"
    ]
    
    # Add docs files if they exist
    if Path("docs/conf.py").exists():
        files_to_add.append("docs/conf.py")
    if Path("docs/metadata.rst").exists():
        files_to_add.append("docs/metadata.rst")
    
    subprocess.run(["git", "add"] + files_to_add, check=True)
    
    # Create commit
    subprocess.run(["git", "commit", "-m", commit_message], check=True)
    
    print(f"Created commit: {commit_message}")


def main():
    parser = argparse.ArgumentParser(description="Bump version for sparksneeze")
    parser.add_argument("bump_type", choices=["patch", "minor", "major"], 
                       help="Type of version bump")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be done without making changes")
    
    args = parser.parse_args()
    
    try:
        # Get current version
        current_version = get_current_version()
        print(f"Current version: {current_version}")
        
        # Parse and bump version
        version_tuple = parse_version(current_version)
        new_version_tuple = bump_version(version_tuple, args.bump_type)
        new_version = format_version(new_version_tuple)
        
        print(f"New version: {new_version}")
        
        if args.dry_run:
            print("\nDry run - would make the following changes:")
            print("- Update pyproject.toml")
            print("- Update src/sparksneeze/__init__.py")
            if Path("docs/conf.py").exists():
                print("- Update docs/conf.py")
            if Path("docs/metadata.rst").exists():
                print("- Update docs/metadata.rst")
            print(f"- Create git commit: 'Bump version from {current_version} to {new_version}'")
            return
        
        # Update files
        print("\nUpdating files...")
        update_pyproject_toml(current_version, new_version)
        update_init_py(current_version, new_version)
        
        # Update docs files if they exist
        try:
            update_docs_conf(current_version, new_version)
            print("Updated docs/conf.py")
        except (ValueError, FileNotFoundError):
            pass
        
        try:
            update_docs_metadata_rst(current_version, new_version)
            print("Updated docs/metadata.rst")
        except (ValueError, FileNotFoundError):
            pass
        
        # Create git commit
        print("Creating git commit...")
        create_git_commit(current_version, new_version)
        
        print(f"\nVersion successfully bumped from {current_version} to {new_version}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()