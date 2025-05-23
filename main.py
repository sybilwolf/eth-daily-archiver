#!/usr/bin/env python3

import json
import re
import subprocess
import sys
import os
import time
import urllib.request
import argparse
import glob
from datetime import datetime, timedelta, timezone

URS_ROOT_DIR = "../URS"
URS_SCRAPES_RELATIVE_DIR = f"./scrapes"
FINAL_OUTPUT_DIR = "../eth-daily-archiver-data/data"
THREAD_ID_REGEX = re.compile(r'/comments/(.+?)/')
SUBREDDIT_ID_REGEX = re.compile(r'r/(.+?)/comments/')
POST_ID_FROM_FILENAME_REGEX = re.compile(r'-([a-zA-Z0-9]+)\.json$')

# Argument parsing
parser = argparse.ArgumentParser(description="Reddit daily scraper")
parser.add_argument('-n', '--number-of-discussions', type=int, default=0,
                    help='Maximum number of reddit threads to process in this batch before exiting (0 means unlimited)')
args = parser.parse_args()

# Print summary of command line flags
print(f"Flags: --number-of-discussions={args.number_of_discussions}")

# Create directories if they don't exist
os.makedirs(FINAL_OUTPUT_DIR, exist_ok=True)
os.makedirs(URS_SCRAPES_RELATIVE_DIR, exist_ok=True)

# Create a list of all scrapes from dailies.json
# GitHub URL:
# https://raw.githubusercontent.com/etheralpha/dailydoots-com/refs/heads/main/_data/dailies.json
# Site URL:
# https://dailydoots.com/dailies.json
# dailies.json format example:
# [{"date": "2025-05-16", "title": "Daily General Discussion - May 16, 2025", "link": "https://reddit.com/r/ethereum/comments/1kntpet/", "comments": 5}, ...]

doots_json_url = "https://dailydoots.com/dailies.json"
with urllib.request.urlopen(doots_json_url) as response:
    all_threads_json = json.load(response)

# Remove dailies newer than 3 days ago from the set to scrape, since they may still be active.
# Dailies are typically posted at 06:00 UTC on their thread date, so we can use that as a cutoff
# to determine if a daily is old enough to scrape.
current_datetime = datetime.now(timezone.utc)
datetime_three_days_ago = current_datetime - timedelta(days=3)
aged_threads_json = []
for elem in all_threads_json:
    thread_date_utc_six_am = datetime.strptime(elem['date'], "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(hours=6)
    if thread_date_utc_six_am < datetime_three_days_ago:
        aged_threads_json.append(elem)

# Transform the aged_threads_json to a dictionary with the thread id as the key and the official dailydoots thread date as the value
# This is used later to add the thread date metadata to the thread that has just been scraped
aged_threads_dict = {}
for elem in aged_threads_json:
    match = THREAD_ID_REGEX.search(elem['link'])
    if match:
        thread_id = match[1]
        aged_threads_dict[thread_id] = elem['date']

# Create a list of already finished scrape IDs
finished_scrape_filename_list = glob.glob(f"{FINAL_OUTPUT_DIR}/**/*.json", recursive=True)
print(f"Found {len(finished_scrape_filename_list)} postprocessed scrape files. Generating list of files to scrape...")
finished_scrape_id_list = []
for line in finished_scrape_filename_list:
    match = POST_ID_FROM_FILENAME_REGEX.search(os.path.basename(line))
    if match:
        thread_id = match[1]
        finished_scrape_id_list.append(thread_id)

# Create upcoming_scrapes_json: only scrape threads whose id is not already in finished_scrape_id_list
finished_scrape_id_set = set(finished_scrape_id_list)
upcoming_scrapes_json = []
for elem in aged_threads_json:
    match = THREAD_ID_REGEX.search(elem['link'])
    if match:
        thread_id = match[1]
        if thread_id not in finished_scrape_id_set:
            upcoming_scrapes_json.append(elem)

# Print statistics to the user before we begin scraping
total_ct = len(aged_threads_json)
finished_ct = len(finished_scrape_id_list)
upcoming_ct = len(upcoming_scrapes_json)
print(f'Total Daily Threads: {total_ct}, In Archive: {finished_ct}, To Archive: {upcoming_ct}')

# Process up to X reddit threads in this invocation of main.py, based on the command line option
if args.number_of_discussions == 0:
    num_discussions = len(upcoming_scrapes_json)
else:
    num_discussions = args.number_of_discussions

def get_all_json_files():
    scrape_dir = f"{URS_ROOT_DIR}/{URS_SCRAPES_RELATIVE_DIR}/**/*.json"
    globbed_files = set(glob.glob(scrape_dir, recursive=True))
    return set(globbed_files)

for i in range(min(num_discussions, len(upcoming_scrapes_json))):
    thread = upcoming_scrapes_json[i]
    print()
    print(f"Now Scraping: date={thread['date']}, comments={thread['comments']}")

    # 1. List all json files before scraping
    before_files = get_all_json_files()

    # 2. Run URS
    urs_call = f"poetry run python ./Urs.py -c {thread['link']} 0"
    print(f"> {urs_call}")
    result = subprocess.run(
        urs_call,
        shell=True,
        cwd=f"{URS_ROOT_DIR}/urs/",
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(result.stdout)
        raise subprocess.CalledProcessError(result.returncode, urs_call)

    # 3. List all json files after scraping
    after_files = get_all_json_files()

    # 4. Find the new file(s)
    new_files = list(after_files - before_files)
    if not new_files:
        print("Warn: No new JSON file found after scraping.")
        continue
    # If multiple, pick the newest
    newest_file_name = max(new_files, key=os.path.getmtime)

    # 5. Postprocess the new scrape file, adding some metadata and renaming it
    print(f"Postprocessing: {newest_file_name}")
    # Collect date metadata from the scrape
    with open(newest_file_name) as json_data:
        original_json_object = json.load(json_data)
        thread_link = original_json_object['scrape_settings']['url']
        thread_id = THREAD_ID_REGEX.search(thread_link)[1]
        subreddit_id = SUBREDDIT_ID_REGEX.search(thread_link)[1]

    date_of_thread = aged_threads_dict.get(thread_id, None)

    # Create the new structure
    new_json = {
        "datetime_retrieved": int(time.time()),
        "date_of_thread": date_of_thread,
        "urs_data": original_json_object
    }
    # Write file according to its subreddit and date, e.g. 2020-01-01-ethfinance-xxxxxx.json
    new_filename = f"{date_of_thread}-{subreddit_id}-{thread_id}.json"
    new_filepath = os.path.join(f'{FINAL_OUTPUT_DIR}', new_filename)
    print(f"Writing postprocessed json: {new_filename}")
    with open(new_filepath, 'w') as outfile:
        json.dump(new_json, outfile, separators=(',', ':')) # Minify JSON

    # Rename the original file to add the ".finished" suffix to indicate it has been processed
    newest_file_postprocessed_name = newest_file_name + ".finished"
    print(f"Renaming original file to: {newest_file_postprocessed_name}")
    os.rename(newest_file_name, newest_file_postprocessed_name)

    # 6. Continue scraping
    print(f"Upcoming scrapes to perform this run: {len(upcoming_scrapes_json) - i - 1}")
    print("Continuing...")

print(f"Successfully completed ({num_discussions}) scrapes.")
