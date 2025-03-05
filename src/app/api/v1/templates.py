from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio.session import AsyncSession

from ...core.auth.auth import get_current_user
from ...core.db.database import async_get_db
from ...crud.crud_host_templates import (
    create_host_template,
    delete_host_template,
    get_host_template,
    get_host_template_headers,
)
from ...crud.crud_range_templates import (
    create_range_template,
    delete_range_template,
    get_range_template,
    get_range_template_headers,
)
from ...crud.crud_subnet_templates import (
    create_subnet_template,
    delete_subnet_template,
    get_subnet_template,
    get_subnet_template_headers,
)
from ...crud.crud_vpc_templates import (
    create_vpc_template,
    delete_vpc_template,
    get_vpc_template,
    get_vpc_template_headers,
)
from ...models.user_model import UserModel
from ...schemas.template_host_schema import (
    TemplateHostBaseSchema,
    TemplateHostID,
    TemplateHostSchema,
)
from ...schemas.template_range_schema import (
    TemplateRangeBaseSchema,
    TemplateRangeHeaderSchema,
    TemplateRangeID,
    TemplateRangeSchema,
)
from ...schemas.template_subnet_schema import (
    TemplateSubnetBaseSchema,
    TemplateSubnetHeaderSchema,
    TemplateSubnetID,
    TemplateSubnetSchema,
)
from ...schemas.template_vpc_schema import (
    TemplateVPCBaseSchema,
    TemplateVPCHeaderSchema,
    TemplateVPCID,
    TemplateVPCSchema,
)
from ...validators.id import is_valid_uuid4

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("/ranges")
async def get_range_template_headers_endpoint(
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> list[TemplateRangeHeaderSchema]:
    """Get a list of range template headers.

    Args:
    ----
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        list[TemplateRangeID]: List of range template headers. For admin users, shows all templates.
                               For regular users, shows only templates they own.

    """
    # If user is admin, get all templates, otherwise only get templates owned by the user
    user_id = None if current_user.is_admin else current_user.id
    range_headers = await get_range_template_headers(db, user_id=user_id)

    if not range_headers:
        detail = (
            "No range templates found!"
            if current_user.is_admin
            else "Unable to find any range templates that you own!"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )

    return [
        TemplateRangeHeaderSchema.model_validate(header, from_attributes=True)
        for header in range_headers
    ]


@router.get("/ranges/{range_id}")
async def get_range_template_endpoint(
    range_id: str,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> TemplateRangeSchema:
    """Get a range template.

    Args:
    ----
        range_id (str): ID of the range.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        TemplateRangeSchema: Range template data from database. Admin users can access any template.

    """
    if not is_valid_uuid4(range_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID provided is not a valid UUID4.",
        )

    # For admin users, don't filter by user_id to allow access to all templates
    user_id = None if current_user.is_admin else current_user.id

    # Get the template
    range_template = await get_range_template(
        db, TemplateRangeID(id=range_id), user_id=user_id
    )

    if not range_template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Range with ID: {range_id} not found or you don't have access to it!",
        )

    return TemplateRangeSchema.model_validate(range_template, from_attributes=True)


@router.post("/ranges")
async def upload_range_template_endpoint(
    range_template: TemplateRangeBaseSchema,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> TemplateRangeID:
    """Upload a range template.

    Args:
    ----
        range_template (TemplateRangeBaseSchema): OpenLabs compliant range template object.
        db (AsynSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        TemplateRangeID: Identity of the range template.

    """
    created_range = await create_range_template(db, range_template, current_user.id)
    return TemplateRangeID.model_validate(created_range, from_attributes=True)


@router.delete("/ranges/{range_id}")
async def delete_range_template_endpoint(
    range_id: str,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> bool:
    """Delete a range template.

    Args:
    ----
        range_id (str): Id of the range template.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        bool: True if successfully deleted. False otherwise.

    """
    # Invalid UUID4 ID
    if not is_valid_uuid4(range_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID provided is not a valid UUID4.",
        )

    # For admin users, don't filter by user_id to allow access to all templates
    user_id = None if current_user.is_admin else current_user.id

    range_template = await get_range_template(
        db, TemplateRangeID(id=range_id), user_id=user_id
    )

    # Does not exist
    if not range_template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Range template with id: {range_id} not found or you don't have access to it!",
        )

    # Not standalone template
    if not range_template.is_standalone():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete range template because it is not a standalone template.",
        )

    return await delete_range_template(db, range_template)


@router.get("/vpcs")
async def get_vpc_template_headers_endpoint(
    standalone_only: bool = True,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> list[TemplateVPCHeaderSchema]:
    """Get a list of vpc template headers.

    Args:
    ----
        standalone_only (bool): Return only standalone VPC templates (not part of a range template). Defaults to True.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        list[TemplateVPCID]: List of vpc template headers owned by the current user.

    """
    # If user is admin, get all templates, otherwise only get templates owned by the user
    user_id = None if current_user.is_admin else current_user.id

    vpc_headers = await get_vpc_template_headers(
        db, user_id=user_id, standalone_only=standalone_only
    )

    if not vpc_headers:
        standalone_text = " standalone" if standalone_only else ""
        detail = (
            f"No{standalone_text} VPC templates found!"
            if current_user.is_admin
            else f"Unable to find any{standalone_text} VPC templates that you own!"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )

    return [
        TemplateVPCHeaderSchema.model_validate(header, from_attributes=True)
        for header in vpc_headers
    ]


@router.get("/vpcs/{vpc_id}")
async def get_vpc_template_endpoint(
    vpc_id: str,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> TemplateVPCSchema:
    """Get a VPC template.

    Args:
    ----
        vpc_id (str): ID of the VPC template.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        TemplateVPCSchema: Template VPC data from database if it belongs to the user.

    """
    if not is_valid_uuid4(vpc_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID provided is not a valid UUID4.",
        )

    # For admin users, don't filter by user_id to allow access to all templates
    user_id = None if current_user.is_admin else current_user.id

    # Get the template
    vpc_template = await get_vpc_template(db, TemplateVPCID(id=vpc_id), user_id=user_id)

    if not vpc_template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VPC with ID: {vpc_id} not found or you don't have access to it!",
        )

    return TemplateVPCSchema.model_validate(vpc_template, from_attributes=True)


@router.post("/vpcs")
async def upload_vpc_template_endpoint(
    vpc_template: TemplateVPCBaseSchema,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> TemplateVPCID:
    """Upload a VPC template.

    Args:
    ----
        vpc_template (TemplateVPCBaseSchema): OpenLabs compliant VPC object.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        TemplateVPCID: Identity of the VPC template.

    """
    # Create the template with the current user as the owner
    created_vpc = await create_vpc_template(db, vpc_template, owner_id=current_user.id)
    return TemplateVPCID.model_validate(created_vpc, from_attributes=True)


@router.delete("/vpcs/{vpc_id}")
async def delete_vpc_template_endpoint(
    vpc_id: str,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> bool:
    """Delete a VPC template.

    Args:
    ----
        vpc_id (str): Id of the VPC template.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        bool: True if successfully deleted. False otherwise.

    """
    # Invalid UUID4 ID
    if not is_valid_uuid4(vpc_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID provided is not a valid UUID4.",
        )

    # For admin users, don't filter by user_id to allow access to all templates
    user_id = None if current_user.is_admin else current_user.id

    vpc_template = await get_vpc_template(db, TemplateVPCID(id=vpc_id), user_id=user_id)

    # Does not exist
    if not vpc_template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VPC template with id: {vpc_id} not found or you don't have access to it!",
        )

    # Not standalone template
    if not vpc_template.is_standalone():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete VPC template because it is not a standalone template. Connected to range: {vpc_template.range_id}",
        )

    return await delete_vpc_template(db, vpc_template)


@router.get("/subnets")
async def get_subnet_template_headers_endpoint(
    standalone_only: bool = True,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> list[TemplateSubnetHeaderSchema]:
    """Get a list of subnet template headers.

    Args:
    ----
        standalone_only (bool): Return only standalone subnet templates (not part of a range/vpc template). Defaults to True.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        list[TemplateSubnetHeaderSchema]: List of subnet template headers owned by the current user.

    """
    # If user is admin, get all templates, otherwise only get templates owned by the user
    user_id = None if current_user.is_admin else current_user.id

    # Get subnet headers
    subnet_headers = await get_subnet_template_headers(
        db, standalone_only=standalone_only, user_id=user_id
    )

    if not subnet_headers:
        standalone_text = " standalone" if standalone_only else ""
        detail = (
            f"No{standalone_text} subnet templates found!"
            if current_user.is_admin
            else f"Unable to find any{standalone_text} subnet templates that you own!"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )

    return [
        TemplateSubnetHeaderSchema.model_validate(header, from_attributes=True)
        for header in subnet_headers
    ]


@router.get("/subnets/{subnet_id}")
async def get_subnet_template_endpoint(
    subnet_id: str,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> TemplateSubnetSchema:
    """Get a subnet template.

    Args:
    ----
        subnet_id (str): ID of the subnet.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        TemplateSubnetSchema: Subnet data from database. Admin users can access any template.

    """
    if not is_valid_uuid4(subnet_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID provided is not a valid UUID4.",
        )

    # For admin users, don't filter by user_id to allow access to all templates
    user_id = None if current_user.is_admin else current_user.id

    subnet_template = await get_subnet_template(
        db, TemplateSubnetID(id=subnet_id), user_id=user_id
    )

    if not subnet_template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subnet with ID: {subnet_id} not found or you don't have access to it!",
        )

    return TemplateSubnetSchema.model_validate(subnet_template, from_attributes=True)


@router.post("/subnets")
async def upload_subnet_template_endpoint(
    subnet_template: TemplateSubnetBaseSchema,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> TemplateSubnetID:
    """Upload a subnet template.

    Args:
    ----
        subnet_template (TemplateSubnetBaseSchema): OpenLabs compliant subnet template object.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        TemplateSubnetID: Identity of the subnet template.

    """
    # Create subnet with current user as owner
    created_subnet = await create_subnet_template(
        db, subnet_template, owner_id=current_user.id
    )

    return TemplateSubnetID.model_validate(created_subnet, from_attributes=True)


@router.delete("/subnets/{subnet_id}")
async def delete_subnet_template_endpoint(
    subnet_id: str,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> bool:
    """Delete a subnet template.

    Args:
    ----
        subnet_id (str): Id of the subnet template.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        bool: True if successfully deleted. False otherwise.

    """
    # Invalid UUID4 ID
    if not is_valid_uuid4(subnet_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID provided is not a valid UUID4.",
        )

    # For admin users, don't filter by user_id to allow access to all templates
    user_id = None if current_user.is_admin else current_user.id

    subnet_template = await get_subnet_template(
        db, TemplateSubnetID(id=subnet_id), user_id=user_id
    )

    # Does not exist
    if not subnet_template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subnet template with id: {subnet_id} not found or you don't have access to it!",
        )

    # Not standalone template
    if not subnet_template.is_standalone():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete subnet template because it is not a standalone template. Connected to VPC: {subnet_template.vpc_id}",
        )

    return await delete_subnet_template(db, subnet_template)


@router.get("/hosts")
async def get_host_template_headers_endpoint(
    standalone_only: bool = True,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> list[TemplateHostSchema]:
    """Get a list of host template headers.

    Args:
    ----
        standalone_only (bool): Return only standalone host templates (not part of a range/vpc/subnet template). Defaults to True.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        list[TemplateHostID]: List of host template UUIDs owned by the current user.

    """
    # If user is admin, get all templates, otherwise only get templates owned by the user
    user_id = None if current_user.is_admin else current_user.id

    # Get host headers
    host_headers = await get_host_template_headers(
        db, standalone_only=standalone_only, user_id=user_id
    )

    if not host_headers:
        standalone_text = " standalone" if standalone_only else ""
        detail = (
            f"No{standalone_text} host templates found!"
            if current_user.is_admin
            else f"Unable to find any{standalone_text} host templates that you own!"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )

    return [
        TemplateHostSchema.model_validate(header, from_attributes=True)
        for header in host_headers
    ]


@router.get("/hosts/{host_id}")
async def get_host_template_endpoint(
    host_id: str,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> TemplateHostSchema:
    """Get a host template.

    Args:
    ----
        host_id (str): Id of the host.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        TemplateHostSchema: Host data from database. Admin users can access any template.

    """
    if not is_valid_uuid4(host_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID provided is not a valid UUID4.",
        )

    # For admin users, don't filter by user_id to allow access to all templates
    user_id = None if current_user.is_admin else current_user.id

    host_template = await get_host_template(
        db, TemplateHostID(id=host_id), user_id=user_id
    )

    if not host_template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Host with ID: {host_id} not found or you don't have access to it!",
        )

    return TemplateHostSchema.model_validate(host_template, from_attributes=True)


@router.post("/hosts")
async def upload_host_template_endpoint(
    host_template: TemplateHostBaseSchema,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> TemplateHostID:
    """Upload a host template.

    Args:
    ----
        host_template (TemplateHostBaseSchema): OpenLabs compliant host template object.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        TemplateHostID: Identity of the host template.

    """
    # Create host with current user as owner
    created_host = await create_host_template(
        db, host_template, owner_id=current_user.id
    )

    return TemplateHostID.model_validate(created_host, from_attributes=True)


@router.delete("/hosts/{host_id}")
async def delete_host_template_endpoint(
    host_id: str,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> bool:
    """Delete a host template.

    Args:
    ----
        host_id (str): Id of the host.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        bool: True if successfully deleted. False otherwise.

    """
    # Invalid UUID4 ID
    if not is_valid_uuid4(host_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID provided is not a valid UUID4.",
        )

    # For admin users, don't filter by user_id to allow access to all templates
    user_id = None if current_user.is_admin else current_user.id

    host_template = await get_host_template(
        db, TemplateHostID(id=host_id), user_id=user_id
    )

    # Does not exist
    if not host_template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Host with id: {host_id} not found or you don't have access to it!",
        )

    # Not standalone template
    if not host_template.is_standalone():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete host template because it is not a standalone template. Connected to subnet: {host_template.subnet_id}",
        )

    return await delete_host_template(db, host_template)
