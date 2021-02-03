from .models import Tag, Search
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from . import serializers

import pandas as pd
import requests
import json
import itertools
import re


def get_credentials():
    credentials = {}
    credentials['graph_domain'] = 'https://graph.facebook.com/'
    credentials['graph_version'] = 'v9.0'
    credentials['endpoint_base'] = credentials['graph_domain'] + credentials['graph_version'] + '/'
    return credentials


# Instagram Graph APIコール
def call_api(url, endpoint_params):
    data = requests.get(url, endpoint_params)
    response = {}
    response['json_data'] = json.loads(data.content)
    return response


# ハッシュタグID取得
def get_hashtag_id(params):
    endpoint_params = {}
    endpoint_params['user_id'] = params['instagram_account_id']
    endpoint_params['q'] = params['tagname']
    endpoint_params['access_token'] = params['access_token']
    url = params['endpoint_base'] + 'ig_hashtag_search'
    return call_api(url, endpoint_params)


# トップメディア取得
def get_hashtag_media(params):
    endpoint_params = {}
    endpoint_params['user_id'] = params['instagram_account_id']
    endpoint_params['fields'] = 'caption'
    # endpoint_params['limit'] = 50
    endpoint_params['access_token'] = params['access_token']
    url = params['endpoint_base'] + params['hashtag_id'] + '/top_media'
    return call_api(url, endpoint_params)


# ユーザーアカウント情報取得
def get_account_info(params):
    endpoint_params = {}
    # ユーザ名、プロフィール画像、フォロワー数、フォロー数、投稿数、メディア情報取得
    endpoint_params['fields'] = 'business_discovery.username(' + params['ig_username'] + '){\
        username,biography,profile_picture_url,follows_count,followers_count,media_count,\
        media.limit(100){comments_count,like_count,caption,media_url,permalink,timestamp,media_type}}'
    endpoint_params['access_token'] = params['access_token']
    url = params['endpoint_base'] + params['instagram_account_id']
    return call_api(url, endpoint_params)


class SearchView(APIView):
    def get_hashtag(self, tagname, access_token, instagram_account_id):
        # Instagram Graph API認証情報取得
        params = get_credentials()
        params['access_token'] = access_token
        params['instagram_account_id'] = instagram_account_id

        # ハッシュタグ設定
        params['tagname'] = tagname
        # ハッシュタグID取得
        hashtag_id_response = get_hashtag_id(params)
        # ハッシュタグID設定
        params['hashtag_id'] = hashtag_id_response['json_data']['data'][0]["id"]
        # ハッシュタグ検索
        hashtag_media_response = get_hashtag_media(params)
        hashag_data = hashtag_media_response['json_data']["data"]

        hashtag_group = []
        for i in range(len(hashag_data)):
            if hashag_data[i].get('caption'):
                caption = hashag_data[i]["caption"]
                hash_tag_list = re.findall('#([^\s→#\ufeff]*)', caption)
                if hash_tag_list:
                    hashtag_group.append(hash_tag_list)

        tag_list = list(itertools.chain.from_iterable(hashtag_group))
        hashtag_list = [a for a in tag_list if a != '']
        data = pd.Series(hashtag_list).value_counts()

        search_data = Search.objects.create(tagname=tagname)

        for i, (hashtag, hashtag_count) in enumerate(zip(data.index, data.values)):
            # TOP30取得
            if i >= 30:
                break
            else:
                tag_data = Tag.objects.create(tagname=tagname, hashtag=hashtag, hashtag_count=hashtag_count)
                search_data.ranking.add(tag_data)
                search_data.save()
        return search_data

    def get(self, request):
        results = []
        tagname = request.GET.get(key="tagname")

        # 本番用
        access_token = request.GET.get(key="access_token")
        instagram_account_id = request.GET.get(key="instagram_account_id")

        # ローカルで確認する場合は下記のコメントアウトを外す(.envが必要)
        # access_token = settings.ACCESS_TOKEN
        # instagram_account_id = settings.USER_ID

        if tagname and access_token and instagram_account_id:
            search_data = Search.objects.filter(tagname=tagname)

            if search_data:
                search_data = search_data[0]

                # 一週間以上経過しているのでハッシュタグの再取得
                if search_data.created_at < (timezone.now() - timedelta(weeks=1)):
                    search_data.delete()
                    tag_data = Tag.objects.filter(tagname=tagname)
                    tag_data.delete()
                    search_data = self.get_hashtag(tagname, access_token, instagram_account_id)
            else:
                search_data = self.get_hashtag(tagname, access_token, instagram_account_id)

            search_serializer = serializers.SearchSerializer(search_data)
            return Response(search_serializer.data)
        return Response(status=status.HTTP_400_BAD_REQUEST)


