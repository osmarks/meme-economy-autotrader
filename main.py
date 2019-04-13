import praw
import time
from datetime import datetime, timedelta
import requests

reddit = praw.Reddit()

def id_from_name(name):
    return reddit.redditor(name).id

meme_economy = reddit.subreddit("MemeEconomy")
mib_name = "MemeInvestor_bot"
mib_id = id_from_name(mib_name)
bot_name = "AutoMeme5000"
bot_id = id_from_name(bot_name)

def balance(user):
    bal = requests.get(f"https://meme.market/api/investor/{user}").json()["balance"]
    print("Balance is", bal)
    return bal

def is_good_investment(score, age, num_comments):
    return age < 60 and age > 1 and num_comments > age and score > age

last_investment = None

def minutes_ago(ev):
    return (datetime.utcnow() - ev).total_seconds() // 60

def invest(submission):
    for comment in submission.comments:
        # found the investmentbot comment - must reply to this
        if comment.author.id == mib_id:
            comment.replies.replace_more(limit=None)
            # check for previous investment by us
            for subcomment in comment.replies:
                if subcomment.author != None and subcomment.author.id == bot_id:
                    print("Already invested in", submission)
                    return

            global last_investment
            if last_investment != None and minutes_ago(last_investment) < 11:
                print("Last investment was", minutes_ago(last_investment), "mins ago (too recent). Waiting...")
                return

            bal = balance(bot_name)
            if bal < 100:
                raise RuntimeError("The bot is broke. Please file for bankruptcy.")
            qty = max(bal // 3, 100)
            print("Investing", qty, "in", submission)
            last_investment = datetime.utcnow()
            comment.reply(f"!invest {qty}")
            return

while True:
    print("Running meme check cycle")
    for submission in meme_economy.new():
        if not submission.is_self and not submission.over_18:
            created = datetime.utcfromtimestamp(submission.created)
            age = minutes_ago(created)
            if is_good_investment(submission.score, age, submission.num_comments or 0):
                invest(submission)

    time.sleep(15)