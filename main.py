import praw
import time
from datetime import datetime, timedelta
import requests
import shelve
import logging

shelf = shelve.open("autotrader")

reddit = praw.Reddit()

def id_from_name(name):
    return reddit.redditor(name).id

meme_economy = reddit.subreddit("MemeEconomy")
mib_name = "MemeInvestor_bot"
bot_name = "AutoMeme5000"

def info(user):
    data = requests.get(f"https://meme.market/api/investor/{user}").json()
    logging.info(f"Balance: {data['balance']}.")
    logging.info(f"Net worth: {data['networth']}.")
    return data

def is_good_investment(score, age, num_comments):
    return age < 60 and age > 1 and num_comments > age and score > age

last_investment_time = None

def minutes_ago(ev):
    return (datetime.utcnow() - ev).total_seconds() // 60

def invest(submission):
    if submission.id in shelf["invested"]:
        logging.info(f"Already invested in {submission.id}.")
        return

    for comment in submission.comments:
        # found the investmentbot comment - must reply to this
        if comment.author.name == mib_name:
            global last_investment_time
            if last_investment_time != None and minutes_ago(last_investment_time) < 11:
                logging.info(f"Last investment was {minutes_ago(last_investment_time)} minutes ago (too recent). Waiting...")
                return

            data = info(bot_name)
            if data["balance"] < 100:
                logging.warning(f"Not enough money to invest. Waiting...")
                if data["networth"] < 100:
                    raise RuntimeError("The bot is broke (balance and possible value of investments below 100). Please file for bankruptcy.")
                return

            qty = max(data["balance"] // 3, 100)
            last_investment_time = datetime.utcnow()
            comment.reply(f"!invest {qty}")
            logging.info(f"Invested {qty} in {submission.id}")

            invested_list = shelf["invested"]
            invested_list.add(submission.id)
            shelf["invested"] = invested_list

            return

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(asctime)s %(message)s", datefmt="%H:%M:%S %d/%m/%Y")

while True:
    logging.info("Running meme check cycle.")
    for submission in meme_economy.new():
        if not submission.is_self and not submission.over_18:
            created = datetime.utcfromtimestamp(submission.created)
            age = minutes_ago(created)
            if is_good_investment(submission.score, age, submission.num_comments or 0):
                invest(submission)

    time.sleep(15)