from django.conf import settings
from django.utils import timezone
from django.shortcuts import render
from django.contrib.auth.models import User
from django.views import generic
from django.shortcuts import render

import stripe
from django.http.response import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import Tag, Search, Profile, Benchmark, Pricing, Hashtag
from datetime import datetime, timedelta

from rest_framework.views import APIView
from rest_framework import status, permissions, generics, viewsets
from rest_framework.response import Response
from . import serializers

import pandas as pd
import requests
import json
import numpy as np
import itertools
import re
import math

# ユーザー作成
class CreateUserView(generics.CreateAPIView):
    serializer_class = serializers.UserSerializer
    permission_classes = (permissions.AllowAny,)


# プロフィール関連
class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = serializers.ProfileSerializer

    def perform_create(self, serializer):
        serializer.save(userProfile=self.request.user)


# 全プロフィールリスト取得
class MyProfileListView(generics.ListAPIView):
    queryset = Profile.objects.all()
    serializer_class = serializers.ProfileSerializer

    def get_queryset(self):
        return self.queryset.filter(userProfile=self.request.user)


# 認証
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
    if data.status_code == requests.codes.ok:
        response['json_data'] = json.loads(data.content)
    return response


# 長期アクセストークン取得
def get_long_access_token(params):
    endpoint_params = {}
    endpoint_params['fb_exchange_token'] = params['access_token']
    endpoint_params['grant_type'] = 'fb_exchange_token'
    endpoint_params['client_id'] = '1712895282220029'
    endpoint_params['client_secret'] = '183befdc6dac90ca608d1b0ee5027010' # 環境変数にする
    url = params['endpoint_base'] + 'oauth/access_token'
    return call_api(url, endpoint_params)


# FacebookPageID取得
def get_facebook_page_id(params):
    endpoint_params = {}
    endpoint_params['access_token'] = params['access_token']
    url = params['endpoint_base'] + 'me/accounts'
    return call_api(url, endpoint_params)


# Instagram Business ID取得
def get_instagram_business_id(params):
    endpoint_params = {}
    endpoint_params['fields'] = 'instagram_business_account'
    endpoint_params['access_token'] = params['access_token']
    url = params['endpoint_base'] + params['facebook_page_id']
    return call_api(url, endpoint_params)


# Instagram ユーザー名取得
def get_username(params):
    endpoint_params = {}
    endpoint_params['fields'] = 'username'
    endpoint_params['access_token'] = params['access_token']
    url = params['endpoint_base'] + params['instagram_business_id']
    return call_api(url, endpoint_params)


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
    endpoint_params['fields'] = 'caption,comments_count,like_count,media_url,permalink,media_type,children{media_url}'
    endpoint_params['access_token'] = params['access_token']
    url = params['endpoint_base'] + params['hashtag_id'] + '/top_media'
    return call_api(url, endpoint_params)


# ユーザーアカウント情報取得
def get_account_info(params):
    endpoint_params = {}
    # ユーザ名、プロフィール画像、フォロワー数、フォロー数、投稿数、メディア情報取得
    endpoint_params['fields'] = 'business_discovery.username(' + params['ig_username'] + '){\
        username,biography,profile_picture_url,follows_count,followers_count,media_count,\
        media.limit(' + params['limit'] + '){comments_count,like_count,caption,media_url,permalink,timestamp,media_type}}'
    endpoint_params['access_token'] = params['access_token']
    url = params['endpoint_base'] + params['instagram_account_id']
    return call_api(url, endpoint_params)


# メディアインサイト情報取得
def get_media_insights(params):
    endpoint_params = {}
    endpoint_params['metric'] = 'engagement,impressions,reach,saved'
    endpoint_params['access_token'] = params['access_token']
    url = params['endpoint_base'] + params['media_id'] + '/insights'
    return call_api(url, endpoint_params)


# ユーザーインサイト情報取得
def get_user_insights(params):
    endpoint_params = {}
    endpoint_params['metric'] = 'impressions,reach,follower_count,profile_views,website_clicks'
    endpoint_params['period'] = 'day'
    endpoint_params['since'] = params['since']
    endpoint_params['until'] = params['until']
    endpoint_params['access_token'] = params['access_token']
    url = params['endpoint_base'] + params['instagram_account_id'] + '/insights'
    return call_api(url, endpoint_params)


