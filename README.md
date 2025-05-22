# Ethereum Daily Archiver

A quick & dirty GitHub Actions bot that archives Ethereum daily discussion threads to .json files to create a big canonical archive. See `.workflows` for installation steps (you can run the same steps as the runner on your local machine).

* Uses a forked version of [URS](https://github.com/JosephLai241/URS) with updated dependencies, since URS needs [a little help to start cooking.](https://github.com/JosephLai241/URS/issues/73#issuecomment-2535549934)

* Within the URS fork, this uses a commit-hash-pinned version of [PRAW](https://github.com/praw-dev/praw). This is because the latest PRAW release does not currently support [prawcore](https://github.com/praw-dev/prawcore) >3, and this updated prawcore is required to avoid 429 errors in the new API versions.

* For the latest dump of the archive, see the artifacts from the latest workflow run in the Actions tab.
