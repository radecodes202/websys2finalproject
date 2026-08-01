from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from customer.models import Customer

User = get_user_model()


class CustomerCRUDTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='admin_user',
            email='admin@example.com',
            password='StrongPass123',
            role='admin',
            is_approved=True,
        )
        self.client.force_login(self.user)

    def test_customer_create_and_list(self):
        create_response = self.client.post(
            reverse('customer:customer-create'),
            {
                'name': 'Walk-in Customer',
                'contact_person': 'John Customer',
                'email': 'customer@example.com',
                'phone': '987654321',
                'address': '456 Side St',
                'city': 'Quezon City',
                'postal_code': '1100',
                'country': 'Philippines',
                'is_active': True,
            },
            follow=True,
        )

        self.assertEqual(create_response.status_code, 200)
        self.assertTrue(Customer.objects.filter(name='Walk-in Customer').exists())

        list_response = self.client.get(reverse('customer:customer-list'))
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, 'Walk-in Customer')
