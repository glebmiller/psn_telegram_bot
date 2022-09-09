from aiogram import Bot, Dispatcher, executor, types
from psnawp_api import psnawp
from psnawp_api import user
import pymongo
import re
import aiogram.types
import telebot
import database
import os
import subprocess
import threading
import asyncio
import telegram
import random
import emoji
import datetime
import logging
from subprocess import PIPE, Popen
from telegram import ParseMode


def cmdline(command):
    process = Popen(args=command, stdout=PIPE, shell=True)
    return process.communicate()[0]


# Configure logging
logging.basicConfig(level=logging.INFO)

psnawp = psnawp.PSNAWP(database.getPSNToken())

# подключаемся к БД
client = pymongo.MongoClient("mongodb://localhost:27017")
db = client.PSNTrophies

# общая таблица без названий трофеев
collection = db.games
# таблица пользователей
users_collection = db.users

# таблица игр со списком трофеев с названиями
games_collection = db.games_with_trophies


# смотрим, есть ли игра в БД
def game_in_db(game_id):
    query = {"_id": game_id}
    res = list(collection.find(query))
    if len(res) == 0:
        return False
    else:
        return True


def add_game_to_db(game_id, version, user_account_id):
    result = user_account_id.get_game_trophy_names(game_id, version)
    print(result)
    list_of_trophies = result["trophies"]
    print(list_of_trophies)
    values = {"_id": game_id, "trophies": list_of_trophies}
    games_collection.insert_one(values)


def game_trophies(game_id, version, user_account_id):
    result = user_account_id.get_game_trophies(game_id, version)
    return result


# не используется?
def complete_users_collection(login):
    user_account_id = psnawp.user(online_id=login)
    l = user_account_id.get_all_trophies()
    d = l["trophyTitles"]

    for i in d:
        #     i['npCommunicationId']  i['trophyTitlePlatform']
        res = game_trophies(
            i["npCommunicationId"], i["trophyTitlePlatform"], user_account_id
        )
        users_collection.update_one(
            {"_id": login}, {"$push": {"games": {i["npCommunicationId"]: res}}}
        )

    # sleep(3)


def add_game_to_collection(
    npCommunicationId,
    trophyTitleName,
    login,
    progress,
    trophyTitlePlatform,
    trophyTitleIconUrl,
):
    values = {
        "_id": npCommunicationId,
        "title": trophyTitleName,
        "user complitage": [{login: progress}],
        "title platform": trophyTitlePlatform,
        "image": trophyTitleIconUrl,
    }
    collection.insert_one(values)


# добавляем данные пользователя в collection
def update_collection(login):
    user_account_id = psnawp.user(online_id=login)
    l = user_account_id.get_all_trophies()

    d = l["trophyTitles"]
    values = {}
    for i in d:
        # если игры нет в бд, добавляем запись полностью
        if not game_in_db(i["npCommunicationId"]):
            add_game_to_collection(
                i["npCommunicationId"],
                i["trophyTitleName"],
                login,
                i["progress"],
                i["trophyTitlePlatform"],
                i["trophyTitleIconUrl"],
            )

        else:  # если игра есть, только добавляем пользователя в список
            _id = i["npCommunicationId"]
            progress = i["progress"]
            collection.update_one(
                {"_id": _id}, {"$push": {"user complitage": {login: progress}}}
            )

        # добавляем пользователя в users_collection, а его данные в  collection


def add_user(login):
    # complete_users_collection(login)
    users_collection.insert_one({"_id": login, "games": []})

    update_collection(login)


# поиск игры по ключу
def find_game_by_id(game):
    query = {"_id": re.compile(game, re.IGNORECASE)}
    res = list(collection.find(query))
    return res


# поиск игры в БД по названию
def find_game(game):
    query = {"title": re.compile(game, re.IGNORECASE)}
    result = []
    res = collection.find(query)
    return res


# токен телеграм бота Wisely
TOKEN = database.getBotToken()

