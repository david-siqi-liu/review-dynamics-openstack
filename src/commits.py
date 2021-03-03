from datetime import datetime
from pydriller import RepositoryMining, GitRepository
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
        self.merged = commit.merge
        self.lines_added = commit.insertions
        self.lines_deleted = self.getLOC()
        self.files_impacted = commit.files
        self.dirs_impacted = self.getDirsImpacted()
        self.min_complexity, self.mean_complexity, self.max_complexity = self.getComplexities()
        self.entropy = self.getEntropy()
        self.bug_fixing = self.isBugFixing()
        self.description_length = self.getDescriptionLength()
        # Prior and future commit info
        self.num_prior_commits = 0
        self.num_prior_authors = 0
        self.num_prior_commits_bug_fixing = 0
        self.num_future_commits_bug_fixing = 0
        self.fix_inducing = False

    def getLOC(self):
        if len(self.modifications) == 0:
            return 0

        sum_nloc = 0
        for file in self.modifications:
            nloc = file.nloc if file.nloc else 0
            sum_nloc += nloc
        return sum_nloc

    def getDirsImpacted(self):
        if len(self.modifications) == 0:
            return 0

        dirs_impacted = set()
        for file in self.modifications:
            for path in [file.old_path, file.new_path]:
                if path:
                    dir = str(pathlib.Path(path).parent)
                    dirs_impacted.add(dir)
        return len(dirs_impacted)

    def getComplexities(self):
        if len(self.modifications) == 0:
            return 0, 0, 0

        complexities = []
        for file in self.modifications:
            if file.complexity:
                complexities.append(file.complexity)

        if len(complexities) == 0:
            return 0, 0, 0

        return min(complexities), sum(complexities) / len(complexities), max(complexities)

    def getEntropy(self):
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

    def isBugFixing(self):
        for kw in bug_fixing_keywords:
            if re.search(kw, self.msg, re.IGNORECASE):
                return True
        return False

    def getDescriptionLength(self):
        words = re.findall('\w+', self.msg)
        return len(words)
