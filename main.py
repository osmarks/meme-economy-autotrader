import praw
import time
from datetime import datetime, timedelta
import requests
import shelve
import logging
import re

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(asctime)s %(message)s", datefmt="%H:%M:%S %d/%m/%Y")

shelf = shelve.open("autotrader")

reddit = praw.Reddit()

meme_economy = reddit.subreddit("MemeEconomy")
mib_name = "MemeInvestor_bot"
bot_name = reddit.user.me().name

logging.info(f"Running as {bot_name}.")

def info(user):
    data = requests.get(f"https://meme.market/api/investor/{user}").json()
    logging.info(f"Balance: {data['balance']}.")
    logging.info(f"Net worth: {data['networth']}.")
    return data

def find_mib_comment(submission):
    for comment in submission.comments:
        if comment.author.name == mib_name:
            return comment

investment_amount_regex = re.compile(r"\*([0-9,]+) MemeCoins invested")

# Parses a MemeInvestor_bot reply to an !invest command
def parse_investment_amount(comment_body):
    result = re.search(investment_amount_regex, comment_body)
    if result != None:
        return int(result.group(1).replace(",", ""))

# Guesses if a submission will be a good investment or not, primarily by piggybacking off human traders' guesses
def good_investment(submission):
    created = datetime.utcfromtimestamp(submission.created)
    age = minutes_ago(created)

    if submission.num_comments - 1 > age and age < 120: # preliminary check to avoid wasting API call budget - if too few investments anyway, we can ignore it
        logging.info(f"{submission} passes basic check, summing investment amounts...")

        invested = 0
        investments = 0

        mib_comment = find_mib_comment(submission)
        mib_comment.replies.replace_more(limit=None) # load all replies to the MemeInvestment_bot comment
        for reply in mib_comment.replies: 
            for subreply in reply.replies:
                if subreply.author.name == mib_name: # response to investment found
                    amount = parse_investment_amount(subreply.body)
                    if amount != None: # increment our totals
                        invested += amount
                        investments += 1

        logging.info(f"Total invested: {invested}, investment count: {investments}.")
        if invested > 1000000 and investments > (age + 5):
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
    if data["balance"] < 100:
        logging.warning(f"Not enough money to invest. Waiting...")
        if data["networth"] < 100:
            raise RuntimeError("The bot is broke (balance and possible value of investments below 100). Please file for bankruptcy.")
        return False

    qty = max(data["balance"] // 2, 100)
    last_investment_time = datetime.utcnow()
    comment.reply(f"!invest {qty}")
    logging.info(f"Invested {qty} in {submission.id}")

    return True

while True:
    try:
        logging.info("Running meme check cycle.")
        for submission in meme_economy.new():
            if not submission.is_self and not submission.over_18:
                if good_investment(submission):
                    # Check that we haven't already invested
                    previous_investments = shelf.get("invested")
                    if previous_investments != None and submission.id in previous_investments:
                        logging.info(f"Already invested in {submission.id}.")
                        continue

                    success = invest(submission)
                    # If investment actually goes through, add it to the already invested list
                    if success:
                        invested_list = shelf.get("invested", default=set())
                        invested_list.add(submission.id)
                        shelf["invested"] = invested_list
    except Exception as e:
        import traceback
        logging.error(f"Failed to load or invest in memes: {repr(e)}.\n{''.join(traceback.format_tb(e.__traceback__))}Trying again in 15 seconds.")

    time.sleep(15)