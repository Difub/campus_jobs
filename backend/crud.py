from sqlalchemy.orm import Session
from .models import *
from .schemas import *
from .auth import get_password_hash


# -- User --
def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user: UserCreate):
    hashed = get_password_hash(user.password)   # <-- используем функцию из auth
    db_user = User(email=user.email, password_hash=hashed, role=user.role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# -- Student --
def create_student(db: Session, student: StudentCreate, user_id: int):
    db_st = Student(**student.dict(), user_id=user_id)
    db.add(db_st)
    db.commit()
    db.refresh(db_st)
    return db_st

# -- Employer --
def create_employer(db: Session, emp: EmployerCreate, user_id: int):
    db_emp = Employer(**emp.dict(), user_id=user_id)
    db.add(db_emp)
    db.commit()
    db.refresh(db_emp)
    return db_emp

# -- Vacancy --
def get_vacancies(db: Session, skip=0, limit=100, type=None, search=None):
    q = db.query(Vacancy).filter(Vacancy.is_active == True)
    if type:
        q = q.filter(Vacancy.type == type)
    if search:
        q = q.filter(Vacancy.title.ilike(f"%{search}%"))
    return q.offset(skip).limit(limit).all()

def create_vacancy(db: Session, vacancy: VacancyCreate, employer_id: int):
    db_vac = Vacancy(**vacancy.dict(), employer_id=employer_id)
    db.add(db_vac)
    db.commit()
    db.refresh(db_vac)
    return db_vac

# -- Application --
def apply_for_vacancy(db: Session, app: ApplicationCreate, student_id: int):
    # Проверка дубликата
    existing = db.query(Application).filter(
        Application.student_id == student_id,
        Application.vacancy_id == app.vacancy_id
    ).first()
    if existing:
        return None
    # Создаём резюме
    resume = Resume(content=app.resume_content, student_id=student_id)
    db.add(resume)
    db.flush()
    # Создаём сопроводительное
    letter = CoverLetter(content=app.cover_letter_content)
    db.add(letter)
    db.flush()
    # Заявка
    application = Application(
        vacancy_id=app.vacancy_id,
        student_id=student_id,
        resume_id=resume.id,
        cover_letter_id=letter.id,
        status="pending"
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application

def get_student_applications(db: Session, student_id: int):
    return db.query(Application).filter(Application.student_id == student_id).all()

# Обновление статуса заявки (работодателем)
def update_application_status(db: Session, app_id: int, new_status: str, employer_id: int):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        return None
    # Проверяем, что работодатель владеет вакансией
    vacancy = db.query(Vacancy).filter(Vacancy.id == app.vacancy_id).first()
    if vacancy.employer_id != employer_id:
        return None
    app.status = new_status
    db.commit()
    db.refresh(app)
    return app

def get_application_details(db: Session, app_id: int):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        return None
    resume = db.query(Resume).filter(Resume.id == app.resume_id).first()
    cover = db.query(CoverLetter).filter(CoverLetter.id == app.cover_letter_id).first()
    return {
        "application": app,
        "resume": resume,
        "cover_letter": cover
    }