import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Enum, Float,
    ForeignKey, Boolean, JSON, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class LeadStatus(str, enum.Enum):
    DISCOVERED = "discovered"
    VERIFIED = "verified"
    REJECTED = "rejected"
    WEBSITE_BUILDING = "website_building"
    WEBSITE_READY = "website_ready"
    DEPLOYED = "deployed"
    OUTREACH_SENT = "outreach_sent"
    FOLLOW_UP_1 = "follow_up_1"
    FOLLOW_UP_2 = "follow_up_2"
    RESPONDED = "responded"
    INTERESTED = "interested"
    CONVERTED = "converted"
    UNSUBSCRIBED = "unsubscribed"
    BOUNCED = "bounced"


class RejectionReason(str, enum.Enum):
    HAS_WEBSITE = "has_website"
    NO_CONTACT_INFO = "no_contact_info"
    BUSINESS_CLOSED = "business_closed"
    DUPLICATE = "duplicate"
    OUTSIDE_TARGET = "outside_target"
    MANUAL = "manual"


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    place_id = Column(String(255), unique=True, nullable=False, index=True)
    business_name = Column(String(500), nullable=False)
    business_type = Column(String(255))
    address = Column(Text)
    city = Column(String(255), index=True)
    postal_code = Column(String(20))
    country = Column(String(100), default="DE")
    phone = Column(String(50))
    email = Column(String(255))
    existing_website = Column(String(500))
    latitude = Column(Float)
    longitude = Column(Float)
    rating = Column(Float)
    review_count = Column(Integer, default=0)
    business_hours = Column(JSON)
    photos_urls = Column(JSON)

    status = Column(
        Enum(LeadStatus), default=LeadStatus.DISCOVERED, nullable=False, index=True
    )
    rejection_reason = Column(Enum(RejectionReason), nullable=True)
    rejection_details = Column(Text, nullable=True)

    scan_source = Column(String(100), default="google_places")
    scan_query = Column(String(500))
    scan_location = Column(String(255))

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    verified_at = Column(DateTime, nullable=True)
    outreach_at = Column(DateTime, nullable=True)

    websites = relationship("Website", back_populates="lead", cascade="all, delete-orphan")
    deployments = relationship("Deployment", back_populates="lead", cascade="all, delete-orphan")
    outreach_messages = relationship("OutreachMessage", back_populates="lead", cascade="all, delete-orphan")
    domain_suggestions = relationship("DomainSuggestion", back_populates="lead", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Lead {self.id}: {self.business_name} [{self.status.value}]>"


class Website(Base):
    __tablename__ = "websites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    template_name = Column(String(100))
    html_content = Column(Text)
    css_content = Column(Text)
    generated_copy = Column(JSON)
    screenshot_path = Column(String(500))
    preview_url = Column(String(500))
    version = Column(Integer, default=1)
    quality_score = Column(Float, nullable=True)
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    lead = relationship("Lead", back_populates="websites")

    def __repr__(self):
        return f"<Website {self.id} for Lead {self.lead_id} v{self.version}>"


class Deployment(Base):
    __tablename__ = "deployments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    website_id = Column(Integer, ForeignKey("websites.id"), nullable=False)
    live_url = Column(String(500))
    custom_domain = Column(String(255))
    status = Column(String(50), default="pending")
    is_active = Column(Boolean, default=True)
    deployed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    lead = relationship("Lead", back_populates="deployments")
    website = relationship("Website")

    def __repr__(self):
        return f"<Deployment {self.id} → {self.live_url}>"


class OutreachMessage(Base):
    __tablename__ = "outreach_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    channel = Column(String(50), default="email")
    subject = Column(String(500))
    body = Column(Text)
    recipient_email = Column(String(255))
    message_id = Column(String(255))
    status = Column(String(50), default="pending")
    is_follow_up = Column(Boolean, default=False)
    follow_up_number = Column(Integer, default=0)
    opened_at = Column(DateTime, nullable=True)
    replied_at = Column(DateTime, nullable=True)
    bounced_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    lead = relationship("Lead", back_populates="outreach_messages")

    def __repr__(self):
        return f"<Outreach {self.id} to {self.recipient_email} [{self.status}]>"


class DomainSuggestion(Base):
    __tablename__ = "domain_suggestions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    domain_name = Column(String(255), nullable=False)
    tld = Column(String(20), default=".de")
    is_available = Column(Boolean, nullable=True)
    checked_at = Column(DateTime, nullable=True)
    price_estimate = Column(Float, nullable=True)
    is_recommended = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    lead = relationship("Lead", back_populates="domain_suggestions")

    __table_args__ = (
        UniqueConstraint("lead_id", "domain_name", name="uq_lead_domain"),
    )

    def __repr__(self):
        return f"<Domain {self.domain_name}{self.tld} for Lead {self.lead_id}>"


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String(100), nullable=False)
    status = Column(String(50), default="running")
    leads_processed = Column(Integer, default=0)
    leads_succeeded = Column(Integer, default=0)
    leads_failed = Column(Integer, default=0)
    error_log = Column(Text, nullable=True)
    config_snapshot = Column(JSON, nullable=True)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<PipelineRun {self.id}: {self.agent_name} [{self.status}]>"
