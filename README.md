# Ethereum Daily Archiver

A quick & dirty GitHub Actions bot that archives Ethereum daily discussion threads to .json files to create a big canonical archive. See `.workflows` for installation steps (you can run the same steps as the runner on your local machine).

* Uses a forked version of [URS](https://github.com/JosephLai241/URS) with updated dependencies, since URS needs [a little help to start cooking.](https://github.com/JosephLai241/URS/issues/73#issuecomment-2535549934)

* Within the URS fork, this uses a commit-hash-pinned version of [PRAW](https://github.com/praw-dev/praw). This is because the latest PRAW release does not currently support [prawcore](https://github.com/praw-dev/prawcore) >3, and this updated prawcore is required to avoid 429 errors in the new API versions.

* Currently the json archive is stored in a private repository. Contact me if you want a dump of it. I may update the action to automatically post the data somewhere like Arweave.