telebot = telegram.Bot(token=TOKEN)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)


# извлечь аргумент команды в виде строки
def extract_arg(arg):
    # s=''
    n = arg.split()[1:]
    s = " ".join(n)
    return s


# вовращает id игры по названию и платформе


def game_id_from_name(game_name, platform):
    query = {"title": game_name, "title platform": platform}
    tmp = list(collection.find(query))
    return tmp[0]["_id"]


# составляем ответ для /find game
def compose_answer(found_game):
    game_name = found_game[0]
    platform = found_game[2]

    tmp_list = []
    d = found_game[1]

    result = game_name + " " + platform + "\n"
    for line in d:
        for keys, vals in line.items():
            tmp_list.append((keys, vals))
    tmp_list = sorted(tmp_list, key=lambda x: x[1], reverse=True)
    print("tmp_list = ", tmp_list)
    # check if platinum
    game_id = game_id_from_name(game_name, platform)
    tmp_list = check_if_platinum(tmp_list, game_id, platform)
    # ('gorcheque', 100, True, datetime.timedelta(days=350, seconds=15105))
    for i in tmp_list:
        print(i)
        if i[2]:
            result += "\n" + i[0] + ": " + str(i[1]) + "\U0001F525"
            if i[5]:
                result += i[6]
        else:
            result += "\n" + i[0] + ": " + str(i[1])

    return result


def check_if_platinum(user_list, game_id, platform):
    today = datetime.datetime.today()
    temp_date = datetime.datetime.strptime("2950-03-28T8:13:11", "%Y-%m-%dT%H:%M:%S")
    tmp_list = []
    for i in user_list:
        print(" i for i in user list", i)

        query = {"_id": i[0]}

        searched_game = {}
        all_user_games = list(users_collection.find(query))
        arr = all_user_games[0]["games"]
        # arrr = arr['games']
        for j in arr:
            for keys, vals in j.items():
                if keys == game_id:
                    searched_game = vals
                    break

        if searched_game == {}:
            print(i[0])
            user_account_id = psnawp.user(online_id=i[0])
            online_trophies = game_trophies(game_id, platform, user_account_id)
            searched_game = online_trophies

            users_collection.update_one(
                {"_id": i[0]},
                {"$push": {"games": {game_id: online_trophies}}},
                True,
                True,
            )

        plat = searched_game["trophies"]
        if plat[0]["trophyType"] == "platinum" and plat[0]["earned"]:
            print("platinum")
            earnedDateList = []
            for j in plat:
                # print(i)
                if j["earned"]:
                    earnedDateList.append(j["earnedDateTime"])

            earnedDateList = sorted(earnedDateList)
            firstTrophy = datetime.datetime.strptime(
                earnedDateList[-1], "%Y-%m-%dT%H:%M:%SZ"
            )
            lastTrophy = datetime.datetime.strptime(
                earnedDateList[0], "%Y-%m-%dT%H:%M:%SZ"
            )

            print(firstTrophy - lastTrophy)
            tmp_list.append((True, firstTrophy - lastTrophy, lastTrophy))
        else:
            tmp_list.append((False, temp_date - today, temp_date))
    print(len(user_list), len(tmp_list))
    # new_list = list(zip(user_list, tmp_list))

    #  fast = 0
    #  for i in tmp_list:
    #     if i[0] and i[2]

    for i in range(len(user_list)):
        user_list[i] = user_list[i] + tmp_list[i]
    # print(user_list)
    user_list = sorted(user_list, key=lambda x: x[3])
    print("user list = ", user_list)
    # user_list=list(sorted(user_list, key=lambda x: x[1], reverse=True))
    user_list[0] = user_list[0] + (True, "\U0001F407")

    for i in range(len(user_list) - 1, -1, -1):
        if user_list[i][2]:
            user_list[i] = user_list[i] + (True, "\U0001F422 ")
            break

    for i in range(len(user_list)):
        if len(user_list[i]) == 5:
            user_list[i] = user_list[i] + (False,)

    user_list = sorted(user_list, key=lambda x: x[0])
    user_list = list(sorted(user_list, key=lambda x: (x[1]), reverse=True))
    return user_list


