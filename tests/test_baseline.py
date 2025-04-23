# tests/test_baseline.py
import pytest
import baseline
from baseline import route_message, TEMPLATES

@pytest.fixture
def order_info():
    return {
        "order_id": "ID1",
        "order_date": "2025-04-20",
        "user_id": "U1"
    }

class DummyClient:
    def __init__(self, resp):
        self.resp = resp
    def track(self, order_id):
        assert order_id == "ID1"
        return self.resp
    def cancel(self, order_id):
        assert order_id == "ID1"
        return self.resp

@pytest.mark.parametrize("text, setup, expected", [
    # tracking success
    (
        "please track my order",
        lambda mp: mp.setattr(baseline, "OrderTrackingClient", lambda: DummyClient({"status":"pending","order_id":"ID1","message":"Simulated tracking: pending."})),
        ("track_order", TEMPLATES["track"].format(order_id="ID1", status="pending"))
    ),
    # tracking error
    (
        "what's the status?",
        lambda mp: mp.setattr(baseline, "OrderTrackingClient", lambda: DummyClient({"status":"error","order_id":"ID1","message":"Simulated tracking: error."})),
        ("track_order", TEMPLATES["error"].format(error="Simulated tracking: error."))
    ),
    # cancel denied by policy
    (
        "cancel order",
        lambda mp: (
            mp.setattr(baseline, "can_cancel", lambda d, u: False),
            mp.setattr(baseline, "OrderCancellationClient", lambda: DummyClient({"status":"ok","order_id":"ID1","message": "Simulated cancellation failure."}))
        ),
        ("cancel_order", TEMPLATES["cancel_fail"].format(order_id="ID1"))
    ),
    # cancel success
    (
        "please cancel",
        lambda mp: (
            mp.setattr(baseline, "can_cancel", lambda d, u: True),
            mp.setattr(baseline, "OrderCancellationClient", lambda: DummyClient({"status":"ok","order_id":"ID1","message": "Simulated cancellation successful."}))
        ),
        ("cancel_order", TEMPLATES["cancel_success"].format(order_id="ID1"))
    ),
    # cancel API error
    (
        "i want to cancel",
        lambda mp: (
            mp.setattr(baseline, "can_cancel", lambda d, u: True),
            mp.setattr(baseline, "OrderCancellationClient", lambda: DummyClient({"status":"error","order_id":"ID1","message":"Down"}))
        ),
        ("cancel_order", TEMPLATES["error"].format(error="Down"))
    ),
])
def test_route_message_all_paths(monkeypatch, order_info, text, setup, expected):
    # default policy allow
    monkeypatch.setattr(baseline, "can_cancel", lambda d, u: True)
    # apply test-specific stubs
    setup(monkeypatch)
    tool, resp = expected
    result = route_message(text, order_info)
    assert result.tool_name == tool
    assert result.final_response == resp

def test_route_message_no_match(order_info):
    result = route_message("hello there", order_info)
    assert result.tool_name == "none"
    assert result.final_response == "Sorry, I didn't understand that."