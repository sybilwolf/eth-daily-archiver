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

URS_ROOT_DIR = "../URS"
URS_SCRAPES_RELATIVE_DIR = f"./scrapes"
FINAL_OUTPUT_DIR = "../eth-daily-archiver-data"
THREAD_ID_REGEX = re.compile('/comments/(.+?)/')
SUBREDDIT_ID_REGEX = re.compile('r/(.+?)/comments/')

# Argument parsing
parser = argparse.ArgumentParser(description="Reddit daily scraper")
parser.add_argument('-n', '--number-of-discussions', type=int, default=0,
                    help='Maximum number of reddit threads to process before exiting (0 means unlimited)')
parser.add_argument('-c', '--check-quota', action='store_true',
                    help='Check Reddit API quota and exit')
args = parser.parse_args()

# Print summary of command line flags
print(f"Flags: --number-of-discussions={args.number_of_discussions} --check-quota={args.check_quota}")

if args.check_quota:
    # Run URS quota check and exit
    check_cmd = "poetry run python ./Urs.py --check"
    print(f"Running quota check: {check_cmd}")
    subprocess.run(check_cmd, shell=True, cwd=f"{URS_ROOT_DIR}/urs/")
    sys.exit(0)

# Create directories if they don't exist
subprocess.check_output(f"mkdir -p {FINAL_OUTPUT_DIR}/", shell=True, universal_newlines=True)
subprocess.check_output(f"mkdir -p {URS_SCRAPES_RELATIVE_DIR}/", shell=True, universal_newlines=True)

# Create a list of all scrapes from dailies.json
# https://raw.githubusercontent.com/etheralpha/dailydoots-com/refs/heads/main/_data/dailies.json
# dailies.json format example:
# [{"date": "2025-05-16", "title": "Daily General Discussion - May 16, 2025", "link": "https://reddit.com/r/ethereum/comments/1kntpet/", "comments": 5}, ...]

github_url = "https://raw.githubusercontent.com/etheralpha/dailydoots-com/refs/heads/main/_data/dailies.json"
with urllib.request.urlopen(github_url) as response:
    all_scrapes_json = json.load(response)

# Remove dailies newer than 3 days ago from the set to scrape, since they may still be active
three_days_ago = time.time() - (3 * 24 * 60 * 60)
all_scrapes_json = [elem for elem in all_scrapes_json if time.mktime(time.strptime(elem['date'], "%Y-%m-%d")) < three_days_ago]

# Transform the all_scrapes_json to a dictionary with the thread id as the key and the date as the value
all_scrapes_dict = {}
for elem in all_scrapes_json:
    match = THREAD_ID_REGEX.search(elem['link'])
    if match:
        thread_id = match[1]
        all_scrapes_dict[thread_id] = elem['date']

# Create a list of finished scrape IDs
finished_scrape_filename_list = subprocess.check_output(f"find {FINAL_OUTPUT_DIR}/ -type f -name '*.json'", shell=True, universal_newlines=True).splitlines()
print(f"Found {len(finished_scrape_filename_list)} postprocessed scrape files. Generating list of files to scrape...")
finished_scrape_id_list = []

for line in finished_scrape_filename_list:
    with open(line) as json_data:
        finished_scrape = json.load(json_data)
        link = finished_scrape['urs_data']['scrape_settings']['url']
        thread_id = THREAD_ID_REGEX.search(link)[1]
        finished_scrape_id_list.append(thread_id)

# List diff
finished_scrape_id_set = set(finished_scrape_id_list)

# Create upcoming_scrapes_json: only scrapes whose id is not in finished_scrape_id_list
upcoming_scrapes_json = []
for elem in all_scrapes_json:
    match = THREAD_ID_REGEX.search(elem['link'])
    if match:
        thread_id = match[1]
        if thread_id not in finished_scrape_id_set:
            upcoming_scrapes_json.append(elem)

# Print statistics
total_ct = len(all_scrapes_json)
finished_ct = len(finished_scrape_id_list)
upcoming_ct = len(upcoming_scrapes_json)
print(f'Total Daily Threads: {total_ct}, In Archive: {finished_ct}, To Archive: {upcoming_ct}')

