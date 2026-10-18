"""Build the Vietnamese 5-7 minute OpenCV presentation, with speaker notes.

Tool-only dependency setup (Python 3.12; not a backend dependency):
backend/.venv/Scripts/python.exe -m pip install --target .document-tools/presentation-deps python-pptx==1.0.2
backend/.venv/Scripts/python.exe .document-tools/build_opencv_presentation.py
"""
from pathlib import Path
import sys
import os

ROOT = Path(__file__).resolve().parents[1]
presentation_deps = Path(os.environ.get('PRESENTATION_TOOL_DEPS', Path(__file__).parent / 'presentation-deps'))
sys.path.insert(0, str(presentation_deps))
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

OUT = ROOT / 'docs/thuyet-trinh-opencv.pptx'
NAVY = '102338'
WHITE = 'F5F8FC'
MUTED = 'B6C8DB'
TEAL = '55D5C6'
CARD = '1C354D'
AMBER = 'FFD18A'

SLIDES = [
    ('Điểm danh với OpenCV', 'MVP v1.4 • Django UI local • Demo 5–7 phút', [
        ('Bài toán', ['Ghi nhận có mặt, giờ đến và đồng phục theo từng buổi học.', 'GVCN xem lớp được giao; giám thị quản lý toàn bộ.']),
        ('Nguyên tắc', ['OpenCV chỉ gợi ý; nhân sự kiểm tra người thực tế rồi xác nhận.', 'Không chắc chắn hoặc camera lỗi: điểm danh thủ công.'])
    ], '0:00–0:50. Giới thiệu bài toán và vai trò. Nói rõ UI local được người dùng cho phép trước gate ngày18/10/2026; browser/camera cần evidence riêng. Không công bố độ chính xác hoặc chống giả khi chưa có đánh giá thực tế.'),
    ('Một ảnh → một đề xuất → xác nhận', 'Scan không tự ghi PRESENT', [
        ('1. Chuẩn bị', ['Nhân sự đăng nhập và mở buổi đúng quyền, ngày và khung giờ.', 'Đăng ký riêng 3–10 mẫu của mỗi người; ảnh hồ sơ không tự thành mẫu.']),
        ('2. Gợi ý và quyết định', ['Gửi một ảnh: ứng viên + màu áo; proposal PENDING tối đa 120 giây.', 'Nhìn người thật → xác nhận danh tính → attendance source VISION.'])
    ], '0:50–1:40. Trình bày đường đi dữ liệu. Enrollment và ảnh đánh giá phải tách biệt. UNKNOWN, nhiều mặt hoặc ảnh mờ chuyển chụp lại/manual. PRESENT chỉ được ghi sau xác nhận hợp lệ; không tự suy đồng phục đạt.'),
    ('Kiến trúc cục bộ, dữ liệu private', 'Django session + CSRF + kiểm tra phạm vi lớp ở từng API', [
        ('Django UI local', ['Cookie/session của staff', 'Camera hoặc upload ảnh', 'Ngoại lệ trước API gate']),
        ('Vision', ['YuNet: phát hiện 5 landmark', 'SFace: embedding + cosine', 'HSV gợi ý màu áo']),
        ('Attendance', ['Staff confirm + version', 'Idempotency + ChangeLog', 'Manual fallback']),
        ('Report / DB', ['JSON, XLSX, CSV', 'Crop112×112 + embedding private', 'Không lưu frame/video'])
    ], '1:40–2:25. YuNet phát hiện5landmark, SFace so cosine trong roster, HSV chỉ đo màu vùng áo. Service attendance là nơi ghi kết quả. Mẫu crop112x112 và embedding128float lưu private trong DB; frame phân tích không lưu. Mẫu LBPH cũ cần enrollment lại3–10ảnh. Cosine≥0.45 và margin≥0.10 chỉ là ngưỡng demo, không phải xác suất. Models chuẩn bị trước, request không tải network. QR mặc định tắt, dữ liệu và migrations cũ giữ lại.'),
    ('Demo trực tiếp bằng UI local', 'Thực hiện trên DB thử riêng và ảnh được phép sử dụng', [
        ('Chuẩn bị / phân tích', ['1. Đăng nhập staff; chọn lớp và tạo/mở buổi đúng quyền.', '2. Mục Học sinh: đăng ký 3–10 ảnh mẫu riêng.', '3. Camera/upload → phân tích: PENDING, chưa ghi có mặt.']),
        ('Xác nhận / đối soát', ['4. Nhìn người thật rồi xác nhận danh tính; kiểm tra áo.', '5. Thử reject/manual; kiểm tra kết quả và source VISION.', '6. Chốt buổi; mở báo cáo, tải XLSX/CSV cùng bộ lọc.'])
    ], '2:25–3:50. Mở http://127.0.0.1:8000/; API client api-requests.http là dự phòng. UI dùng API cũ và quyền cũ. Mẫu multipart images lặp 3–10 file; scan chỉ một image, không student_id. Nhìn người thực tế trước confirm. arrived_at lấy scanned_at server. Chỉ chọn COMPLIANT sau kiểm tra thực tế; có thể bỏ uniform để kiểm tra sau.'),
    ('Tình huống lỗi và đường thủ công', 'Không biến kết quả chưa chắc chắn thành có mặt hoặc vi phạm', [
        ('Ảnh / đồng phục', ['Mặt lạ, mờ, nhiều mặt hoặc ứng viên sát nhau: chụp lại/manual.', 'Áo bị che, thiếu vùng thân, màu không trội: UNKNOWN.', 'HSV không nhận biết logo, chất liệu hay đồng phục đầy đủ.']),
        ('Trạng thái / quyền', ['Scan hết hạn, mẫu/version đổi, buổi đóng: không confirm mới.', 'GVCN khác lớp và học sinh bị chặn các API vision.', 'Mất camera/mạng: kiểm tra retry và chuyển manual.'])
    ], '3:50–4:40. Cho thấy một trường hợp không nhận diện hoặc dùng dữ liệu thử có nhãn. Không sửa student_id để chọn người trong confirm. Mẫu mới/xóa mẫu, manual, transfer và close làm proposal cũ không còn dùng để ghi attendance.'),
    ('Kiểm chứng và bằng chứng', 'Chỉ trình bày kết quả từ log kiểm chứng hiện tại', [
        ('Backend / dữ liệu', ['Test scope, ảnh, matching, expiry, version, retry và rollback.', 'Migrate DB mới/nâng cấp; check, migration drift và pip check.', 'Mở lại XLSX/CSV, so chi tiết và tổng với API.']),
        ('Thiết bị / review', ['Fixture synthetic hoặc mock detector không chứng minh camera thật.', 'Thử ánh sáng, góc mặt, người lạ, áo bị che trên thiết bị thật.', 'Implementation + validation + review trước khi tick Finish?.'])
    ], '4:40–5:35. Mở evidence mới của backend thay vì đọc số test trên slide. Không lấy126test QR lịch sử làm kết quả vision. Giải thích phần nào dùng fixture/mocked detection và phần nào chạy SFace/HSV thật. Checklist thiết bị thật chưa hoàn tất nếu chưa có log và reviewer.'),
    ('Giới hạn và bước tiếp theo', 'API_Gate = NOT_APPROVED • UI local là ngoại lệ do người dùng yêu cầu', [
        ('Giới hạn demo', ['Chưa có số liệu độ chính xác camera thật; không bảo đảm liveness.', 'HSV là heuristic màu; SQLite và cache dùng cho demo nhỏ.', 'Quota 20 phân tích/phút/actor: phút cố định, cache từng process.']),
        ('Bàn giao', ['PM xem evidence mới và quyết định API gate riêng.', 'UI local đã có; browser/thiết bị thật cần evidence riêng.', 'Không tự deploy, chia sẻ ngoài hoặc đánh dấu mọi task hoàn tất.'])
    ], '5:35–6:30, dành phần còn lại cho câu hỏi. Cần đánh giá trên bộ ảnh được phép, tách enrollment/evaluation trước mọi tuyên bố accuracy. Rate limit không phải rolling window hoặc giới hạn toàn hệ thống nhiều process. UI local đã được cho phép trước gate bằng yêu cầu làm luôn UI để demo. Ngoại lệ không phê duyệt API hoặc deploy.')
]


