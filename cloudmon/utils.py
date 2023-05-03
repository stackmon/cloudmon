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

import importlib
import logging
from pathlib import Path
import shutil
import subprocess
import yaml

from git import exc
from git import Repo

from cloudmon.types import GitRepoModel


def checkout_git_repository(repo_dir, repo: GitRepoModel):
    logging.info(f"Checkout repo {repo.repo_url} to {repo_dir}")
    checkout_exists = repo_dir.exists()
    repo_dir.mkdir(parents=True, exist_ok=True)
    branch = repo.repo_ref
    if not checkout_exists:
        git_repo = Repo.clone_from(repo.repo_url, repo_dir, branch=branch)
    else:
        logging.debug("Checkout already exists")
        try:
            git_repo = Repo(repo_dir)
        except exc.NoSuchPathError:
            # folder is not a git repo?
            git_repo = Repo.clone_from(repo.repo_url, repo_dir, branch=branch)

        git_repo.remotes.origin.fetch()
        git_repo.git.checkout(branch)
        git_repo.remotes.origin.pull()


def copy_kustomize_app_base(kustomize_base_dir: Path, kustomize_app_name: str):
    """Copy Kustomize app base to the destination directory"""
    kust_base_src = Path(
        importlib.resources.files("cloudmon"), "kustomize", kustomize_app_name
    )
    shutil.copytree(kust_base_src, kustomize_base_dir)


def prepare_kustomize_overlay(
    overlays_dir: Path,
    base: str,
    name: str,
    kustomization: dict,
    config_dir: Path = None,
) -> Path:
    """Prepare Kustomize overlay"""
    new_kustomization = dict(
        apiVersion="kustomize.config.k8s.io/v1beta1",
        kind="Kustomization",
    )
    kustomize_overlay_extra_files = []
    for k, v in kustomization.items():
        if k == "extra_files":
            kustomize_overlay_extra_files = v
        else:
            new_kustomization[k] = v
    resources = new_kustomization.setdefault("resources", [])
    if base not in resources:
        resources.append(base)

    overlay_dir = Path(overlays_dir, name)
    overlay_dir.mkdir(parents=True, exist_ok=True)
    with open(Path(overlay_dir, "kustomization.yaml"), "w") as f:
        logging.debug("Dumping overlay kustomization file")
        yaml.dump(new_kustomization, f)

    if kustomize_overlay_extra_files:
        if not config_dir:
            logging.warn(
                "Not processing extra kustomize files since config_dir "
                "is not set"
            )
        for extra_file in kustomize_overlay_extra_files:
            src = Path(config_dir, extra_file)
            dest = Path(overlay_dir, extra_file)
            if src.exists():
                logging.debug("Preparing %s for kustomize deploy" % src)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dest)

    return overlay_dir


def apply_kustomize(overlay_dir: Path, kube_context: str, kube_namespace: str):
    res = subprocess.run(
        args=[
            "kubectl",
            "--context",
            kube_context,
            "--namespace",
            kube_namespace,
            "apply",
            "-k",
            ".",
        ],
        cwd=overlay_dir,
        check=True,
    )
    return res
