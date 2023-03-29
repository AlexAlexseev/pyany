from django.contrib import admin

from .models import Follow, Group, Post, Comment


class PostAdmin(admin.ModelAdmin):
    list_display = ('pk', 'text', 'pub_date', 'author', 'group', )
    list_editable = ('group', 'text', 'author',)
    search_fields = ('text',)
    list_filter = ('pub_date',)
    empty_value_display = '-пусто-'


class CommentAdmin(admin.ModelAdmin):
    list_display = ('pk', 'post', 'author', 'text', 'created', )
    list_editable = ('text', )
    search_fields = ('text',)
    list_filter = ('created',)


class FollowAdmin(admin.ModelAdmin):
    list_display = ('pk', 'author', 'user',)
    list_editable = ('author', )


admin.site.register(Post, PostAdmin)
admin.site.register(Group)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Follow, FollowAdmin)
