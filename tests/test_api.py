"""
Автотесты для сервиса Campus Jobs.
Запуск из корня проекта: pytest tests/
Требует установки: pip install pytest httpx
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import engine, Base

# Создаём клиент для тестирования API
client = TestClient(app)

# Перед каждым тестом создаём чистую БД и таблицы
@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

# Вспомогательная функция: регистрация студента и получение токена
def register_and_login_student(email="student@test.com", password="pass123"):
    # Регистрация
    resp = client.post("/auth/register", json={
        "email": email,
        "password": password,
        "role": "student"
    })
    assert resp.status_code == 200
    # Вход
    resp = client.post("/auth/login", data={
        "username": email,
        "password": password
    })
    assert resp.status_code == 200
    return resp.json()["access_token"]

# Вспомогательная функция: регистрация работодателя и получение токена
def register_and_login_employer(email="employer@test.com", password="pass123"):
    resp = client.post("/auth/register", json={
        "email": email,
        "password": password,
        "role": "employer"
    })
    assert resp.status_code == 200
    resp = client.post("/auth/login", data={
        "username": email,
        "password": password
    })
    assert resp.status_code == 200
    return resp.json()["access_token"]

# =====================================================================
# Тесты
# =====================================================================

# 1. Успешное создание вакансии работодателем
def test_create_vacancy():
    token = register_and_login_employer()
    response = client.post(
        "/vacancies",
        json={
            "title": "Lab Assistant",
            "description": "Help in lab",
            "type": "part-time"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Lab Assistant"
    assert data["employer_name"] == "New Company"  # дефолтное имя компании при регистрации


# 2. Получение списка вакансий с фильтром по типу
def test_get_vacancies_filtered():
    token = register_and_login_employer()
    # Создаём две вакансии разных типов
    client.post("/vacancies", json={
        "title": "Intern", "description": "...", "type": "internship"
    }, headers={"Authorization": f"Bearer {token}"})
    client.post("/vacancies", json={
        "title": "Cafe worker", "description": "...", "type": "part-time"
    }, headers={"Authorization": f"Bearer {token}"})

    # Запрашиваем только стажировки
    response = client.get("/vacancies?type=internship")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["type"] == "internship"


# 3. Успешная подача заявки студентом
def test_apply_success():
    emp_token = register_and_login_employer()
    stud_token = register_and_login_student()

    # Работодатель создаёт вакансию
    vac_resp = client.post("/vacancies", json={
        "title": "TA", "description": "Teaching", "type": "part-time"
    }, headers={"Authorization": f"Bearer {emp_token}"})
    vac_id = vac_resp.json()["id"]

    # Студент подаёт заявку
    app_resp = client.post("/applications", json={
        "vacancy_id": vac_id,
        "resume_content": "My resume text",
        "cover_letter_content": "I am interested"
    }, headers={"Authorization": f"Bearer {stud_token}"})
    assert app_resp.status_code == 200
    app = app_resp.json()
    assert app["status"] == "pending"
    assert app["vacancy_id"] == vac_id


# 4. Ошибка валидации – отсутствует обязательное поле
def test_apply_missing_field():
    stud_token = register_and_login_student()
    resp = client.post("/applications", json={
        "vacancy_id": 1,
        # намеренно пропущено resume_content
        "cover_letter_content": "hello"
    }, headers={"Authorization": f"Bearer {stud_token}"})
    assert resp.status_code == 422  # Unprocessable Entity


# 5. Просмотр своих заявок студентом
def test_get_my_applications():
    emp_token = register_and_login_employer()
    stud_token = register_and_login_student()

    # Создаём вакансию и подаём заявку
    vac_resp = client.post("/vacancies", json={
        "title": "Lab", "description": "...", "type": "part-time"
    }, headers={"Authorization": f"Bearer {emp_token}"})
    vac_id = vac_resp.json()["id"]
    client.post("/applications", json={
        "vacancy_id": vac_id,
        "resume_content": "resume",
        "cover_letter_content": "cl"
    }, headers={"Authorization": f"Bearer {stud_token}"})

    # Студент получает свои заявки
    resp = client.get("/students/me/applications",
                      headers={"Authorization": f"Bearer {stud_token}"})
    assert resp.status_code == 200
    apps = resp.json()
    assert len(apps) == 1
    assert apps[0]["vacancy_id"] == vac_id


# 6. Попытка подать заявку от работодателя (запрет доступа)
def test_apply_as_employer_fails():
    emp_token = register_and_login_employer()
    # Создаём вакансию
    vac_resp = client.post("/vacancies", json={
        "title": "Job", "description": "...", "type": "part-time"
    }, headers={"Authorization": f"Bearer {emp_token}"})
    vac_id = vac_resp.json()["id"]

    # Пытаемся подать заявку от имени работодателя
    resp = client.post("/applications", json={
        "vacancy_id": vac_id,
        "resume_content": "x",
        "cover_letter_content": "y"
    }, headers={"Authorization": f"Bearer {emp_token}"})
    assert resp.status_code == 403


# 7. Запрет дублирующейся заявки
def test_duplicate_application():
    emp_token = register_and_login_employer()
    stud_token = register_and_login_student()

    vac_resp = client.post("/vacancies", json={
        "title": "Job", "description": "...", "type": "part-time"
    }, headers={"Authorization": f"Bearer {emp_token}"})
    vac_id = vac_resp.json()["id"]

    payload = {
        "vacancy_id": vac_id,
        "resume_content": "A",
        "cover_letter_content": "B"
    }
    # Первая попытка – успех
    resp1 = client.post("/applications", json=payload,
                        headers={"Authorization": f"Bearer {stud_token}"})
    assert resp1.status_code == 200

    # Вторая попытка – дубликат
    resp2 = client.post("/applications", json=payload,
                        headers={"Authorization": f"Bearer {stud_token}"})
    assert resp2.status_code == 400
    assert resp2.json()["detail"] == "Already applied or error"


# 8. Обновление статуса заявки работодателем (принять)
def test_update_application_status():
    emp_token = register_and_login_employer()
    stud_token = register_and_login_student()

    # Создаём вакансию и подаём заявку
    vac_resp = client.post("/vacancies", json={
        "title": "QA", "description": "...", "type": "part-time"
    }, headers={"Authorization": f"Bearer {emp_token}"})
    vac_id = vac_resp.json()["id"]
    app_resp = client.post("/applications", json={
        "vacancy_id": vac_id,
        "resume_content": "CV",
        "cover_letter_content": "CL"
    }, headers={"Authorization": f"Bearer {stud_token}"})
    app_id = app_resp.json()["id"]

    # Работодатель меняет статус на "accepted"
    patch_resp = client.patch(
        f"/applications/{app_id}/status?new_status=accepted",
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert patch_resp.status_code == 200

    # Студент проверяет статус
    apps_resp = client.get("/students/me/applications",
                           headers={"Authorization": f"Bearer {stud_token}"})
    assert apps_resp.json()[0]["status"] == "accepted"


# 9. Получение своих вакансий работодателем
def test_employer_get_my_vacancies():
    token = register_and_login_employer()
    # Создаём две вакансии
    client.post("/vacancies", json={
        "title": "V1", "description": "...", "type": "internship"
    }, headers={"Authorization": f"Bearer {token}"})
    client.post("/vacancies", json={
        "title": "V2", "description": "...", "type": "part-time"
    }, headers={"Authorization": f"Bearer {token}"})

    resp = client.get("/employers/me/vacancies",
                      headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    titles = [v["title"] for v in data]
    assert "V1" in titles and "V2" in titles


# 10. Просмотр заявок на вакансию работодателем
def test_employer_get_applications_for_vacancy():
    emp_token = register_and_login_employer()
    stud_token = register_and_login_student(email="stud2@test.com")

    # Создаём вакансию
    vac_resp = client.post("/vacancies", json={
        "title": "Designer", "description": "...", "type": "internship"
    }, headers={"Authorization": f"Bearer {emp_token}"})
    vac_id = vac_resp.json()["id"]

    # Студент подаёт заявку
    client.post("/applications", json={
        "vacancy_id": vac_id,
        "resume_content": "resume",
        "cover_letter_content": "cover"
    }, headers={"Authorization": f"Bearer {stud_token}"})

    # Работодатель получает заявки на эту вакансию
    resp = client.get(f"/employers/me/vacancies/{vac_id}/applications",
                      headers={"Authorization": f"Bearer {emp_token}"})
    assert resp.status_code == 200
    apps = resp.json()
    assert len(apps) == 1
    assert apps[0]["vacancy_id"] == vac_id
    assert apps[0]["status"] == "pending"