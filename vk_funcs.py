# -*- coding: utf-8 -*-
import os
import time
from time import sleep
import datetime
import vk_api
import requests
import psycopg2

first = True


def captcha_handler(captcha):
    key = input("Enter captcha code {0}: ".format(captcha.get_url())).strip()
    return captcha.try_again(key)


def secure_access(app_id, key):
    secure_token = requests.get('https://oauth.vk.com/access_token?client_id='
                                + str(app_id) + '&client_secret=' + key
                                + '&v=5.80&grant_type=client_credentials').json()
    return secure_token['access_token']


def get_ifonline(vk, id):
    status = vk.users.get(user_id = id, fields = 'online')
    if status[0]['online']:
        return True
    else:
        return False


def get_status(current_status, vk, id):
    global first
    profiles = vk.users.get(user_id = id, fields = 'online, last_seen')
    if profiles[0]['online']:
        if not current_status:  # если появился в сети, то выводим время
            now = datetime.datetime.now()
            print('online: ' + str(now.strftime("%d-%m-%Y %H:%M") + '\n'))
            current_status = True
            return True
    if not profiles[0][
        'online']:  # если был онлайн, но уже вышел, то выводим время выхода
        if first:
            current_status = True
            first = False
        if current_status:
            print('last_seen: ' + str(datetime.datetime.fromtimestamp(
                profiles[0]['last_seen']['time']).strftime('%d-%m-%Y %H:%M') + '\n'))
            current_status = False
            return False
    return current_status


def get_groups(vk, id):
    try:
        group_list = vk.groups.get(user_id = id)
        return group_list['items']
    except  vk_api.exceptions.ApiError as error_msg:
        error_list = [error_msg]
        return error_list


def get_groupname(vk, gid):
    group = vk.groups.getById(group_ids = gid, fields = 'name')
    return group[0]['name']


def get_friends(vk, id):
    try:
        friend_list = vk.friends.get(user_id = id)
        return friend_list['items']
    except  vk_api.exceptions.ApiError as error_msg:
        return error_msg


def get_fullname(vk, id):
    fullname = vk.users.get(user_id = id, fields = 'first_name,last_name')
    url = '( https://vk.com/id' + str(id) + ' )'
    fullname = fullname[0]['first_name'] + ' ' + fullname[0]['last_name'] + url
    return fullname

def get_online_friends(vk, id):
    try:
        friends_list = get_friends(vk, id)
        online_friends = []
        for friend in friends_list:
            status = vk.users.get(user_id = friend, fields = 'online')
            if status[0]['online']:
                online_friends.append(friend)
        return online_friends
    except  vk_api.exceptions.ApiError as error_msg:
        return error_msg


def get_mutual_friends(vk, id1, id2):
    try:
        mutual_friends = vk.friends.getMutual(source_uid = id1, target_uid = id2)
        return mutual_friends
    except  vk_api.exceptions.ApiError as error_msg:
        return error_msg


def collect_friends_data(vk, id, db):
    pass



def collect_friend_connections(vk, id, db):
    try:
        friends = get_online_friends(vk, id)
        if get_ifonline(vk, id):
            my_id = 160947474  # me
            # vk.messages.send(user_id = my_id, message = "True")
            for friend in friends:
                db.execute(
                    "UPDATE friends SET is_online = is_online + 1 WHERE vk_id = %s;",
                    [friend])
                db.execute(
                    "UPDATE friends SET total_online = total_online + 1 WHERE vk_id = %s;",
                    [friend])
        else:
            for friend in friends:
                db.execute(
                    "UPDATE friends SET total_online = total_online + 1 WHERE vk_id = %s;",
                    [friend])
    except  vk_api.exceptions.ApiError as error_msg:
        pass




def get_likes(vk, id, cnt):
    # подписки пользователя
    subscriptions_list = vk.users.get_subscriptions(user_id = id, extended = 0)['groups']['items']
    # формируем список id, который нужно передать в следующий метод
    groups_list = ['-' + str(x) for x in subscriptions_list]
    posts = {}
    # формируем ленту новостей
    newsfeed = vk.newsfeed.get(
        filters = 'post',
        source_ids = ', '.join(groups_list),
        count = 100, timeout = 10)
    # добавляем посты в словарь в формате id_поста: id_группы
    posts.update({x['post_id']: x['source_id'] for x in newsfeed['items']})
    # нужно для получения следующей партии
    # если требуется более одного запроса — делаем остаток в цикле
    if cnt != 1:
        for c in range(cnt - 1):
            next_from = newsfeed['next_from']
            kwargs = {
                'start_from': next_from,
                'filters':    'post',
                'source_ids': ', '.join(groups_list),
                'count':      100,
                'timeout':    10
            }
            newsfeed = vk.newsfeed.get(**kwargs)

            posts.update({x['post_id']: x['source_id'] for x in newsfeed['items']})
            time.sleep(.5)
    liked_posts = []
    liked_post = []
    groupnames = []

    for post in posts.items():
        try:
            itemID = post[0]
            ownerID = post[1]
            timeOut = 5
            isLiked = vk.likes.isLiked(
                user_id = id,
                item_id = itemID,
                type = 'post',
                owner_id = ownerID,
                timeout = timeOut)
        except Exception:
            # print('ERROR! ' + 'vk.com/wall{0}_{1}'.format(post[1], post[0]))
            # isLiked = 0
            pass

        if isLiked['liked'] == 1:
            liked_post.append('https://vk.com/wall{0}_{1}'.format(post[1], post[0]))
            groupnames.append(get_groupname(vk, str(abs(post[1]))))
            time.sleep(.5)
    liked_posts.append(liked_post)
    liked_posts.append(groupnames)
    return liked_posts