# オンラインフォロワーインサイト情報取得
def get_online_followers_insights(params):
    endpoint_params = {}
    endpoint_params['metric'] = 'online_followers'
    endpoint_params['period'] = 'lifetime'
    endpoint_params['since'] = params['since']
    endpoint_params['until'] = params['until']
    endpoint_params['access_token'] = params['access_token']
    url = params['endpoint_base'] + params['instagram_account_id'] + '/insights'
    return call_api(url, endpoint_params)


# オーディエンスインサイト情報取得
def get_audience_insights(params):
    endpoint_params = {}
    endpoint_params['metric'] = 'audience_city,audience_country,audience_gender_age'
    endpoint_params['period'] = 'lifetime'
    endpoint_params['access_token'] = params['access_token']
    url = params['endpoint_base'] + params['instagram_account_id'] + '/insights'
    return call_api(url, endpoint_params)


# ストーリー情報取得
def get_stories(params):
    endpoint_params = {}
    endpoint_params['access_token'] = params['access_token']
    url = params['endpoint_base'] + params['instagram_account_id'] + '/stories'
    return call_api(url, endpoint_params)


# メディア情報取得
def get_media_info(params):
    endpoint_params = {}
    endpoint_params['fields'] = 'media_type,media_url,timestamp,caption'
    endpoint_params['access_token'] = params['access_token']
    url = params['endpoint_base'] + params['media_id']
    return call_api(url, endpoint_params)


# ストーリーメディアインサイト情報取得
def get_story_media_insights(params):
    endpoint_params = {}
    endpoint_params['metric'] = 'impressions,reach,replies,taps_forward,taps_back,exits'
    endpoint_params['access_token'] = params['access_token']
    url = params['endpoint_base'] + params['media_id'] + '/insights'
    return call_api(url, endpoint_params)


# ユーザー情報取得
def get_profile_data(userProfile):
    params = get_credentials()
    profile_data = Profile.objects.get(userProfile=userProfile)
    params['access_token'] = profile_data.accessToken
    params['instagram_account_id'] = profile_data.instagramBusinessID
    params['ig_username'] = profile_data.nickName

    return params


# プロフィール作成
class TokenView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        params = get_credentials()
        access_token = request.GET.get(key="access_token")
        user_id = request.GET.get(key="user_id")

        params['access_token'] = access_token
        long_access_token = get_long_access_token(params)
        params['access_token'] = long_access_token['json_data']['access_token']
        facebook_page_id = get_facebook_page_id(params)
        params['facebook_page_id'] = facebook_page_id['json_data']['data'][0]['id']
        instagram_business_id = get_instagram_business_id(params)
        params['instagram_business_id'] = instagram_business_id['json_data']['instagram_business_account']['id']
        username = get_username(params)
        params['username'] = username['json_data']['username']

        profile_data = Profile.objects.get(userProfile=user_id)
        profile_data.nickName = params['username']
        profile_data.accessToken = params['access_token']
        profile_data.instagramBusinessID = params['instagram_business_id']
        profile_data.save()

        response_data = {}

        return Response(response_data)


# プロフィール作成(仮) アプリレビューまで
class TokenBetaView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        params = get_credentials()
        access_token = request.GET.get(key="access_token")
        instagram_business_id = request.GET.get(key="instagram_business_id")
        username = request.GET.get(key="username")
        user_id = request.GET.get(key="user_id")

        profile_data = Profile.objects.get(userProfile=user_id)
        profile_data.nickName = username
        profile_data.accessToken = access_token
        profile_data.instagramBusinessID = instagram_business_id
        profile_data.save()

        response_data = {}

        return Response(response_data)


