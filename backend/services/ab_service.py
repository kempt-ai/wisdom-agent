"""
Investigation Builder (AB) Service

Business logic for CRUD operations on investigations,
definitions, claims, evidence, credibility, and counterarguments.

Uses raw SQL via SQLAlchemy text() to match the existing
knowledge_service.py and parsing_service.py patterns.

Follows singleton pattern used by other services.
"""

import re
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from backend.models.ab_schemas import (
    Investigation, InvestigationSummary, InvestigationCreate, InvestigationUpdate,
    Definition, DefinitionCreate, DefinitionUpdate,
    ABClaim, ABClaimCreate, ABClaimUpdate,
    ABEvidence, ABEvidenceCreate, ABEvidenceUpdate,
    Counterargument, CounterargumentCreate, CounterargumentUpdate,
    SourceCredibility, SourceCredibilityCreate,
    EvidenceCredibility, EvidenceCredibilityCreate,
    ChangelogEntry,
)

logger = logging.getLogger(__name__)


# ============================================================================
# EXCEPTIONS
# ============================================================================

class ABServiceError(Exception):
    """Base exception for Investigation Builder errors"""
    pass


class InvestigationNotFoundError(ABServiceError):
    """Investigation not found"""
    pass


class DefinitionNotFoundError(ABServiceError):
    """Definition not found"""
    pass


class ClaimNotFoundError(ABServiceError):
    """Claim not found"""
    pass


class EvidenceNotFoundError(ABServiceError):
    """Evidence not found"""
    pass


class CounterargumentNotFoundError(ABServiceError):
    """Counterargument not found"""
    pass


class DuplicateSlugError(ABServiceError):
    """Slug already exists within the investigation"""
    pass


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    slug = text.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    return slug[:255]


def _row_to_dict(row) -> dict:
    """Convert a SQLAlchemy Row to a dict."""
    if hasattr(row, '_mapping'):
        return dict(row._mapping)
    return dict(row)


