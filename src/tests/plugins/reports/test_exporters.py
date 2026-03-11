#
# Unit and integration tests for pretix.plugins.reports exporters.
# Coverage targets: exporters.py (line-rate 0.295), accountingreport.py (0.1677).
#
from datetime import datetime, time, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from django.core import mail as djmail
from django.utils.timezone import now
from django_scopes import scope
from freezegun import freeze_time

from pretix.base.models import (
    Event,
    Organizer,
    ScheduledEventExport,
    ScheduledOrganizerExport,
    User,
)
from pretix.base.services.export import run_scheduled_exports


# --- Fixtures ---


@pytest.fixture(scope="function")
def event():
    o = Organizer.objects.create(name="Dummy", slug="dummy")
    event = Event.objects.create(
        organizer=o,
        name="Dummy",
        slug="dummy",
        date_from=datetime(2023, 1, 19, 2, 30, 0, tzinfo=timezone.utc),
        plugins="pretix.plugins.banktransfer,pretix.plugins.reports",
    )
    o.settings.timezone = "Europe/Berlin"
    with scope(organizer=o):
        yield event


@pytest.fixture
def team(event):
    return event.organizer.teams.create(all_events=True, can_view_orders=True)


@pytest.fixture
def user(team):
    user = User.objects.create_user("dummy@dummy.dummy", "dummy")
    team.members.add(user)
    return user


# --- Unit tests: OverviewReport (Report base, _header_story, _filter_story, _table_story, _get_data) ---


@pytest.mark.django_db
def test_overview_report_identifier_and_verbose_name(event):
    """Unit test: OverviewReport identifier and verbose_name."""
    from pretix.plugins.reports.exporters import OverviewReport

    set_progress = MagicMock()
    ex = OverviewReport(event, event.organizer, set_progress)
    assert ex.identifier == "pdfreport"
    assert "overview" in str(ex.verbose_name).lower() or "PDF" in str(ex.verbose_name)


@pytest.mark.django_db
def test_overview_report_pagesize(event):
    """Unit test: OverviewReport pagesize property."""
    from pretix.plugins.reports.exporters import OverviewReport

    ex = OverviewReport(event, event.organizer, MagicMock())
    size = ex.pagesize
    assert size is not None
    assert len(size) == 2


@pytest.mark.django_db
def test_overview_report_get_data_returns_structure(event):
    """Unit test: _get_data returns (items_by_category, total) from order_overview."""
    from pretix.plugins.reports.exporters import OverviewReport

    ex = OverviewReport(event, event.organizer, MagicMock())
    form_data = {}
    items_by_category, total = ex._get_data(form_data)
    # order_overview returns List[Tuple[ItemCategory, List[Item]]], Dict
    assert isinstance(items_by_category, list)
    assert isinstance(total, dict)


@pytest.mark.django_db
def test_overview_report_get_data_with_date_range(event):
    """Unit test: _get_data with date_range and date_axis."""
    from pretix.plugins.reports.exporters import OverviewReport

    ex = OverviewReport(event, event.organizer, MagicMock())
    form_data = {"date_range": "year_this", "date_axis": "order_date", "skip_empty_lines": False}
    items_by_category, total = ex._get_data(form_data)
    assert isinstance(items_by_category, list)
    assert isinstance(total, dict)


# --- Unit tests: ReportExporter (accountingreport) describe_filters, _transaction_row_label ---


@pytest.mark.django_db
def test_report_exporter_identifier(event):
    """Unit test: ReportExporter identifier (single-event: pass event, not queryset)."""
    from pretix.plugins.reports.accountingreport import ReportExporter

    ex = ReportExporter(event, event.organizer, MagicMock())
    assert ex.identifier == "accountingreport"


@pytest.mark.django_db
def test_report_exporter_describe_filters_single_event(event):
    """Unit test: describe_filters for single event (no date range, no_testmode)."""
    from pretix.plugins.reports.accountingreport import ReportExporter

    ex = ReportExporter(event, event.organizer, MagicMock())
    form_data = {"date_range": "", "no_testmode": True}
    filters = ex.describe_filters(form_data)
    assert isinstance(filters, list)
    assert any("Event" in f or "event" in f.lower() for f in filters)


@pytest.mark.django_db
def test_report_exporter_describe_filters_with_date_range(event):
    """Unit test: describe_filters with date_range adds begin/end."""
    from pretix.plugins.reports.accountingreport import ReportExporter

    ex = ReportExporter(event, event.organizer, MagicMock())
    form_data = {"date_range": "year_this", "no_testmode": True}
    filters = ex.describe_filters(form_data)
    assert isinstance(filters, list)


