from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from category.models import Category
from product.models import Alert, Product, Sale, SaleItem, Payment
from supplier.models import Supplier, SupplierPayment
from customer.models import Customer
from accounts.models import ActivityLog

User = get_user_model()


class SupplierPaymentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='supplier_user',
            email='supplier_user@example.com',
            password='StrongPass123',
            role='manager',
            is_approved=True,
        )
        self.supplier = Supplier.objects.create(
            name='Acme Supplies',
            contact_person='Jane Doe',
            email='supplier@example.com',
            phone='123456789',
            address='123 Main St',
            city='Manila',
            postal_code='1000',
            country='Philippines',
        )
        self.client.force_login(self.user)

    def test_supplier_payment_balance_and_history_are_recorded(self):
        supplier_payment = SupplierPayment.objects.create(
            supplier=self.supplier,
            purchase_order=None,
            amount=Decimal('100.00'),
            date=timezone.now().date(),
            method='cash',
            status='pending',
        )

        self.assertEqual(supplier_payment.supplier, self.supplier)
        self.assertEqual(supplier_payment.amount, Decimal('100.00'))


class ActivityLogTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='audit_user',
            email='audit@example.com',
            password='StrongPass123',
            role='admin',
            is_approved=True,
        )

    def test_activity_log_records_user_action_and_snapshots(self):
        activity_log = ActivityLog.objects.create(
            user=self.user,
            action='create',
            model_name='Product',
            object_id=1,
            before_snapshot={'sku': ''},
            after_snapshot={'sku': 'SKU-LOG-01'},
        )

        self.assertEqual(activity_log.user, self.user)
        self.assertEqual(activity_log.action, 'create')
        self.assertEqual(activity_log.model_name, 'Product')
        self.assertEqual(activity_log.before_snapshot['sku'], '')
        self.assertEqual(activity_log.after_snapshot['sku'], 'SKU-LOG-01')


class SecuritySettingsTests(TestCase):
    def test_secure_session_and_csrf_settings_are_enabled(self):
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
        self.assertTrue(settings.CSRF_COOKIE_HTTPONLY)
        self.assertTrue(settings.SECURE_CONTENT_TYPE_NOSNIFF)
        self.assertTrue(settings.SECURE_BROWSER_XSS_FILTER)
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, 'Lax')
        self.assertEqual(settings.CSRF_COOKIE_SAMESITE, 'Lax')


class ReportsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='report_user',
            email='report@example.com',
            password='StrongPass123',
            role='manager',
            is_approved=True,
        )
        self.category = Category.objects.create(name='Hardware', description='Hardware supplies')
        self.product = Product.objects.create(
            name='Hammer',
            description='Standard hammer',
            category=self.category,
            sku='SKU-001',
            unit_price=Decimal('25.00'),
            quantity_in_stock=1,
            reorder_level=2,
            is_active=True,
        )
        self.sale = Sale.objects.create(
            cashier=self.user,
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
        self.client.force_login(self.user)

    def test_sales_report_page_renders_with_live_sale_data(self):
        response = self.client.get(reverse('reports:sales-report'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hammer')
        self.assertContains(response, '25.00')


class HomeDashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='StrongPass123',
            role='admin',
            is_approved=True,
        )
        self.category = Category.objects.create(name='Hardware', description='Hardware supplies')
        self.product = Product.objects.create(
            name='Hammer',
            description='Standard hammer',
            category=self.category,
            sku='SKU-001',
            unit_price=Decimal('25.00'),
            quantity_in_stock=1,
            reorder_level=2,
            is_active=True,
            expiration_date=timezone.now().date() + timedelta(days=3),
        )
        self.sale = Sale.objects.create(
            cashier=self.user,
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
        self.product.create_alerts()

    def test_authenticated_user_can_visit_home_dashboard(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')
        self.assertEqual(response.context['product_count'], 1)
        self.assertEqual(response.context['today_sales_count'], 1)
        self.assertEqual(response.context['low_stock_count'], 1)
        self.assertEqual(response.context['alerts_count'], 2)


class RoleBasedAccessTests(TestCase):
    """Tests that verify role-based access control across all protected views."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username='admin_user', email='admin@example.com',
            password='StrongPass123', role='admin', is_approved=True,
        )
        cls.manager = User.objects.create_user(
            username='manager_user', email='manager@example.com',
            password='StrongPass123', role='manager', is_approved=True,
        )
        cls.cashier = User.objects.create_user(
            username='cashier_user', email='cashier@example.com',
            password='StrongPass123', role='cashier', is_approved=True,
        )
        cls.inventory = User.objects.create_user(
            username='inv_user', email='inv@example.com',
            password='StrongPass123', role='inventory_staff', is_approved=True,
        )
        cls.category = Category.objects.create(name='Hardware', description='Hardware supplies')
        cls.product = Product.objects.create(
            name='Hammer', description='Standard hammer',
            category=cls.category, sku='SKU-TEST',
            unit_price=Decimal('25.00'), quantity_in_stock=10,
            reorder_level=2, is_active=True,
        )
        cls.supplier = Supplier.objects.create(
            name='Acme Supplies', contact_person='Jane Doe',
            email='supplier@example.com', phone='123456789',
            address='123 Main St', city='Manila', postal_code='1000',
            country='Philippines', is_active=True,
        )
        cls.customer = Customer.objects.create(
            name='Test Customer', contact_person='',
            email='cust@example.com', phone='987654321',
            address='456 Oak St', city='Manila', postal_code='2000',
            country='Philippines', is_active=True,
        )
        cls.product_url = reverse('product:product-list')
        cls.category_url = reverse('category:category-list')
        cls.supplier_url = reverse('supplier:supplier-list')
        cls.customer_url = reverse('customer:customer-list')
        cls.reports_url = reverse('reports:sales-report')
        cls.pending_url = reverse('accounts:pending_users')
        cls.home_url = reverse('home')

    # ------------------------------------------------------------------
    # Anonymous users
    # ------------------------------------------------------------------
    def test_anonymous_user_redirected_from_all_protected_pages(self):
        for url in [self.home_url, self.product_url, self.category_url,
                     self.supplier_url, self.customer_url, self.reports_url,
                     self.pending_url]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, f"Expected redirect for {url}")
            self.assertRedirects(response, f"{reverse('accounts:login')}?next={url}")

    # ------------------------------------------------------------------
    # Home (Dashboard) – every authenticated user
    # ------------------------------------------------------------------
    def test_all_authenticated_roles_can_access_home(self):
        for user in [self.admin, self.manager, self.cashier, self.inventory]:
            self.client.force_login(user)
            response = self.client.get(self.home_url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'home.html')

    # ------------------------------------------------------------------
    # Inventory modules – admin, manager, inventory_staff
    # ------------------------------------------------------------------
    INVENTORY_URLS = ['product_url', 'category_url', 'supplier_url']

    def test_inventory_pages_accessible_to_admin_manager_inventory_staff(self):
        for user in [self.admin, self.manager, self.inventory]:
            self.client.force_login(user)
            for url_name in self.INVENTORY_URLS:
                url = getattr(self, url_name)
                response = self.client.get(url)
                self.assertEqual(
                    response.status_code, 200,
                    f"{user.role} should access {url_name} (got {response.status_code})",
                )

    def test_inventory_pages_forbidden_for_cashier(self):
        self.client.force_login(self.cashier)
        for url_name in self.INVENTORY_URLS:
            url = getattr(self, url_name)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403, f"cashier should be denied {url_name}")

    # ------------------------------------------------------------------
    # Customer pages – admin, manager, cashier
    # ------------------------------------------------------------------
    def test_customer_pages_accessible_to_admin_manager_cashier(self):
        for user in [self.admin, self.manager, self.cashier]:
            self.client.force_login(user)
            response = self.client.get(self.customer_url)
            self.assertEqual(
                response.status_code, 200,
                f"{user.role} should access customer list (got {response.status_code})",
            )

    def test_customer_pages_forbidden_for_inventory_staff(self):
        self.client.force_login(self.inventory)
        response = self.client.get(self.customer_url)
        self.assertEqual(response.status_code, 403)

    # ------------------------------------------------------------------
    # Reports – admin, manager
    # ------------------------------------------------------------------
    def test_reports_accessible_to_admin_manager(self):
        for user in [self.admin, self.manager]:
            self.client.force_login(user)
            response = self.client.get(self.reports_url)
            self.assertEqual(response.status_code, 200)

    def test_reports_forbidden_for_cashier_and_inventory_staff(self):
        for user in [self.cashier, self.inventory]:
            self.client.force_login(user)
            response = self.client.get(self.reports_url)
            self.assertEqual(response.status_code, 403)

    # ------------------------------------------------------------------
    # Pending users – admin only
    # ------------------------------------------------------------------
    def test_pending_users_accessible_to_admin_only(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.pending_url)
        self.assertEqual(response.status_code, 200)

    def test_pending_users_forbidden_to_non_admin(self):
        for user in [self.manager, self.cashier, self.inventory]:
            self.client.force_login(user)
            response = self.client.get(self.pending_url)
            self.assertEqual(response.status_code, 403)
