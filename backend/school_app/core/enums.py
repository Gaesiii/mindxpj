"""B01 shared choices. Stored values are part of docs/api-contract.md."""
from django.db import models


class Role(models.TextChoices):
    HOMEROOM_TEACHER = "HOMEROOM_TEACHER", "Giáo viên chủ nhiệm"
    SUPERVISOR = "SUPERVISOR", "Giám thị"
    STUDENT = "STUDENT", "Học sinh"


class Weekday(models.IntegerChoices):
    MONDAY = 0, "Thứ Hai"
    TUESDAY = 1, "Thứ Ba"
    WEDNESDAY = 2, "Thứ Tư"
    THURSDAY = 3, "Thứ Năm"
    FRIDAY = 4, "Thứ Sáu"
    SATURDAY = 5, "Thứ Bảy"
    SUNDAY = 6, "Chủ Nhật"


class Slot(models.TextChoices):
    MORNING = "MORNING", "Sáng"
    AFTERNOON = "AFTERNOON", "Chiều"


class SessionStatus(models.TextChoices):
    PLANNED = "PLANNED", "Dự kiến"
    OPEN = "OPEN", "Đang điểm danh"
    CLOSED = "CLOSED", "Đã chốt"


class AttendanceStatus(models.TextChoices):
    UNMARKED = "UNMARKED", "Chưa ghi nhận"
    PRESENT = "PRESENT", "Có mặt"
    ABSENT = "ABSENT", "Vắng"


class ArrivalStatus(models.TextChoices):
    ON_TIME = "ON_TIME", "Đúng giờ"
    LATE = "LATE", "Đi muộn"
    NOT_APPLICABLE = "NOT_APPLICABLE", "Không áp dụng"


class RequiredUniform(models.TextChoices):
    SHIRT = "SHIRT", "Sơ mi"
    SPORTS = "SPORTS", "Thể dục"


class ObservedUniform(models.TextChoices):
    SHIRT = "SHIRT", "Sơ mi"
    SPORTS = "SPORTS", "Thể dục"
    OTHER = "OTHER", "Loại khác"
    UNKNOWN = "UNKNOWN", "Chưa rõ"


class UniformStatus(models.TextChoices):
    NOT_CHECKED = "NOT_CHECKED", "Chưa kiểm tra"
    COMPLIANT = "COMPLIANT", "Đạt"
    NON_COMPLIANT = "NON_COMPLIANT", "Không đạt"
    NOT_APPLICABLE = "NOT_APPLICABLE", "Không áp dụng"
    REVIEW_REQUIRED = "REVIEW_REQUIRED", "Cần ghi lý do"


class AttendanceSource(models.TextChoices):
    VISION = "VISION", "Nhận diện OpenCV"
    QR = "QR", "QR đã xác minh"
    MANUAL = "MANUAL", "Thủ công"


class QrScanStatus(models.TextChoices):
    PENDING = "PENDING", "Chờ xác minh"
    CONFIRMED = "CONFIRMED", "Đã xác minh"
    REJECTED = "REJECTED", "Từ chối"
    EXPIRED = "EXPIRED", "Hết hạn"
    SUPERSEDED = "SUPERSEDED", "Thay bằng thủ công"
