# -*- coding: utf-8 -*-
"""The safety claim about crash reports, written as assertions.

The module tells users that reports carry nothing about their vehicles,
customers or amounts. That promise is only worth what the tests are worth, so
these raise exceptions whose messages are stuffed with exactly the things that
must never travel -- a VIN, a plate, a customer name, an order number, a sum --
and then assert that none of them appear anywhere in the serialised payload.

That is the test that has to keep passing. If someone later decides the error
text would be useful after all, this file is what stops it.

There is a second promise here that a bank connector does not make: most
exceptions in this module are the module *talking to the user* (``UserError``
and family), not bugs. Those must never be reported -- both because they are
noise and because that is exactly where the customer data lives. The decorator
tests below are the guarantee for that.
"""

import json
import sys
from unittest.mock import patch

from odoo import SUPERUSER_ID, api
from odoo.addons.adealer.models import error_report as reporting
from odoo.addons.adealer.models.error_report import report_errors
from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged

# Every one of these is a real leak if it ever shows up in a report.
SECRETS = [
    "WBAJB1C50BC123456",  # a VIN
    "AA1234BB",  # a licence plate
    "Іван Петренко",  # a customer
    "ТОВ «Ромашка»",  # a company
    "SO0042",  # an order number
    "350000.00",  # a sum of money
    "buhgalter@example.com",  # an address
]

POISONED_MESSAGE = (
    "Cannot sell car VIN WBAJB1C50BC123456 (plate AA1234BB) "
    "to Іван Петренко / ТОВ «Ромашка», order SO0042, "
    "amount 350000.00, contact buhgalter@example.com"
)


class PoisonedError(Exception):
    """An exception carrying every kind of data that must not be reported."""


@tagged("post_install", "-at_install")
class TestErrorReport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Report = cls.env["adealer.error.report"]
        cls.env["ir.config_parameter"].sudo().set_param(reporting.PARAM_CONSENT, "on")

    def _vals(self, operation="import_vehicles"):
        """Build report values from a live exception, without touching the DB."""
        try:
            raise PoisonedError(POISONED_MESSAGE)
        except PoisonedError:
            return self.Report._build_vals(*sys.exc_info(), operation, self.env.company)

    def _report(self, **kwargs):
        return self.Report.create(self._vals(**kwargs))

    # ------------------------------------------------------------------
    # The promise: no customer data ever leaves
    # ------------------------------------------------------------------
    def test_payload_carries_no_customer_data(self):
        body = json.dumps(self._report()._payload(), ensure_ascii=False)
        for secret in SECRETS:
            self.assertNotIn(secret, body, "%r leaked into the error report" % secret)

    def test_error_text_is_never_sent(self):
        """Not even a fragment: the type travels, the message does not."""
        report = self._report()
        body = json.dumps(report._payload(), ensure_ascii=False)
        self.assertNotIn("Cannot sell car", body)
        self.assertEqual(report.error_type, "PoisonedError")

    def test_displayed_payload_is_what_gets_sent(self):
        """The form shows the request body itself, so the field cannot drift."""
        report = self._report()
        self.assertEqual(json.loads(report.payload), report._payload())

    def test_module_is_adealer(self):
        self.assertEqual(self._report()._payload()["module"], "adealer")

    def test_paths_do_not_expose_the_filesystem(self):
        report = self._report()
        self.assertTrue(report.frames, "a report with no frames diagnoses nothing")
        for frame in report.frames.splitlines():
            self.assertNotIn(":\\", frame, "a Windows drive path survived")
            self.assertNotIn(":/", frame, "a Windows drive path survived")
            self.assertFalse(frame.startswith("/"), "an absolute path survived")
            self.assertNotIn("home/", frame, "a home directory survived")

    def test_frames_still_point_at_the_bug(self):
        """Redaction has to leave enough to find the line that failed."""
        report = self._report()
        last = report.frames.splitlines()[-1]
        self.assertIn("test_error_report.py", last)
        self.assertIn(" in _vals", last)

    def test_short_path_keeps_the_module_and_drops_the_rest(self):
        self.assertEqual(
            reporting._short_path(
                r"C:\Users\ivan\odoo\my_addons\adealer\models\document_chain.py"
            ),
            "adealer/models/document_chain.py",
        )
        self.assertEqual(
            reporting._short_path("/home/ivan/.venv/lib/requests/adapters.py"),
            "requests/adapters.py",
        )

    def test_http_status_travels_but_body_does_not(self):
        """A status code is three digits and no customer data -- keep it."""

        class Response:
            status_code = 429
            text = POISONED_MESSAGE

        class Refused(Exception):
            response = Response()

        try:
            raise Refused(POISONED_MESSAGE)
        except Refused:
            vals = self.Report._build_vals(*sys.exc_info(), "update_from_git", self.env.company)
        self.assertEqual(vals["http_status"], 429)
        body = json.dumps(self.Report.create(vals)._payload(), ensure_ascii=False)
        for secret in SECRETS:
            self.assertNotIn(secret, body)

    # ------------------------------------------------------------------
    # The decorator: talking-to-the-user errors are never reported
    # ------------------------------------------------------------------
    def test_user_errors_are_not_reported(self):
        """UserError is the module talking to the user -- pass it through, say nothing.

        This is the whole reason the decorator exists in this module and not in a
        bank connector: a missing VIN is a conversation, not a bug, and its text
        holds the very data we refuse to send.
        """
        @report_errors("probe-expected")
        def boom(_rec):
            raise UserError("VIN WBAJB1C50BC123456 not filled for Іван Петренко")

        with patch.object(type(self.Report), "_capture", return_value=1) as cap:
            with self.assertRaises(UserError):
                boom(self.Report)
        cap.assert_not_called()

    def test_validation_errors_are_not_reported(self):
        @report_errors("probe-expected")
        def boom(_rec):
            raise ValidationError("order SO0042 has no mechanic")

        with patch.object(type(self.Report), "_capture", return_value=1) as cap:
            with self.assertRaises(ValidationError):
                boom(self.Report)
        cap.assert_not_called()

    def test_unexpected_errors_are_reported(self):
        """A real bug (KeyError, AttributeError, ...) is captured and re-raised."""
        @report_errors("probe-unexpected")
        def boom(_rec):
            raise KeyError("WBAJB1C50BC123456")

        with patch.object(type(self.Report), "_capture", return_value=1) as cap:
            with self.assertRaises(KeyError):
                boom(self.Report)
        cap.assert_called_once_with("probe-unexpected")

    def test_decorator_preserves_the_return_value(self):
        @report_errors("probe-ok")
        def ok(_rec):
            return {"type": "ir.actions.act_window_closed"}

        self.assertEqual(ok(self.Report), {"type": "ir.actions.act_window_closed"})

    def test_reporting_failure_never_masks_the_real_error(self):
        """If queuing the report itself blows up, the original error still wins."""
        @report_errors("probe-unexpected")
        def boom(_rec):
            raise KeyError("real bug")

        with patch.object(type(self.Report), "_capture", side_effect=RuntimeError("collector down")):
            with self.assertRaises(KeyError):
                boom(self.Report)

    # ------------------------------------------------------------------
    # Consent
    # ------------------------------------------------------------------
    def test_nothing_is_queued_without_consent(self):
        self.env["ir.config_parameter"].sudo().set_param(reporting.PARAM_CONSENT, "off")
        try:
            raise PoisonedError(POISONED_MESSAGE)
        except PoisonedError:
            self.assertFalse(self.Report._capture("import_vehicles"))

    def test_unset_consent_is_not_consent(self):
        """A database that was never asked must behave as if it said no."""
        self.env["ir.config_parameter"].sudo().set_param(reporting.PARAM_CONSENT, False)
        try:
            raise PoisonedError(POISONED_MESSAGE)
        except PoisonedError:
            self.assertFalse(self.Report._capture("import_vehicles"))

    def test_cron_sends_nothing_without_consent(self):
        report = self._report()
        self.env["ir.config_parameter"].sudo().set_param(reporting.PARAM_CONSENT, "off")
        self.Report._cron_send_reports()
        self.assertEqual(report.state, "pending")
        self.assertEqual(report.attempts, 0)

    # ------------------------------------------------------------------
    # Volume
    # ------------------------------------------------------------------
    def test_different_failures_are_separate_reports(self):
        first = self._vals(operation="import_vehicles")
        second = self._vals(operation="import_partners")
        self.assertNotEqual(first["fingerprint"], second["fingerprint"])

    def test_capture_needs_a_live_exception(self):
        """Reporting sits on the failure path; it must not add a second failure."""
        self.assertFalse(self.Report._capture("import_vehicles"))


