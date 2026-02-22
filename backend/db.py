from sqlmodel import SQLModel, create_engine, Session

# creates a local database file
engine = create_engine("sqlite:///arthamantri.db")

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    return Session(engine)