"""Run with: uv run python -m tests.test_garmin_sync"""

from datetime import date

from src import garmin_sync


class FakeClient:
    def __init__(self, n_activities: int):
        self.activities = [{"activityId": i} for i in range(n_activities)]
        self.ranges: list[tuple[date, date]] = []

    def search_activities(self, *, start, limit, start_date, end_date):
        return self.activities[start:start + limit]

    def get_daily_summaries(self, s, e):
        self.ranges.append((s, e))
        return {"data": [{
            "calendarDate": s.isoformat(),
            "heartRate": {"restingValue": 40},
            "movement": {"steps": {"value": 11001}},
            "pulseOx": {"avgValue": 97, "minValue": 88},
            "bodyBattery": None,
        }]}

    def get_daily_sleep_summaries(self, s, e):
        return [
            {"calendarDate": s.isoformat(), "sleepScores": {"overall": {"value": 99}}, "sleepTimeSeconds": 32640},
            {"calendarDate": None, "sleepTimeSeconds": 1},
        ]

    def get_daily_hrv_summaries(self, s, e):
        return {"hrvSummaries": [{"calendarDate": s.isoformat(), "lastNightAvg": 70}]}

    def get_weight_measurements(self, s, e):
        return {"dailyWeightSummaries": [{"summaryDate": s.isoformat(), "latestWeight": {"weight": 77500.0}}]}


def test_fetch_activities_paginates():
    assert len(garmin_sync.fetch_activities(FakeClient(250), date(2026, 1, 1), date(2026, 3, 1))) == 250
    assert len(garmin_sync.fetch_activities(FakeClient(100), date(2026, 1, 1), date(2026, 3, 1))) == 100


def test_fetch_wellness_chunks_and_maps():
    client = FakeClient(0)
    wellness = garmin_sync.fetch_wellness(client, date(2026, 8, 3), date(2026, 10, 31))

    assert client.ranges[0] == (date(2026, 8, 3), date(2026, 8, 30))
    assert client.ranges[-1][1] == date(2026, 10, 31)
    assert all((e - s).days < garmin_sync.CHUNK_DAYS for s, e in client.ranges)

    assert wellness["2026-08-03"] == {
        "resting_hr": 40, "steps": 11001, "avg_spo2": 97, "lowest_spo2": 88,
        "sleep_score": 99, "sleep_duration_s": 32640, "hrv": 70, "weight_kg": 77.5,
    }
    assert None not in wellness


if __name__ == "__main__":
    test_fetch_activities_paginates()
    test_fetch_wellness_chunks_and_maps()
    print("ok")
