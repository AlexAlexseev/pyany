from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        self.guest_client = Client()

    def test_static_url(self):
        """Доступность статичных страниц."""
        url_names = ['/about/author/', '/about/tech/']
        for address in url_names:
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_static_page_accessible_by_name(self):
        """URL, генерируемый при помощи имени author, tech, доступен."""
        templates_page_names = ['about:author']
        for reverse_name in templates_page_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.guest_client.get(reverse(reverse_name))
                self.assertEqual(response.status_code, HTTPStatus.OK)
