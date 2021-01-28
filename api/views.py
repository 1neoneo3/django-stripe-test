from .models import Tag, Search
from django.conf import settings
import pandas as pd
import requests
import json
import itertools
import re
from rest_framework.views import APIView
from rest_framework.response import Response


def get_credentials():
    credentials = {}
    credentials['access_token'] = settings.ACCESS_TOKEN
    credentials['instagram_account_id'] = settings.USER_ID
    credentials['graph_domain'] = 'https://graph.facebook.com/'
    credentials['graph_version'] = 'v9.0'
    credentials['endpoint_base'] = credentials['graph_domain'] + \
        credentials['graph_version'] + '/'
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
    endpoint_params['fields'] = 'id,media_type,caption,comments_count,like_count'
    endpoint_params['limit'] = 50
    endpoint_params['access_token'] = params['access_token']
    url = params['endpoint_base'] + params['hashtag_id'] + '/top_media'
    return call_api(url, endpoint_params)


class ApiResponse(Response):
    def __init__(self, results=None, status=200, message='成功', message_disp='', **kwargs):
        data = dict(status=status, message=message, message_disp=message_disp)
        if results is not None:
            data['results'] = results
        super().__init__(data, status=status, **kwargs)


class SearchView(APIView):
    def get(self, request):
        results = []
        tagname = request.GET.get(key="tagname")
        if tagname:
            search_data = Search.objects.filter(tagname=tagname)
            if search_data:
                search_data = search_data[0]
            else:
                # Instagram Graph API認証情報取得
                params = get_credentials()
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
                        hash_tag_list = re.findall(
                            '#([^\s→#\ufeff]*)', caption)
                        if hash_tag_list:
                            hashtag_group.append(hash_tag_list)

                tag_list = list(itertools.chain.from_iterable(hashtag_group))
                hashtag_list = [a for a in tag_list if a != '']
                data = pd.Series(hashtag_list).value_counts()

                search_data = Search.objects.create(tagname=tagname)

                for i, (hashtag, hashtag_count) in enumerate(zip(data.index, data.values)):
                    # TOP30取得
                    if i > 29:
                        break
                    else:
                        tag_data = Tag.objects.create(
                            hashtag=hashtag, hashtag_count=hashtag_count)
                        search_data.ranking.add(tag_data)
                        search_data.save()

            results.append({
                'tagname': search_data.tagname,
                'ranking': list(search_data.ranking.all().values('hashtag', 'hashtag_count')),
                'created_on': search_data.created_on,
            })

        return ApiResponse(
            results=results,
        )
