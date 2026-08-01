from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from supplier.models import Supplier

User = get_user_model()


class SupplierCRUDTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='admin_user',
            email='admin@example.com',
            password='StrongPass123',
            role='admin',
            is_approved=True,
        )
        self.client.force_login(self.user)

    def test_supplier_create_and_list(self):
        create_response = self.client.post(
            reverse('supplier:supplier-create'),
            {
                'name': 'Acme Supplies',
                'contact_person': 'Jane Doe',
                'email': 'supplier@example.com',
                'phone': '123456789',
                'address': '123 Main St',
                'city': 'Manila',
                'postal_code': '1000',
                'country': 'Philippines',
                'is_active': True,
            },
            follow=True,
        )

        self.assertEqual(create_response.status_code, 200)
        self.assertTrue(Supplier.objects.filter(name='Acme Supplies').exists())

        list_response = self.client.get(reverse('supplier:supplier-list'))
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, 'Acme Supplies')
