# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

from git import exc
from git import Repo


def checkout_git_repository(repo_dir, repo):
    logging.info(f"Checkout repo {repo['repo_url']} to {repo_dir}")
    checkout_exists = repo_dir.exists()
    repo_dir.mkdir(parents=True, exist_ok=True)
    branch = repo.get("repo_ref", "main")
    if not checkout_exists:
        git_repo = Repo.clone_from(repo["repo_url"], repo_dir, branch=branch)
    else:
        logging.debug(f"Checkout already exists")
        try:
            git_repo = Repo(repo_dir)
        except exc.NoSuchPathError:
            # folder is not a git repo?
            git_repo = Repo.clone_from(
                repo["repo_url"], repo_dir, branch=branch
            )

        git_repo.remotes.origin.fetch()
        git_repo.git.checkout(branch)
        git_repo.remotes.origin.pull()
