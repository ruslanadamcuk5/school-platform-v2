"""Platform service catalog and activation API.

Administrators switch functionality on or off at any level of the hierarchy.
The most specific activation wins, so a republic-wide service can be disabled
for one school without affecting the rest of the country.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep, ensure_scope_access, require_permission
from app.core.scopes import COUNTRY_SCOPE_ID, SCOPE_DEPTH
from app.models.iam import User
from app.models.system import Service, ServiceActivation
from app.schemas.services import (
    EffectiveServiceOut,
    MyServicesOut,
    ServiceActivationOut,
    ServiceActivationSet,
    ServiceListOut,
    ServiceOut,
)
from app.services.access import pick_service_state, scope_ancestors
from app.services.registry import SERVICE_BY_CODE

router = APIRouter(prefix="/services", tags=["system"])

ServicesRead = Annotated[User, Depends(require_permission("system.services.read"))]
ServicesWrite = Annotated[
    User, Depends(require_permission("system.services.write"))
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _resolve_scope(
    scope_type: str, scope_id: uuid.UUID | None
) -> tuple[str, uuid.UUID]:
    if scope_type not in SCOPE_DEPTH:
        raise HTTPException(status_code=422, detail="Unknown scope type")
    if scope_type == "country":
        return scope_type, COUNTRY_SCOPE_ID
    if scope_id is None:
        raise HTTPException(
            status_code=422,
            detail="scope_id is required for a non-country scope",
        )
    return scope_type, scope_id


def _fallback_services() -> list[Service]:
    return [
        Service(
            code=manifest.code,
            name=manifest.name,
            description=manifest.description,
            version=manifest.version,
            category=manifest.category,
            api_prefix=manifest.api_prefix,
            icon=manifest.icon,
            default_enabled=manifest.default_enabled,
            is_core=manifest.is_core,
            status=manifest.status,
            manifest=manifest.manifest_payload,
        )
        for manifest in SERVICE_BY_CODE.values()
    ]


async def _all_services(session) -> list[Service]:
    services = list((await session.execute(select(Service))).scalars().all())
    return services or _fallback_services()


# --------------------------------------------------------------------- catalog
@router.get("", response_model=ServiceListOut, summary="Каталог сервисов")
async def list_services(current_user: ServicesRead, session: SessionDep):
    services = await _all_services(session)
    return ServiceListOut(
        items=[ServiceOut.model_validate(service) for service in services],
        total=len(services),
    )


@router.get(
    "/effective",
    response_model=MyServicesOut,
    summary="Действующие сервисы для области",
)
async def effective_services(
    current_user: ServicesRead,
    session: SessionDep,
    scope_type: str = Query(default="country"),
    scope_id: uuid.UUID | None = Query(default=None),
):
    resolved_type, resolved_id = _resolve_scope(scope_type, scope_id)
    await ensure_scope_access(session, current_user, resolved_type, resolved_id)

    scopes = await scope_ancestors(session, resolved_type, resolved_id)
    # Load the whole chain so the answer is identical to the user resolver.
    chain = list(
        (
            await session.execute(
                select(ServiceActivation)
            )
        )
        .scalars()
        .all()
    )
    by_service: dict[str, list[ServiceActivation]] = {}
    for activation in chain:
        if (activation.scope_type, activation.scope_id) not in scopes:
            continue
        by_service.setdefault(activation.service_code, []).append(activation)

    items: list[EffectiveServiceOut] = []
    for service in await _all_services(session):
        state = pick_service_state(
            service.code,
            default_enabled=service.default_enabled,
            is_core=service.is_core,
            activations=by_service.get(service.code, []),
        )
        items.append(
            EffectiveServiceOut(
                code=service.code,
                name=service.name,
                description=service.description,
                icon=service.icon,
                category=service.category,
                api_prefix=service.api_prefix,
                status=service.status,
                enabled=state.enabled,
                source=state.source,
                permission_codes=[],
            )
        )
    items.sort(key=lambda item: (item.category, item.name))
    return MyServicesOut(items=items, total=len(items))


@router.get(
    "/{service_code}",
    response_model=ServiceOut,
    summary="Карточка сервиса",
)
async def get_service(
    service_code: str,
    current_user: ServicesRead,
    session: SessionDep,
):
    services = await _all_services(session)
    for service in services:
        if service.code.lower() == service_code.lower():
            return ServiceOut.model_validate(service)
    raise HTTPException(status_code=404, detail="Service not found")


# ------------------------------------------------------------------ activation
@router.get(
    "/{service_code}/activation",
    response_model=ServiceActivationOut,
    summary="Активация сервиса в области",
)
async def get_activation(
    service_code: str,
    current_user: ServicesRead,
    session: SessionDep,
    scope_type: str = Query(default="country"),
    scope_id: uuid.UUID | None = Query(default=None),
):
    resolved_type, resolved_id = _resolve_scope(scope_type, scope_id)
    await ensure_scope_access(session, current_user, resolved_type, resolved_id)
    activation = (
        await session.execute(
            select(ServiceActivation).where(
                ServiceActivation.service_code == service_code,
                ServiceActivation.scope_type == resolved_type,
                ServiceActivation.scope_id == resolved_id,
            )
        )
    ).scalar_one_or_none()
    if activation is None:
        raise HTTPException(status_code=404, detail="Activation not found")
    return ServiceActivationOut.model_validate(activation)


@router.put(
    "/{service_code}/activation",
    response_model=ServiceActivationOut,
    summary="Включить или отключить сервис",
)
async def set_activation(
    service_code: str,
    payload: ServiceActivationSet,
    current_user: ServicesWrite,
    session: SessionDep,
    scope_type: str = Query(default="country"),
    scope_id: uuid.UUID | None = Query(default=None),
):
    resolved_type, resolved_id = _resolve_scope(scope_type, scope_id)
    await ensure_scope_access(session, current_user, resolved_type, resolved_id)

    service = (
        await session.execute(
            select(Service).where(Service.code == service_code)
        )
    ).scalar_one_or_none()
    published = SERVICE_BY_CODE.get(service_code)
    if service is None and published is None:
        raise HTTPException(status_code=404, detail="Service not found")
    is_core = bool(
        (service is not None and service.is_core)
        or (published is not None and published.is_core)
    )
    if is_core and not payload.enabled:
        raise HTTPException(
            status_code=409,
            detail="Core platform services cannot be disabled",
        )

    activation = (
        await session.execute(
            select(ServiceActivation).where(
                ServiceActivation.service_code == service_code,
                ServiceActivation.scope_type == resolved_type,
                ServiceActivation.scope_id == resolved_id,
            )
        )
    ).scalar_one_or_none()
    stamp = _now()
    if activation is None:
        activation = ServiceActivation(
            id=uuid.uuid4(),
            service_code=service_code,
            scope_type=resolved_type,
            scope_id=resolved_id,
            depth=SCOPE_DEPTH[resolved_type],
            enabled=payload.enabled,
            config=payload.config,
            updated_by=current_user.id,
            updated_at=stamp,
        )
        session.add(activation)
    else:
        activation.enabled = payload.enabled
        activation.config = payload.config
        activation.depth = SCOPE_DEPTH[resolved_type]
        activation.updated_by = current_user.id
        activation.updated_at = stamp
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=409, detail="Activation already exists"
        ) from exc
    return ServiceActivationOut.model_validate(activation)


@router.delete(
    "/{service_code}/activation",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Снять активацию и вернуть наследование",
)
async def delete_activation(
    service_code: str,
    current_user: ServicesWrite,
    session: SessionDep,
    scope_type: str = Query(default="country"),
    scope_id: uuid.UUID | None = Query(default=None),
):
    resolved_type, resolved_id = _resolve_scope(scope_type, scope_id)
    await ensure_scope_access(session, current_user, resolved_type, resolved_id)
    activation = (
        await session.execute(
            select(ServiceActivation).where(
                ServiceActivation.service_code == service_code,
                ServiceActivation.scope_type == resolved_type,
                ServiceActivation.scope_id == resolved_id,
            )
        )
    ).scalar_one_or_none()
    if activation is None:
        raise HTTPException(status_code=404, detail="Activation not found")
    await session.delete(activation)
    await session.commit()
