import pymongo
import datetime
import emoji
from psnawp_api import psnawp
from psnawp_api import user
import database
import re

psnawp = psnawp.PSNAWP(database.getPSNToken())

client = pymongo.MongoClient("mongodb://localhost:27017")

database = client.TestMongo
collection = database.test2

#client = pymongo.MongoClient("mongodb://localhost:27017")
db = client.PSNTrophies

# общая таблица без названий трофеев
collection_scores = db.games
# таблица пользователей
users_collection = db.users

# таблица игр со списком трофеев с названиями
games_collection = db.games_with_trophies


login = 'DanilaRU'
query = {"_id": login}
users_collection.delete_one(query)



ids = []
for x in collection_scores.find():
    ids.append(x['_id'])
   # print(x)


for i in ids:

    collection_scores.update_one({'_id': i}, {
        "$pull": {"user complitage": {login: {"$exists": True}}}})  # , True, False)