# подготовить список из данных одной игры
def make_single_list(list_of_games):
    found_game = []
    temp_d = dict(list_of_games)
    for keys, vals in temp_d.items():
        if keys in ("image", "title", "user complitage", "title platform"):
            found_game.append(vals)
    return found_game


# ищет заданную игру
@dp.message_handler(commands=["find"])
async def find(message):
    # asyncio.run(send_test())
    game = extract_arg(message.text)
    list_of_games = list(find_game(game))
    print(f"list_of_games {list_of_games}")
    if len(list_of_games) == 1:
        print(f"list_of_games[0] в функции find {list_of_games[0]}")
        found_game = make_single_list(list_of_games[0])
        print(f"found_game в функции find {found_game}")
        result = compose_answer(found_game)
        print(result)

        print(f"found_game = {found_game}")
        print(f"result = {result}")

        await bot.send_photo(message.chat.id, found_game[3], result)
    elif list_of_games == []:
        await bot.send_message(message.chat.id, f"Can not find {game}")
    else:
        if len(game) > 2:
            # print(list_of_games[0])
            games_array = []
            ids_array = []
            for lines in list_of_games:
                s = ""
                for keys, vals in lines.items():
                    if keys == "title" or keys == "title platform":
                        s += vals + " "
                    if keys == "_id":
                        ids_array.append(vals)
                s = s.strip()
                games_array.append(s)

            if len(games_array) == len(set(games_array)):

                buttons_list = dict(zip(games_array, ids_array))
                print(buttons_list)

                markup = types.InlineKeyboardMarkup()

                for key, value in buttons_list.items():
                    markup.add(
                        types.InlineKeyboardButton(text=key, callback_data=value)
                    )

                await message.reply("Выбери игру", reply_markup=markup)

                print(list_of_games[0]["_id"])
            else:
                buttons_list = [(i, j) for i, j in zip(games_array, ids_array)]
                markup = types.InlineKeyboardMarkup()
                for i in buttons_list:
                    markup.add(
                        types.InlineKeyboardButton(text=i[0], callback_data=i[1])
                    )
                await message.reply("Выбери игру", reply_markup=markup)


@dp.callback_query_handler()
async def button_reply(call: types.CallbackQuery):
    f = find_game_by_id(call.data)
    print(f"f = {f}")
    found_game = make_single_list(f[0])
    print(f"found_game = {found_game}")

    result = compose_answer(found_game)
    print(f"resul = {result}")
    await bot.answer_callback_query(call.id)
    await bot.send_photo(call.message.chat.id, found_game[3], result)
    await call.answer()


# проверяет, если ли user в users_collection
def check_if_user_in_db(login):
    query = {"_id": login}
    res = list(users_collection.find(query))
    if len(res) == 0:
        return False
    else:
        return True


# добавляем пользователя если он в друзьях и еще не добавлен
@dp.message_handler(commands=["add"])
async def add(message):
    login = extract_arg(message.text)

    user_account_id = psnawp.user(online_id=login)
    l = user_account_id.friendship()
    if l["friendRelation"] == "friend" and not check_if_user_in_db(login):
        await bot.send_message(message.chat.id, f"adding {login} to DB")
        add_user(login)
    elif l["friendRelation"] == "friend" and check_if_user_in_db(login):
        await bot.send_message(message.chat.id, f"{login} alredy in DB")
    else:
        await bot.send_message(
            message.chat.id, "Become friends with MillerUSACC first!"
        )


