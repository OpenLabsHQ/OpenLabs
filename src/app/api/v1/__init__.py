"""Version 1 of the OpenLabs API routes."""

from fastapi import APIRouter

from .auth import router as auth_router
from .blueprint_hosts import router as blueprint_hosts_router
from .blueprint_ranges import router as blueprint_ranges_router
from .blueprint_subnets import router as blueprint_subnets_router
from .blueprint_vpcs import router as blueprint_vpcs_router
from .health import router as health_router
from .jobs import router as job_router
from .ranges import router as ranges_router
from .users import router as user_router

router = APIRouter(prefix="/v1")
router.include_router(health_router)
router.include_router(blueprint_ranges_router)
router.include_router(blueprint_vpcs_router)
router.include_router(blueprint_subnets_router)
router.include_router(blueprint_hosts_router)
router.include_router(ranges_router)
router.include_router(auth_router)
router.include_router(user_router)
router.include_router(job_router)
