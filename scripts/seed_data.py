from app.db import Base, SessionLocal, engine
from app.repositories import ExperimentsRepository


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        ExperimentsRepository.reset_all(db)
        ExperimentsRepository.seed_defaults(db)
        db.commit()
    print("Database reset and seeded.")
