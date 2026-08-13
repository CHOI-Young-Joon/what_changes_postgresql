from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model


class HealthViewTests(TestCase):
    def test_health_reports_database_up(self):
        response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy", "database": "up"})


class AdminAccessTests(TestCase):
    def test_admin_requires_authentication_and_staff_role(self):
        admin_url = reverse("admin:index")
        anonymous_response = self.client.get(admin_url)
        self.assertEqual(anonymous_response.status_code, 302)
        self.assertIn(reverse("admin:login"), anonymous_response.url)

        user_model = get_user_model()
        regular_user = user_model.objects.create_user(username="regular", password="test-password")
        self.client.force_login(regular_user)
        regular_response = self.client.get(admin_url)
        self.assertEqual(regular_response.status_code, 302)

        staff_user = user_model.objects.create_user(username="staff", password="test-password", is_staff=True)
        self.client.force_login(staff_user)
        staff_response = self.client.get(admin_url)
        self.assertEqual(staff_response.status_code, 200)
