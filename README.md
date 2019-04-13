# MemeEconomy Autotrader

This is a simple bot which attempts to make MemeCoins on the [MemeEconomy subreddit](https://www.reddit.com/r/MemeEconomy/) by investing in posts which are considered likely to be popular.

You can run your own instance of it - just replace the `this_name` constant in `main.py`, create your own [praw.ini](https://praw.readthedocs.io/en/latest/getting_started/configuration/prawini.html), and run `main.py`. Please note that, due to its *very* simple method for determining whether to invest or not, some failure modes will become much more common given a large population of Autotraders.

Look at it in action [here](https://www.reddit.com/user/AutoMeme5000/).