# ハッシュタグ検索
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
                tag_data = Tag.objects.create(
                    tagname=tagname, hashtag=hashtag, hashtag_count=hashtag_count)
                search_data.ranking.add(tag_data)
                search_data.save()
        return search_data

    def get(self, request):
        results = []
        tagname = request.GET.get(key="tagname")
        userProfile = request.GET.get(key="userProfile")

        profile_data = Profile.objects.get(userProfile=userProfile)
        access_token = profile_data.accessToken
        instagram_account_id = profile_data.instagramBusinessID

        if tagname and access_token and instagram_account_id:
            search_data = Search.objects.filter(tagname=tagname)

            if search_data:
                search_data = search_data[0]

                # 一週間以上経過しているのでハッシュタグの再取得
                if search_data.created_at < (timezone.now() - timedelta(weeks=1)):
                    search_data.delete()
                    tag_data = Tag.objects.filter(tagname=tagname)
                    tag_data.delete()
                    search_data = self.get_hashtag(
                        tagname, access_token, instagram_account_id)
            else:
                search_data = self.get_hashtag(
                    tagname, access_token, instagram_account_id)

            search_serializer = serializers.SearchSerializer(search_data)
            return Response(search_serializer.data)
        return Response(status=status.HTTP_400_BAD_REQUEST)


# ベンチマーク情報取得
class AccountView(APIView):
    def get(self, request):
        params = get_credentials()
        ig_username = request.GET.get(key="ig_username")
        userProfile = request.GET.get(key="userProfile")
        is_search = request.GET.get(key="is_search")

        params = get_credentials()
        profile_data = Profile.objects.get(userProfile=userProfile)
        params['access_token'] = profile_data.accessToken
        params['instagram_account_id'] = profile_data.instagramBusinessID
        params['ig_username'] = ig_username
        params['limit'] = '100'

        account_response = get_account_info(params)
        business_discovery = account_response['json_data']['business_discovery']
        username = business_discovery['username']
        biography = business_discovery['biography']
        profile_picture_url = business_discovery['profile_picture_url']
        follows_count = business_discovery['follows_count']
        followers_count = business_discovery['followers_count']
        media_count = business_discovery['media_count']
        media_data = business_discovery['media']['data']

        benchmark_data, created = Benchmark.objects.update_or_create(
            name=username,
            defaults={
                'name': username,
                'profile_picture_url': profile_picture_url,
                'followers_count': followers_count,
                'media_count': media_count,
            }
        )
        if is_search == 'true':
            profile_data.benchmark.add(benchmark_data)
            profile_data.save()

        # 最近の投稿を取得
        recently_data = []
        for i in range(6):
            if media_data[i].get('media_url'):
                tags = re.findall('#([^\s→#\ufeff]*)',
                                  media_data[i]['caption'])
                tags = [a for a in tags if a != '']
                tags = map(lambda x: '#' + x, tags)
                tags = ' '.join(tags)

                timestamp = timezone.localtime(datetime.strptime(
                    media_data[i]['timestamp'], '%Y-%m-%dT%H:%M:%S%z'))
                timestamp = timestamp.strftime("%Y-%m-%d %H:%M")

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
        row_count = media_data_frame['caption'].str.extractall(
            '#([^\s→#\ufeff]*)').reset_index(level=0).drop_duplicates()[0]
        # ハッシュタグが含まれている投稿件数
        hashtag_count = row_count.value_counts().to_dict()

        # ハッシュタグ毎にデータを作成
        hashtag_data = []
        for key, val in hashtag_count.items():
            post_data = media_data_frame[media_data_frame['caption'].str.contains(
                '#' + key, na=False)]
            hashag_post_data = []
            average_eng = 0
            average_eng_percent = 0
            for index, row in post_data.iterrows():
                timestamp = (datetime.strptime(
                    row['timestamp'], '%Y-%m-%dT%H:%M:%S%z')).strftime("%Y-%m-%d %H:%M")

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
                average_eng_percent = round(average_eng / followers_count, 1)

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


