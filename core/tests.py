from django.test import TestCase
from django.urls import reverse


class HealthViewTests(TestCase):
    def test_health_reports_database_up(self):
        response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy", "database": "up"})
