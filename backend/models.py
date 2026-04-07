from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime, ForeignKey, Float, Boolean
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # "student" or "employer"
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    phone = Column(String)
    university_year = Column(String)
    major = Column(String)
    bio = Column(Text)

    user = relationship("User", backref="student")
    resumes = relationship("Resume", back_populates="student")
    applications = relationship("Application", back_populates="student")


class Employer(Base):
    __tablename__ = "employers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    company_name = Column(String, nullable=False)
    department = Column(String)
    description = Column(Text)

    user = relationship("User", backref="employer")
    vacancies = relationship("Vacancy", back_populates="employer")


class Vacancy(Base):
    __tablename__ = "vacancies"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"))
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    department = Column(String)
    location = Column(String)
    type = Column(String)  # "internship" or "part-time"
    deadline = Column(Date)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    employer = relationship("Employer", back_populates="vacancies")
    applications = relationship("Application", back_populates="vacancy")


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    content = Column(Text, nullable=False)  # храним текстовое резюме
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("Student", back_populates="resumes")
    applications = relationship("Application", back_populates="resume")


class CoverLetter(Base):
    __tablename__ = "cover_letters"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    application = relationship("Application", back_populates="cover_letter", uselist=False)


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    vacancy_id = Column(Integer, ForeignKey("vacancies.id"))
    student_id = Column(Integer, ForeignKey("students.id"))
    resume_id = Column(Integer, ForeignKey("resumes.id"))
    cover_letter_id = Column(Integer, ForeignKey("cover_letters.id"))
    status = Column(String, default="pending")  # pending, reviewed, accepted, rejected
    applied_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    vacancy = relationship("Vacancy", back_populates="applications")
    student = relationship("Student", back_populates="applications")
    resume = relationship("Resume", back_populates="applications")
    cover_letter = relationship("CoverLetter", back_populates="application")
    interviews = relationship("Interview", back_populates="application")


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"))
    scheduled_time = Column(DateTime, nullable=False)
    location = Column(String)
    notes = Column(Text)
    status = Column(String, default="scheduled")  # scheduled, completed, cancelled

    application = relationship("Application", back_populates="interviews")


class Review(Base):
    __tablename__ = "reviews"  # отзыв работодателя о студенте

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"))
    student_id = Column(Integer, ForeignKey("students.id"))
    rating = Column(Integer, nullable=False)  # 1-5
    comment = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class StudentReview(Base):
    __tablename__ = "student_reviews"  # отзыв студента о работодателе/стажировке

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    employer_id = Column(Integer, ForeignKey("employers.id"))
    rating = Column(Integer, nullable=False)
    comment = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())