# アカウント情報取得
class AccountInfoView(APIView):
    def get(self, request):
        userProfile = request.GET.get(key="userProfile")
        params = get_profile_data(userProfile)
        response_data = {}

        if params['access_token']:
            params['limit'] = '8'
            response = get_account_info(params)
            if response:
                response_data = response['json_data']['business_discovery']

                business_discovery = response['json_data']['business_discovery']
                media_data = business_discovery['media']['data']

                # 自分の投稿の平均エンゲージメント数を取得
                engagement = 0
                for i in range(int(params['limit'])):
                    if media_data[i].get('media_url'):
                        engagement += media_data[i]['like_count'] + media_data[i]['comments_count']
                try:
                    my_eng_ave = math.floor(engagement / len(media_data))
                except ZeroDivisionError:
                    my_eng_ave = 0

                response_data['my_eng_ave'] = my_eng_ave

        return Response(response_data)


# メディアインサイト取得
class MediaInsightsView(APIView):
    def get(self, request):
        userProfile = request.GET.get(key="userProfile")
        media_id = request.GET.get(key="media_id")
        params = get_profile_data(userProfile)
        params['media_id'] = media_id

        response_data = {}
        response = get_media_insights(params)
        if response:
            response_data = response['json_data']

        return Response(response_data)


# ユーザーインサイト取得
class UserInsightsView(APIView):
    def get(self, request):
        userProfile = request.GET.get(key="userProfile")
        since = request.GET.get(key="since")
        until = request.GET.get(key="until")
        params = get_profile_data(userProfile)
        params['since'] = since
        params['until'] = until

        response_data = {}
        response = get_user_insights(params)
        if response:
            response_data = response['json_data']

        return Response(response_data)


# オンラインフォロワーインサイト取得
class OnlineFollowersInsightsView(APIView):
    def get(self, request):
        userProfile = request.GET.get(key="userProfile")
        since = request.GET.get(key="since")
        until = request.GET.get(key="until")
        params = get_profile_data(userProfile)
        params['since'] = since
        params['until'] = until

        response_data = {}
        response = get_online_followers_insights(params)
        if response:
            response_data = response['json_data']

        return Response(response_data)


# オーディエンスインサイト取得
class AudienceInsightsView(APIView):
    def get(self, request):
        userProfile = request.GET.get(key="userProfile")
        params = get_profile_data(userProfile)

        response_data = {}
        response = get_audience_insights(params)
        if response:
            response_data = response['json_data']

        return Response(response_data)


# ストーリー情報取得
class StoriesInfoView(APIView):
    def get(self, request):
        userProfile = request.GET.get(key="userProfile")
        params = get_profile_data(userProfile)

        strories_data = get_stories(params)['json_data']['data']

        stories_insights_data = []
        for data in strories_data:
            params['media_id'] = data['id']
            media_data = get_media_info(params)['json_data']
            media_insights_data = get_story_media_insights(params)['json_data']['data']
            timestamp = timezone.localtime(datetime.strptime(media_data['timestamp'], '%Y-%m-%dT%H:%M:%S%z'))
            timestamp = timestamp.strftime("%Y-%m-%d %H:%M")

            stories_insights_data.append({
                'id': media_data['id'],
                'caption': media_data['caption'] if media_data.get('caption') else '',
                'media_type': media_data['media_type'],
                'media_url': media_data['media_url'],
                'timestamp': timestamp,
                'impressions': media_insights_data[0]['values'][0]['value'],
                'reach': media_insights_data[1]['values'][0]['value'],
                'replies': media_insights_data[2]['values'][0]['value'],
                'taps_forward': media_insights_data[3]['values'][0]['value'],
                'taps_back': media_insights_data[4]['values'][0]['value'],
                'exits': media_insights_data[5]['values'][0]['value'],
            })

        return Response(stories_insights_data)


# プラン変更
class PlanView(APIView):
    def get(self, request):
        userProfile = request.GET.get(key="userProfile")
        plan = request.GET.get(key="plan")
        profile_data = Profile.objects.get(userProfile=userProfile)
        pricing_data = Pricing.objects.get(slug=plan)
        profile_data.pricing = pricing_data
        profile_data.save()

        return Response({})


# ハッシュタグ登録
class RegisterHashtagView(APIView):
    def get(self, request):
        userProfile = request.GET.get(key="userProfile")
        hashtag = request.GET.get(key="hashtag")
        profile_data = Profile.objects.get(userProfile=userProfile)

        hashtag_data, _ = Hashtag.objects.get_or_create(name=hashtag)

        if not hashtag_data in profile_data.hashtag.all():
            profile_data.hashtag.add(hashtag_data)
            profile_data.save()

        return Response({})


