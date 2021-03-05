from datetime import datetime
from pydriller import RepositoryMining, GitRepository
from collections import Counter
import numpy as np
import pandas as pd
import pathlib
import math
import re

bug_fixing_keywords = ['fix', 'bug', 'defect']


class CommitInfo:
    def __init__(self, commit):
        # Current info
        self.hash = commit.hash
        self.msg = commit.msg
        self.author = commit.author.name
        self.committer = commit.committer.name
        self.author_date = commit.author_date
        self.commit_date = commit.committer_date
        self.modifications = commit.modifications
        self.num_lines_added = commit.insertions
        self.num_lines_deleted = commit.deletions
        self.num_lines_of_code = self.get_lines_of_code()
        self.num_files_impacted = commit.files
        self.num_dirs_impacted = self.get_dirs_impacted()
        self.min_complexity, self.mean_complexity, self.max_complexity = self.get_complexities()
        self.entropy = self.get_entropy()
        self.bug_fixing = self.is_bug_fixing()
        self.description_length = self.get_description_length()
        # Prior and future commit info
        self.prior_commits = []
        self.num_prior_commits = 0
        self.avg_prior_age = 0
        self.num_prior_commits_bug_fixing = 0
        self.num_future_commits_bug_fixing = 0
        self.fix_inducing = False

    def get_lines_of_code(self):
        if len(self.modifications) == 0:
            return 0

        sum_nloc = 0
        for file in self.modifications:
            nloc = file.nloc if file.nloc else 0
            sum_nloc += nloc
        return sum_nloc

    def get_dirs_impacted(self):
        if len(self.modifications) == 0:
            return 0

        dirs_impacted = set()
        for file in self.modifications:
            for path in [file.old_path, file.new_path]:
                if path:
                    dir = str(pathlib.Path(path).parent)
                    dirs_impacted.add(dir)
        return len(dirs_impacted)

    def get_complexities(self):
        if len(self.modifications) == 0:
            return 0, 0, 0

        complexities = []
        for file in self.modifications:
            if file.complexity:
                complexities.append(file.complexity)

        if len(complexities) == 0:
            return 0, 0, 0

        return min(complexities), sum(complexities) / len(complexities), max(complexities)

    def get_entropy(self):
        if len(self.modifications) == 0:
            return 0

        lines_changed = []
        for file in self.modifications:
            added = file.added if file.added else 0
            removed = file.removed if file.removed else 0
            lines_changed.append(added + removed)
        entropy = 0
        if sum(lines_changed) == 0:
            return 0
        for lc in lines_changed:
            if lc == 0:
                continue
            p = lc / sum(lines_changed)
            entropy += -1 * (p) * math.log(p, 2)
        if len(self.modifications) > 1:
            entropy /= math.log(len(self.modifications), 2)
        return entropy

    def is_bug_fixing(self):
        for kw in bug_fixing_keywords:
            if re.search(kw, self.msg, re.IGNORECASE):
                return True
        return False

    def get_description_length(self):
        words = re.findall('\w+', self.msg)
        return len(words)

    def toDict(self):
        d = {}
        d['hash'] = self.hash
        d['author_name'] = self.author
        d['committer_name'] = self.committer
        d['author_date'] = self.author_date
        d['commit_date'] = self.commit_date
        d['num_lines_added'] = self.num_lines_added
        d['num_lines_deleted'] = self.num_lines_deleted
        d['num_lines_of_code'] = self.num_lines_of_code
        d['num_file_impacted'] = self.num_files_impacted
        d['num_dirs_impacted'] = self.num_dirs_impacted
        d['min_complexity'] = self.min_complexity
        d['mean_complexity'] = self.mean_complexity
        d['max_complexity'] = self.max_complexity
        d['entropy'] = self.entropy
        d['bug_fixing'] = self.bug_fixing
        d['description_length'] = self.description_length
        d['prior_commits'] = self.prior_commits
        d['num_prior_commits'] = self.num_prior_commits
        d['avg_prior_age'] = self.avg_prior_age
        d['num_prior_commits_bug_fixing'] = self.num_prior_commits_bug_fixing
        d['num_future_commits_bug_fixing'] = self.num_future_commits_bug_fixing
        d['fix_inducing'] = self.fix_inducing
        return d


def update_prior_and_future_info(commit_hash, gr, all_commit_info):
    # Current commit
    curr_commit = gr.get_commit(commit_hash)
    # Current commit info
    curr_commit_info = all_commit_info[commit_hash]
    # Prior commits
    prior_commits = set()
    for file in curr_commit.modifications:
        # Prior commits that last modified the same lines
        bug_inducing_commits = gr.get_commits_last_modified_lines(
            curr_commit, file)
        for prior_commit_hashes in bug_inducing_commits.values():
            for prior_commit_hash in prior_commit_hashes:
                # Prior commit is in scope
                if prior_commit_hash in all_commit_info:
                    prior_commits.add(prior_commit_hash)
    # No prior commits
    if len(prior_commits) == 0:
        return
    # Initialize attribtues
    prior_ages = []
    num_prior_commits_bug_fixing = 0
    for prior_commit_hash in prior_commits:
        # Get prior commit info
        prior_commit_info = all_commit_info[prior_commit_hash]
        # Add to prior ages (in days elapsed)
        prior_ages.append((curr_commit_info.commit_date -
                           prior_commit_info.commit_date).days)
        # If prior commit is bug fixing, increment counter
        if prior_commit_info.bug_fixing:
            num_prior_commits_bug_fixing += 1
        # If current commit is bug fixing, make prior commit bug inducing
        if curr_commit_info.bug_fixing:
            prior_commit_info.num_future_commits_bug_fixing += 1
            prior_commit_info.fix_inducing = True
    # Update attributes
    curr_commit_info.prior_commits = list(prior_commits)
    curr_commit_info.num_prior_commits = len(prior_commits)
    curr_commit_info.avg_prior_age = sum(prior_ages) / len(prior_ages) \
        if len(prior_ages) > 0 else 0
    curr_commit_info.num_prior_commits_bug_fixing = num_prior_commits_bug_fixing


def is_valid_commit(commit):
    # Remove commits made by systems
    if (commit.committer.name == 'Gerrit Code Review') and \
            (commit.author.name == 'Jenkins'):
        return False
    elif (commit.author.name in ['OpenDev Sysadmins', 'OpenStack Jenkins',
                                 'OpenStack Proposal Bot', 'OpenStack Release Bot']):
        return False
    elif (commit.author.name == 'Zuul'):
        return False

    return True
