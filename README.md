# Ethereum Daily Archiver

A quick & dirty bot that:

* Runs daily via a scheduled GitHub Action
* Retrieves fresh daily discussion thread metadata from the [dailydoots.com project's](https://github.com/etheralpha/dailydoots-com) `.json` published at [https://dailydoots.com/dailies.json](https://dailydoots.com/dailies.json).
* Archives new Ethereum daily discussion threads to `.json` files, then commits them to the [data repo](https://github.com/sybilwolf/eth-daily-archiver-data). The bot waits until a daily discussion thread is 3 days old before archiving it, to make sure any late comment replies are captured.

In effect, this bot maintains a full canonical archive of all historical ethereum and ethfinance daily threads. To get a copy of the archive, clone or download the [Ethereum Daily Archiver Data Repo](https://github.com/sybilwolf/eth-daily-archiver-data).

# Installation

It's only necessary to install Ethereum Daily Archiver locally if you want to develop/test the script. If you just want the data, visit the [data repo](https://github.com/sybilwolf/eth-daily-archiver-data).

To install and run locally, the workflow in the `.workflows` folder for the necessary steps (you can run the same steps as the runner to install and run on your local machine). Running this script locally will require you to clone three repos side-by-side: this repo, [the data dump repo](https://github.com/sybilwolf/eth-daily-archiver-data), and [my URS fork](https://github.com/sybilwolf/URS).

# Under The Hood

Some info about Ethereum Daily Archiver's code:

* It uses a forked version of [URS](https://github.com/JosephLai241/URS) with updated dependencies, since URS needs [a little help to start cooking.](https://github.com/JosephLai241/URS/issues/73#issuecomment-2535549934)

* Within the URS fork, a commit-hash-pinned version of [PRAW](https://github.com/praw-dev/praw) is used as a dependency (the latest commit to `main` at the time). This is because the latest PRAW release does not currently support [prawcore](https://github.com/praw-dev/prawcore) >3, and this updated prawcore is required to avoid 429 errors in the new forum API versions.
