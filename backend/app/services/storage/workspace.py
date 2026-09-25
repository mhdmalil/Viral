from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Account, Project
from app.services.storage.paths import library_root

WORKSPACE_HANDLE = "workspace"
LIBRARY_VAULT_STATUS = "vault"
LIBRARY_VAULT_NAME = "Library"


def ensure_workspace_account(db: Session) -> Account:
    existing = db.scalar(select(Account).where(Account.handle == WORKSPACE_HANDLE))
    if existing is not None:
        return existing
    account = Account(
        name="Workspace",
        platform="local",
        handle=WORKSPACE_HANDLE,
        description="Hidden default until social accounts are connected.",
        content_strategy="mixed",
        default_clip_count=10,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def is_library_vault(project: Project | None) -> bool:
    return project is not None and project.status == LIBRARY_VAULT_STATUS


def ensure_library_vault(db: Session) -> Project:
    existing = db.scalar(select(Project).where(Project.status == LIBRARY_VAULT_STATUS))
    if existing is not None:
        if not existing.folder_path:
            existing.folder_path = str(library_root())
            db.flush()
        return existing
    account = ensure_workspace_account(db)
    project = Project(
        account_id=account.id,
        name=LIBRARY_VAULT_NAME,
        status=LIBRARY_VAULT_STATUS,
        folder_path=str(library_root()),
        reframe_enabled=0,
    )
    db.add(project)
    db.flush()
    db.refresh(project)
    return project
