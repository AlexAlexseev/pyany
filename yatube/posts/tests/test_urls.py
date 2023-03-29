from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from ..models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.user = User.objects.create_user(username='auth_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост',
            id='2'
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.author_client = Client()
        self.author_client.force_login(self.author)

    def test_non_auth_url(self):
        """Доступность страниц для неавторизованного пользователя."""
        url_names = ['/', '/about/author/',
                     '/about/tech/', f'/profile/{self.user.username}/',
                     f'/group/{self.group.slug}/',
                     f'/posts/{self.post.id}/']
        for address in url_names:
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_auth_url(self):
        """Страница /posts/{post.id}/edit/ доступна автору пользователю."""
        response = self.author_client.get(f'/posts/{self.post.id}/edit/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def tet_authorized_url(self):
        """Страницы доступны авторизованному пользователю."""
        url_names = ['/create/', 'follow/', '/follow/', '/unfollow/',
                     '/comment/']
        for address in url_names:
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_redirect_anonymous_on_admin_login(self):
        """ Проверяем редиректы для неавторизованного пользователя """
        url_names = {
            '/auth/login/?next=/create/': '/create/',
            f'/auth/login/?next=/posts/{self.post.id}/edit/':
                f'/posts/{self.post.id}/edit/',
        }
        for template, address in url_names.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address, follow=True)
                self.assertRedirects(response, template)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            '/create/': 'posts/create_post.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            f'/profile/{self.author.username}/': 'posts/profile.html',
            f'/posts/{self.post.id}/edit/': 'posts/create_post.html',
            '/follow/': 'posts/follow.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.author_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_404_page(self):
        """Проверка 404 для несуществующих страниц."""
        url = '/unexisting_page/'
        clients = (
            self.authorized_client,
            self.author_client,
            self.client,
        )
        for client in clients:
            with self.subTest(url=url):
                response = client.get(url, follow=True)
                self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
                self.assertTemplateUsed(response, 'core/404.html')
