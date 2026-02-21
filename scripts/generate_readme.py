import json
import os
import re
import requests
from collections import defaultdict
from datetime import datetime

GITHUB_TOKEN = os.environ.get('GH_PAT') or os.environ.get('GITHUB_TOKEN')
headers = {'Accept': 'application/vnd.github.v3+json'}
if GITHUB_TOKEN:
    headers['Authorization'] = f'token {GITHUB_TOKEN}'

# Check if repos.json exists
if not os.path.exists('repos.json'):
    print("repos.json not found. Make sure the API fetch step ran.")
    exit(0)

with open('repos.json', 'r') as f:
    try:
        repos = json.load(f)
    except json.JSONDecodeError:
        print("repos.json is invalid.")
        exit(1)

if not isinstance(repos, list):
    print("repos.json does not contain a list of repositories.")
    exit(1)

# Filter out forks
source_repos = repos

# Differentiate between public and private
public_repos = [r for r in source_repos if not r.get('private', False)]
private_repos = [r for r in source_repos if r.get('private', False)]

total_public = len(public_repos)
total_private = len(private_repos)
total_stars = sum(r.get('stargazers_count', 0) for r in source_repos)

# Aggregate language stats by bytes directly from the API
language_bytes = defaultdict(int)
IGNORE_LANGUAGES = ['Jupyter Notebook', 'HTML', 'CSS', 'SCSS']

print("Fetching detailed language stats for repositories...")
for repo in source_repos:
    lang_url = repo.get('languages_url')
    if not lang_url:
        continue
        
    try:
        response = requests.get(lang_url, headers=headers)
        if response.status_code == 200:
            repo_langs = response.json()
            for lang, bytes_count in repo_langs.items():
                if lang not in IGNORE_LANGUAGES:
                    language_bytes[lang] += bytes_count
    except Exception as e:
        print(f"Error fetching languages for {repo.get('name')}: {e}")

# Calculate percentages and sort
total_bytes = sum(language_bytes.values())
sorted_langs = sorted(language_bytes.items(), key=lambda x: x[1], reverse=True)[:5]
top_langs_str = "N/A"

if total_bytes > 0:
    formatted_langs = []
    for lang, size in sorted_langs:
        # Avoid 0% print if it's very small
        percentage = max(1, round((size / total_bytes) * 100))
        formatted_langs.append(f"{lang} ({percentage}%)")
    top_langs_str = ', '.join(formatted_langs)

# Sort repos by updated_at, filter out '.github', only show PUBLIC repos in recent activity
recent_candidates = [r for r in public_repos if r.get('name') != '.github']
recent_repos = sorted(recent_candidates, key=lambda x: x.get('updated_at', ''), reverse=True)[:5]

markdown = f"""
| 🏆 GitHub Stats | |
| :--- | :--- |
| **Total Public Repos** | {total_public} |
| **Total Private Repos** | {total_private} |
| **Total Stars Earned** | {total_stars} 🌟 |
| **Top Languages Used** | {top_langs_str} |

### ⚡ Recent Activity
"""

for repo in recent_repos:
    name = repo.get('name')
    url = repo.get('html_url')
    date_str = repo.get('updated_at', '')
    if date_str:
        try:
            date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ").strftime("%b %d, %Y")
        except ValueError:
            date = date_str
    else:
        date = "Unknown"
    markdown += f"- [{name}]({url}) - {date}\n"

# Replace in README
readme_path = 'profile/README.md'
if not os.path.exists(readme_path):
    print(f"{readme_path} not found.")
    exit(1)

with open(readme_path, 'r') as f:
    content = f.read()

pattern = re.compile(r'<!-- START_STATS -->.*<!-- END_STATS -->', re.DOTALL)
if pattern.search(content):
    content = pattern.sub(f'<!-- START_STATS -->\n{markdown}\n<!-- END_STATS -->', content)
    with open(readme_path, 'w') as f:
        f.write(content)
    print("Successfully updated README.md with granular language stats.")
else:
    print("Markers <!-- START_STATS --> and <!-- END_STATS --> not found in README.md.")
    exit(1)
