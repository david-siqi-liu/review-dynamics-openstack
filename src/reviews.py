import json
import re
from collections import Counter, defaultdict
BOT_NAMES = ['Zuul', 'Jenkins', 'VMware NSX CI', 'Glance Bot']

# https://github.com/SAILResearch/replication_review-dynamics/blob/master/ClassifyHistory.sql
VOTES_REGEX_PATTERNS = {
    1: [
        'Patch Set [0-9]+: Code-Review[+]1',
        'Patch Set [0-9]+: [^;]*[; ]*Looks good to me, but someone else must approve',
        'Patch Set [0-9]+: Might be fine, but I am too lame to make sure'
    ],
    2: [
        'Patch Set [0-9]+: Code-Review[+]2',
        '^Patch Set [0-9]+:[^\n]*Code-Review[ ]*[+]2',
        'Patch Set [0-9]+: Looks good to me',
        'Patch Set [0-9]+: Approved',
        'Patch Set [0-9]+: Looks good to me, approved',
        'Patch Set [0-9]+: Woah! Awesome!! You rule!!!'
    ],
    -1: [
        'Patch Set [0-9]+: Code-Review[-]1',
        "Patch Set [0-9]+: [^;]*[; ]*I would prefer that you didn't merge this",
        "Patch Set [0-9]+: [^;]*[; ]*I would prefer that you didn't submit this",
        'Patch Set [0-9]+: [^;]*[; ]*This need some tweaks before it is merged',
        'Patch Set [0-9]+: [^;]*[; ]*I would prefer this is not merged as is',
        'Patch Set [0-9]+: [^;]*[; ]*I would prefer that you didnt submit this'
    ],
    -2: [
        'Patch Set [0-9]+: Code-Review[-]2',
        'Patch Set [0-9]+: [^;]*[; ]*Do not merge',
        'Patch Set [0-9]+: [^;]*[; ]*Abandoned',
        'Patch Set [0-9]+: Abandoned\n\n',
        'Patch Set [0-9]+: [^;]*[; ]*Do not submit',
        'Patch Set [0-9]+: [^;]*[; ]*This shall not be merged',
        '^Abandoned\n\n',
        '^Abandoned$'
    ]
}

with open('../data/core_devs.json', 'r') as j:
    CORE_DEVS = json.loads(j.read())


def get_change_id(msg):
    pos = re.search('change-id:', msg, re.IGNORECASE)
    if pos == None:
        return ''
    after = msg[pos.end():]
    after = re.sub('[^a-zA-Z0-9]', '', after)
    change_id = after[:41]
    return change_id


# patches_written[i] = number of patches i wrote in total
patches_written = Counter()
# review_interactions[i][j] = number of patches i wrote and j reviewed
review_interactions = defaultdict(Counter)


def get_review_info(project, response, author_name):
    reviews = defaultdict(lambda x: {})
    votes = defaultdict(lambda x: 0)
    comments_count = Counter()
    for res in response:
        try:
            reviewer_id = res['author']['_account_id']
            reviewer_name = res['author']['name']
            msg = res['message']
        except KeyError:
            continue
        # If bot, continue
        if reviewer_name in BOT_NAMES:
            continue
        # Check if we need remove prior review
        remove_prior_review = is_code_review_removal_message(msg)
        if remove_prior_review:
            if reviewer_name in reviews:
                reviews.pop(reviewer_name)
            if reviewer_name in votes:
                votes.pop(reviewer_name)
            continue
        # Get current vote from message
        # If vote is 0, then it is not a vote, skip current comment
        vote = get_vote_from_message(msg)
        if vote == 0:
            comments_count[reviewer_name] += 1
            continue
        # Get prior vote info
        num_prior_votes, \
            num_prior_pos_votes, num_prior_pos_votes_core, \
            num_prior_neg_votes, num_prior_neg_votes_core = get_prior_votes(
                project, reviewer_name, votes)
        # Check if core developer member
        is_core = reviewer_name in CORE_DEVS[project]
        # Other comments
        num_prior_comments = sum(comments_count.values())
        pct_prior_comments_by_reviewer = comments_count[reviewer_name] / \
            num_prior_comments if num_prior_comments > 0 else 0
        # Update review info
        review = {
            'reviewer_id': reviewer_id,
            'reviewer_name': reviewer_name,
            'reviewer_vote': vote,
            'reviewer_is_core': is_core,
            'num_prior_comments': num_prior_comments,
            'pct_prior_comments_by_reviewer': pct_prior_comments_by_reviewer,
            'num_prior_votes': num_prior_votes,
            'pct_prior_pos_votes':  num_prior_pos_votes / num_prior_votes if num_prior_votes > 0 else 0,
            'pct_prior_neg_votes':  num_prior_neg_votes / num_prior_votes if num_prior_votes > 0 else 0,
            'pct_prior_pos_votes_core': num_prior_pos_votes_core / num_prior_pos_votes if num_prior_pos_votes > 0 else 0,
            'pct_prior_neg_votes_core': num_prior_neg_votes_core / num_prior_neg_votes if num_prior_neg_votes > 0 else 0
        }
        # Replace review if reviewer has already posted one
        reviews[reviewer_name] = review
        # Update vote info
        votes[reviewer_name] = vote
    # Get interaction frequency between each reviewer and the author
    for reviewer_name, review in reviews.items():
        review['reviewer_freq'] = get_reviewer_freq(reviewer_name, author_name)
    # Increment number of patches the author had written
    patches_written[author_name] += 1
    # Return only the values (i.e., reviews) in a list
    return reviews.values()


def get_reviewer_freq(reviewer_name, author_name):
    # Author hasn't written any patch before, or
    # Reviewer hasn't reviewed for the author before
    if (author_name not in patches_written) or \
            (reviewer_name not in review_interactions[author_name]):
        review_interactions[author_name][reviewer_name] = 1
        return 0
    num_patches_written = patches_written[author_name]
    assert num_patches_written > 0
    num_interactions = review_interactions[author_name][reviewer_name]
    assert num_interactions > 0
    assert num_interactions <= num_patches_written
    # Increment counter
    review_interactions[author_name][reviewer_name] += 1
    return num_interactions / num_patches_written


def is_code_review_removal_message(msg):
    return re.search('-Code-Review', msg)


def get_vote_from_message(msg):
    for vote, patterns in VOTES_REGEX_PATTERNS.items():
        for p in patterns:
            if re.search(p, msg):
                return vote
    return 0


def get_prior_votes(project, reviewer, votes):
    num_prior_pos_votes, num_prior_neg_votes = 0, 0
    num_prior_pos_votes_core, num_prior_neg_votes_core = 0, 0
    for prior_reviewer, prior_vote in votes.items():
        # Do not count prior votes by the current reviewer
        if (reviewer == prior_reviewer):
            continue
        if prior_vote > 0:
            num_prior_pos_votes += 1
            if prior_reviewer in CORE_DEVS[project]:
                num_prior_pos_votes_core += 1
        elif prior_vote < 0:
            num_prior_neg_votes += 1
            if prior_reviewer in CORE_DEVS[project]:
                num_prior_neg_votes_core += 1
    return num_prior_pos_votes + num_prior_neg_votes, \
        num_prior_pos_votes, num_prior_pos_votes_core, \
        num_prior_neg_votes, num_prior_neg_votes_core
