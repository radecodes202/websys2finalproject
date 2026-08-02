from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from category.models import Category
from product.models import Product, Sale, SaleItem, Payment
from decimal import Decimal

User = get_user_model()


class SalesReportTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin', email='admin@example.com',
            password='StrongPass123', role='admin', is_approved=True,
        )
        self.cashier = User.objects.create_user(
            username='cashier', email='cashier@example.com',
            password='StrongPass123', role='cashier', is_approved=True,
        )
        self.category = Category.objects.create(name='Hardware', description='Hardware supplies')
        self.product = Product.objects.create(
            name='Hammer', description='Standard hammer',
            category=self.category, sku='SKU-001',
            unit_price=Decimal('25.00'), quantity_in_stock=10,
            reorder_level=2, is_active=True,
        )
        self.sale = Sale.objects.create(
            cashier=self.cashier,
            payment_method='cash',
            subtotal=Decimal('25.00'),
            tax=Decimal('0.00'),
            discount=Decimal('0.00'),
            total=Decimal('25.00'),
            status='completed',
        )
        SaleItem.objects.create(
            sale=self.sale,
            product=self.product,
            quantity=1,
            unit_price=Decimal('25.00'),
            subtotal=Decimal('25.00'),
        )
        Payment.objects.create(
            sale=self.sale,
            amount=Decimal('25.00'),
            method='cash',
            reference_number='RCPT-001',
            change_given=Decimal('0.00'),
        )
        self.client.force_login(self.admin)

    def test_sales_report_page_renders_with_live_sale_data(self):
        response = self.client.get(reverse('reports:sales-report'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hammer')
        self.assertContains(response, '25.00')


class SalesHistoryTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin', email='admin@example.com',
            password='StrongPass123', role='admin', is_approved=True,
        )
        self.cashier1 = User.objects.create_user(
            username='cashier1', email='c1@example.com',
            password='StrongPass123', role='cashier', is_approved=True,
        )
        self.cashier2 = User.objects.create_user(
            username='cashier2', email='c2@example.com',
            password='StrongPass123', role='cashier', is_approved=True,
        )
        self.category = Category.objects.create(name='Hardware', description='Hardware supplies')
        self.product = Product.objects.create(
            name='Hammer', description='Standard hammer',
            category=self.category, sku='SKU-001',
            unit_price=Decimal('25.00'), quantity_in_stock=10,
            reorder_level=2, is_active=True,
        )
        self.sale1 = Sale.objects.create(
            cashier=self.cashier1, payment_method='cash',
            subtotal=Decimal('25.00'), tax=Decimal('0.00'),
            discount=Decimal('0.00'), total=Decimal('25.00'),
            status='completed',
        )
        SaleItem.objects.create(
            sale=self.sale1, product=self.product,
            quantity=1, unit_price=Decimal('25.00'), subtotal=Decimal('25.00'),
        )
        Payment.objects.create(
            sale=self.sale1, amount=Decimal('25.00'), method='cash',
            reference_number='RCPT-001', change_given=Decimal('0.00'),
        )
        self.sale2 = Sale.objects.create(
            cashier=self.cashier2, payment_method='card',
            subtotal=Decimal('50.00'), tax=Decimal('0.00'),
            discount=Decimal('0.00'), total=Decimal('50.00'),
            status='pending',
        )
        SaleItem.objects.create(
            sale=self.sale2, product=self.product,
            quantity=2, unit_price=Decimal('25.00'), subtotal=Decimal('50.00'),
        )
        Payment.objects.create(
            sale=self.sale2, amount=Decimal('50.00'), method='card',
            reference_number='RCPT-002', change_given=Decimal('0.00'),
        )
        self.history_url = reverse('reports:sales-history')
        self.detail_url = reverse('reports:sale-detail', kwargs={'pk': self.sale1.pk})

    def test_admin_can_view_sales_history(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.history_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sales History')

    def test_manager_can_view_sales_history(self):
        manager = User.objects.create_user(
            username='manager', email='mgr@example.com',
            password='StrongPass123', role='manager', is_approved=True,
        )
        self.client.force_login(manager)
        response = self.client.get(self.history_url)
        self.assertEqual(response.status_code, 200)

    def test_cashier_can_view_own_sales_history(self):
        self.client.force_login(self.cashier1)
        response = self.client.get(self.history_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '#{}'.format(self.sale1.pk))
        self.assertNotContains(response, '#{}'.format(self.sale2.pk))

    def test_cashier_cannot_view_other_cashier_sales(self):
        self.client.force_login(self.cashier2)
        response = self.client.get(self.history_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '#{}'.format(self.sale2.pk))
        self.assertNotContains(response, '#{}'.format(self.sale1.pk))

    def test_sale_detail_view_renders(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hammer')
        self.assertContains(response, '25.00')

    def test_sale_detail_has_reprint_link(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reprint Receipt')

    def test_sales_history_filter_by_status(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.history_url, {'status': 'completed'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '#{}'.format(self.sale1.pk))
        self.assertNotContains(response, '#{}'.format(self.sale2.pk))

    def test_sales_history_filter_by_payment_method(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.history_url, {'payment_method': 'card'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '#{}'.format(self.sale2.pk))
        self.assertNotContains(response, '#{}'.format(self.sale1.pk))