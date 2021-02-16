from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Tag, Search, Profile, Benchmark, Pricing, Hashtag


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('id', 'email', 'password')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = get_user_model().objects.create_user(**validated_data)
        return user


class BenchmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Benchmark
        fields = ('name', 'profile_picture_url', 'followers_count', 'media_count')


class HashtagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hashtag
        fields = ('name',)


class PricingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pricing
        fields = ('name', 'price')


class ProfileSerializer(serializers.ModelSerializer):
    created_on = serializers.DateTimeField(format='%Y-%m-%d', read_only=True)
    benchmark = BenchmarkSerializer(many=True, read_only=True)
    hashtag = HashtagSerializer(many=True, read_only=True)
    pricing = PricingSerializer(read_only=True)

    class Meta:
        model = Profile
        fields = ('id', 'nickName', 'userProfile', 'accessToken', 'instagramBusinessID', 'created_on', 'benchmark', 'pricing', 'hashtag')
        extra_kwargs = {'userProfile': {'read_only': True}}


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('hashtag', 'hashtag_count')


class SearchSerializer(serializers.ModelSerializer):
    ranking = TagSerializer(many=True)

    class Meta:
        model = Search
        fields = ('ranking',)
