import praw
import time
from datetime import datetime, timedelta
import requests
import shelve

shelf = shelve.open("autotrader")

reddit = praw.Reddit()

def id_from_name(name):
    return reddit.redditor(name).id

meme_economy = reddit.subreddit("MemeEconomy")
mib_name = "MemeInvestor_bot"
bot_name = "AutoMeme5000"

def balance(user):
    bal = requests.get(f"https://meme.market/api/investor/{user}").json()["balance"]
    print("Balance is", bal)
    return bal

def is_good_investment(score, age, num_comments):
    return age < 60 and age > 1 and num_comments > age and score > age

last_investment_time = None

def minutes_ago(ev):
    return (datetime.utcnow() - ev).total_seconds() // 60

def invest(submission):
    if submission.id in shelf["invested"]:
        print("Already invested in", submission.id)
        return

    for comment in submission.comments:
        # found the investmentbot comment - must reply to this
        if comment.author.name == mib_name:
            global last_investment_time
            if last_investment_time != None and minutes_ago(last_investment_time) < 11:
                print("Last investment was", minutes_ago(last_investment_time), "mins ago (too recent). Waiting...")
                return

            bal = balance(bot_name)
            if bal < 100:
                raise RuntimeError("The bot is broke. Please file for bankruptcy.")
            qty = max(bal // 3, 100)
            print("Investing", qty, "in", submission)
            last_investment_time = datetime.utcnow()
            comment.reply(f"!invest {qty}")

            invested_list = shelf["invested"]
            invested_list.add(submission.id)
            shelf["invested"] = invested_list

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