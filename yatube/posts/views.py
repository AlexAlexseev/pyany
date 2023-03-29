from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, PostForm
from .models import Group, Post, Follow
from .utils import get_paginator

User = get_user_model()


def index(request):
    title = 'Последние обновления на сайте'
    user = get_object_or_404(User, username=request.user)
    posts = Post.objects.select_related('author', 'group')
    page_obj = get_paginator(request, posts)
    following = user.is_authenticated and user.following.exists()
    context = {
        'title': title,
        'page_obj': page_obj,
        'follow': following,
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    page_obj = get_paginator(request, posts)
    context = {
        'group': group,
        'posts': posts,
        'page_obj': page_obj,
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    user = get_object_or_404(User, username=username)
    posts = user.posts.all()
    page_obj = get_paginator(request, posts)
    following = user.is_authenticated and user.following.exists()
    context = {
        'author': user,
        'page_obj': page_obj,
        'username': username,
        'following': following,
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    user = get_object_or_404(User, username=post.author)
    post_number = Post.objects.select_related(
        'author', 'post_id'
    ).filter(author__username=post.author).count()
    form = CommentForm()
    context = {
        'author': user,
        'post': post,
        'title': post.text,
        'posts_number': post_number,
        'image': post.image or None,
        'form': form,
        'comments': post.comments.all(),
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    context = {
        'form': form,
    }
    try:
        if request.method == "POST" and form.is_valid():
            instance = form.save(commit=False)
            instance.author = request.user
            instance.save()
            return redirect('posts:profile', request.user)
        return render(request, 'posts/create_post.html', context)
    except IntegrityError:
        return redirect('posts:index')
    
@login_required
def post_delete(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.user != post.author:
        return redirect('posts:post_detail', post.pk,)
    post.delete()
    return redirect('posts:profile', post.author)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = PostForm(request.POST or None, files=request.FILES or None,
                    instance=post)
    if post.author == request.user:
        if request.method == "POST" and form.is_valid():
            post = form.save()
            return redirect('posts:post_detail', post_id)
        context = {
            'form': form,
            'is_edit': True,
            'post': post
        }
        return render(request, 'posts/create_post.html', context)
    else:
        return redirect('profile')


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
        return redirect('posts:post_detail', post_id=post_id)
    return form


@login_required
def follow_index(request):
    posts = Post.objects.filter(
        author__following__user=request.user)
    page_obj = get_paginator(request, posts)
    context = {'page_obj': page_obj}
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if request.user != author:
        Follow.objects.get_or_create(
            user=request.user,
            author=author
        )
    return redirect('posts:profile', username)


@login_required
def profile_unfollow(request, username):
    Follow.objects.get(user=request.user, author__username=username).delete()
    return redirect('posts:profile', username)
