from enum import Enum


class UserActivityType(str, Enum):
    """User activity types for entity operations."""

    ENTITY_CREATE = "entity_create"  # Creating new entities
    ENTITY_EDIT = "entity_edit"  # Editing existing entities
    ENTITY_REVERT = "entity_revert"  # Reverting entity changes
    ENTITY_DELETE = "entity_delete"  # Deleting entities
    ENTITY_UNDELETE = "entity_undelete"  # Undeleting entities
    ENTITY_LOCK = "entity_lock"  # Locking entities
    ENTITY_UNLOCK = "entity_unlock"  # Unlocking entities
    ENTITY_ARCHIVE = "entity_archive"  # Archiving entities
    ENTITY_UNARCHIVE = "entity_unarchive"  # Unarchiving entities
    THANK_SENT = "thank_sent"  # Sending thanks for a revision
    THANK_RECEIVED = "thank_received"  # Receiving thanks for a revision
    ENDORSEMENT_GIVEN = "endorsement_given"  # Giving endorsement to a statement
    ENDORSEMENT_WITHDRAWN = (
        "endorsement_withdrawn"  # Withdrawing endorsement from a statement
    )


class EntityChangeType(str, Enum):
    """Granular kind of change for the recent-changes list."""

    ENTITY_CREATE = "entity_create"  # New item/property/lexeme
    ENTITY_IMPORT = "entity_import"  # Bulk/system import (special case)
    LABEL_UPDATE = "label_update"
    LABEL_DELETE = "label_delete"
    DESCRIPTION_UPDATE = "description_update"
    DESCRIPTION_DELETE = "description_delete"
    ALIASES_UPDATE = "aliases_update"
    ALIASES_DELETE = "aliases_delete"
    STATEMENT_ADD = "statement_add"
    STATEMENT_REMOVE = "statement_remove"
    STATEMENT_PATCH = "statement_patch"
    STATEMENTS_BATCH = "statements_batch"  # Multi-statement entity update
    LEXEME_UPDATE = "lexeme_update"  # Lemmas/senses/forms
    ENTITY_REVERT = "entity_revert"
    ENTITY_LOCK = "entity_lock"
    ENTITY_UNLOCK = "entity_unlock"
    THANK_SENT = "thank_sent"
