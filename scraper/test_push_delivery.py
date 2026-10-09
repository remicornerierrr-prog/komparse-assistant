"""Tests for multi-browser push delivery and per-device retry behavior."""
from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from unittest.mock import patch

# This test exercises notification orchestration without making real push
# requests or requiring the Supabase client in lightweight development setups.
try:
    from pywebpush import WebPushException as _WebPushException  # noqa: F401
except ImportError:
    pywebpush_stub = types.ModuleType("pywebpush")

    class WebPushException(Exception):
        pass

    pywebpush_stub.WebPushException = WebPushException
    pywebpush_stub.webpush = lambda **kwargs: None
    sys.modules["pywebpush"] = pywebpush_stub

try:
    from supabase import Client as _SupabaseClient, create_client as _create_client  # noqa: F401
except ImportError:
    supabase_stub = types.ModuleType("supabase")
    supabase_stub.Client = object
    supabase_stub.create_client = lambda *args, **kwargs: None
    sys.modules["supabase"] = supabase_stub

from scraper import main as pipeline  # noqa: E402


class FakeResponse:
    def __init__(self, data=None):
        self.data = data or []


class FakeQuery:
    def __init__(self, backend, table):
        self.backend = backend
        self.table_name = table
        self.action = "select"
        self.filters = {}
        self.payload = None
        self.limit_count = None

    def select(self, *args, **kwargs):
        self.action = "select"
        return self

    def eq(self, column, value):
        self.filters[column] = value
        return self

    def limit(self, count):
        self.limit_count = count
        return self

    def order(self, *args, **kwargs):
        return self

    def upsert(self, payload, **kwargs):
        self.action = "upsert"
        self.payload = dict(payload)
        return self

    def delete(self):
        self.action = "delete"
        return self

    def execute(self):
        rows = self.backend.tables.setdefault(self.table_name, [])

        if self.action == "select":
            selected = [
                dict(row)
                for row in rows
                if all(row.get(k) == v for k, v in self.filters.items())
            ]
            if self.limit_count is not None:
                selected = selected[: self.limit_count]
            return FakeResponse(selected)

        if self.action == "upsert":
            key = (
                self.payload.get("match_id"),
                self.payload.get("push_subscription_id"),
            )
            existing = next(
                (
                    row for row in rows
                    if (row.get("match_id"), row.get("push_subscription_id")) == key
                ),
                None,
            )
            if existing:
                existing.update(self.payload)
            else:
                new_row = dict(self.payload)
                new_row["id"] = len(rows) + 1
                rows.append(new_row)
            return FakeResponse([dict(existing or rows[-1])])

        if self.action == "delete":
            self.backend.tables[self.table_name] = [
                row for row in rows
                if not all(row.get(k) == v for k, v in self.filters.items())
            ]
            return FakeResponse([])

        raise AssertionError(f"Unsupported fake DB action: {self.action}")


class FakeSupabase:
    def __init__(self, subscriptions):
        self.tables = {
            "push_subscriptions": [dict(row) for row in subscriptions],
            "match_push_deliveries": [],
        }

    def table(self, table_name):
        return FakeQuery(self, table_name)


class MultiBrowserPushTests(unittest.TestCase):
    def setUp(self):
        for key in pipeline.NOTIFICATION_STATS:
            pipeline.NOTIFICATION_STATS[key] = 0

    def make_subscription(self, subscription_id, label):
        endpoint = f"https://push.example.test/{subscription_id}"
        return {
            "id": subscription_id,
            "user_id": "user-1",
            "endpoint": endpoint,
            "device_id": f"device-{subscription_id}",
            "device_label": label,
            "subscription_json": {
                "endpoint": endpoint,
                "keys": {"p256dh": "test", "auth": "test"},
            },
        }

    def test_sends_to_all_registered_browsers(self):
        supabase = FakeSupabase([
            self.make_subscription(1, "Chrome · Windows"),
            self.make_subscription(2, "Firefox · Linux"),
        ])

        with patch.object(
            pipeline,
            "send_push_notification",
            side_effect=[(True, 201, None), (True, 201, None)],
        ) as send:
            result = pipeline.notify_match_user(
                supabase,
                "user-1",
                {"title": "Test offer", "source_url": "https://komparse.de/test"},
                77,
            )

        self.assertTrue(result)
        self.assertEqual(send.call_count, 2)
        deliveries = supabase.tables["match_push_deliveries"]
        self.assertEqual(len(deliveries), 2)
        self.assertTrue(all(row["status"] == "sent" for row in deliveries))

    def test_retries_only_the_browser_that_failed(self):
        supabase = FakeSupabase([
            self.make_subscription(1, "Chrome · Windows"),
            self.make_subscription(2, "Firefox · Linux"),
        ])
        offer = {"title": "Test offer", "source_url": "https://komparse.de/test"}

        with patch.object(
            pipeline,
            "send_push_notification",
            side_effect=[(True, 201, None), (False, 503, "temporary error")],
        ) as send_first:
            result_first = pipeline.notify_match_user(
                supabase, "user-1", offer, 88
            )

        self.assertFalse(result_first)
        self.assertEqual(send_first.call_count, 2)

        with patch.object(
            pipeline,
            "send_push_notification",
            return_value=(True, 201, None),
        ) as send_retry:
            result_retry = pipeline.notify_match_user(
                supabase, "user-1", offer, 88
            )

        self.assertTrue(result_retry)
        # The first browser was already served and is not sent a duplicate.
        self.assertEqual(send_retry.call_count, 1)
        deliveries = supabase.tables["match_push_deliveries"]
        self.assertEqual(len(deliveries), 2)
        self.assertTrue(all(row["status"] == "sent" for row in deliveries))
        self.assertEqual(
            sorted(row["attempts"] for row in deliveries),
            [1, 2],
        )


if __name__ == "__main__":
    unittest.main()
