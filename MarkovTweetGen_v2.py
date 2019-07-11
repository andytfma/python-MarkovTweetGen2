### SCRAPER

# The following code is modified from source https://mdl.library.utoronto.ca/technology/tutorials/scraping-tweets-using-python.

import tweepy
import csv
import json
import pandas as pd
import codecs

# load Twitter API credentials
with open('twitter_credentials.json') as cred_data:
    info = json.load(cred_data)
consumer_key = info['CONSUMER_KEY']
consumer_secret = info['CONSUMER_SECRET']
access_key = info['ACCESS_KEY']
access_secret = info['ACCESS_SECRET']

# Twitter allows access to only 3240 tweets via this method
def get_all_tweets(screen_name):

    # Authorization and initialization
    print('Downloading tweets...')
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_key, access_secret)
    api = tweepy.API(auth)

    all_the_tweets = []                                                     # initialization of a list to hold all Tweets

    new_tweets = api.user_timeline(screen_name=screen_name, count=200, tweet_mode = 'extended')      # We will get the tweets with multiple requests of 200 tweets each

    all_the_tweets.extend(new_tweets)                                       # saving the most recent tweets

    oldest_tweet = all_the_tweets[-1].id - 1                                # save id of 1 less than the oldest tweet

    # Grabbing tweets till none are left
    while len(new_tweets) > 0:                           
        new_tweets = api.user_timeline(screen_name=screen_name, count=200, max_id=oldest_tweet, tweet_mode='extended')  # The max_id param will be used subsequently to prevent duplicates

        all_the_tweets.extend(new_tweets)                                       # save most recent tweets

        oldest_tweet = all_the_tweets[-1].id - 1                                # id is updated to oldest tweet - 1 to keep track

        print ('...%s tweets have been downloaded so far' % len(all_the_tweets))

    # transforming the tweets into a 2D array that will be used to populate the csv
    print('All tweets (or API max of 3240) have been downloaded, saving tweets to file.')
    outtweets = [[tweet.id_str, tweet.full_text.encode("utf-8")] for tweet in all_the_tweets]       #UTF-8 coding too hard for me
    df = pd.DataFrame(outtweets, columns = ['id', 'text'])
    return df

if __name__ == '__main__':
    screen_name = (input("Enter the twitter handle of the person whose tweets you want to simulate:- "))
    df = get_all_tweets(screen_name)

##### PROGRAM TWO TBH
### CLEANING

from numpy.random import choice
import ast

df1 = df.drop(["id"], axis = 1)
df1.text = df1.text.str.decode("utf-8")

    # Manual string cleaning.

# Dropping retweets: https://stackoverflow.com/questions/28679930/how-to-drop-rows-from-pandas-data-frame-that-contains-a-particular-string-in-a-p.

print("Removing RTs")
df1 = df1[~df1.text.str.contains('RT')]
print("Tweets used: "+ str(df1.shape[0]))

# Removing URLs (s/o Jerry Wang for his personal masterclass on regex).

df1.text = df1.text.replace('https?\:\/\/t\.co\/.{10}', r'', regex = True) 

# Separate sentences into tokens by column.
  # Markov model, based on https://towardsdatascience.com/using-a-markov-chain-sentence-generator-in-python-to-generate-real-fake-news-e9c904e967e.


print("Tokenizing tweets")
df1.text = df1.text.astype(str) + " STOPHERE"

df1.text.replace('\s{2,}', ' ', regex = True, inplace = True)
df2 = df1.text.str.split(" ", expand = True)
df2.replace(to_replace = ['“', '”', '\"'], value = '', regex = True, inplace = True)

print("Collecting start words")
start_word = df2.iloc[:,0].sort_values(ascending = True)
start_word = pd.DataFrame(start_word.value_counts().reset_index(drop = False))
start_word.columns = ['word', 'n']
start_word = start_word[start_word.n > 1]

df2 = df2.stack()

print("Creating Markov probability matrix")
markov_df = pd.DataFrame(columns = ['word', 'nextword'])
markov_df.word = df2.reset_index(drop = True)
nextword = df2[1:].reset_index(drop = True)
markov_df.nextword = nextword
count = markov_df.groupby(by = ['word', 'nextword']).size().\
  sort_values(ascending = False).reset_index(name = 'n').drop_duplicates(subset = ['word', 'nextword'])
count = count[count.word != 'STOPHERE']

print("Collecting end words")
end_words = count[count.nextword == 'STOPHERE']
markov_df2 = count.pivot(index = 'word', columns = 'nextword', values = 'n')
totalct_word = markov_df2.sum(axis = 1)

print("Populating probabilities")
markov_df2 = markov_df2.apply(lambda x: x / totalct_word)

### GENERATING FUNCTION

def make_a_sentence():
    trials = 1  #Log trials
    word = choice(start_word.word.tolist()) #Pick a word from startwords
    satisfaction = False
    while satisfaction == False:
      sentence = [word]

      while len(sentence) < 30:
        child_prob = ((markov_df2.iloc[markov_df2.index == word].fillna(0).values)[0]).tolist()
        deadendcheck = len([x for x in child_prob if x])
        #print(word, '=>[', deadendcheck, '] ', end = '')
        if deadendcheck == 1 and len(sentence) == 1:
          word = choice(start_word.word.tolist())
          trials += 1
          break
        elif deadendcheck == 1:
          #print('END')
          break
        else:
          next_word = choice(a = list(markov_df2.columns), p = child_prob)
          if next_word == 'STOPHERE':
            break
          elif next_word in end_words:
            if len(sentence) > 2:    
              sentence.append(next_word)
              break
            else:
              continue
          else:
            sentence.append(next_word)
        word = next_word
      if len(sentence) > 12:
        sentence = ' '.join(sentence)
        return sentence, trials
      else:
        trials += 1
        continue

print("Generating sentences")

tweets_df = pd.DataFrame(columns = ['id', 'trial #', 'tweet'])
for x in range(30):
  tweet, trials = make_a_sentence()
  tweets_df.at[x,'id'] = str(x+1)
  tweets_df.at[x, 'trial #'] = str(trials)
  tweets_df.at[x,'tweet'] = tweet

print("Generating COMPLETE, writing to file")

print(tweets_df)
tweets_df.to_csv(screen_name + '_generatedtweets.csv', header = True, index = False, encoding = 'UTF-8')