# обновляет game complitage в таблице games
def game_complitage_update(login, game_id):
    user_account_id = psnawp.user(online_id=login)
    l = user_account_id.get_all_trophies()

    d = l["trophyTitles"]

    for i in d:
        if i["npCommunicationId"] == game_id:
            # print(i)
            progress = i["progress"]
            print("progress ", progress)

    collection.update_one(
        {"_id": game_id}, {"$pull": {"user complitage": {login: {"$exists": True}}}}
    )  # , True, False)
    collection.update_one(
        {"_id": game_id}, {"$push": {"user complitage": {login: progress}}}
    )  # , True, True)
    # {'$push': {'games': {i['npCommunicationId']: progress}}}


# отбирает трофеи для печати
def print_new_trophies(difference, game_id, rates, trophy_type):
    query = {"_id": game_id}
    res = list(games_collection.find(query))
    # print(difference)
    # print(res[0]['trophies'])
    trophies_to_print = []
    for i in res[0]["trophies"]:
        temp_list = []
        if i["trophyId"] in difference[::-1]:
            st = i["trophyDetail"]
            st = st.replace('"', "'")
            temp_list.append(i["trophyName"])
            temp_list.append(st)
            temp_list.append(i["trophyType"])
            temp_list.append(i["trophyIconUrl"])
            temp_list.append(rates[difference.index(i["trophyId"])])
            temp_list.append(trophy_type[difference.index(i["trophyId"])])

            trophies_to_print.append(temp_list)
    return trophies_to_print


# проверяет, получил ли пользоваель новые трофеи
def check_new_trophies(game_id, user_name, platform):
    print(game_id)
    user_account_id = psnawp.user(online_id=user_name)
    query = {"_id": user_name}
    print("user_name = ", user_name)
    res = list(users_collection.find(query))

    # print(res)
    # тут был index out of range
    if len(res) > 0:
        # l = res[0]["games"]
        # print("res[0]['games']=", l)
        # saved_game =
        for i in res[0]["games"]:

            try:
                saved_game = i[game_id]
                print(saved_game)
                break
            except:
                pass

        online_trophies = game_trophies(game_id, platform, user_account_id)
        # print((saved_game))
        # print((online_trophies))

        if saved_game["lastUpdatedDateTime"] == online_trophies["lastUpdatedDateTime"]:
            print(
                """ saved_game["lastUpdatedDateTime"] == online_trophies["lastUpdatedDateTime"] """
            )
        else:
            # if выпал трофей
            if saved_game["totalItemCount"] == online_trophies["totalItemCount"]:
                print("trophie received")
                old_list = saved_game["trophies"]
                new_list = online_trophies["trophies"]
                # print(old_list)
                # print(new_list)
                difference = []
                rates = []
                trophy_type = []
                today = datetime.date.today()
                for i in range(len(old_list)):

                    if old_list[i]["earned"] != new_list[i]["earned"]:
                        # print(new_list[i])
                        print(new_list[i]["earnedDateTime"][:10])
                        date_earned = new_list[i]["earnedDateTime"][:10]
                        date_earned = datetime.datetime.strptime(
                            date_earned, "%Y-%m-%d"
                        ).date()
                        bb = int(str(today)[-2:])
                        aa = int(str(date_earned)[-2:])
                        if bb - aa <= 2:
                            rate = new_list[i]["trophyEarnedRate"]
                            difference.append(new_list[i]["trophyId"])
                            rates.append(rate)
                            trophy_type.append(new_list[i]["trophyType"])
                            # difference.append(dict({new_list[i]['trophyId']:rate}))
                print(f"difference = {difference}")
                trophies_to_print = print_new_trophies(
                    difference, game_id, rates, trophy_type
                )

                # внести изменения в users_collection
                users_collection.update_one(
                    {"_id": user_name},
                    {"$pull": {"games": {game_id: saved_game}}},
                    True,
                    False,
                )
                users_collection.update_one(
                    {"_id": user_name},
                    {"$push": {"games": {game_id: online_trophies}}},
                    True,
                    True,
                )

                # обновляет game complitage в таблице games
                game_complitage_update(user_name, game_id)
                # print(trophies_to_print)
                f = find_game_by_id(game_id)
                # print(f"f = {f}")
                found_game = make_single_list(f[0])
                send_trophies_to_chat(
                    trophies_to_print, user_name, found_game[0], platform
                )
            else:
                print("вышло DLC")
                # надо обновить таблицу игры с названиями трофеями

                # надо обновить таблицу пользователей с айди трофеями