# ハッシュタグ削除
class DeleteHashtagView(APIView):
    def get(self, request):
        userProfile = request.GET.get(key="userProfile")
        hashtag = request.GET.get(key="hashtag")
        profile_data = Profile.objects.get(userProfile=userProfile)

        hashtag_data = Hashtag.objects.get(name=hashtag)

        profile_data.hashtag.remove(hashtag_data)
        profile_data.save()

        return Response({})


# ハッシュタグ分析
class AnalyticsHashtagView(APIView):
    # リストの中で対象値と一番近い要素のインデックス取得
    def get_nearest_value(self, list, num):
        idx = np.abs(np.asarray(list) - num).argmin()
        return idx

    def get(self, request):
        userProfile = request.GET.get(key="userProfile")
        eng = request.GET.get(key="eng")

        params = get_credentials()
        profile_data = Profile.objects.get(userProfile=userProfile)
        params['access_token'] = profile_data.accessToken
        params['instagram_account_id'] = profile_data.instagramBusinessID
        params['ig_username'] = profile_data.nickName

        response_data = []

        hashtag_list = profile_data.hashtag.all()

        for tagname in hashtag_list:
            params['tagname'] = tagname.name
            params['hashtag_id'] = get_hashtag_id(params)['json_data']['data'][0]['id']

            # トップメディアのエンゲージメント数のリストを作成
            hashtag_media_response = get_hashtag_media(params)

            if 'json_data' in hashtag_media_response:
                hashag_data = hashtag_media_response['json_data']["data"]
                length = len(hashag_data)
                engage_list = [hashag_data[i]['comments_count'] + hashag_data[i]['like_count'] for i in range(length)]

                # 自分の投稿の平均エンゲージメント数と一番近い値のタグリストを取得
                for i in range(len(engage_list)):
                    idx = self.get_nearest_value(engage_list, int(eng))
                    caption = hashag_data[idx]["caption"]
                    hash_tag_list = re.findall('#([^\s→#\ufeff]*)', caption)
                    if hash_tag_list:
                        break
                    else:
                        del engage_list[idx]
                        continue
                try:
                    if hashag_data[idx]['media_type'] == 'CAROUSEL_ALBUM':
                        media_url = hashag_data[idx]['children']['data'][0]['media_url']
                    else:
                        media_url = hashag_data[idx]['media_url']
                except:
                    media_url = 'http://placehold.jp/500x500.png?text=No Image'

                response_data.append({
                    'tagname': tagname.name,
                    'permalink': hashag_data[idx]['permalink'],
                    'media_url': media_url,
                    'like_count': hashag_data[idx]['like_count'],
                    'comments_count': hashag_data[idx]['comments_count'],
                    'hash_tag_list': hash_tag_list,
                })

        return Response(response_data)
    
    
class IndexView(generic.TemplateView):
    template_name = "checkout/checkout_test.html"
    def get(self, request, *args, **kwargs):
        return render(request, self.template_name )    


logger = logging.getLogger(__name__)


@csrf_exempt
def onetime_payment_checkout(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        domain_url = os.getenv('DOMAIN')
        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            # Create new Checkout Session for the order
            # ?session_id={CHECKOUT_SESSION_ID} means the redirect will have the session ID set as a query param
            checkout_session = stripe.checkout.Session.create(
                success_url=domain_url +
                "checkout/success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=domain_url + "checkout/canceled/",
                payment_method_types=["card"],
                line_items=[
                    {
                        "name": "Pasha photo",
                        "images": ["https://picsum.photos/300/300?random=4"],
                        "quantity": data['quantity'],
                        "currency": os.getenv('CURRENCY'),
                        "amount": os.getenv('BASE_PRICE'),
                    }
                ]
            )
            logger.debug( str(checkout_session))
            return JsonResponse({'sessionId': checkout_session['id']})
        except Exception as e:
            logger.warning( str(e) )
            return JsonResponse({'error':str(e)})