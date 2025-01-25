from sqlalchemy import Column, String, Boolean
from sqlalchemy.sql.expression import text


from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from app.database.async_connect import Base



class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'), nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'), onupdate=text('now()'))
    is_active = Column(Boolean, nullable=False, server_default='true')
    is_superuser = Column(Boolean, server_default='false', nullable=False)