def make_html(trophies_to_print, user_name, gamename):
    print(trophies_to_print)
    with open("blank_page.html", "r") as file:
        content = file.read()
        # print(type(content))
        content = content.replace("insert_title", trophies_to_print[0])
        content = content.replace(
            "insert_description",
            trophies_to_print[1]
            + "\n"
            + trophies_to_print[-2]
            + " - "
            + trophies_to_print[-1],
        )
        content = content.replace("insert_image", trophies_to_print[3])
        content = content.replace("insert_username", user_name)
        content = content.replace("insert_gamename", gamename)
        # print(content)
    today = str(datetime.datetime.now())
    today = today.replace(" ", "")
    url = today + ".html"
    with open(url, "w") as file:
        file.write(content)
        file.close()
    return url


def send_trophies_to_chat(trophies_to_print, user_name, game_name, platform):
    chatid = -1001105821166
    for i in trophies_to_print:
        # result = user_name + ' ' + game_name + '\n' + \
        #         i[0] + '\n' + i[1] + '\n' + i[-1] + " - " + i[-2]
        # url = i[3]
        print(i)
        print(game_name)
        print(type(game_name))
        # for i in range(len(trophies_to_print))
        url = make_html(i, user_name, game_name)
        os.system(f"sudo cp {url} /var/www/tutorial/{url}")

        # result = user_name + ' ' + game_name + \
        #         '\nhttp://ec2-34-201-58-112.compute-1.amazonaws.com/' + url
        result = f"{user_name} -<a href='http://ec2-34-201-58-112.compute-1.amazonaws.com/{url}'> {game_name}</a> - {platform.upper()}"
        print(result)
        telebot.sendMessage(chatid, result, parse_mode=ParseMode.HTML)
        os.system(f"rm {url}")
        if i[2] == "platinum":
            telebot.send_sticker(
                chatid,
                sticker="CAACAgIAAxkBAAEV9xliz9cW_7inof3UGYHVLF3AbJuy_QACTwsAAkKvaQABE3jwX_D6RZYpBA",
            )


def friends_check():
    bot_friends = psnawp.client.get_friends()
    # print(f"friends {bot_friends}")

    for i in bot_friends:

        user_id = psnawp.user(account_id=i)
        user_name = user_id.profile()["onlineId"]

        all_user_games = user_id.get_all_trophies()
        last_user_games = all_user_games["trophyTitles"][:2]
        # print(last_user_games)
        # break
        # presence = user_id.get_presence()

        # print(presence)
        # primaryPlatformInfo = presence["basicPresence"]["primaryPlatformInfo"]
        # print(primaryPlatformInfo["onlineStatus"], primaryPlatformInfo["platform"])

        # находит game_id по названию и добавляет в collection, если там игры не было

        # game_id = find_game_with_platform(cusa, i, user_id, user_name)
        for game in last_user_games:
            game_id = game["npCommunicationId"]
            platform = game["trophyTitlePlatform"]
            if game_id != "":
                # проверим, есть ли информация о трофеях игры
                check_game_in_games_db(game_id, platform, user_id)

                # проверим, есть ли информация о трофеях игры в таблице пользователи с названиями трофеев
                # при первом запуске игры занесет информацию о ней в таблицу
                check_game_in_users_db(game_id, platform, user_name, user_id)

                # проверяем, появились ли новые трофеи

                check_new_trophies(game_id, user_name, platform)


