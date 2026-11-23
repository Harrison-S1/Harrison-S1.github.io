"""Fixed non-secret identity contract from verified setup, not caller allowlists.

Scope readback proves the bounded token only, not full installation inventory.
"""
import content_policy as policy

APP_ID = 5645498
APP_SLUG = 'harrison-s1-blog-reviewer'
INSTALLATION_ID = 179326232
BOT_ID = 353438493
BOT_LOGIN = 'harrison-s1-blog-reviewer[bot]'
REPOSITORY_ID = 504555593
OWNER_ID = 54186142


def verify_repository(repository):
    owner = repository.get('owner') or {}
    policy.require(type(repository.get('id')) is int and repository['id'] == REPOSITORY_ID and
                   repository.get('full_name') == policy.REPO and
                   type(owner.get('id')) is int and owner['id'] == OWNER_ID and
                   owner.get('login') == 'Harrison-S1', 'review repository identity mismatch')


def verify_review(review, head):
    user = review.get('user') or {}
    policy.require(policy.SHA.fullmatch(head) and review.get('state') == 'APPROVED' and
                   review.get('commit_id') == head and
                   type(review.get('id')) is int and review['id'] > 0 and
                   type(user.get('id')) is int and user['id'] == BOT_ID and
                   user.get('login') == BOT_LOGIN and user.get('type') == 'Bot',
                   'exact-head numeric App-bot review not confirmed')
