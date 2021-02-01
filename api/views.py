from .models import Tag, Search
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

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
