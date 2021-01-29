from rest_framework import serializers
from .models import Tag, Search


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('hashtag', 'hashtag_count')


class SearchSerializer(serializers.ModelSerializer):
    ranking = TagSerializer(many=True)

    class Meta:
        model = Search
        fields = ('ranking',)
