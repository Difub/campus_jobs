from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, datetime

# ---------- User ----------
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str

class UserOut(BaseModel):
    id: int
    email: str
    role: str
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# ---------- Student ----------
class StudentCreate(BaseModel):
    first_name: str
    last_name: str
    phone: Optional[str] = None
    university_year: Optional[str] = None
    major: Optional[str] = None
    bio: Optional[str] = None

class StudentOut(StudentCreate):
    id: int
    user_id: int

# ---------- Employer ----------
class EmployerCreate(BaseModel):
    company_name: str
    department: Optional[str] = None
    description: Optional[str] = None

class EmployerOut(EmployerCreate):
    id: int
    user_id: int

# ---------- Vacancy ----------
class VacancyCreate(BaseModel):
    title: str
    description: str
    department: Optional[str] = None
    location: Optional[str] = None
    type: str  # internship, part-time
    deadline: Optional[date] = None
    is_active: Optional[bool] = True

class VacancyOut(VacancyCreate):
    id: int
    employer_id: int
    created_at: datetime
    employer_name: Optional[str] = None  # добавим для удобства
    class Config: from_attributes=True

# ---------- Resume ----------
class ResumeCreate(BaseModel):
    content: str

class ResumeOut(ResumeCreate):
    id: int
    student_id: int

# ---------- CoverLetter ----------
class CoverLetterCreate(BaseModel):
    content: str

class CoverLetterOut(CoverLetterCreate):
    id: int

# ---------- Application ----------
class ApplicationCreate(BaseModel):
    vacancy_id: int
    resume_content: str  # упрощённо: сразу текст резюме
    cover_letter_content: str

class ApplicationOut(BaseModel):
    id: int
    vacancy_id: int
    student_id: int
    resume_id: int
    cover_letter_id: int
    status: str
    applied_at: datetime
    vacancy_title: Optional[str] = None
    class Config: from_attributes=True

# ---------- Interview (упрощённо) ----------
class InterviewCreate(BaseModel):
    application_id: int
    scheduled_time: datetime
    location: Optional[str] = None
    notes: Optional[str] = None

class InterviewOut(InterviewCreate):
    id: int
    status: str