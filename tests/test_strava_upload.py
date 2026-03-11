import pytest
import responses

from sync_onelap_strava.strava_client import StravaClient, StravaPermanentError


@responses.activate
def test_upload_fit_and_poll_until_ready(tmp_path):
    fit_file = tmp_path / "sample.fit"
    fit_file.write_bytes(b"fit-bytes")

    responses.add(
        responses.POST,
        "https://www.strava.com/api/v3/uploads",
        json={"id": 123},
        status=201,
    )
    responses.add(
        responses.GET,
        "https://www.strava.com/api/v3/uploads/123",
        json={"status": "processing", "error": None, "activity_id": None},
        status=200,
    )
    responses.add(
        responses.GET,
        "https://www.strava.com/api/v3/uploads/123",
        json={"status": "ready", "error": None, "activity_id": 456},
        status=200,
    )

    client = StravaClient(
        client_id="id",
        client_secret="secret",
        refresh_token="refresh",
        access_token="token",
        expires_at=9999999999,
    )

    upload_id = client.upload_fit(fit_file)
    result = client.poll_upload(upload_id, max_attempts=3, poll_interval_seconds=0)

    assert upload_id == 123
    assert result["activity_id"] == 456


@responses.activate
def test_upload_fit_retries_on_5xx(tmp_path):
    fit_file = tmp_path / "sample.fit"
    fit_file.write_bytes(b"fit-bytes")

    responses.add(
        responses.POST,
        "https://www.strava.com/api/v3/uploads",
        json={"message": "server error"},
        status=500,
    )
    responses.add(
        responses.POST,
        "https://www.strava.com/api/v3/uploads",
        json={"id": 321},
        status=201,
    )

    client = StravaClient(
        client_id="id",
        client_secret="secret",
        refresh_token="refresh",
        access_token="token",
        expires_at=9999999999,
    )

    upload_id = client.upload_fit(fit_file, retries=2, backoff_seconds=0)

    assert upload_id == 321
    assert len(responses.calls) == 2


@responses.activate
def test_upload_fit_includes_strava_error_payload_on_4xx(tmp_path):
    fit_file = tmp_path / "sample.fit"
    fit_file.write_bytes(b"fit-bytes")

    responses.add(
        responses.POST,
        "https://www.strava.com/api/v3/uploads",
        json={
            "message": "Bad Request",
            "errors": [{"resource": "Upload", "field": "file", "code": "invalid"}],
        },
        status=400,
    )

    client = StravaClient(
        client_id="id",
        client_secret="secret",
        refresh_token="refresh",
        access_token="token",
        expires_at=9999999999,
    )

    with pytest.raises(StravaPermanentError) as exc:
        client.upload_fit(fit_file)

    message = str(exc.value)
    assert "400" in message
    assert "Bad Request" in message
    assert "invalid" in message
