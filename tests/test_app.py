from datetime import date
from decimal import Decimal

from app import Manutencao, Veiculo, app, db

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

def test_maintenance_pages():
    app.config["TESTING"] = True
    with app.test_client() as client:
        list_response = client.get("/manutencoes")
        form_response = client.get("/manutencoes/novo")

        assert list_response.status_code == 200
        assert form_response.status_code == 200
        assert b"tipo_manutencao" in form_response.data

def test_generic_maintenance_routes_use_specific_flow():
    app.config["TESTING"] = True
    with app.test_client() as client:
        list_response = client.get("/cadastros/manutencoes")
        form_response = client.get("/cadastros/manutencoes/novo")

        assert list_response.status_code == 302
        assert list_response.location.endswith("/manutencoes")
        assert form_response.status_code == 302
        assert form_response.location.endswith("/manutencoes/novo")


def test_maintenance_requires_vehicle_type_date_and_description():
    app.config["TESTING"] = True
    with app.test_client() as client:
        response = client.post(
            "/manutencoes/novo",
            data={
                "veiculo_id": "",
                "tipo_manutencao": "",
                "data_manutencao": "",
                "quilometragem": "0",
                "descricao_manutencao": "",
                "custo_manutencao": "0",
                "status_manutencao": "ABERTA",
            },
        )

        assert response.status_code == 200
        assert b"Ve\xc3\xadculo, tipo, data e descri\xc3\xa7\xc3\xa3o s\xc3\xa3o obrigat\xc3\xb3rios." in response.data


def test_maintenance_rejects_negative_cost():
    app.config["TESTING"] = True
    with app.app_context():
        vehicle = Veiculo.query.first()
        assert vehicle is not None

        with app.test_client() as client:
            response = client.post(
                "/manutencoes/novo",
                data={
                    "veiculo_id": str(vehicle.id),
                    "tipo_manutencao": "CORRETIVA",
                    "data_manutencao": "2026-01-15",
                    "quilometragem": "100",
                    "descricao_manutencao": "Teste de custo negativo",
                    "custo_manutencao": "-1",
                    "status_manutencao": "ABERTA",
                },
            )

        assert response.status_code == 200
        assert b"O custo n\xc3\xa3o pode ser negativo." in response.data
        assert Manutencao.query.filter_by(descricao_manutencao="TESTE DE CUSTO NEGATIVO").first() is None


def test_maintenance_list_is_ordered_and_highlights_pending_records():
    app.config["TESTING"] = True
    descriptions = ["TESTE MANUTENCAO ANTIGA", "TESTE MANUTENCAO RECENTE"]

    with app.app_context():
        vehicle = Veiculo.query.first()
        assert vehicle is not None
        records = [
            Manutencao(
                veiculo_id=vehicle.id,
                data_manutencao=date(2026, 1, 1),
                tipo_manutencao="PREVENTIVA",
                quilometragem=100,
                descricao_manutencao=descriptions[0],
                custo_manutencao=Decimal("10.00"),
                status_manutencao="CONCLUÍDA",
            ),
            Manutencao(
                veiculo_id=vehicle.id,
                data_manutencao=date(2026, 2, 1),
                tipo_manutencao="CORRETIVA",
                quilometragem=200,
                descricao_manutencao=descriptions[1],
                custo_manutencao=Decimal("20.00"),
                status_manutencao="ABERTA",
            ),
        ]
        db.session.add_all(records)
        db.session.commit()

        try:
            with app.test_client() as client:
                response = client.get("/manutencoes")

            assert response.status_code == 200
            body = response.data
            assert body.index(b"01/02/2026") < body.index(b"01/01/2026")
            assert "manutenção(ões) pendente(s).".encode("utf-8") in body
            assert b'class="table-warning"' in body
        finally:
            for record in records:
                db.session.delete(record)
            db.session.commit()
