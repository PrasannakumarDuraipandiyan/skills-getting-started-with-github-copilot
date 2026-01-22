"""
Tests for Mergington High School Activities API
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add the src directory to the path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app

# Create a test client
client = TestClient(app)


@pytest.fixture
def test_app():
    """Provide a test client"""
    return client


class TestRootEndpoint:
    """Test the root endpoint"""

    def test_root_redirect(self, test_app):
        """Test that root redirects to static/index.html"""
        response = test_app.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestActivitiesEndpoint:
    """Test the activities endpoint"""

    def test_get_activities(self, test_app):
        """Test getting all activities"""
        response = test_app.get("/activities")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        assert "Basketball" in data
        assert "Tennis Club" in data

    def test_activities_have_required_fields(self, test_app):
        """Test that activities have all required fields"""
        response = test_app.get("/activities")
        data = response.json()

        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)

    def test_activities_have_participants(self, test_app):
        """Test that some activities have participants"""
        response = test_app.get("/activities")
        data = response.json()

        # Basketball should have at least one participant
        assert len(data["Basketball"]["participants"]) > 0


class TestSignupEndpoint:
    """Test the signup endpoint"""

    def test_signup_new_participant(self, test_app):
        """Test signing up a new participant"""
        response = test_app.post(
            "/activities/Art%20Club/signup?email=newemail@mergington.edu"
        )
        assert response.status_code == 200

        data = response.json()
        assert "message" in data
        assert "newemail@mergington.edu" in data["message"]

        # Verify the participant was added
        activities = test_app.get("/activities").json()
        assert "newemail@mergington.edu" in activities["Art Club"]["participants"]

    def test_signup_duplicate_participant(self, test_app):
        """Test that duplicate signups are rejected"""
        # First signup
        test_app.post("/activities/Art%20Club/signup?email=duplicate@mergington.edu")

        # Second signup with same email
        response = test_app.post(
            "/activities/Art%20Club/signup?email=duplicate@mergington.edu"
        )
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data
        assert "already signed up" in data["detail"]

    def test_signup_nonexistent_activity(self, test_app):
        """Test signup for non-existent activity"""
        response = test_app.post(
            "/activities/NonExistent%20Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"]

    def test_signup_updates_availability(self, test_app):
        """Test that availability spots decrease after signup"""
        activities_before = test_app.get("/activities").json()
        participants_before = len(activities_before["Basketball"]["participants"])

        test_app.post("/activities/Basketball/signup?email=newbasketball@mergington.edu")

        activities_after = test_app.get("/activities").json()
        participants_after = len(activities_after["Basketball"]["participants"])

        assert participants_after == participants_before + 1


class TestUnregisterEndpoint:
    """Test the unregister endpoint"""

    def test_unregister_existing_participant(self, test_app):
        """Test unregistering an existing participant"""
        # First, sign up
        test_app.post("/activities/Chess%20Club/signup?email=unregister@mergington.edu")

        # Then unregister
        response = test_app.post(
            "/activities/Chess%20Club/unregister?email=unregister@mergington.edu"
        )
        assert response.status_code == 200

        data = response.json()
        assert "message" in data
        assert "unregister@mergington.edu" in data["message"]

        # Verify the participant was removed
        activities = test_app.get("/activities").json()
        assert "unregister@mergington.edu" not in activities["Chess Club"]["participants"]

    def test_unregister_nonexistent_participant(self, test_app):
        """Test unregistering a participant who isn't signed up"""
        response = test_app.post(
            "/activities/Programming%20Class/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data
        assert "not signed up" in data["detail"]

    def test_unregister_nonexistent_activity(self, test_app):
        """Test unregister from non-existent activity"""
        response = test_app.post(
            "/activities/NonExistent%20Activity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"]

    def test_unregister_updates_participation_count(self, test_app):
        """Test that participation count decreases after unregister"""
        # Sign up
        test_app.post("/activities/Robotics%20Club/signup?email=robot@mergington.edu")

        activities_before = test_app.get("/activities").json()
        participants_before = len(activities_before["Robotics Club"]["participants"])

        # Unregister
        test_app.post("/activities/Robotics%20Club/unregister?email=robot@mergington.edu")

        activities_after = test_app.get("/activities").json()
        participants_after = len(activities_after["Robotics Club"]["participants"])

        assert participants_after == participants_before - 1


class TestIntegrationScenarios:
    """Test complete user workflows"""

    def test_signup_and_unregister_workflow(self, test_app):
        """Test a complete signup and unregister workflow"""
        email = "workflow@mergington.edu"
        activity = "Drama%20Club"

        # Verify initial state
        activities = test_app.get("/activities").json()
        initial_count = len(activities["Drama Club"]["participants"])

        # Sign up
        response = test_app.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200

        # Verify participant was added
        activities = test_app.get("/activities").json()
        assert email in activities["Drama Club"]["participants"]
        assert len(activities["Drama Club"]["participants"]) == initial_count + 1

        # Unregister
        response = test_app.post(f"/activities/{activity}/unregister?email={email}")
        assert response.status_code == 200

        # Verify participant was removed
        activities = test_app.get("/activities").json()
        assert email not in activities["Drama Club"]["participants"]
        assert len(activities["Drama Club"]["participants"]) == initial_count

    def test_multiple_signups_different_activities(self, test_app):
        """Test signing up for multiple activities"""
        email = "multi@mergington.edu"

        # Sign up for multiple activities
        response1 = test_app.post(f"/activities/Tennis%20Club/signup?email={email}")
        assert response1.status_code == 200

        response2 = test_app.post(f"/activities/Debate%20Team/signup?email={email}")
        assert response2.status_code == 200

        # Verify both signups
        activities = test_app.get("/activities").json()
        assert email in activities["Tennis Club"]["participants"]
        assert email in activities["Debate Team"]["participants"]
