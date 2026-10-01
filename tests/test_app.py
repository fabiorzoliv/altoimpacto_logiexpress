from app import app, db

def test_health():
    app.config["TESTING"] = True
    with app.test_client() as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json["status"] == "ok"

def test_dashboard():
    app.config["TESTING"] = True
    with app.test_client() as client:
        response = client.get("/")
        assert response.status_code == 200
        assert b"LOGIEXPRESS" in response.data
