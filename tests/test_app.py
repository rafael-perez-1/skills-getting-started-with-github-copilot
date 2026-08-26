from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src.app import activities, app


client = TestClient(app)


@pytest.fixture(autouse=True)
def restore_activities():
    original_activities = deepcopy(activities)
    yield
    activities.clear()
    activities.update(original_activities)


def test_root_redirects_to_static_index():
    # Arrange
    test_client = TestClient(app, follow_redirects=False)

    # Act
    response = test_client.get("/")

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities_returns_all_activity_details():
    # Arrange
    expected_fields = {"description", "schedule", "max_participants", "participants"}

    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    response_activities = response.json()
    assert set(response_activities) == set(activities)
    assert all(expected_fields <= set(activity) for activity in response_activities.values())


def test_signup_adds_student_and_returns_confirmation():
    # Arrange
    activity_name = "Chess Club"
    email = "new.student@mergington.edu"

    # Act
    response = client.post(f"/activities/{activity_name}/signup", params={"email": email})

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": f"Signed up {email} for {activity_name}"}
    assert email in activities[activity_name]["participants"]


def test_signup_rejects_unknown_activity():
    # Arrange
    activity_name = "Unknown Club"

    # Act
    response = client.post(f"/activities/{activity_name}/signup", params={"email": "student@example.com"})

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}


def test_signup_rejects_duplicate_student():
    # Arrange
    activity_name = "Chess Club"
    email = activities[activity_name]["participants"][0]

    # Act
    response = client.post(f"/activities/{activity_name}/signup", params={"email": email})

    # Assert
    assert response.status_code == 400
    assert response.json() == {"detail": "Student already signed up for this activity"}
    assert activities[activity_name]["participants"].count(email) == 1


def test_signup_rejects_full_activity():
    # Arrange
    activity_name = "Chess Club"
    activity = activities[activity_name]
    activity["participants"] = ["student@example.com"] * activity["max_participants"]

    # Act
    response = client.post(
        f"/activities/{activity_name}/signup",
        params={"email": "new.student@example.com"},
    )

    # Assert
    assert response.status_code == 400
    assert response.json() == {"detail": "Activity is full"}
    assert len(activity["participants"]) == activity["max_participants"]


def test_signup_requires_email():
    # Arrange
    activity_name = "Chess Club"

    # Act
    response = client.post(f"/activities/{activity_name}/signup")

    # Assert
    assert response.status_code == 422


def test_remove_participant_returns_confirmation_and_removes_student():
    # Arrange
    activity_name = "Chess Club"
    email = activities[activity_name]["participants"][0]

    # Act
    response = client.delete(f"/activities/{activity_name}/participants/{email}")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": f"Removed {email} from {activity_name}"}
    assert email not in activities[activity_name]["participants"]


def test_remove_participant_rejects_unknown_activity():
    # Arrange
    activity_name = "Unknown Club"

    # Act
    response = client.delete(f"/activities/{activity_name}/participants/student@example.com")

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}


def test_remove_participant_rejects_unknown_student():
    # Arrange
    activity_name = "Chess Club"
    email = "not-enrolled@example.com"

    # Act
    response = client.delete(f"/activities/{activity_name}/participants/{email}")

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Participant not found"}