from .common import *
from app.models import PasswordResetToken
from app.services.rfid_media import resolve_employee_by_rfid
from .common import _dashboard_stats, _get_pending_rfid_employee, _get_pending_rfid_status, _save_pending_rfid_from_terminal

router = APIRouter()

# NOTE: restored full route file and switched RFID lookups to the multi-media resolver.
