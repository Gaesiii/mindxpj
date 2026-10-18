# core

Common backend contracts, enums, errors, private storage and idempotency; A01/B01/B08.

A01/B01 có enums.py, errors.py và middleware.py (request ID server). api.py xử lý method/JSON Unicode+number/schema/form/error/SQLitebusy; service vẫn phải scope user/tài nguyên. A06 storage.py validate/normalize ảnh private. B08 models.py/idempotency.py cung cấp ChangeLog và IdempotencyRequest24h, unique actor/operation/key, canonical fingerprint/hash, response status/body và atomic CAS. Token scan chỉ fingerprint trong idempotency, không token rõ/password/ảnh trong log. Scope hiện tại được kiểm tra trước replay kể cả sau đổi GVCN.

Graph core/0001 chỉ phụ thuộc User; không FK ngược attendance/qr. Hợp đồng ở docs/api-contract.md; interfaces được phối hợp trước implementation trong plan backend-api. SQLite busy409 không thông báo đã lưu, callback lỗi rollback cả nghiệp vụ/log/key. Test giúp kiểm chứng chức năng, không chứng minh throughput/ghi đồng thời thật; không thêm worker/queue/cloud.
