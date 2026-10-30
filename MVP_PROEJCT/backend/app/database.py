"""데이터베이스 연결과 테이블 정의. 원본과 판정 시점의 기준을 함께 보관한다."""
import os
from datetime import datetime, timezone
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


def now():
    return datetime.now(timezone.utc)


DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+psycopg://traceproof:traceproof_local_demo@localhost:5432/traceproof')
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Equipment(Base):
    __tablename__ = 'equipment'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    model: Mapped[str] = mapped_column(String(100))
    location: Mapped[str] = mapped_column(String(150))


class Profile(Base):
    __tablename__ = 'profiles'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    document: Mapped[dict] = mapped_column(JSON)


class Release(Base):
    __tablename__ = 'releases'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    equipment_id: Mapped[str] = mapped_column(ForeignKey('equipment.id'), index=True)
    label: Mapped[str] = mapped_column(String(150))
    software_version: Mapped[str] = mapped_column(String(100))
    source: Mapped[str] = mapped_column(String(30))
    filename: Mapped[str] = mapped_column(String(200))
    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    # 원본 JSON 문자열을 그대로 보존하므로 다운로드 시 해시를 다시 확인할 수 있다.
    raw_content: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Validation(Base):
    __tablename__ = 'validations'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    baseline_id: Mapped[int] = mapped_column(ForeignKey('releases.id'))
    candidate_id: Mapped[int] = mapped_column(ForeignKey('releases.id'))
    profile_id: Mapped[str] = mapped_column(ForeignKey('profiles.id'))
    profile_snapshot: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON)
    review_status: Mapped[str] = mapped_column(String(30), default='PENDING')
    reviews: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


def get_db():
    with SessionLocal() as session:
        yield session
