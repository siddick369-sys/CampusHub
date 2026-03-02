from django.contrib import admin

# Register your models here.

from django.contrib import admin
from .models import Track, School, Job, Question, Choice, ChoiceTrackScore, OrientationResult, OrientationAnswer

admin.site.register(Track)
admin.site.register(School)
admin.site.register(Job)
admin.site.register(Question)
admin.site.register(Choice)
admin.site.register(ChoiceTrackScore)
admin.site.register(OrientationResult)
admin.site.register(OrientationAnswer)


# orientation/admin.py
from django.contrib import admin
from .models import YouTubePlaylist

@admin.register(YouTubePlaylist)
class YouTubePlaylistAdmin(admin.ModelAdmin):
    list_display = ['title', 'channel_name', 'difficulty', 'language', 'is_active']
    list_filter = ['difficulty', 'language', 'is_active', 'tracks']
    filter_horizontal = ['tracks']
    search_fields = ['title', 'channel_name', 'description']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('title', 'youtube_url', 'description')
        }),
        ('Chaîne YouTube', {
            'fields': ('channel_name', 'channel_url', 'thumbnail_url')
        }),
        ('Caractéristiques', {
            'fields': ('difficulty', 'language', 'estimated_hours', 'video_count')
        }),
        ('Relations', {
            'fields': ('tracks',)
        }),
        ('Statut', {
            'fields': ('is_active', 'is_free', 'last_verified')
        }),
    )