#ссылка на группу https://vk.com/public174895433

def collect_liked(vk, id, db):
    q = 1
    gr_id = -174532295
    likes = get_likes(vk, id, 20)
    print("likes successfully collected.\n")
    list = likes[0]
    names = likes[1]
    db.execute("SELECT url FROM liked_posts;")
    old_tuple = db.fetchall()
    old_list = []
    for x in old_tuple:
        old_list.append(x[0])
    print("startin to compare with db.\n")
    for post in list:
        name = names[list.index(post)]
        if not post in old_list:
            q += 1
            attach = post.replace("https://vk.com/", "")
            # vk.messages.send(user_id = 160947474, message = 'from her', attachment = attach)
            if q == 10:
                q = 0
                sleep(60)
            elif q == 50:
                conn.commit()
                db.close()
                conn.close()
                q = 0
                sleep(43200)
                DATABASE_URL = os.environ['DATABASE_URL']
                conn = psycopg2.connect(DATABASE_URL, sslmode = 'require')
                db = conn.cursor()
            else:
                sleep(.5)
            db.execute(
                "INSERT INTO liked_posts (url, source, owner) VALUES (%s, %s, %s);",
                (post, name, id))
            vk.wall.repost(object = attach, group_id = abs(gr_id))

def collect_friends(vk, id, db):
    # try:
    db.execute("SELECT vk_id FROM friends WHERE owner_id = %s;", [id])
    old_tuple = db.fetchall()
    old_list = []
    for x in old_tuple:
        old_list.append(x[0])
    list = get_friends(vk, id)
    for friend in list:
        gr_list1 = get_groups(vk, id)
        gr_list2 = get_groups(vk, friend)
        common_groups = []
        for group in gr_list2:
            if group in gr_list1:
                common_groups.append(group)
        if not friend in old_list:
            mutual_friends = get_mutual_friends(vk, id, friend)
            now = datetime.datetime.now()
            fname = get_fullname(vk, friend)
            change = 'added:' + str(now.strftime("%d-%m-%Y %H:%M")) + ', '
            db.execute(
                "INSERT INTO friends (vk_id, full_name, mutual_friends, groups_incommon, owner_id) VALUES (%s, %s, %s, %s, %s);",
                (friend, str(fname), str(mutual_friends), str(common_groups), id))
            db.execute("UPDATE friends SET status = status || %s WHERE vk_id = %s;",
                       (change, friend))

    for friend in old_list:
        if not friend in list:
            now = datetime.datetime.now()
            change = 'deleted/hidden:' + str(now.strftime("%d-%m-%Y %H:%M")) + ', '
            db.execute("UPDATE friends SET status += %s WHERE vk_id = %s;",
                       (change, friend))
    collect_friend_connections(vk, id, db)
    # except Exception as error_msg:
    # print(error_msg)


def get_audio_status(vk, id, db):
    db.execute("SELECT audio_id FROM music_scrobbler;")
    old_audios = db.fetchall()
    audios = []
    for item in old_audios:
        audios.append(item[0])
    audio_sts = vk.users.get(user_id = id, fields = 'status')[0]
    # if audio_sts['status_audio'] is not None:
    # if audio_sts['status_audio']:
    try:
        audio_id = audio_sts['status_audio']['id']
        artist = audio_sts['status_audio']['artist']
        title = audio_sts['status_audio']['title']
        if not audio_id in audios:
            db.execute(
                "INSERT INTO music_scrobbler (audio_id, artist, title, owner_id) VALUES (%s, %s, %s, %s);",
                (audio_id, str(artist), str(title), id))
        else:
            db.execute(
                "UPDATE music_scrobbler SET times_scrobbled = times_scrobbled + 1 WHERE audio_id = %s;",
                [audio_id])
    except KeyError:
        pass

def make_cleanup():
    for arg in kwargs:
        del arg[:]
