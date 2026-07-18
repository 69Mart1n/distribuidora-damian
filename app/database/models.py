from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarativa de SQLAlchemy."""


def utc_now() -> datetime:
    return datetime.now(UTC)


Money = Numeric(12, 2)
Percentage = Numeric(7, 3)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class Settings(Base, TimestampMixin):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_name: Mapped[str] = mapped_column(String(160), nullable=False)
    business_phone: Mapped[str | None] = mapped_column(String(50))
    business_address: Mapped[str | None] = mapped_column(String(220))
    business_email: Mapped[str | None] = mapped_column(String(160))
    business_logo_path: Mapped[str | None] = mapped_column(String(500))
    currency_symbol: Mapped[str] = mapped_column(String(8), default="$", nullable=False)
    receipt_prefix: Mapped[str] = mapped_column(String(12), default="BD", nullable=False)
    next_receipt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    default_rounding: Mapped[str] = mapped_column(String(40), default="peso_entero", nullable=False)
    backup_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    backup_frequency: Mapped[str] = mapped_column(String(40), default="daily", nullable=False)
    backup_retention_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    monthly_retention_count: Mapped[int] = mapped_column(Integer, default=12, nullable=False)
    exports_path: Mapped[str | None] = mapped_column(String(500))
    backups_path: Mapped[str | None] = mapped_column(String(500))
    theme: Mapped[str] = mapped_column(String(30), default="light", nullable=False)


class Supplier(Base, TimestampMixin):
    __tablename__ = "suppliers"
    __table_args__ = (UniqueConstraint("normalized_name", name="uq_suppliers_normalized_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(160), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(160))
    phone: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(160))
    notes: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    brands: Mapped[list[Brand]] = relationship(back_populates="supplier")
    products: Mapped[list[Product]] = relationship(back_populates="supplier")


class Category(Base, TimestampMixin):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("normalized_name", name="uq_categories_normalized_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    products: Mapped[list[Product]] = relationship(back_populates="category")


class Brand(Base, TimestampMixin):
    __tablename__ = "brands"
    __table_args__ = (
        UniqueConstraint("normalized_name", "supplier_id", name="uq_brands_name_supplier"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(140), nullable=False)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    supplier: Mapped[Supplier | None] = relationship(back_populates="brands")
    products: Mapped[list[Product]] = relationship(back_populates="brand")


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    internal_code: Mapped[str | None] = mapped_column(String(40), unique=True)
    barcode: Mapped[str | None] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(220), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True, nullable=False)
    brand_id: Mapped[int | None] = mapped_column(ForeignKey("brands.id"), index=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"),
        index=True,
        nullable=False,
    )
    presentation: Mapped[str] = mapped_column(String(160), nullable=False)
    weight_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    weight_unit: Mapped[str | None] = mapped_column(String(20))
    units_per_package: Mapped[int | None] = mapped_column(Integer)
    purchase_price: Mapped[Decimal | None] = mapped_column(Money)
    wholesale_price: Mapped[Decimal | None] = mapped_column(Money)
    retail_price: Mapped[Decimal | None] = mapped_column(Money)
    suggested_wholesale_price: Mapped[Decimal | None] = mapped_column(Money)
    profit_margin_percentage: Mapped[Decimal | None] = mapped_column(Percentage)
    requires_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    supplier: Mapped[Supplier] = relationship(back_populates="products")
    brand: Mapped[Brand | None] = relationship(back_populates="products")
    category: Mapped[Category] = relationship(back_populates="products")
    price_history: Mapped[list[PriceHistory]] = relationship(back_populates="product")
    receipt_items: Mapped[list[ReceiptItem]] = relationship(back_populates="product")


class PriceUpdateBatch(Base):
    __tablename__ = "price_update_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    description: Mapped[str] = mapped_column(String(260), nullable=False)
    target_type: Mapped[str] = mapped_column(String(40), nullable=False)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    brand_id: Mapped[int | None] = mapped_column(ForeignKey("brands.id"))
    percentage: Mapped[Decimal | None] = mapped_column(Percentage)
    fixed_amount: Mapped[Decimal | None] = mapped_column(Money)
    operation: Mapped[str] = mapped_column(String(60), nullable=False)
    price_type: Mapped[str] = mapped_column(String(20), nullable=False)
    rounding_rule: Mapped[str] = mapped_column(String(40), nullable=False)
    products_affected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    applied_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    reverted_at: Mapped[datetime | None] = mapped_column(DateTime)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    price_history: Mapped[list[PriceHistory]] = relationship(back_populates="batch")


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True, nullable=False)
    price_type: Mapped[str] = mapped_column(String(20), nullable=False)
    old_price: Mapped[Decimal | None] = mapped_column(Money)
    new_price: Mapped[Decimal | None] = mapped_column(Money)
    percentage_change: Mapped[Decimal | None] = mapped_column(Percentage)
    fixed_change: Mapped[Decimal | None] = mapped_column(Money)
    change_source: Mapped[str] = mapped_column(String(60), nullable=False)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"))
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("price_update_batches.id"))
    reason: Mapped[str | None] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    changed_by: Mapped[str | None] = mapped_column(String(120))

    product: Mapped[Product] = relationship(back_populates="price_history")
    batch: Mapped[PriceUpdateBatch | None] = relationship(back_populates="price_history")


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    business_name: Mapped[str | None] = mapped_column(String(180))
    document: Mapped[str | None] = mapped_column(String(80))
    phone: Mapped[str | None] = mapped_column(String(50), index=True)
    alternative_phone: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(String(240))
    email: Mapped[str | None] = mapped_column(String(160))
    customer_type: Mapped[str] = mapped_column(String(40), default="wholesale", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    receipts: Mapped[list[Receipt]] = relationship(back_populates="customer")


class Receipt(Base, TimestampMixin):
    __tablename__ = "receipts"
    __table_args__ = (UniqueConstraint("receipt_code", name="uq_receipts_receipt_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    receipt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    receipt_code: Mapped[str] = mapped_column(String(40), nullable=False)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"))
    customer_name_snapshot: Mapped[str] = mapped_column(String(180), nullable=False)
    customer_phone_snapshot: Mapped[str | None] = mapped_column(String(50))
    customer_address_snapshot: Mapped[str | None] = mapped_column(String(240))
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Money, default=Decimal("0.00"), nullable=False)
    discount_type: Mapped[str | None] = mapped_column(String(30))
    discount_value: Mapped[Decimal] = mapped_column(Money, default=Decimal("0.00"), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Money, default=Decimal("0.00"), nullable=False)
    total: Mapped[Decimal] = mapped_column(Money, default=Decimal("0.00"), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(40), default="cash", nullable=False)
    payment_status: Mapped[str] = mapped_column(String(40), default="paid", nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(Money, default=Decimal("0.00"), nullable=False)
    pending_amount: Mapped[Decimal] = mapped_column(Money, default=Decimal("0.00"), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancellation_reason: Mapped[str | None] = mapped_column(Text)

    customer: Mapped[Customer | None] = relationship(back_populates="receipts")
    items: Mapped[list[ReceiptItem]] = relationship(
        back_populates="receipt",
        cascade="all, delete-orphan",
    )
    payments: Mapped[list[ReceiptPayment]] = relationship(
        back_populates="receipt",
        cascade="all, delete-orphan",
    )
    revisions: Mapped[list[ReceiptRevision]] = relationship(
        back_populates="receipt",
        cascade="all, delete-orphan",
    )


class ReceiptItem(Base):
    __tablename__ = "receipt_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    receipt_id: Mapped[int] = mapped_column(ForeignKey("receipts.id"), nullable=False)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    product_code_snapshot: Mapped[str | None] = mapped_column(String(40))
    product_name_snapshot: Mapped[str] = mapped_column(String(220), nullable=False)
    presentation_snapshot: Mapped[str | None] = mapped_column(String(160))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Money, nullable=False)
    discount_percentage: Mapped[Decimal] = mapped_column(
        Percentage,
        default=Decimal("0"),
        nullable=False,
    )
    discount_amount: Mapped[Decimal] = mapped_column(Money, default=Decimal("0.00"), nullable=False)
    line_subtotal: Mapped[Decimal] = mapped_column(Money, nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Money, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    receipt: Mapped[Receipt] = relationship(back_populates="items")
    product: Mapped[Product | None] = relationship(back_populates="receipt_items")


class ReceiptPayment(Base):
    __tablename__ = "receipt_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    receipt_id: Mapped[int] = mapped_column(ForeignKey("receipts.id"), index=True, nullable=False)
    payment_method: Mapped[str] = mapped_column(String(40), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    receipt: Mapped[Receipt] = relationship(back_populates="payments")


class ReceiptRevision(Base):
    __tablename__ = "receipt_revisions"
    __table_args__ = (
        UniqueConstraint("receipt_id", "revision_number", name="uq_receipt_revision_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    receipt_id: Mapped[int] = mapped_column(ForeignKey("receipts.id"), index=True, nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(300), nullable=False)
    customer_name_snapshot: Mapped[str] = mapped_column(String(180), nullable=False)
    customer_phone_snapshot: Mapped[str | None] = mapped_column(String(50))
    customer_address_snapshot: Mapped[str | None] = mapped_column(String(240))
    payment_method: Mapped[str] = mapped_column(String(40), nullable=False)
    payment_status: Mapped[str] = mapped_column(String(40), nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(Money, nullable=False)
    pending_amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    total: Mapped[Decimal] = mapped_column(Money, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    receipt: Mapped[Receipt] = relationship(back_populates="revisions")
    items: Mapped[list[ReceiptRevisionItem]] = relationship(
        back_populates="revision",
        cascade="all, delete-orphan",
    )


class ReceiptRevisionItem(Base):
    __tablename__ = "receipt_revision_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    revision_id: Mapped[int] = mapped_column(
        ForeignKey("receipt_revisions.id"),
        index=True,
        nullable=False,
    )
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    product_code_snapshot: Mapped[str | None] = mapped_column(String(40))
    product_name_snapshot: Mapped[str] = mapped_column(String(220), nullable=False)
    presentation_snapshot: Mapped[str | None] = mapped_column(String(160))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Money, nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Money, nullable=False)

    revision: Mapped[ReceiptRevision] = relationship(back_populates="items")


class ImportJob(Base):
    __tablename__ = "imports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(260), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(260), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    total_rows_detected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_rows_imported: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_rows_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_errors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    rows: Mapped[list[ImportRow]] = relationship(back_populates="import_job")


class ImportRow(Base):
    __tablename__ = "import_rows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_id: Mapped[int] = mapped_column(ForeignKey("imports.id"), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    supplier_detected: Mapped[str | None] = mapped_column(String(160))
    product_name_detected: Mapped[str | None] = mapped_column(String(220))
    presentation_detected: Mapped[str | None] = mapped_column(String(160))
    price_detected: Mapped[Decimal | None] = mapped_column(Money)
    discount_detected: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    linked_product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))

    import_job: Mapped[ImportJob] = relationship(back_populates="rows")


class ExportJob(Base):
    __tablename__ = "exports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    export_type: Mapped[str] = mapped_column(String(60), nullable=False)
    format: Mapped[str] = mapped_column(String(20), nullable=False)
    filename: Mapped[str] = mapped_column(String(260), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    filters_json: Mapped[str | None] = mapped_column(Text)
    total_products: Mapped[int | None] = mapped_column(Integer)
    receipt_id: Mapped[int | None] = mapped_column(ForeignKey("receipts.id"))


class Backup(Base):
    __tablename__ = "backups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(260), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    backup_type: Mapped[str] = mapped_column(String(60), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(40), nullable=False)
