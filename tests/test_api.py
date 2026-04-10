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


