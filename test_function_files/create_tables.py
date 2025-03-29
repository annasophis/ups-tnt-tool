from database import Base, engine
from models import TNTInputData  # add other models here later if needed

Base.metadata.create_all(bind=engine)
