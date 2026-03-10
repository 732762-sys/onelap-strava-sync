from datetime import date

import responses

from sync_onelap_strava.onelap_client import OneLapClient


@responses.activate
def test_list_fit_activities_filters_since_date():
    responses.add(
        responses.GET,
        "https://www.onelap.cn/api/activities",
        json={
            "data": [
                {
                    "id": "a1",
                    "start_time": "2026-03-06T08:00:00Z",
                    "fit_url": "/fit/a1.fit",
                },
                {
                    "id": "a2",
                    "start_time": "2026-03-08T08:00:00Z",
                    "fit_url": "/fit/a2.fit",
                },
            ]
        },
        status=200,
    )
    c = OneLapClient(base_url="https://www.onelap.cn", username="u", password="p")
    items = c.list_fit_activities(since=date(2026, 3, 7), limit=50)
    assert [i.activity_id for i in items] == ["a2"]