@tagged("post_install", "-at_install")
class TestErrorReportOutOfBand(TransactionCase):
    """``_capture`` commits on its own connection, so it needs its own test.

    Nothing here can be asserted through ``self.env``: the row is written by a
    different transaction and this one's snapshot predates it. So the check runs
    on a fresh cursor -- and, because those rows really are committed, cleans up
    after itself rather than relying on the test rollback.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Report = cls.env["adealer.error.report"]
        # No commit here, and none is needed: consent is read on the caller's
        # cursor before the second one is opened. Odoo forbids committing inside
        # a test anyway, which is a good rule -- it would break the rollback.
        cls.env["ir.config_parameter"].sudo().set_param(reporting.PARAM_CONSENT, "on")
        cls.addClassCleanup(cls._drop_committed_reports)

    @classmethod
    def _drop_committed_reports(cls):
        with cls.env.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env["adealer.error.report"].search(
                [("error_type", "=", "PoisonedError")]
            ).unlink()

    def _capture(self, operation):
        # Each test passes its own operation on purpose. These rows are really
        # committed, so unlike every other test they are not rolled back between
        # methods -- sharing a fingerprint would make one test's count leak into
        # the next, which is exactly the bug that caught this out the first time.
        try:
            raise PoisonedError(POISONED_MESSAGE)
        except PoisonedError:
            return self.Report._capture(operation)

    def _read(self, report_id):
        with self.env.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            return env["adealer.error.report"].browse(report_id).read(
                ["fingerprint", "occurrences", "error_type"]
            )[0]

    def test_capture_commits_independently_of_the_caller(self):
        """The whole reason for the second cursor.

        Reading the row from a connection that knows nothing of this test's
        transaction is the proof: it is already committed, so the rollback that
        follows every failed operation cannot take the report down with it.
        """
        report_id = self._capture("probe-commit")
        self.assertTrue(report_id)
        self.assertEqual(self._read(report_id)["error_type"], "PoisonedError")

    def test_install_id_exists_before_the_first_send(self):
        """The form must show the body that will actually travel.

        The id used to be minted by the sending cron, so a report opened while
        still queued displayed an empty one and then went out with a value --
        a small lie in exactly the field that exists to be trustworthy.
        """
        self._capture("probe-install-id")
        with self.env.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            value = env["ir.config_parameter"].get_param(reporting.PARAM_INSTALL_ID)
        self.assertTrue(value, "install_id should exist as soon as a report is queued")

    def test_same_failure_is_counted_not_requeued(self):
        """A bug firing in a loop must not become a thousand reports."""
        first = self._capture("probe-dedup")
        for _unused in range(4):
            self.assertEqual(self._capture("probe-dedup"), first)
        self.assertEqual(self._read(first)["occurrences"], 5)
