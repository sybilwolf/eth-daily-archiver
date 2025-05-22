#!/usr/bin/env python3

# This script should not need to be run. It's just for renaming
# final scrapes produced before I decided on a new naming convention.

import re
import json
import subprocess

FINAL_SCRAPES_DIR = "../eth-daily-archiver-data"
THREAD_ID_REGEX = re.compile('/comments/(.+?)/')
SUBREDDIT_ID_REGEX = re.compile('r/(.+?)/comments/')

finished_scrape_filename_list = subprocess.check_output(f"find {FINAL_SCRAPES_DIR}/ -type f -name '*.json'", shell=True, universal_newlines=True).splitlines()

for filepath in finished_scrape_filename_list:
    # Open the JSON file and extract the thread ID and subreddit ID
    with open(filepath) as json_data:
        json_obj = json.load(json_data)
        thread_link = json_obj['urs_data']['scrape_settings']['url']
        date_of_thread = json_obj['date_of_thread']
        subreddit_id = SUBREDDIT_ID_REGEX.search(thread_link)[1]
        thread_id = THREAD_ID_REGEX.search(thread_link)[1]
    # Rename the file
    new_filename = f"{FINAL_SCRAPES_DIR}/{date_of_thread}-{subreddit_id}-{thread_id}.json"
    subprocess.run(['mv', filepath, new_filename])
