import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Follow, Group, Post

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.image_name = 'small.gif'
        cls.uploaded = SimpleUploadedFile(
            name=cls.image_name,
            content=small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый текст',
            group=cls.group,
            image=cls.uploaded
        )

    def setUp(self):
        self.guest_client = Client()
        self.author_client = Client()
        self.author_client.force_login(self.author)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_pages_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_page_names = {
            'posts/index.html': reverse('posts:index'),
            'posts/create_post.html': reverse('posts:post_create'),
            'posts/profile.html': reverse(
                'posts:profile', args=[self.author.username]),
            'posts/post_detail.html': reverse(
                'posts:post_detail', args=[self.post.id]),
            'posts/group_list.html': reverse(
                'posts:group_list', args=[self.group.slug])
        }
        for template, reverse_name in templates_page_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.author_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_create_page_show_correct_context(self):
        """Шаблон create сформирован с правильным контекстом.
        Проверка формы """
        response = self.author_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_index_group_profile_page_show_correct_cont(self):
        """Проверка Context страницы index, group, profile"""
        context = [
            self.author_client.get(reverse('posts:index')),
            self.author_client.get(reverse(
                'posts:group_list', args=[self.group.slug])),
            self.author_client.get(reverse(
                'posts:profile', args=[self.author.username])),
        ]
        for response in context:
            first_object = response.context['page_obj'][0]
            context_objects = {
                self.author: first_object.author,
                self.post.text: first_object.text,
                self.group.slug: first_object.group.slug,
                self.post: first_object,
            }
            for reverse_name, response_name in context_objects.items():
                with self.subTest(reverse_name=reverse_name):
                    self.assertEqual(response_name, reverse_name)

    def test_image(self):
        """Проверка контекста (картинка) на главной странице, профиле
            и посте."""
        post = self.author_client.get(
            reverse('posts:index')).context['page_obj'][0]
        post_prof = self.author_client.get(
            reverse('posts:profile', args=[self.author])).context[
                'page_obj'][0]
        post_group = self.author_client.get(
            reverse('posts:group_list', args=[self.group.slug])).context[
                'page_obj'][0]
        post_detail = self.author_client.get(
            reverse('posts:post_detail', args=[self.post.id])).context['image']
        self.assertEqual(post.image, self.post.image)
        self.assertEqual(post_prof.image, self.post.image)
        self.assertEqual(post_group.image, self.post.image)
        self.assertEqual(post_detail, self.post.image)

    def test_posts_detail_pages_show_correct_context(self):
        """Шаблон posts_detail сформирован с правильным контекстом."""
        response = (self.author_client.get(reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id})))
        self.assertEqual(response.context.get('post').text, 'Тестовый текст')

    def test_cache(self):
        """ Проверка кэша."""
        post = Post.objects.create(
            text='Текст',
            author=self.author,
            group=self.group
        )
        response = self.author_client.get(reverse('posts:index'))
        response_post = response.context['page_obj'][0]
        self.assertEqual(post, response_post)
        post.delete()
        response_2 = self.author_client.get(reverse('posts:index'))
        self.assertEqual(response.content, response_2.content)
        cache.clear()
        response_3 = self.author_client.get(reverse('posts:index'))
        self.assertNotEqual(response.content, response_3.content)

    def test_no_in_wrong_group(self):
        """Пост не появляется в чужой группе."""
        wrong_group = Group.objects.create(
            title='Тестовое название группы 2',
            slug='test-slug2',
            description='Тестовое описание группы 2'
        )
        responseWrGr = self.author_client.get(
            reverse('posts:group_list', args={wrong_group.slug}))
        response = self.author_client.get(
            reverse('posts:group_list', args={self.group.slug}))
        self.assertNotEqual(len(response.context['page_obj']),
                            len(responseWrGr.context['page_obj']))


class PaginatorViewTest(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.author = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )
        posts = [Post(author=cls.author,
                 text=f'Тестовый пост{i}',
                 group=cls.group) for i in range(13)]
        cls.posts = Post.objects.bulk_create(posts)

    def test_first_page_10_posts(self):
        """ На первых страницах index, group_list, profile  10 постов"""
        url_names = [
            reverse('posts:index'),
            reverse('posts:profile', args=[self.author.username]),
            reverse('posts:group_list', args=[self.group.slug])
        ]
        for url in url_names:
            response = self.client.get(url)
            self.assertEqual(len(response.context['page_obj'].object_list), 10)

    def test_two_page_3_posts(self):
        """ На вторых страницах index, group_list, profile  3 поста"""
        url_names = [
            reverse('posts:index') + '/?page=2',
            reverse('posts:profile',
                    args=[self.author.username]) + '?page=2',
            reverse('posts:group_list',
                    args=[self.group.slug]) + '?page=2'
        ]
        for url in url_names:
            response = self.client.get(url)
            self.assertEqual(len(response.context['page_obj'].object_list),
                             3, msg=url)


class FollowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_follower = User.objects.create_user(username='user_1')
        cls.user_follower_2 = User.objects.create_user(username='user_2')
        cls.user_following = User.objects.create_user(username='Following')
        cls.post = Post.objects.create(
            author=cls.user_following,
            text='Текст',
        )

    def setUp(self):
        self.following_client = Client()
        self.follower_client = Client()
        self.follower_client_2 = Client()
        self.following_client.force_login(self.user_following)
        self.follower_client.force_login(self.user_follower)
        self.follower_client_2.force_login(self.user_follower_2)

    def test_follow(self):
        """Зарегистрированный пользователь может подписываться."""
        follower_count = Follow.objects.count()
        self.follower_client.get(reverse(
            'posts:profile_follow',
            args=(self.user_following.username,)))
        self.assertEqual(Follow.objects.count(), follower_count + 1)

    def test_unfollow(self):
        """Зарегистрированный пользователь может отписаться."""
        Follow.objects.create(
            user=self.user_follower,
            author=self.user_following
        )
        follower_count = Follow.objects.count()
        self.follower_client.get(reverse(
            'posts:profile_unfollow',
            args=(self.user_following.username,)))
        self.assertEqual(Follow.objects.count(), follower_count - 1)

    def test_new_post_see_follower(self):
        """Пост появляется в ленте подписавшихся."""
        posts = Post.objects.create(
            text='Текст',
            author=self.user_following,
        )
        follow = Follow.objects.create(
            user=self.user_follower,
            author=self.user_following
        )
        response = self.follower_client.get(reverse('posts:follow_index'))
        post = response.context['page_obj'][0]
        self.assertEqual(post, posts)
        follow.delete()
        response_2 = self.follower_client.get(reverse('posts:follow_index'))
        self.assertEqual(len(response_2.context['page_obj']), 0)

    def test_new_post_dont_see_unfollower(self):
        """Пост не появляется в ленте не подписавшихся."""
        Follow.objects.create(user=self.user_follower,
                              author=self.user_following)
        response_unfollower = self.follower_client_2.get(
            reverse('posts:follow_index'))
        post_unfollower = len(response_unfollower.context['page_obj'])
        self.assertEqual(post_unfollower, 0)
