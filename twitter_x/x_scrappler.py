# import snscrape.modules.twitter as sntwitter

# query = "inteligencia artificial since:2025-01-01 until:2025-03-01"

# tweets = []

# for i, tweet in enumerate(sntwitter.TwitterSearchScraper(query).get_items()):
#     if i > 100:  # limita
#         break
    
#     tweets.append({
#         "usuario": tweet.user.username,
#         "texto": tweet.content,
#         "data": tweet.date,
#         "likes": tweet.likeCount
#     })

# for t in tweets[:5]:
#     print(t)


from selenium import webdriver
from selenium.webdriver.common.by import By
import time

driver = webdriver.Chrome()

driver.get("https://twitter.com/login")

input("Faz login manual e aperta ENTER aqui...")

driver.get("https://twitter.com/search?q=python&src=typed_query")

time.sleep(5)

tweets = driver.find_elements(By.CSS_SELECTOR, "article")

for t in tweets:
    print(t.text)