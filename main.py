#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import time
from time import sleep
import datetime
import vk_api
import requests
from requests.adapters import HTTPAdapter
import psycopg2
from raven.base import Client
from vk_funcs import *

def main():
    client = Client()
    # login = input('login(phone number):')
    # password = getpass.getpass('password:')
    login, password = 'login', 'password'

    id = 000000   # id of person whom likes you add
    app_id = 0000000 # your app id of VK
    secret_key = 'Mfe9YOuRNEZTvY1HQ9o3'
    k = 0

    while True:
        try:
            vk_session = vk_api.VkApi(login, password,captcha_handler=captcha_handler, scope='wall, friends, status, photos, audio, offline, groups')
            #vk_session = vk_api.VkApi(login, password, captcha_handler=captcha_handler)
            try:
                t1=datetime.datetime.now()
                vk_session.http.mount('https://', HTTPAdapter(max_retries=10))
                vk_session.auth()
                t2=datetime.datetime.now()-t1
                print('connected in',t2,'sec\n')
            except vk_api.AuthError as error_msg:
                print(error_msg)

            vk = vk_session.get_api()
            vk.account.setOnline(voip = 0)
            t1=datetime.datetime.now()
            DATABASE_URL = os.environ['DATABASE_URL']
            conn = psycopg2.connect(DATABASE_URL, sslmode='require')
            db = conn.cursor()
            print('processing...\n')
            #
            # if k > 149:
            #     k = 0
            collect_liked(vk, id, db)
            # if k % 6 == 0:
            #     collect_friends(vk, id, db)
            # get_audio_status(vk, id, db)

            conn.commit()
            db.close()
            conn.close()
            t2=datetime.datetime.now()-t1
            print('executed in '+str(t2)+' sec\nterminating\n')

        except  vk_api.exceptions.ApiError as error_msg:
            print('Error', error_msg)
            pass

        k += 1
        sleep(14000)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('ancelled')
