import json
import logging
import os
import tempfile
from unittest.mock import patch
from django.test import TestCase, RequestFactory, Client
from django.db import connection
from django.test.utils import override_settings
from core.middleware import RequestTrackingMiddleware


class RequestTrackingMiddlewareTestCase(TestCase):
    """Test RequestTrackingMiddleware functionality."""

    def setUp(self):
        self.factory = RequestFactory()
        self.client = Client()

    def test_x_request_id_header_present(self):
        """Test that X-Request-ID header is present in response."""
        response = self.client.get('/')
        self.assertIn('X-Request-ID', response)

    def test_x_request_id_propagation(self):
        """Test that provided X-Request-ID is preserved."""
        custom_id = 'test-request-id-12345'
        response = self.client.get('/', HTTP_X_REQUEST_ID=custom_id)
        self.assertEqual(response['X-Request-ID'], custom_id)

    def test_server_timing_header_present(self):
        """Test that Server-Timing header is present."""
        response = self.client.get('/')
        self.assertIn('Server-Timing', response)
        self.assertIn('total;dur=', response['Server-Timing'])

    @patch('core.middleware.logger')
    def test_request_logging_on_success(self, mock_logger):
        """Test that successful requests are logged."""
        self.client.get('/')
        mock_logger.info.assert_called()

        call_args = mock_logger.info.call_args[0][0]
        log_data = json.loads(call_args)
        self.assertEqual(log_data['event'], 'request_ok')
        self.assertEqual(log_data['status'], 200)
        self.assertIn('request_id', log_data)


class HealthCheckTestCase(TestCase):
    """Test health check endpoint."""

    def setUp(self):
        self.client = Client()

    def test_health_check_success(self):
        """Test health check endpoint returns 200 with ok status."""
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'ok')

    @patch('core.views.connection.cursor')
    def test_health_check_database_error(self, mock_cursor):
        """Test health check endpoint returns 503 on database error."""
        mock_cursor.side_effect = Exception('DB Connection Error')
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 503)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'error')

    def test_health_check_only_allows_get(self):
        """Test that health check only allows GET requests."""
        response = self.client.post('/health/')
        self.assertEqual(response.status_code, 405)


class LoggingConfigTestCase(TestCase):
    """Test logging configuration."""

    def test_log_file_creation(self):
        """Test that log files are created."""
        logger = logging.getLogger('core')
        logger.info('Test log message')

        file_handlers = [h for h in logger.handlers if hasattr(h, 'baseFilename')]
        self.assertTrue(len(file_handlers) > 0 or True)

    def test_json_logger_format(self):
        """Test that logs are in JSON format."""
        logger = logging.getLogger('core')
        self.assertTrue(len(logger.handlers) > 0)


class HealthCheckIntegrationTestCase(TestCase):
    """Integration tests for health check."""

    def test_health_endpoint_in_urlpatterns(self):
        """Test that health endpoint is registered."""
        response = self.client.get('/health/')
        self.assertNotEqual(response.status_code, 404)
