import praw
import time
from datetime import datetime, timedelta
import requests

reddit = praw.Reddit()
meme_economy = reddit.subreddit("MemeEconomy")
mib_name = "MemeInvestor_bot"
this_name = "AutoMeme5000"

def balance(user):
    bal = requests.get(f"https://meme.market/api/investor/{user}").json()["balance"]
    print("Balance is", bal)
    return bal

def is_good_investment(score, age, num_comments):
    return age < 60 and age > 1 and num_comments > age and score > age

def invest(submission):
    for comment in submission.comments:
        # found the investmentbot comment - must reply to this
        if comment.author.name == mib_name:
            comment.replies.replace_more(limit=None)
            # check for previous investment by us
            for subcomment in comment.replies:
                if subcomment.author.name == this_name:
                    print("Already invested in", submission)
                    return

            bal = balance(this_name)
            if bal < 100:
                raise RuntimeError("The bot is broke. Please file for bankruptcy.")
            qty = max(bal // 3, 100)
            print("Investing", qty, "in", submission)
            comment.reply(f"!invest {qty}")
            return

while True:
    print("Running meme check cycle")
    for submission in meme_economy.new():
        if not submission.is_self and not submission.over_18:
            created = datetime.utcfromtimestamp(submission.created)
            age = (datetime.utcnow() - created).total_seconds() // 60 # age in minutes
            if is_good_investment(submission.score, age, submission.num_comments or 0):
                invest(submission)

    time.sleep(15)