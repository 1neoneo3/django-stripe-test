from django.db import models


class Tag(models.Model):
    tagname = models.CharField(max_length=100)
    hashtag = models.CharField(max_length=100)
    hashtag_count = models.IntegerField()

    def __str__(self):
        return self.tagname

class Search(models.Model):
    tagname = models.CharField(max_length=100)
    ranking = models.ManyToManyField(
        Tag,
        blank=True,
        verbose_name='ランキング',
        help_text='ハッシュタグのランキング',
        related_name='search_set',
        related_query_name='search'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.tagname
