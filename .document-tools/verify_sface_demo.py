"""Real browser -> HTTP -> YuNet/SFace -> SQLite regression, isolated from user DB.

Run with --images pointing to the local ignored demo-images directory.
Playwright may be supplied through PYTHONPATH; models must be prepared first.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import uuid

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/project-management/evidence/sface-upgrade'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--images', required=True, type=Path)
    args = parser.parse_args()
    images = args.images.resolve()
    enrolled = sorted((images / '01-enroll').glob('*.jpg'))
    query = list((images / 'demo').glob('*.jpg'))
    assert len(enrolled) == 3 and len(query) == 1, 'Expected 3 enrollment and 1 held-out image.'
    OUT.mkdir(parents=True, exist_ok=True)
    notes, responses, errors = [], [], []
    process = None
    runtime = None
    connection = None
    temporary_context = tempfile.TemporaryDirectory(prefix='mindx-sface-qa-', ignore_cleanup_errors=True)
    try:
        with temporary_context as temporary:
            ready = Path(temporary) / 'ready.json'
            with (Path(temporary) / 'server.txt').open('w', encoding='utf-8') as server:
                process = subprocess.Popen([sys.executable, str(ROOT / '.document-tools/run_demo.py'),
                    '--port', '8002', '--ready-file', str(ready)], cwd=ROOT,
                    stdout=server, stderr=server, creationflags=subprocess.CREATE_NO_WINDOW)
                deadline = time.monotonic() + 75
                while not ready.exists():
                    if process.poll() is not None:
                        raise RuntimeError('QA server exited before ready.')
                    if time.monotonic() > deadline:
                        raise TimeoutError('QA server startup timed out.')
                    time.sleep(.2)
                info = json.loads(ready.read_text(encoding='utf-8'))
                runtime = Path(info['runtime'])
                while True:
                    try:
                        urllib.request.urlopen(info['url'], timeout=2).close()
                        break
                    except OSError:
                        if time.monotonic() > deadline:
                            raise
                        time.sleep(.2)
                values = dict(line.split(': ', 1) for line in Path(info['credentials']).read_text(encoding='utf-8').splitlines() if ': ' in line)
                database = runtime / 'demo.sqlite3'
                with closing(sqlite3.connect(database)) as connection:
                    student = connection.execute("SELECT id FROM students_student WHERE student_code='DEMOHS01'").fetchone()[0]
                    actor = connection.execute("SELECT id FROM accounts_user WHERE username='demo_supervisor'").fetchone()[0]
                    for index in range(3):
                        crop = f'legacy-private-crop-{index}'.encode()
                        connection.execute('INSERT INTO vision_facesample (id,student_id,image,digest,created_by_id,created_at,model_key,embedding) VALUES (?,?,?,?,?,?,?,?)',
                            (uuid.uuid4().hex, student, crop, hashlib.sha256(crop).hexdigest(), actor,
                             datetime.now(timezone.utc).isoformat(), '', None))
                    connection.commit()
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(executable_path='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless=True)
                    page = browser.new_page()
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    def response_received(response):
                        if '/vision-scans' in response.url and response.request.method == 'POST':
                            responses.append(response.json())
                    page.on('response', response_received)
                    page.goto(info['url'])
                    page.locator('#login-username').fill(values['Username'])
                    page.locator('#login-password').fill(values['Password'])
                    page.locator('#login-form button[type=submit]').click()
                    expect(page.locator('#class-select option')).to_have_count(2)
                    page.locator('.nav-item[data-view=students]').click()
                    row = page.locator('#students-table tr').filter(has_text='DEMOHS01')
                    row.locator('button').click()
                    expect(page.locator('#enroll-metadata')).to_contain_text('cần đăng ký lại')
                    notes.append('Legacy three crops retained; actual API/UI requires enrollment again: PASS')
                    page.locator('#enroll-files').set_input_files([str(path) for path in enrolled])
                    page.locator('#enroll-form button[type=submit]').click()
                    expect(page.locator('#enroll-dialog')).not_to_be_visible(timeout=20000)
                    row.locator('button').click()
                    expect(page.locator('#enroll-metadata')).to_contain_text('3 mẫu dùng được')
                    page.locator('#enroll-dialog .dialog-close').click()
                    notes.append('Real three-photo enrollment replaces legacy samples; usable count3: PASS')
                    page.locator('.nav-item[data-view=attendance]').click()
                    page.locator('#scan-upload').set_input_files(str(images / '02-scan/unknown-person.jpg'))
                    page.locator('#analyze-button').click()
                    expect(page.locator('#scan-feedback')).to_contain_text('Chưa nhận diện')
                    assert responses[-1]['reason'] == 'UNKNOWN_FACE'
                    expect(page.locator('#confirm-scan-form')).not_to_be_visible()
                    notes.append('Different-person image rejected by real YuNet/SFace; no proposal: PASS')
                    page.locator('#scan-upload').set_input_files(str(query[0]))
                    page.locator('#analyze-button').click()
                    expect(page.locator('#confirm-scan-form')).to_be_visible(timeout=20000)
                    scan = responses[-1]['scan']
                    assert scan['student_id'].replace('-', '') == student
                    assert scan['metric'] == 'cosine' and scan['model_key'] == 'sface-2021dec-fp32'
                    assert scan['cosine_score'] >= .45
                    expect(page.locator('#stat-present')).to_have_text('0')
                    expect(page.locator('#candidate-uniform')).to_have_value('')
                    page.locator('#confirm-scan-form button[type=submit]').click()
                    assert page.locator('#identity-confirmed').evaluate('(el)=>el.validity.valueMissing')
                    notes.append(f"Exact held-out user image matches demo student; cosine{scan['cosine_score']}; not a probability. No automatic PRESENT/uniform: PASS")
                    page.locator('#identity-confirmed').check()
                    page.locator('#confirm-scan-form button[type=submit]').click()
                    expect(page.locator('#confirm-scan-form')).not_to_be_visible()
                    expect(page.locator('#stat-present')).to_have_text('1')
                    browser.close()
                with closing(sqlite3.connect(database)) as connection:
                    assert connection.execute("SELECT count(*) FROM attendance_attendance WHERE status='PRESENT' AND source='VISION'").fetchone()[0] == 1
                    rows = list(connection.execute('SELECT model_key,length(embedding) FROM vision_facesample'))
                    assert rows == [('sface-2021dec-fp32',512)] * 3
                assert not errors, errors
                notes.append('Explicit identity confirmation persisted exactly one VISION attendance; private versioned512byte embeddings: PASS')
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                process.wait(timeout=10)
                ready.unlink()
                process = subprocess.Popen([sys.executable, str(ROOT / '.document-tools/run_demo.py'),
                    '--port', '8002', '--ready-file', str(ready), '--resume-runtime', str(runtime)], cwd=ROOT,
                    stdout=server, stderr=server, creationflags=subprocess.CREATE_NO_WINDOW)
                deadline = time.monotonic() + 30
                while not ready.exists():
                    if process.poll() is not None:
                        raise RuntimeError('Resume QA exited before ready.')
                    if time.monotonic() > deadline:
                        raise TimeoutError('Resume QA startup timed out.')
                    time.sleep(.2)
                resumed = dict(line.split(': ', 1) for line in Path(info['credentials']).read_text(encoding='utf-8').splitlines() if ': ' in line)
                assert resumed['Password'] == values['Password']
                with closing(sqlite3.connect(database)) as connection:
                    assert connection.execute("SELECT count(*) FROM attendance_attendance WHERE status='PRESENT' AND source='VISION'").fetchone()[0] == 1
                    assert connection.execute('SELECT count(*) FROM vision_facesample WHERE embedding IS NOT NULL').fetchone()[0] == 3
                notes.append('Restart --resume-runtime preserves account password, existing enrollment and confirmed attendance without reseeding: PASS')
                notes.append('Uncaught JavaScript errors:0. No detector/embedding/HTTP response mocks. Isolated temporary demo DB only; user DB unchanged. No camera/liveness or population accuracy claim.')
    finally:
        if connection is not None:
            connection.close()
        if process is not None:
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            process.wait(timeout=10)
        (OUT / 'browser-real-face-validation.txt').write_text('\n'.join(notes) + '\n', encoding='utf-8')
        temporary_context.cleanup()
        if runtime is not None:
            resolved = runtime.resolve()
            if resolved.parent == Path(tempfile.gettempdir()).resolve() and resolved.name.startswith('projectmindx-demo-ui-'):
                shutil.rmtree(resolved)
    print('\n'.join(notes))


if __name__ == '__main__':
    main()
