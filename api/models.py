from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings


class UserManager(BaseUserManager):
    def create_user(self, email, password=None):
        if not email:
            raise ValueError('email is must')

        user = self.model(email=self.normalize_email(email))
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password):
        user = self.create_user(email, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)

        return user


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'

    def __str__(self):
        return self.email


class Benchmark(models.Model):
    name = models.CharField(max_length=100)
    profile_picture_url = models.CharField(max_length=400)
    followers_count = models.CharField(max_length=100)
    media_count = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Hashtag(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Pricing(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    price = models.IntegerField()

    def __str__(self):
        return self.name


def get_or_create_pricing():
    pricing, _ = Pricing.objects.get_or_create(
        name='スタンダードプラン',
        defaults={
            'slug': 'standard',
            'price': 0
        }
    )
    return pricing.id


class Profile(models.Model):
    userProfile = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='userProfile', on_delete=models.CASCADE)
    nickName = models.CharField(max_length=100, blank=True, null=True)
    accessToken = models.CharField(max_length=200, blank=True, null=True)
    instagramBusinessID = models.CharField(max_length=100, blank=True, null=True)
    created_on = models.DateTimeField(auto_now_add=True)
    benchmark = models.ManyToManyField(Benchmark, blank=True, verbose_name='ベンチマーク')
    hashtag = models.ManyToManyField(Hashtag, blank=True, verbose_name='ハッシュタグ')
    pricing = models.ForeignKey(Pricing, on_delete=models.CASCADE, related_name='pricing', default=get_or_create_pricing)

    def __str__(self):
        return self.userProfile.email


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
