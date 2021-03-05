import numpy as np
import pandas as pd
import re
from collections import Counter


def split_prior_commits(prior_commits):
    prior_commits = re.sub('[^a-zA-Z0-9\,]', '', prior_commits)
    if not prior_commits:
        return []
    return prior_commits.split(',')
