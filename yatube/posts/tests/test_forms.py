import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest_user = Client()
        cls.author_user = Client()
        cls.author = User.objects.create_user(username='author')
        cls.author_user.force_login(cls.author)
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_authorized_user_create_post(self):
        """Проверка создания записи авторизированным клиентом."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Текст нового поста',
            'group': self.group.id,
            'image': self.uploaded,
        }
        response = self.author_user.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse('posts:profile',
                             args=[self.author.username]))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        post = Post.objects.latest('id')
        fields = {
            post.text: form_data['text'],
            post.author: self.author,
            post.group: self.group,
            post.image: f'posts/{self.uploaded}'
        }
        for post_field, self_field in fields.items():
            with self.subTest(post_field=post_field):
                self.assertEqual(post_field, self_field)

    def test_authorized_user_edit_post(self):
        """Проверка редактирования записи автором."""
        post = Post.objects.create(
            text='Текст поста для редактирования',
            author=self.author,
            group=self.group,
        )
        form_data = {
            'text': 'Отредактированный текст поста',
            'group': self.group.id,
        }
        response = self.author_user.post(
            reverse('posts:post_edit', args=[post.id]),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', args=[post.id])
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        post = Post.objects.latest('id')
        fields = {
            post.text: form_data['text'],
            post.author: self.author,
            post.group: self.group,
        }
        for post_field, self_field in fields.items():
            with self.subTest(post_field=post_field):
                self.assertEqual(post_field, self_field)

    def test_nonauthorized_user_create_post(self):
        """Проверка создания записи не авторизированным пользователем."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Текст поста',
            'group': self.group.id,
        }
        response = self.guest_user.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        redirect = reverse('login') + '?next=' + reverse('posts:post_create')
        self.assertRedirects(response, redirect)
        self.assertEqual(Post.objects.count(), posts_count)

    def test_comment(self):
        """Проверка создания пользователем комментария"""
        comments_count = Comment.objects.count()
        post = Post.objects.create(
            text='Текст поста',
            author=self.author,
            group=self.group,
        )
        form_data = {
            'post': post,
            'author': self.author,
            'text': 'comment',
        }
        response = self.author_user.post(
            reverse('posts:add_comment', args=(post.id,)),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail', args=(post.id,)))
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertTrue(Comment.objects.filter(
            text='comment',
            author=self.author,).exists())