def check_game_in_users_db(game_id, platform, user_name, user_id):
    result = game_trophies(game_id, platform, user_id)

    tmpstr = "games." + game_id
    query = {
        "$and": [
            {"_id": re.compile(user_name, re.IGNORECASE)},
            {tmpstr: {"$exists": True}},
        ]
    }
    res = list(users_collection.find(query))
    if len(res) == 0:
        users_collection.update_one(
            {"_id": user_name}, {"$push": {"games": {game_id: result}}}
        )


def check_game_in_games_db(game_id, platform, user_id):
    query = {"_id": game_id}
    res = list(games_collection.find(query))
    print(game_id)
    # print(res)
    if len(res) == 0:
        add_game_to_db(game_id, platform, user_id)


def find_game_with_platform(cusa, account_id, user_id, login):
    try:
        game_id = psnawp.client.get_title_id(cusa, account_id)

        query = {"_id": game_id}
        res = list(collection.find(query))
        # print(res)
        if len(res) > 0:
            return res[0]["_id"]
        else:
            # впервые кто то запустил эту игру и ее надо добавить в collection
            print(" впервые кто то запустил эту игру и ее надо добавить в collection")
            print("cusa = ", cusa)
            l = user_id.get_all_trophies()

            d = l["trophyTitles"]
            # print(d)
            for i in d:
                # print(i['trophyTitleName'])
                # re.compile(game, re.IGNORECASE):
                if i["npCommunicationId"] == game_id:
                    print("нашли игру")
                    add_game_to_collection(
                        i["npCommunicationId"],
                        i["trophyTitleName"],
                        login,
                        i["progress"],
                        i["trophyTitlePlatform"],
                        i["trophyTitleIconUrl"],
                    )
                    print(i["npCommunicationId"])
                    return i["npCommunicationId"]
            # else:
            # print('не нашли игру')
    except:
        print("что то пошло не так в cusa -> game_id")
        return ""


async def start_friends_check(interval, periodic_function):
    while True:
        await asyncio.gather(
            asyncio.sleep(interval),
            periodic_function(),
        )


# asyncio.run(start_friends_check(300, friends_check))


def send_test():
    print("inside test send")
    url = "https://psnobj.prod.dl.playstation.net/psnobj/NPWR22008_00/6c1d6ee2-469a-4b97-ad63-98ec651ad4f2.png"

    os.system(f"wget {url}")
    url = url[url.rfind("/") + 1 :]
    os.system(f"convert {url} -resize 200x200 {url}")
    # https: // psnobj.prod.dl.playstation.net / psnobj / NPWR22008_00 / 6c1d6ee2 - 469a - 4b97 - ad63 - 98ec651ad4f2.png

    chatid = -749962132
    telebot.sendMessage(chat_id=chatid, text="platinum sticker")
    # bot.send_message(chatid, f"platinum sticker")
    telebot.send_sticker(
        chatid,
        sticker="CAACAgIAAxkBAAEV9xliz9cW_7inof3UGYHVLF3AbJuy_QACTwsAAkKvaQABE3jwX_D6RZYpBA",
    )

    # text = "Gran Turismo 7\nschnappi_omsk just got a trophy:\nToughening Up\nIncreased a car's body rigidity 10 times.\nbronze - 5.1"

    telebot.send_photo(
        chatid, photo=open(f"/home/ubuntu/Projects/Python/PSNBot/psnapi/{url}", "rb")
    )

    os.system(f"rm {url}")


# send_test()

# asyncio.run(start_friends_check(300, friends_check))


async def background_on_start() -> None:
    """background task which is created when bot starts"""
    while True:
        friends_check()
        await asyncio.sleep(350 + random.randint(1, 10))


async def on_bot_start_up(dispatcher: Dispatcher) -> None:
    """List of actions which should be done before bot start"""
    asyncio.create_task(background_on_start())  # creates background task


"""    
@dp.message_handler()
async def echo(message: types.Message):
    # old style:
    # await bot.send_message(message.chat.id, message.text)
    print(message.text)
    # await message.answer(message.text)
"""

executor.start_polling(dp, on_startup=on_bot_start_up)