# Process up to X reddit threads
if args.number_of_discussions == 0:
    num_discussions = len(upcoming_scrapes_json)
else:
    num_discussions = args.number_of_discussions

def run_urs_and_get_requests(urs_call, urs_root_dir):
    process = subprocess.Popen(urs_call, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=f"{urs_root_dir}/", universal_newlines=True)
    output_lines = []
    for line in process.stdout:
        # print(line, end='')
        output_lines.append(line)
    process.stdout.close()
    return_code = process.wait()
    output_str = ''.join(output_lines)
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, urs_call)
    req_match = re.search(r"\|\s*(\d+)\s*\|\s*(\d+)\s*\|", output_str)
    if req_match:
        remaining_requests = int(req_match.group(1))
        used_requests = int(req_match.group(2))
        print(f"Remaining Requests: {remaining_requests}, Used Requests: {used_requests}")
        return remaining_requests, used_requests
    else:
        print("Error: Could not extract Remaining and Used Requests from output.")
        sys.exit(1)

def postprocess_scrape(filepath):
    print(f"Postprocessing: {filepath}")
    # Collect date metadata from the scrape
    with open(filepath) as json_data:
        original_json_object = json.load(json_data)
        thread_link = original_json_object['scrape_settings']['url']
        thread_id = THREAD_ID_REGEX.search(thread_link)[1]
        subreddit_id = SUBREDDIT_ID_REGEX.search(thread_link)[1]
    # Add the modified (retrieval) time to the json
    date_of_thread = all_scrapes_dict.get(thread_id, None)

    # Create the new structure
    new_json = {
        "datetime_retrieved": int(time.time()),
        "date_of_thread": date_of_thread,
        "urs_data": original_json_object
    }
    # Write file according to its subreddit and date, e.g. 2020-01-01-ethfinance.json
    new_filename = f"{date_of_thread}-{subreddit_id}.json"
    new_filepath = os.path.join(f'{FINAL_OUTPUT_DIR}', new_filename)
    print(f"Writing postprocessed json: {new_filename}")
    with open(new_filepath, 'w') as outfile:
        json.dump(new_json, outfile, separators=(',', ':')) # Minify JSON

    # Rename the original file to add the ".finished" suffix to indicate it has been processed
    finished_filepath = filepath + ".finished"
    print(f"Renaming original file to: {finished_filepath}")
    os.rename(filepath, finished_filepath)

def get_all_json_files():
    print("Listing all JSON files in the URS scrapes directory...")
    scrape_dir = f"{URS_ROOT_DIR}/{URS_SCRAPES_RELATIVE_DIR}/**/*.json"
    print(f"Glob: {scrape_dir}")
    globbed_files = set(glob.glob(scrape_dir, recursive=True))
    print(f"Globbed files: {len(globbed_files)}")
    return set(globbed_files)

for i in range(min(num_discussions, len(upcoming_scrapes_json))):
    thread = upcoming_scrapes_json[i]
    print()
    print(f"Now Scraping: date={thread['date']}, comments={thread['comments']}")
    urs_call = f"poetry run python ./Urs.py -c {thread['link']} 0"
    print(f"> {urs_call}")

    # 1. List all json files before scraping
    before_files = get_all_json_files()

    # 2. Run URS
    remaining_requests, used_requests = run_urs_and_get_requests(urs_call, URS_ROOT_DIR + "/urs/")

    # 3. List all json files after scraping
    after_files = get_all_json_files()

    # 4. Find the new file(s)
    new_files = list(after_files - before_files)
    if not new_files:
        print("Warn: No new JSON file found after scraping.")
        continue
    # If multiple, pick the newest
    newest_file = max(new_files, key=os.path.getmtime)
    postprocess_scrape(newest_file)
    print(f"Upcoming scrapes left: {len(upcoming_scrapes_json) - i - 1}")
    print("Continuing...")

print(f"Successfully completed ({num_discussions}) scrapes.")
