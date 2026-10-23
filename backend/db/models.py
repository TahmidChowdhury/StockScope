"""Normalized shared research storage; immutable revisions retain source evidence."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, JSON,
    MetaData, Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase


def utcnow():
    return datetime.now(timezone.utc)


def identifier():
    return str(uuid4())


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention={
        "ix": "ix_%(column_0_label)s", "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s", "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    })


class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, unique=True)
    cik = Column(String(10), nullable=True, index=True)
    name = Column(Text, nullable=True)
    first_seen_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class Source(Base):
    __tablename__ = "sources"
    id = Column(Integer, primary_key=True)
    provider = Column(String(200), nullable=False)
    publisher = Column(String(300), nullable=False)
    kind = Column(String(30), nullable=False)
    __table_args__ = (UniqueConstraint("provider", "publisher", "kind", name="uq_sources_identity"),)


class Article(Base):
    __tablename__ = "articles"
    id = Column(String(36), primary_key=True, default=identifier)
    identity_hash = Column(String(64), nullable=False, unique=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    url = Column(Text, nullable=True)
    title = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    first_seen_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    last_seen_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class ArticleCompany(Base):
    __tablename__ = "article_companies"
    article_id = Column(String(36), ForeignKey("articles.id"), primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), primary_key=True)
    first_seen_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class ArticleRevision(Base):
    __tablename__ = "article_revisions"
    id = Column(String(36), primary_key=True, default=identifier)
    article_id = Column(String(36), ForeignKey("articles.id"), nullable=False, index=True)
    content_hash = Column(String(64), nullable=False)
    payload = Column(JSON, nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    fetched_at = Column(DateTime(timezone=True), nullable=True)
    observed_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (UniqueConstraint("article_id", "content_hash", name="uq_article_revision_content"),)


class Filing(Base):
    __tablename__ = "filings"
    id = Column(String(36), primary_key=True, default=identifier)
    identity_hash = Column(String(64), nullable=False, unique=True)
    accession_number = Column(String(30), nullable=True, unique=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    form_type = Column(String(30), nullable=True)
    filing_date = Column(Date, nullable=True)
    report_period = Column(Date, nullable=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    url = Column(Text, nullable=True)
    is_amendment = Column(Boolean, nullable=False, default=False)
    first_seen_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class FilingCompany(Base):
    __tablename__ = "filing_companies"
    filing_id = Column(String(36), ForeignKey("filings.id"), primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), primary_key=True)



class FilingRevision(Base):
    __tablename__ = "filing_revisions"
    id = Column(String(36), primary_key=True, default=identifier)
    filing_id = Column(String(36), ForeignKey("filings.id"), nullable=False, index=True)
    content_hash = Column(String(64), nullable=False)
    payload = Column(JSON, nullable=False)
    fetched_at = Column(DateTime(timezone=True), nullable=True)
    observed_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (UniqueConstraint("filing_id", "content_hash", name="uq_filing_revision_content"),)


class FinancialFact(Base):
    """A filed observation; amendments/restatements create another version, not an overwrite."""
    __tablename__ = "financial_facts"
    id = Column(String(36), primary_key=True, default=identifier)
    identity_hash = Column(String(64), nullable=False, unique=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    filing_id = Column(String(36), ForeignKey("filings.id"), nullable=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    namespace = Column(String(100), nullable=False)
    concept = Column(String(300), nullable=False)
    unit = Column(String(100), nullable=False)
    value = Column(Numeric(), nullable=True)
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    period_type = Column(String(10), nullable=False)
    fiscal_year = Column(Integer, nullable=True)
    fiscal_period = Column(String(10), nullable=True)
    filed_at = Column(Date, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    is_amendment = Column(Boolean, nullable=False, default=False)
    supersedes_id = Column(String(36), ForeignKey("financial_facts.id"), nullable=True)
    observed_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    payload = Column(JSON, nullable=False)
    __table_args__ = (
        CheckConstraint("period_type IN ('instant', 'duration', 'unknown')", name="period_type"),
        CheckConstraint("version >= 1", name="positive_version"),
        CheckConstraint("period_start IS NULL OR period_start <= period_end", name="period_order"),
    )


class Watchlist(Base):
    __tablename__ = "watchlists"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    scope = Column(String(10), nullable=False, default="shared")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (CheckConstraint("scope = 'shared'", name="shared_scope"),)


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    watchlist_id = Column(Integer, ForeignKey("watchlists.id"), primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), primary_key=True)
    added_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class ResearchNote(Base):
    __tablename__ = "research_notes"
    id = Column(String(36), primary_key=True, default=identifier)
    watchlist_id = Column(Integer, ForeignKey("watchlists.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    scope = Column(String(10), nullable=False, default="shared")
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (CheckConstraint("scope = 'shared'", name="shared_scope"),)


class ImportBatch(Base):
    __tablename__ = "import_batches"
    id = Column(String(36), primary_key=True, default=identifier)
    manifest_hash = Column(String(64), nullable=False, unique=True)
    file_count = Column(Integer, nullable=False)
    record_count = Column(Integer, nullable=False)
    applied_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class SnapshotRevision(Base):
    __tablename__ = "snapshot_revisions"
    id = Column(String(36), primary_key=True, default=identifier)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    suffix = Column(String(60), nullable=False)
    content_hash = Column(String(64), nullable=False)
    payload = Column(JSON, nullable=False)
    observed_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    import_batch_id = Column(String(36), ForeignKey("import_batches.id"), nullable=True)
    __table_args__ = (UniqueConstraint("company_id", "suffix", "content_hash", name="uq_snapshot_revision_content"),)


class CurrentSnapshot(Base):
    __tablename__ = "current_snapshots"
    company_id = Column(Integer, ForeignKey("companies.id"), primary_key=True)
    suffix = Column(String(60), primary_key=True)
    revision_id = Column(String(36), ForeignKey("snapshot_revisions.id"), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class CollectionRun(Base):
    __tablename__ = "collection_runs"
    id = Column(String(36), primary_key=True, default=identifier)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False)
    progress = Column(Integer, nullable=False, default=0)
    message = Column(Text, nullable=False)
    requested_sources = Column(JSON, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        CheckConstraint("status IN ('pending','processing','completed','partial','failed')", name="status"),
        CheckConstraint("progress BETWEEN 0 AND 100", name="progress"),
    )


class CollectionSourceOutcome(Base):
    __tablename__ = "collection_source_outcomes"
    run_id = Column(String(36), ForeignKey("collection_runs.id"), primary_key=True)
    source_name = Column(String(200), primary_key=True)
    status = Column(String(30), nullable=False)
    record_count = Column(Integer, nullable=False, default=0)
    message = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (CheckConstraint("record_count >= 0", name="nonnegative_count"),)


class TradingDocument(Base):
    """Shared paper ledgers, disclosure evidence, and immutable backtest snapshots."""
    __tablename__ = "trading_documents"
    id = Column(String(80), primary_key=True)
    kind = Column(String(20), nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    summary = Column(JSON, nullable=False)