@pytest.mark.django_db
def test_report_exporter_transaction_row_label_item(event):
    """Unit test: _transaction_row_label for item row."""
    from pretix.plugins.reports.accountingreport import ReportExporter

    ex = ReportExporter(event, event.organizer, MagicMock())
    r = {"item_id": 1, "item__name": "Ticket", "item__internal_name": None, "variation_id": None, "fee_type": None}
    assert ex._transaction_row_label(r) == "Ticket"


@pytest.mark.django_db
def test_report_exporter_transaction_row_label_fee(event):
    """Unit test: _transaction_row_label for fee type."""
    from pretix.plugins.reports.accountingreport import ReportExporter

    ex = ReportExporter(event, event.organizer, MagicMock())
    r = {"item_id": None, "fee_type": "payment", "internal_type": None}
    label = ex._transaction_row_label(r)
    assert label is not None and label != "?"


@pytest.mark.django_db
def test_order_tax_list_report_identifier(event):
    """Unit test: OrderTaxListReport identifier and sheets."""
    from pretix.plugins.reports.exporters import OrderTaxListReport

    ex = OrderTaxListReport(event, event.organizer, MagicMock())
    assert ex.identifier == "ordertaxeslist"
    sheets = ex.sheets
    assert "orders" in [s[0] for s in sheets]
    assert "countries" in [s[0] for s in sheets]
    assert "companies" in [s[0] for s in sheets]


@pytest.mark.django_db
def test_report_get_left_header_string_single_event(event):
    """Unit test: ReportlabExportMixin get_left_header_string for single event."""
    from pretix.plugins.reports.exporters import OverviewReport

    ex = OverviewReport(event, event.organizer, MagicMock())
    s = ex.get_left_header_string()
    assert event.organizer.name in s
    assert event.name in s


# --- Integration: scheduled export (E2E-style) ---


@pytest.mark.django_db(transaction=True)
@freeze_time("2023-01-18 03:00:00+01:00")
def test_event_scheduled_export_pdfreport_success(event, user, team):
    """Integration: scheduled event export pdfreport produces PDF and email."""
    djmail.outbox = []
    s = ScheduledEventExport(event=event, owner=user)
    s.export_identifier = "pdfreport"
    s.export_form_data = {}
    s.mail_subject = "Overview report"
    s.mail_template = "Your report is attached."
    s.schedule_rrule = "DTSTART:20230118T000000\nRRULE:FREQ=DAILY;INTERVAL=1;WKST=MO"
    s.schedule_rrule_time = time(2, 30, 0)
    s.schedule_next_run = now() - timedelta(minutes=5)
    s.error_counter = 0
    s.save()

    run_scheduled_exports(None)
    s.refresh_from_db()
    assert s.schedule_next_run > now()
    assert s.error_counter == 0
    assert len(djmail.outbox) == 1
    assert djmail.outbox[0].subject == "Overview report"
    assert len(djmail.outbox[0].attachments) == 1
    assert djmail.outbox[0].attachments[0][0] == "report-dummy.pdf"
    assert djmail.outbox[0].attachments[0][1][:4] == b"%PDF"


@pytest.mark.django_db(transaction=True)
@freeze_time("2023-01-18 03:00:00+01:00")
def test_organizer_scheduled_export_accountingreport_success(event, user, team):
    """Integration: scheduled organizer export accountingreport produces PDF."""
    djmail.outbox = []
    s = ScheduledOrganizerExport(organizer=event.organizer, owner=user)
    s.export_identifier = "accountingreport"
    s.export_form_data = {"no_testmode": True}
    s.mail_subject = "Accounting report"
    s.mail_template = "Please find the accounting report attached."
    s.schedule_rrule = "DTSTART:20230118T000000\nRRULE:FREQ=DAILY;INTERVAL=1;WKST=MO"
    s.schedule_rrule_time = time(2, 30, 0)
    s.schedule_next_run = now() - timedelta(minutes=5)
    s.error_counter = 0
    s.save()

    run_scheduled_exports(None)
    s.refresh_from_db()
    assert s.error_counter == 0
    assert len(djmail.outbox) == 1
    assert len(djmail.outbox[0].attachments) == 1
    assert djmail.outbox[0].attachments[0][1][:4] == b"%PDF"
