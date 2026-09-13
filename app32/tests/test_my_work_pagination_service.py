from services.my_work.pagination_service import (
    DEFAULT_ACTIVITIES_PER_PAGE,
    MAX_ACTIVITIES_PER_PAGE,
    paginate_activities,
)


def test_my_work_pagination_caps_page_size_and_preserves_total():
    activities = [{"id": index} for index in range(205)]

    payload = paginate_activities(activities, page=1, per_page=999)

    assert payload["per_page"] == MAX_ACTIVITIES_PER_PAGE
    assert len(payload["items"]) == MAX_ACTIVITIES_PER_PAGE
    assert payload["total"] == 205
    assert payload["has_more"] is True


def test_my_work_pagination_normalizes_invalid_values():
    payload = paginate_activities([{"id": 1}], page="invalid", per_page=0)

    assert payload["page"] == 1
    assert payload["per_page"] == 1
    assert payload["items"] == [{"id": 1}]
    assert payload["has_more"] is False


def test_my_work_pagination_default_is_bounded():
    payload = paginate_activities([], page=1, per_page=None)

    assert payload["per_page"] == DEFAULT_ACTIVITIES_PER_PAGE
