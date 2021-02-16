from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api import views

router = DefaultRouter()
router.register('profile', views.ProfileViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('register/', views.CreateUserView.as_view(), name='register'),
    path('myprofile/', views.MyProfileListView.as_view(), name='myprofile'),

    path('token/', views.TokenView.as_view(), name='token'),
    path('tokenbeta/', views.TokenBetaView.as_view(), name='tokenbeta'), # アプリレビューするまで仮
    path('search/', views.SearchView.as_view(), name='search'),
    path('account/', views.AccountView.as_view(), name='account'),
    path('accountinfo/', views.AccountInfoView.as_view(), name='accountinfo'),
    path('mediainsights/', views.MediaInsightsView.as_view(), name='mediainsights'),
    path('userinsights/', views.UserInsightsView.as_view(), name='userinsights'),
    path('onlinefollowersinsights/', views.OnlineFollowersInsightsView.as_view(), name='onlinefollowersinsights'),
    path('audienceinsights/', views.AudienceInsightsView.as_view(), name='audienceinsights'),
    path('storiesinfo/', views.StoriesInfoView.as_view(), name='storiesinfo'),
    path('plan/', views.PlanView.as_view(), name='plan'),
    path('registerhashtag/', views.RegisterHashtagView.as_view(), name='registerhashtag'),
    path('deletehashtag/', views.DeleteHashtagView.as_view(), name='deletehashtag'),
    path('analyticshashtag/', views.AnalyticsHashtagView.as_view(), name='analyticshashtag'),
]
