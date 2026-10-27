from datetime import date, timedelta

from app import finance


def test_render_template_fills_every_field():
    target = {
        "child_name": "Imron Rahimov", "parent_name": "Xurshid aka", "debt": 1850000,
        "due_date": "2026-11-10", "group_name": "Yulduzcha",
    }
    text = finance.render_template(
        "{childName}/{parentName}/{amount}/{dueDate}/{group}", target
    )
    assert "Imron Rahimov" in text
    assert "Xurshid aka" in text
    assert "so'm" in text
    assert "10-noyabr" in text
    assert "Yulduzcha" in text


def test_reminder_targets_respects_the_before_after_window():
    today = date(2026, 11, 10)
    settings = {"days_before": 3, "days_after": 2, "times": ["09:00"], "template": finance.DEFAULT_TEMPLATE}

    def row(invoice_id, due_offset):
        due = today + timedelta(days=due_offset)
        return {
            "invoice_id": invoice_id, "due_date": due.isoformat(), "debt": 1000,
            "child_name": "X", "parent_name": "Y", "parent_chat_id": 1, "group_name": "G",
        }

    offset_by_id = {"a": -5, "b": -2, "c": 0, "d": 2, "e": 5}

    class FakeConn:
        def execute(self, *_a, **_k):
            class R:
                def fetchall(_self):
                    return [row(iid, off) for iid, off in offset_by_id.items()]
            return R()

    targets = finance.reminder_targets(FakeConn(), "org", settings, today=today)
    offsets = sorted(offset_by_id[t["invoice_id"]] for t in targets)
    assert offsets == [-2, 0, 2]


def test_save_and_get_reminder_settings_round_trip(client, auth_headers):
    headers = auth_headers("accountant")
    payload = {
        "enabled": True, "days_before": 4, "days_after": 6,
        "times": ["09:00", "18:30"], "template": finance.DEFAULT_TEMPLATE,
    }
    res = client.put("/api/v1/billing/reminders", json=payload, headers=headers)
    assert res.status_code == 200
    got = client.get("/api/v1/billing/reminders", headers=headers).json()["settings"]
    assert got["enabled"] is True
    assert got["days_before"] == 4
    assert got["times"] == ["09:00", "18:30"]


def test_reminders_rejects_too_many_send_times(client, auth_headers):
    payload = {
        "enabled": True, "days_before": 1, "days_after": 1,
        "times": [f"0{i}:00" for i in range(7)], "template": finance.DEFAULT_TEMPLATE,
    }
    res = client.put("/api/v1/billing/reminders", json=payload, headers=auth_headers("accountant"))
    assert res.status_code == 400


def test_reminders_rejects_malformed_time(client, auth_headers):
    payload = {
        "enabled": True, "days_before": 1, "days_after": 1,
        "times": ["9am"], "template": finance.DEFAULT_TEMPLATE,
    }
    res = client.put("/api/v1/billing/reminders", json=payload, headers=auth_headers("accountant"))
    assert res.status_code == 400


def test_director_can_view_and_change_reminder_settings(client, auth_headers):
    # billing.remind is a FINANCE permission: super_admin, director, accountant.
    assert client.get("/api/v1/billing/reminders", headers=auth_headers("director")).status_code == 200
    payload = {"enabled": False, "days_before": 1, "days_after": 1, "times": ["09:00"], "template": finance.DEFAULT_TEMPLATE}
    res = client.put("/api/v1/billing/reminders", json=payload, headers=auth_headers("director"))
    assert res.status_code == 200


def test_teacher_cannot_view_or_change_reminder_settings(client, auth_headers):
    assert client.get("/api/v1/billing/reminders", headers=auth_headers("teacher")).status_code == 403
    payload = {"enabled": False, "days_before": 1, "days_after": 1, "times": ["09:00"], "template": finance.DEFAULT_TEMPLATE}
    res = client.put("/api/v1/billing/reminders", json=payload, headers=auth_headers("teacher"))
    assert res.status_code == 403
