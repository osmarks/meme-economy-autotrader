import praw
import time
from datetime import datetime, timedelta
import requests
import json
import logging
import re

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(asctime)s %(message)s", datefmt="%H:%M:%S %d/%m/%Y")

data = {}
data_file = "autotrader-data.json"

def save_data():
    try:
        with open(data_file, "w") as f:
            global data
            json.dump(data, f)
    except Exception as e:
        logging.error(f"Error saving data file: {repr(e)}.")

def load_data():
    try:
        with open(data_file, "r") as f:
            global data
            data = json.load(f)
    except Exception as e:
        logging.warning(f"Error loading data file: {repr(e)}. This is not a critical error.")

load_data()

reddit = praw.Reddit()

meme_economy = reddit.subreddit("MemeEconomy")
mib_name = "MemeInvestor_bot"
bot_name = reddit.user.me().name

logging.info(f"Running as {bot_name}.")

def info(user):
    data = requests.get(f"https://meme.market/api/investor/{user}").json()
    logging.info(f"Balance: {data['balance']}, net worth: {data['networth']}.")
    return data

def find_mib_comment(submission):
    for comment in submission.comments:
        if comment.author.name == mib_name:
            return comment

investment_amount_regex = re.compile(r"\*([0-9,]+) MemeCoins invested") # extracts the investment amount from a MemeInvestor_bot reply to an `!invest` command

# Parses a MemeInvestor_bot reply to an !invest command
def parse_investment_amount(comment_body):
    result = re.search(investment_amount_regex, comment_body)
    if result != None:
        return int(result.group(1).replace(",", ""))

# Guesses if a submission will be a good investment or not, by seeing if many human traders have invested
def good_investment(submission):
    created = datetime.utcfromtimestamp(submission.created_utc)
    age = minutes_ago(created)

    if submission.num_comments - 1 > age and age < 30: # preliminary check to avoid wasting API call budget - if too few investments anyway, we can ignore it
        logging.info(f"{submission} passes fast check, running full check...")

        invested = 0
        investments = 0

        mib_comment = find_mib_comment(submission)

        if mib_comment == None: return False

        mib_comment.replies.replace_more(limit=None) # load all replies to the MemeInvestment_bot comment
        for reply in mib_comment.replies: 
            for subreply in reply.replies:
                if subreply.author.name == mib_name: # response to investment found
                    amount = parse_investment_amount(subreply.body)
                    if amount != None: # increment our totals
                        invested += amount
                        investments += 1

        logging.info(f"MemeCoins invested in submission (by all users): {invested}, number of investments made (by all users): {investments}.")
        if invested > 1000000 and investments - 10 > age:
            return True

    return False

last_investment_time = None

# Calculates how many minutes ago a datetime was
def minutes_ago(ev):
    return (datetime.utcnow() - ev).total_seconds() // 60

# Invest in a submission. Checks if the bot has enough money, and if it has invested too recently
def invest(submission):
    comment = find_mib_comment(submission)

    # Ensure we obey the 1-per-10-minutes comment ratelimit
    global last_investment_time
    if last_investment_time != None and minutes_ago(last_investment_time) <= 10:
        logging.warning(f"Last investment was {minutes_ago(last_investment_time)} minutes ago (too recent). Waiting...")
        return False

    # Check balance and detect total bankruptcy as well as just not having enough balance
    data = info(bot_name)
    balance = data["balance"]

    if balance < 100:
        logging.warning(f"Insufficient funds. Waiting...")
        if data["networth"] < 100:
            raise RuntimeError("The bot is broke (net worth below 100). Please manually run `!broke`.")
        return False

    quantity = balance # If we do not have enough money to make two investments, just spend all of it
    real_quantity = quantity
    if balance >= 200: # If we do, then just invest 50%, as the bot accepts that
        quantity = "50%"
        real_quantity = balance // 2

    last_investment_time = datetime.utcnow()
    comment.reply(f"!invest {quantity}")
    logging.info(f"Invested {quantity} ({real_quantity} MemeCoins) in {submission.id}")

    return True

while True:
    try:
        logging.info("Checking latest submissions.")
        for submission in meme_economy.new(limit=10):
            if not submission.is_self and not submission.over_18:
                if good_investment(submission):
                    # Check that we haven't already invested in this submission
                    previous_investments = data.get("invested", [])
                    if submission.id in previous_investments:
                        logging.info(f"Already invested in {submission.id}.")
                        continue

                    success = invest(submission)
                    # If investment actually goes through, add it to the already invested list
                    if success:
                        previous_investments.append(submission.id)
                        data["invested"] = previous_investments
                        save_data()
    except Exception as e:
        import traceback
        logging.error(f"Error during investment or submission checking: {repr(e)}.\n{''.join(traceback.format_tb(e.__traceback__))}Trying again in 15 seconds.")

    time.sleep(15)