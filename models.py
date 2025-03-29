from sqlalchemy import Column, Integer, String, Date, Time, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class BatchJob(Base):
    __tablename__ = "batch_jobs"

    id = Column(Integer, primary_key=True, index=True)
    batch_date = Column(Date)
    status = Column(String, default="Uploaded")
    progress = Column(Integer, default=0)
    stopped = Column(Boolean, default=False)  # 👈 Add this line

    addresses = relationship("TNTInputData", back_populates="batch", cascade="all, delete-orphan")
    settings = relationship("BatchSettings", uselist=False, back_populates="batch", cascade="all, delete-orphan")



class TNTInputData(Base):
    __tablename__ = "tnt_input_data"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("batch_jobs.id", ondelete="CASCADE"))
    origin_city = Column(String)
    origin_state = Column(String)
    origin_zip = Column(String)
    dest_city_input = Column(String)
    dest_city_ups = Column(String)
    dest_state = Column(String)
    input_dest_zip = Column(String)
    ups_dest_zip = Column(String)
    dest_country = Column(String)
    
    # 🆕 Settings directly on input row
    ship_date = Column(Date, nullable=True)
    avv_flag = Column(Boolean, default=False)
    residential_indicator = Column(String, nullable=True)  # "", "01", "02"
    batch = relationship("BatchJob", back_populates="addresses")
    responses = relationship("TNTAPIResponse", back_populates="input", cascade="all, delete-orphan")


class TNTAPIResponse(Base):
    __tablename__ = "tnt_response"

    id = Column(Integer, primary_key=True, index=True)
    service_level = Column(String)
    service_description = Column(String)
    business_transit_days = Column(Integer)
    total_transit_days = Column(Integer)
    delivery_date = Column(Date)
    delivery_time = Column(Time)
    delivery_day_of_week = Column(String)
    next_day_pickup_indicator = Column(String)
    saturday_pickup_indicator = Column(String)
    saturday_delivery_indicator = Column(String)
    saturday_delivery_time = Column(Time)
    guarantee_indicator = Column(String)
    rest_days_count = Column(Integer)
    holiday_count = Column(Integer)
    delay_count = Column(Integer)
    commit_time = Column(Time)
    ship_date = Column(Date)
    pickup_time = Column(Time)
    pickup_date = Column(Date)
    poddate = Column(Date)
    poddays = Column(Integer)
    cstccutoff_time = Column(Time)
    service_remarks_text = Column(String, nullable=True)

    input_id = Column(Integer, ForeignKey("tnt_input_data.id", ondelete="CASCADE"))
    input = relationship("TNTInputData", back_populates="responses")


class BatchSettings(Base):
    __tablename__ = "batch_settings"

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("batch_jobs.id", ondelete="CASCADE"), unique=True)
    ship_date = Column(Date)
    avv_flag = Column(Boolean, default=False)  # replaces documents_only
    residential_indicator = Column(String, nullable=True)  # "", "01", or "02"

    batch = relationship("BatchJob", back_populates="settings")