class AccountView(APIView):
    def get(self, request):
        params = get_credentials()
        ig_username = request.GET.get(key="ig_username")

        # 本番用
        access_token = request.GET.get(key="access_token")
        instagram_account_id = request.GET.get(key="instagram_account_id")

        # ローカルで確認する場合は下記のコメントアウトを外す(.envが必要)
        access_token = settings.ACCESS_TOKEN
        instagram_account_id = settings.USER_ID

        params['access_token'] = access_token
        params['instagram_account_id'] = instagram_account_id
        params['ig_username'] = ig_username

        account_response = get_account_info(params)
        business_discovery = account_response['json_data']['business_discovery']
        username = business_discovery['username']
        biography = business_discovery['biography']
        profile_picture_url = business_discovery['profile_picture_url']
        follows_count = business_discovery['follows_count']
        followers_count = business_discovery['followers_count']
        media_count = business_discovery['media_count']
        media_data = business_discovery['media']['data']

        # 最近の投稿を取得
        recently_data = []
        for i in range(6):
            if media_data[i].get('media_url'):
                tags = re.findall('#([^\s→#\ufeff]*)', media_data[i]['caption'])
                tags = [a for a in tags if a != '']
                tags = map(lambda x: '#' + x, tags)
                tags = ' '.join(tags)

                timestamp = (datetime.strptime(media_data[i]['timestamp'], '%Y-%m-%dT%H:%M:%S%z')).strftime("%Y-%m-%d %H:%M")

                recently_data.append({
                    'media_url': media_data[i]['media_url'],
                    'permalink': media_data[i]['permalink'],
                    'timestamp': timestamp,
                    'like_count': media_data[i]['like_count'],
                    'comments_count': media_data[i]['comments_count'],
                    'permalink': media_data[i]['permalink'],
                    'tags': tags
                })

        # データフレームの作成
        media_data_frame = pd.DataFrame(media_data, columns=[
            'comments_count',
            'like_count',
            'caption',
            'media_url',
            'permalink',
            'timestamp',
            'media_type',
            'id',
        ])

        # VIDEOはmedia_urlが取得できないため削除
        media_data_frame = media_data_frame[media_data_frame['media_type'] != 'VIDEO']

        # ハッシュタグを合わせる
        row_count = media_data_frame['caption'].str.extractall('#([^\s→#\ufeff]*)').reset_index(level=0).drop_duplicates()[0]
        # ハッシュタグが含まれている投稿件数
        hashtag_count = row_count.value_counts().to_dict()

        # ハッシュタグ毎にデータを作成
        hashtag_data = []
        for key, val in hashtag_count.items():
            post_data = media_data_frame[media_data_frame['caption'].str.contains(key, na=False)]
            hashag_post_data = []
            average_eng = 0
            average_eng_percent = 0
            for index, row in post_data.iterrows():
                timestamp = (datetime.strptime(row['timestamp'], '%Y-%m-%dT%H:%M:%S%z')).strftime("%Y-%m-%d %H:%M")

                hashag_post_data.append({
                    'media_url': row['media_url'],
                    'permalink': row['permalink'],
                    'timestamp': timestamp,
                    'like_count': row['like_count'],
                    'comments_count': row['comments_count'],
                })
                average_eng += row['like_count'] + row['comments_count']

            if average_eng:
                average_eng = int(average_eng / val)
                average_eng_percent = round(average_eng / follows_count, 1)

            hashtag_data.append({
                'hashtag': key,
                'post_num': val,
                'average_eng': average_eng,
                'average_eng_percent': average_eng_percent,
                'media': hashag_post_data
            })

        account_data = {
            'username': username,
            'biography': biography,
            'profile_picture_url': profile_picture_url,
            'follows_count': follows_count,
            'followers_count': followers_count,
            'media_count': media_count,
            'recently_data': recently_data,
            'hashtag_data': hashtag_data,
        }

        return Response(account_data)