def _parse_json_field(value):
    """Parse a JSON field that might be a string (SQLite) or already parsed."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


# ============================================================================
# SERVICE CLASS
# ============================================================================

class ABService:
    """
    Service for the Investigation Builder.

    Manages CRUD for investigations, definitions, claims,
    evidence, credibility, and counterarguments.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.db = None
        self._initialized = True
        logger.info("ABService initialized")

    def initialize(self, db_connection):
        """Set database connection."""
        self.db = db_connection
        logger.info("ABService database connection set")

    def is_initialized(self) -> bool:
        return self.db is not None

    # ========================================================================
    # INVESTIGATIONS
    # ========================================================================

    async def list_investigations(self) -> List[InvestigationSummary]:
        """List all investigations with summary counts."""
        from sqlalchemy import text

        rows = self.db.execute(text("""
            SELECT i.*,
                   (SELECT COUNT(*) FROM ab_definitions d WHERE d.investigation_id = i.id) AS definition_count,
                   (SELECT COUNT(*) FROM ab_claims c WHERE c.investigation_id = i.id) AS claim_count
            FROM ab_investigations i
            ORDER BY i.updated_at DESC
        """)).fetchall()

        return [
            InvestigationSummary(
                id=r.id, title=r.title, slug=r.slug, status=r.status,
                created_at=r.created_at, updated_at=r.updated_at,
                definition_count=r.definition_count, claim_count=r.claim_count,
            )
            for r in rows
        ]

    async def get_investigation(self, slug: str) -> Optional[Investigation]:
        """Get a full investigation by slug, including definitions and claims."""
        from sqlalchemy import text

        row = self.db.execute(
            text("SELECT * FROM ab_investigations WHERE slug = :slug"),
            {"slug": slug}
        ).fetchone()

        if not row:
            return None

        inv_id = row.id

        # Fetch definitions
        def_rows = self.db.execute(
            text("SELECT * FROM ab_definitions WHERE investigation_id = :inv_id ORDER BY term"),
            {"inv_id": inv_id}
        ).fetchall()

        definitions = [
            Definition(
                id=d.id, investigation_id=d.investigation_id, term=d.term,
                slug=d.slug, definition_html=d.definition_html,
                see_also=_parse_json_field(d.see_also) or [],
                created_at=d.created_at, updated_at=d.updated_at,
            )
            for d in def_rows
        ]

        # Fetch claims with evidence and counterarguments
        claim_rows = self.db.execute(
            text("SELECT * FROM ab_claims WHERE investigation_id = :inv_id ORDER BY position, id"),
            {"inv_id": inv_id}
        ).fetchall()

        claims = []
        for c in claim_rows:
            evidence = await self._get_evidence_for_claim(c.id)
            counterarguments = await self._get_counterarguments_for_claim(c.id)
            claims.append(ABClaim(
                id=c.id, investigation_id=c.investigation_id, title=c.title,
                slug=c.slug, claim_text=c.claim_text,
                exposition_html=c.exposition_html, status=c.status,
                temporal_note=c.temporal_note, position=c.position,
                created_at=c.created_at, updated_at=c.updated_at,
                evidence=evidence, counterarguments=counterarguments,
            ))

        return Investigation(
            id=row.id, title=row.title, slug=row.slug,
            overview_html=row.overview_html, status=row.status,
            created_at=row.created_at, updated_at=row.updated_at,
            created_by=row.created_by, version=row.version,
            definitions=definitions, claims=claims,
        )

    async def create_investigation(self, data: InvestigationCreate) -> Investigation:
        """Create a new investigation."""
        from sqlalchemy import text

        slug = _slugify(data.title)

        # Ensure unique slug
        existing = self.db.execute(
            text("SELECT id FROM ab_investigations WHERE slug = :slug"),
            {"slug": slug}
        ).fetchone()

        if existing:
            # Append a numeric suffix
            counter = 2
            while True:
                new_slug = f"{slug}-{counter}"
                check = self.db.execute(
                    text("SELECT id FROM ab_investigations WHERE slug = :slug"),
                    {"slug": new_slug}
                ).fetchone()
                if not check:
                    slug = new_slug
                    break
                counter += 1

        now = datetime.utcnow()
        result = self.db.execute(
            text("""
                INSERT INTO ab_investigations (title, slug, overview_html, status, created_at, updated_at)
                VALUES (:title, :slug, :overview_html, :status, :created_at, :updated_at)
                RETURNING id
            """),
            {
                "title": data.title, "slug": slug,
                "overview_html": data.overview_html, "status": data.status.value,
                "created_at": now, "updated_at": now,
            }
        )
        inv_id = result.fetchone()[0]
        self.db.commit()

        return await self.get_investigation(slug)

    async def update_investigation(self, slug: str, data: InvestigationUpdate) -> Optional[Investigation]:
        """Update an existing investigation."""
        from sqlalchemy import text

        existing = self.db.execute(
            text("SELECT id FROM ab_investigations WHERE slug = :slug"),
            {"slug": slug}
        ).fetchone()

        if not existing:
            raise InvestigationNotFoundError(f"Investigation '{slug}' not found")

        updates = []
        params = {"slug": slug}

        if data.title is not None:
            updates.append("title = :title")
            params["title"] = data.title
        if data.overview_html is not None:
            updates.append("overview_html = :overview_html")
            params["overview_html"] = data.overview_html
        if data.status is not None:
            updates.append("status = :status")
            params["status"] = data.status.value

        if updates:
            updates.append("updated_at = :updated_at")
            updates.append("version = version + 1")
            params["updated_at"] = datetime.utcnow()

            self.db.execute(
                text(f"UPDATE ab_investigations SET {', '.join(updates)} WHERE slug = :slug"),
                params
            )
            self.db.commit()

        return await self.get_investigation(slug)

    async def delete_investigation(self, slug: str):
        """Delete an investigation and all its children (cascade)."""
        from sqlalchemy import text

        existing = self.db.execute(
            text("SELECT id FROM ab_investigations WHERE slug = :slug"),
            {"slug": slug}
        ).fetchone()

        if not existing:
            raise InvestigationNotFoundError(f"Investigation '{slug}' not found")

        self.db.execute(
            text("DELETE FROM ab_investigations WHERE slug = :slug"),
            {"slug": slug}
        )
        self.db.commit()

    # ========================================================================
    # DEFINITIONS
    # ========================================================================

    async def list_definitions(self, inv_slug: str) -> List[Definition]:
        """List all definitions for an investigation."""
        from sqlalchemy import text

        inv = await self._get_investigation_id(inv_slug)

        rows = self.db.execute(
            text("SELECT * FROM ab_definitions WHERE investigation_id = :inv_id ORDER BY term"),
            {"inv_id": inv}
        ).fetchall()

        return [
            Definition(
                id=d.id, investigation_id=d.investigation_id, term=d.term,
                slug=d.slug, definition_html=d.definition_html,
                see_also=_parse_json_field(d.see_also) or [],
                created_at=d.created_at, updated_at=d.updated_at,
            )
            for d in rows
        ]

    async def get_definition(self, inv_slug: str, def_slug: str) -> Optional[Definition]:
        """Get a single definition by slug."""
        from sqlalchemy import text

        inv_id = await self._get_investigation_id(inv_slug)

        row = self.db.execute(
            text("SELECT * FROM ab_definitions WHERE investigation_id = :inv_id AND slug = :slug"),
            {"inv_id": inv_id, "slug": def_slug}
        ).fetchone()

        if not row:
            return None

        return Definition(
            id=row.id, investigation_id=row.investigation_id, term=row.term,
            slug=row.slug, definition_html=row.definition_html,
            see_also=_parse_json_field(row.see_also) or [],
            created_at=row.created_at, updated_at=row.updated_at,
        )

    async def create_definition(self, inv_slug: str, data: DefinitionCreate) -> Definition:
        """Create a new definition in an investigation."""
        from sqlalchemy import text

        inv_id = await self._get_investigation_id(inv_slug)
        slug = _slugify(data.term)

        now = datetime.utcnow()
        see_also_json = json.dumps(data.see_also)

        self.db.execute(
            text("""
                INSERT INTO ab_definitions (investigation_id, term, slug, definition_html, see_also, created_at, updated_at)
                VALUES (:inv_id, :term, :slug, :def_html, :see_also, :created_at, :updated_at)
            """),
            {
                "inv_id": inv_id, "term": data.term, "slug": slug,
                "def_html": data.definition_html, "see_also": see_also_json,
                "created_at": now, "updated_at": now,
            }
        )
        self.db.commit()

        return await self.get_definition(inv_slug, slug)

    async def update_definition(self, inv_slug: str, def_slug: str, data: DefinitionUpdate) -> Optional[Definition]:
        """Update a definition."""
        from sqlalchemy import text

        inv_id = await self._get_investigation_id(inv_slug)

        existing = self.db.execute(
            text("SELECT id FROM ab_definitions WHERE investigation_id = :inv_id AND slug = :slug"),
            {"inv_id": inv_id, "slug": def_slug}
        ).fetchone()

        if not existing:
            raise DefinitionNotFoundError(f"Definition '{def_slug}' not found")

        updates = []
        params = {"inv_id": inv_id, "slug": def_slug}

        if data.term is not None:
            updates.append("term = :term")
            params["term"] = data.term
        if data.definition_html is not None:
            updates.append("definition_html = :def_html")
            params["def_html"] = data.definition_html
        if data.see_also is not None:
            updates.append("see_also = :see_also")
            params["see_also"] = json.dumps(data.see_also)

        if updates:
            updates.append("updated_at = :updated_at")
            params["updated_at"] = datetime.utcnow()

            self.db.execute(
                text(f"UPDATE ab_definitions SET {', '.join(updates)} WHERE investigation_id = :inv_id AND slug = :slug"),
                params
            )
            self.db.commit()

        return await self.get_definition(inv_slug, def_slug)

    async def delete_definition(self, inv_slug: str, def_slug: str):
        """Delete a definition."""
        from sqlalchemy import text

        inv_id = await self._get_investigation_id(inv_slug)

        result = self.db.execute(
            text("DELETE FROM ab_definitions WHERE investigation_id = :inv_id AND slug = :slug"),
            {"inv_id": inv_id, "slug": def_slug}
        )
        self.db.commit()

        if result.rowcount == 0:
            raise DefinitionNotFoundError(f"Definition '{def_slug}' not found")

    # ========================================================================
    # CLAIMS
    # ========================================================================

    async def list_claims(self, inv_slug: str) -> List[ABClaim]:
        """List all claims for an investigation."""
        from sqlalchemy import text

        inv_id = await self._get_investigation_id(inv_slug)

        rows = self.db.execute(
            text("SELECT * FROM ab_claims WHERE investigation_id = :inv_id ORDER BY position, id"),
            {"inv_id": inv_id}
        ).fetchall()

        claims = []
        for c in rows:
            evidence = await self._get_evidence_for_claim(c.id)
            counterarguments = await self._get_counterarguments_for_claim(c.id)
            claims.append(ABClaim(
                id=c.id, investigation_id=c.investigation_id, title=c.title,
                slug=c.slug, claim_text=c.claim_text,
                exposition_html=c.exposition_html, status=c.status,
                temporal_note=c.temporal_note, position=c.position,
                created_at=c.created_at, updated_at=c.updated_at,
                evidence=evidence, counterarguments=counterarguments,
            ))

        return claims

    async def get_claim(self, inv_slug: str, claim_slug: str) -> Optional[ABClaim]:
        """Get a single claim by slug with evidence and counterarguments."""
        from sqlalchemy import text

        inv_id = await self._get_investigation_id(inv_slug)

        row = self.db.execute(
            text("SELECT * FROM ab_claims WHERE investigation_id = :inv_id AND slug = :slug"),
            {"inv_id": inv_id, "slug": claim_slug}
        ).fetchone()

        if not row:
            return None

        evidence = await self._get_evidence_for_claim(row.id)
        counterarguments = await self._get_counterarguments_for_claim(row.id)

        return ABClaim(
            id=row.id, investigation_id=row.investigation_id, title=row.title,
            slug=row.slug, claim_text=row.claim_text,
            exposition_html=row.exposition_html, status=row.status,
            temporal_note=row.temporal_note, position=row.position,
            created_at=row.created_at, updated_at=row.updated_at,
            evidence=evidence, counterarguments=counterarguments,
        )

    async def create_claim(self, inv_slug: str, data: ABClaimCreate) -> ABClaim:
        """Create a new claim in an investigation."""
        from sqlalchemy import text

        inv_id = await self._get_investigation_id(inv_slug)
        slug = _slugify(data.title)

        now = datetime.utcnow()
        self.db.execute(
            text("""
                INSERT INTO ab_claims (investigation_id, title, slug, claim_text, exposition_html,
                                       status, temporal_note, position, created_at, updated_at)
                VALUES (:inv_id, :title, :slug, :claim_text, :exposition_html,
                        :status, :temporal_note, :position, :created_at, :updated_at)
            """),
            {
                "inv_id": inv_id, "title": data.title, "slug": slug,
                "claim_text": data.claim_text, "exposition_html": data.exposition_html,
                "status": data.status.value, "temporal_note": data.temporal_note,
                "position": data.position, "created_at": now, "updated_at": now,
            }
        )
        self.db.commit()

        return await self.get_claim(inv_slug, slug)

    async def update_claim(self, inv_slug: str, claim_slug: str, data: ABClaimUpdate) -> Optional[ABClaim]:
        """Update a claim."""
        from sqlalchemy import text

        inv_id = await self._get_investigation_id(inv_slug)

        existing = self.db.execute(
            text("SELECT id FROM ab_claims WHERE investigation_id = :inv_id AND slug = :slug"),
            {"inv_id": inv_id, "slug": claim_slug}
        ).fetchone()

        if not existing:
            raise ClaimNotFoundError(f"Claim '{claim_slug}' not found")

        updates = []
        params = {"inv_id": inv_id, "slug": claim_slug}

        if data.title is not None:
            updates.append("title = :title")
            params["title"] = data.title
        if data.claim_text is not None:
            updates.append("claim_text = :claim_text")
            params["claim_text"] = data.claim_text
        if data.exposition_html is not None:
            updates.append("exposition_html = :exposition_html")
            params["exposition_html"] = data.exposition_html
        if data.status is not None:
            updates.append("status = :status")
            params["status"] = data.status.value
        if data.temporal_note is not None:
            updates.append("temporal_note = :temporal_note")
            params["temporal_note"] = data.temporal_note
        if data.position is not None:
            updates.append("position = :position")
            params["position"] = data.position

        if updates:
            updates.append("updated_at = :updated_at")
            params["updated_at"] = datetime.utcnow()

            self.db.execute(
                text(f"UPDATE ab_claims SET {', '.join(updates)} WHERE investigation_id = :inv_id AND slug = :slug"),
                params
            )
            self.db.commit()

        return await self.get_claim(inv_slug, claim_slug)

    async def delete_claim(self, inv_slug: str, claim_slug: str):
        """Delete a claim and its children (cascade)."""
        from sqlalchemy import text

        inv_id = await self._get_investigation_id(inv_slug)

        result = self.db.execute(
            text("DELETE FROM ab_claims WHERE investigation_id = :inv_id AND slug = :slug"),
            {"inv_id": inv_id, "slug": claim_slug}
        )
        self.db.commit()

        if result.rowcount == 0:
            raise ClaimNotFoundError(f"Claim '{claim_slug}' not found")

    # ========================================================================
    # EVIDENCE
    # ========================================================================

    async def add_evidence(self, claim_id: int, data: ABEvidenceCreate) -> ABEvidence:
        """Add evidence to a claim."""
        from sqlalchemy import text

        # Verify claim exists
        claim = self.db.execute(
            text("SELECT id FROM ab_claims WHERE id = :id"),
            {"id": claim_id}
        ).fetchone()
        if not claim:
            raise ClaimNotFoundError(f"Claim {claim_id} not found")

        now = datetime.utcnow()
        anchor_data = json.dumps(data.source_anchor_data) if data.source_anchor_data else None

        result = self.db.execute(
            text("""
                INSERT INTO ab_evidence (claim_id, kb_resource_id, source_title, source_url,
                                         source_type, key_quote, key_point, position, created_at,
                                         source_anchor_type, source_anchor_data)
                VALUES (:claim_id, :kb_resource_id, :source_title, :source_url,
                        :source_type, :key_quote, :key_point, :position, :created_at,
                        :source_anchor_type, :source_anchor_data)
                RETURNING id
            """),
            {
                "claim_id": claim_id, "kb_resource_id": data.kb_resource_id,
                "source_title": data.source_title, "source_url": data.source_url,
                "source_type": data.source_type, "key_quote": data.key_quote,
                "key_point": data.key_point, "position": data.position,
                "created_at": now, "source_anchor_type": data.source_anchor_type,
                "source_anchor_data": anchor_data,
            }
        )
        ev_id = result.fetchone()[0]
        self.db.commit()

        return await self._get_evidence_by_id(ev_id)

    async def update_evidence(self, evidence_id: int, data: ABEvidenceUpdate) -> ABEvidence:
        """Update an evidence item."""
        from sqlalchemy import text

        existing = self.db.execute(
            text("SELECT id FROM ab_evidence WHERE id = :id"),
            {"id": evidence_id}
        ).fetchone()
        if not existing:
            raise EvidenceNotFoundError(f"Evidence {evidence_id} not found")

        updates = []
        params = {"id": evidence_id}

        if data.source_title is not None:
            updates.append("source_title = :source_title")
            params["source_title"] = data.source_title
        if data.source_url is not None:
            updates.append("source_url = :source_url")
            params["source_url"] = data.source_url
        if data.source_type is not None:
            updates.append("source_type = :source_type")
            params["source_type"] = data.source_type
        if data.key_quote is not None:
            updates.append("key_quote = :key_quote")
            params["key_quote"] = data.key_quote
        if data.key_point is not None:
            updates.append("key_point = :key_point")
            params["key_point"] = data.key_point
        if data.position is not None:
            updates.append("position = :position")
            params["position"] = data.position
        if data.source_anchor_type is not None:
            updates.append("source_anchor_type = :source_anchor_type")
            params["source_anchor_type"] = data.source_anchor_type
        if data.source_anchor_data is not None:
            updates.append("source_anchor_data = :source_anchor_data")
            params["source_anchor_data"] = json.dumps(data.source_anchor_data)

        if updates:
            self.db.execute(
                text(f"UPDATE ab_evidence SET {', '.join(updates)} WHERE id = :id"),
                params
            )
            self.db.commit()

        return await self._get_evidence_by_id(evidence_id)

    async def delete_evidence(self, evidence_id: int):
        """Delete an evidence item."""
        from sqlalchemy import text

        result = self.db.execute(
            text("DELETE FROM ab_evidence WHERE id = :id"),
            {"id": evidence_id}
        )
        self.db.commit()

        if result.rowcount == 0:
            raise EvidenceNotFoundError(f"Evidence {evidence_id} not found")

    # ========================================================================
    # COUNTERARGUMENTS
    # ========================================================================

    async def add_counterargument(self, claim_id: int, data: CounterargumentCreate) -> Counterargument:
        """Add a counterargument to a claim."""
        from sqlalchemy import text

        claim = self.db.execute(
            text("SELECT id FROM ab_claims WHERE id = :id"),
            {"id": claim_id}
        ).fetchone()
        if not claim:
            raise ClaimNotFoundError(f"Claim {claim_id} not found")

        now = datetime.utcnow()
        result = self.db.execute(
            text("""
                INSERT INTO ab_counterarguments (claim_id, counter_text, rebuttal_text, position, created_at)
                VALUES (:claim_id, :counter_text, :rebuttal_text, :position, :created_at)
                RETURNING id
            """),
            {
                "claim_id": claim_id, "counter_text": data.counter_text,
                "rebuttal_text": data.rebuttal_text, "position": data.position,
                "created_at": now,
            }
        )
        ca_id = result.fetchone()[0]
        self.db.commit()

        row = self.db.execute(
            text("SELECT * FROM ab_counterarguments WHERE id = :id"),
            {"id": ca_id}
        ).fetchone()

        return Counterargument(
            id=row.id, claim_id=row.claim_id, counter_text=row.counter_text,
            rebuttal_text=row.rebuttal_text, position=row.position,
            created_at=row.created_at,
        )

    async def update_counterargument(self, ca_id: int, data: CounterargumentUpdate) -> Counterargument:
        """Update a counterargument."""
        from sqlalchemy import text

        existing = self.db.execute(
            text("SELECT id FROM ab_counterarguments WHERE id = :id"),
            {"id": ca_id}
        ).fetchone()
        if not existing:
            raise CounterargumentNotFoundError(f"Counterargument {ca_id} not found")

        updates = []
        params = {"id": ca_id}

        if data.counter_text is not None:
            updates.append("counter_text = :counter_text")
            params["counter_text"] = data.counter_text
        if data.rebuttal_text is not None:
            updates.append("rebuttal_text = :rebuttal_text")
            params["rebuttal_text"] = data.rebuttal_text
        if data.position is not None:
            updates.append("position = :position")
            params["position"] = data.position

        if updates:
            self.db.execute(
                text(f"UPDATE ab_counterarguments SET {', '.join(updates)} WHERE id = :id"),
                params
            )
            self.db.commit()

        row = self.db.execute(
            text("SELECT * FROM ab_counterarguments WHERE id = :id"),
            {"id": ca_id}
        ).fetchone()

        return Counterargument(
            id=row.id, claim_id=row.claim_id, counter_text=row.counter_text,
            rebuttal_text=row.rebuttal_text, position=row.position,
            created_at=row.created_at,
        )

    async def delete_counterargument(self, ca_id: int):
        """Delete a counterargument."""
        from sqlalchemy import text

        result = self.db.execute(
            text("DELETE FROM ab_counterarguments WHERE id = :id"),
            {"id": ca_id}
        )
        self.db.commit()

        if result.rowcount == 0:
            raise CounterargumentNotFoundError(f"Counterargument {ca_id} not found")

    # ========================================================================
    # PRIVATE HELPERS
    # ========================================================================

    async def _get_investigation_id(self, slug: str) -> int:
        """Get investigation ID from slug, raising if not found."""
        from sqlalchemy import text

        row = self.db.execute(
            text("SELECT id FROM ab_investigations WHERE slug = :slug"),
            {"slug": slug}
        ).fetchone()

        if not row:
            raise InvestigationNotFoundError(f"Investigation '{slug}' not found")
        return row.id

    async def _get_evidence_for_claim(self, claim_id: int) -> List[ABEvidence]:
        """Get all evidence for a claim."""
        from sqlalchemy import text

        rows = self.db.execute(
            text("SELECT * FROM ab_evidence WHERE claim_id = :claim_id ORDER BY position, id"),
            {"claim_id": claim_id}
        ).fetchall()

        return [
            ABEvidence(
                id=e.id, claim_id=e.claim_id, kb_resource_id=e.kb_resource_id,
                source_title=e.source_title, source_url=e.source_url,
                source_type=e.source_type, key_quote=e.key_quote,
                key_point=e.key_point, position=e.position,
                created_at=e.created_at,
                source_anchor_type=e.source_anchor_type,
                source_anchor_data=_parse_json_field(e.source_anchor_data),
            )
            for e in rows
        ]

    async def _get_evidence_by_id(self, evidence_id: int) -> ABEvidence:
        """Get a single evidence item by ID."""
        from sqlalchemy import text

        row = self.db.execute(
            text("SELECT * FROM ab_evidence WHERE id = :id"),
            {"id": evidence_id}
        ).fetchone()

        if not row:
            raise EvidenceNotFoundError(f"Evidence {evidence_id} not found")

        return ABEvidence(
            id=row.id, claim_id=row.claim_id, kb_resource_id=row.kb_resource_id,
            source_title=row.source_title, source_url=row.source_url,
            source_type=row.source_type, key_quote=row.key_quote,
            key_point=row.key_point, position=row.position,
            created_at=row.created_at,
            source_anchor_type=row.source_anchor_type,
            source_anchor_data=_parse_json_field(row.source_anchor_data),
        )

    async def _get_counterarguments_for_claim(self, claim_id: int) -> List[Counterargument]:
        """Get all counterarguments for a claim."""
        from sqlalchemy import text

        rows = self.db.execute(
            text("SELECT * FROM ab_counterarguments WHERE claim_id = :claim_id ORDER BY position, id"),
            {"claim_id": claim_id}
        ).fetchall()

        return [
            Counterargument(
                id=ca.id, claim_id=ca.claim_id, counter_text=ca.counter_text,
                rebuttal_text=ca.rebuttal_text, position=ca.position,
                created_at=ca.created_at,
            )
            for ca in rows
        ]


# ============================================================================
# SINGLETON GETTER
# ============================================================================

_service_instance: Optional[ABService] = None


def get_ab_service() -> ABService:
    """Get the Investigation Builder service singleton."""
    global _service_instance
    if _service_instance is None:
        _service_instance = ABService()
    return _service_instance
