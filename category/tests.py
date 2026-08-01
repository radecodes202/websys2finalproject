from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from category.models import Category

User = get_user_model()


class CategoryCRUDTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='admin_user',
            email='admin@example.com',
            password='StrongPass123',
            role='admin',
            is_approved=True,
        )
        self.client.force_login(self.user)

    def test_category_create_and_list(self):
        create_response = self.client.post(
            reverse('category:category-create'),
            {'name': 'Hardware', 'description': 'Hardware supplies'},
            follow=True,
        )

        self.assertEqual(create_response.status_code, 200)
        self.assertTrue(Category.objects.filter(name='Hardware').exists())

        list_response = self.client.get(reverse('category:category-list'))
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, 'Hardware')