def color(value):
    return RGBColor.from_string(value)


def box(slide, x, y, w, h, fill):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = color(fill)
    shape.line.fill.background()
    return shape


def text(slide, x, y, w, h, value, size=21, fill=WHITE, bold=False):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = shape.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(.02)
    tf.margin_top = tf.margin_bottom = Inches(.02)
    for i, line in enumerate(value.split('\n')):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.font.name = 'Arial'
        p.font.size = Pt(size)
        p.font.bold = bold
        p.font.color.rgb = color(fill)
        p.space_after = Pt(14)
    return shape


def build():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    for number, (title, subtitle, cards, notes) in enumerate(SLIDES, 1):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = color(NAVY)
        text(slide, .65, .48, 12, .7, title, 33, bold=True)
        text(slide, .65, 1.25, 12, .65, subtitle, 19, TEAL)
        if len(cards) == 4:
            for i, (heading, lines) in enumerate(cards):
                x = .65 + i * 3.12
                box(slide, x, 2.2, 2.95, 3.7, CARD)
                text(slide, x+.18, 2.42, 2.6, .55, heading, 22, TEAL, True)
                text(slide, x+.18, 3.12, 2.6, 2.6, '\n'.join(lines), 20)
        else:
            for i, (heading, lines) in enumerate(cards):
                x = .65 + i * 6.17
                box(slide, x, 2.12, 5.99, 4.37, CARD)
                text(slide, x+.25, 2.35, 5.45, .55, heading, 24, TEAL, True)
                text(slide, x+.25, 3.12, 5.43, 3.08, '\n'.join('• '+line for line in lines), 21)
        text(slide, .65, 6.98, 11.5, .25, 'OpenCV MVP v1.4 | UI local | Nhân sự xác nhận bắt buộc', 11, MUTED)
        text(slide, 12.05, 6.96, .65, .3, f'{number}/7', 12, AMBER)
        slide.notes_slide.notes_text_frame.text = notes
    prs.save(OUT)
    # Reopen and confirm every authored title, card and note survived serialization.
    reopened = Presentation(OUT)
    assert len(reopened.slides) == 7
    for slide, (title, subtitle, cards, notes) in zip(reopened.slides, SLIDES):
        all_text = '\n'.join(shape.text for shape in slide.shapes if shape.has_text_frame)
        assert title in all_text and subtitle in all_text
        for heading, lines in cards:
            assert heading in all_text
            assert all(line in all_text for line in lines)
        assert notes in slide.notes_slide.notes_text_frame.text
    print('PASS: created and reopened 7 slides; all titles, card text and speaker notes match.')
    print('Limit: no PowerPoint rendering or live presentation/camera test performed.')
    print(str(OUT))


if __name__ == '__main__':
    build()
