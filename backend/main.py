import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import uvicorn

from .database import engine, Base, SessionLocal
from .models import * # все ORM-модели (User, Student, Employer, Vacancy, Application, ...)
from .schemas import * # Pydantic-схемы для валидации запросов/ответов
from . import crud # функции для работы с БД (создание, чтение, обновление)
from .auth import * # утилиты аутентификации: хеширование, токены, get_current_user

# ----------------------------------------------------------------------
# Создание таблиц в БД (если их ещё нет)
# ----------------------------------------------------------------------
Base.metadata.create_all(bind=engine)

# ----------------------------------------------------------------------
# Инициализация FastAPI-приложения
# ----------------------------------------------------------------------
app = FastAPI(title="Campus Jobs API", version="1.0.0")

# ----------------------------------------------------------------------
# Настройка CORS (разрешаем все источники для разработки)
# ----------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------------------------
# Монтирование папки frontend как статического ресурса
# (стили, скрипты, дополнительные HTML-страницы)
# ----------------------------------------------------------------------
frontend_path = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

# ----------------------------------------------------------------------
# Аутентификация и регистрация
# ----------------------------------------------------------------------

@app.post("/auth/register", response_model=UserOut)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """
    Регистрация нового пользователя.
    Проверяет уникальность email, хеширует пароль, создаёт запись User и профиль (Student/Employer).
    """
    if crud.get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    db_user = crud.create_user(db, user)

    # Автоматически создаём профиль нужного типа с заглушкой
    if user.role == "student":
        crud.create_student(db, StudentCreate(first_name="New", last_name="Student"), db_user.id)
    elif user.role == "employer":
        crud.create_employer(db, EmployerCreate(company_name="New Company"), db_user.id)
    return db_user


@app.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Аутентификация пользователя по email и паролю.
    Возвращает JWT-токен для доступа к защищённым эндпоинтам.
    """
    user = crud.get_user_by_email(db, form_data.username)  # form_data.username = email
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


# ----------------------------------------------------------------------
# Работа с вакансиями (публичное и для работодателя)
# ----------------------------------------------------------------------

@app.get("/vacancies", response_model=list[VacancyOut])
def read_vacancies(
    type: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Получение списка активных вакансий с возможностью фильтрации по типу и поиску.
    """
    vacs = crud.get_vacancies(db, skip, limit, type, search)
    result = []
    for v in vacs:
        emp = db.query(Employer).filter(Employer.id == v.employer_id).first()
        result.append(VacancyOut(
            id=v.id, employer_id=v.employer_id,
            title=v.title, description=v.description,
            department=v.department, location=v.location,
            type=v.type, deadline=v.deadline, is_active=v.is_active,
            created_at=v.created_at,
            employer_name=emp.company_name if emp else "Unknown"
        ))
    return result


@app.get("/vacancies/{vacancy_id}", response_model=VacancyOut)
def read_vacancy(vacancy_id: int, db: Session = Depends(get_db)):
    """
    Получение одной вакансии по ID.
    """
    v = db.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    emp = db.query(Employer).filter(Employer.id == v.employer_id).first()
    return VacancyOut(
        id=v.id, employer_id=v.employer_id,
        title=v.title, description=v.description,
        department=v.department, location=v.location,
        type=v.type, deadline=v.deadline, is_active=v.is_active,
        created_at=v.created_at,
        employer_name=emp.company_name if emp else "Unknown"
    )


@app.post("/vacancies", response_model=VacancyOut)
def create_vacancy(
    vacancy: VacancyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Создание новой вакансии. Доступно только работодателям.
    """
    if current_user.role != "employer":
        raise HTTPException(status_code=403, detail="Only employers can create vacancies")
    employer = db.query(Employer).filter(Employer.user_id == current_user.id).first()
    if not employer:
        raise HTTPException(status_code=400, detail="Employer profile not found")

    # Используем CRUD-функцию из модуля crud (избегаем конфликта имён)
    db_vac = crud.create_vacancy(db, vacancy, employer.id)
    return VacancyOut(
        id=db_vac.id, employer_id=db_vac.employer_id,
        title=db_vac.title, description=db_vac.description,
        department=db_vac.department, location=db_vac.location,
        type=db_vac.type, deadline=db_vac.deadline, is_active=db_vac.is_active,
        created_at=db_vac.created_at,
        employer_name=employer.company_name
    )



# эндпоинт – отдаёт главную страницу (фронтенд)

@app.get("/", response_class=HTMLResponse)
def read_root():
    """
    Возвращает index.html из папки frontend.
    """
    index_path = Path(__file__).parent.parent / "frontend" / "index.html"
    with open(index_path, encoding="utf-8") as f:
        return f.read()


# ----------------------------------------------------------------------
# Запуск сервера (только при прямом вызове скрипта)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)