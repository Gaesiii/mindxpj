"""Reproducible local-only real-inference measurements; never uploads fixtures.

Run with backend's existing venv Python. A fresh child process migrates a temporary
SQLite database, uses private local JPEGs, and returns only sanitized aggregates.
"""
import argparse
import ctypes
import io
import json
import os
from pathlib import Path
import platform
import secrets
import subprocess
import sys
import tempfile
import time
from datetime import datetime, time as day_time, timezone as utc

ROOT = Path(__file__).resolve().parents[1]


def memory():
    """Windows OS process working set, not Python allocator estimates."""
    class Counters(ctypes.Structure):
        _fields_ = [('cb', ctypes.c_ulong), ('PageFaultCount', ctypes.c_ulong)] + [
            (name, ctypes.c_size_t) for name in ('PeakWorkingSetSize', 'WorkingSetSize',
            'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
            'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong]
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return {'working_set_bytes': counters.WorkingSetSize,
            'process_peak_working_set_bytes': counters.PeakWorkingSetSize}


def measure(label, operation):
    before = memory()
    wall, cpu = time.perf_counter(), time.process_time()
    value = operation()
    cpu, wall = time.process_time() - cpu, time.perf_counter() - wall
    return value, {'label': label, 'wall_ms': round(wall * 1000, 3),
                   'process_cpu_ms': round(cpu * 1000, 3), 'memory_before': before,
                   'memory_after': memory()}


def worker(workdir, images):
    os.environ.pop('VERCEL', None)
    os.environ.update(DJANGO_SETTINGS_MODULE='config.settings', DJANGO_SECRET_KEY=secrets.token_urlsafe(48),
                      DJANGO_DB_PATH=str(workdir / 'benchmark.sqlite3'), DJANGO_DEBUG='false',
                      DJANGO_ALLOWED_HOSTS='testserver', VISION_FACE_MIN_COSINE='0.45',
                      VISION_FACE_MIN_COSINE_MARGIN='0.10', VISION_AUTO_MIN_COSINE='0.60',
                      VISION_AUTO_MIN_MARGIN='0.15', VISION_MIN_SHARPNESS='50')
    sys.path.insert(0, str(ROOT / 'backend'))
    import django
    django.setup()
    from django.core.management import call_command
    from django.contrib.auth import get_user_model
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.db import connections
    from django.test import Client
    from django.utils import timezone
    from school_app.academics.models import Grade, Classroom
    from school_app.students.models import Student
    from school_app.schedules.models import Session, ScheduleRule
    from school_app.vision.models import VisionScan

    result = {'measured_at_utc': datetime.now(utc.utc).isoformat(),
              'environment': {'os': platform.platform(), 'python': platform.python_version(),
                              'processor': platform.processor(), 'logical_cpu_count': os.cpu_count()},
              'method': {'execution': 'fresh isolated Windows child process; local Django test Client, no network',
                         'authentication': 'force_login SUPERVISOR; test Client CSRF enforcement disabled',
                         'database': 'temporary SQLite, real migrations; 1 class, 1 student, 1 OPEN session today',
                         'vision': 'real pinned YuNet/SFace OpenCV CPU, default production thresholds; no inference mocks',
                         'cold_definition': 'first routed request after Django setup, migrations and login; not OS cold boot or Vercel cold start',
                         'memory': 'GetProcessMemoryInfo WorkingSetSize and lifetime PeakWorkingSetSize; snapshots, not per-operation allocation',
                         'timing': 'perf_counter wall time and process_time CPU; one process, sequential requests',
                         'privacy': 'no images, embeddings, IDs, cookies, credentials or database retained in evidence'},
              'measurements': []}
    try:
        _, metric = measure('migrate_temporary_database', lambda: call_command('migrate', verbosity=0, stdout=io.StringIO()))
        result['measurements'].append(metric)
        User = get_user_model()
        teacher = User.objects.create_user(username='benchmark-teacher', role='HOMEROOM_TEACHER')
        actor = User.objects.create_user(username='benchmark-supervisor', role='SUPERVISOR')
        grade = Grade.objects.create(code='BENCH', name='Benchmark')
        classroom = Classroom.objects.create(code='BENCH', name='Benchmark', grade=grade, teacher=teacher)
        student = Student.objects.create(student_code='BENCH', full_name='Synthetic benchmark student', classroom=classroom)
        today = timezone.localdate()
        ScheduleRule.objects.create(classroom=classroom, weekday=today.weekday(), slot='MORNING',
                                    start_time=day_time(0), close_time=day_time(23, 59, 59),
                                    grace_minutes=5, required_uniform='SHIRT')
        session = Session.objects.create(classroom=classroom, school_date=today, slot='MORNING')
        client = Client()
        client.force_login(actor)

        def request(label, operation):
            response, metric = measure(label, operation)
            body = response.json()
            metric['http_status'] = response.status_code
            for key in ('outcome', 'reason', 'sample_count', 'usable_sample_count'):
                if key in body:
                    metric[key] = body[key]
            if 'uniform' in body:
                metric['uniform'] = body['uniform']
            result['measurements'].append(metric)
            if response.status_code >= 400:
                raise RuntimeError(f'{label} failed: HTTP {response.status_code}; {body.get("error", {}).get("code", "unknown")}')
            return body

        for i in range(4):
            request('classes_first_routed_request' if not i else f'classes_warm_{i}', lambda: client.get('/api/v1/classes'))
        request('open_session', lambda: client.post(f'/api/v1/sessions/{session.pk}/open',
                data=json.dumps({'expected_version': 0}), content_type='application/json'))
        # API-opened snapshots span the actual current local day; no clock mocks.
        session.refresh_from_db()
        assert session.status == 'OPEN' and session.start_at <= timezone.now() <= session.close_at
        enrolled = sorted((images / '01-enroll').glob('*.jpg'))
        heldout = [images / 'demo' / name for name in (
            '1753240560-trump-67651-width698height558.jpg', '1f64783ac2712b2f7260.jpg')]
        assert len(enrolled) == 3 and all(p.is_file() for p in heldout)
        def uploads(paths):
            return [SimpleUploadedFile(p.name, p.read_bytes(), content_type='image/jpeg') for p in paths]
        result['fixtures'] = {'enrollment_relative_paths': [str(p.relative_to(images)).replace('\\', '/') for p in enrolled],
                              'heldout_relative_paths': [str(p.relative_to(images)).replace('\\', '/') for p in heldout],
                              'enrollment_bytes': sum(p.stat().st_size for p in enrolled),
                              'heldout_bytes': [p.stat().st_size for p in heldout]}
        request('first_enrollment_including_model_initialization_and_3_embeddings', lambda: client.post(
            f'/api/v1/students/{student.pk}/face-samples', {'images': uploads(enrolled)}))
        def scan(paths, key):
            return client.post(f'/api/v1/sessions/{session.pk}/auto-attendance-scans',
                {'images': uploads(paths), 'scan_mode': 'AUTO_ATTENDANCE', 'expected_session_version': str(session.version)},
                HTTP_IDEMPOTENCY_KEY=key)
        first = request('heldout_pair_first_unique_key_real_inference', lambda: scan(heldout, 'heldout-0'))
        for i in range(1, 4):
            request(f'heldout_pair_warm_unique_key_{i}_real_inference', lambda i=i: scan(heldout, f'heldout-{i}'))
        request('heldout_same_key_replay_no_inference', lambda: scan(heldout, 'heldout-0'))
        # If held-out photos are another person, preserve UNKNOWN and separately
        # measure successful routing using two distinct enrollment images.
        if first.get('outcome') != 'RECORDED':
            result['known_pair_limitation'] = 'Two enrollment images reused for workflow timing only; not recognition generalization evidence.'
            known = enrolled[:2]
            body = request('enrollment_reuse_pair_first_record_unique_key_real_inference', lambda: scan(known, 'known-0'))
            assert body['outcome'] == 'RECORDED', body.get('reason')
            for i in range(1, 4):
                body = request(f'enrollment_reuse_pair_warm_unique_key_{i}_real_inference', lambda i=i: scan(known, f'known-{i}'))
                assert body['outcome'] == 'ALREADY_RECORDED'
        result['recorded_scans'] = list(VisionScan.objects.values('status', 'cosine_score', 'distance', 'model_key'))
        result['runtime'] = {'opencv_version': __import__('cv2').__version__,
                             'opencv_threads': __import__('cv2').getNumThreads(), 'torch_imported': 'torch' in sys.modules,
                             'final_memory': memory()}
        result['limitations'] = ['Local single-process synthetic minimal roster; no concurrency/load/browser/network benchmark.',
                                'No Vercel deployment, native Linux runtime, deployed bundle size or Vercel cold-start measured.',
                                'No approved trained uniform model available: NOT_CHECKED; trained-model benchmark pending.',
                                'Cosine scores are similarities, not probability or liveness/accuracy guarantees.',
                                'Three warm unique-key calls run full inference even when outcome ALREADY_RECORDED; replay is separate.']
        return result
    finally:
        connections.close_all()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--images', type=Path, default=Path('E:/projectmindx/demo-images'))
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/project-management/evidence/v1.5/performance.json')
    parser.add_argument('--worker-dir', type=Path)
    args = parser.parse_args()
    if args.worker_dir:
        result = worker(args.worker_dir, args.images)
        (args.worker_dir / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        return
    if os.name != 'nt':
        raise RuntimeError('This evidence harness measures Windows GetProcessMemoryInfo only.')
    with tempfile.TemporaryDirectory(prefix='mindx-v15-benchmark-') as temporary:
        wall = time.perf_counter()
        process = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--worker-dir', temporary,
                                  '--images', str(args.images)], cwd=ROOT / 'backend', capture_output=True)
        if process.returncode:
            # Fixture/secret bytes are never echoed; traceback only goes to local stderr.
            sys.stderr.write(process.stderr.decode('utf-8', errors='replace'))
            raise SystemExit(process.returncode)
        result = json.loads((Path(temporary) / 'result.json').read_text(encoding='utf-8'))
        result['child_process_total_wall_ms'] = round((time.perf_counter() - wall) * 1000, 3)
    # Current production source includes newly added files before git staging.
    # Explicit roots omit tests, venv, generated staticfiles, database/media,
    # model binaries and Vercel build outputs.
    files = [p for directory in ('backend/config', 'backend/school_app')
             for p in (ROOT / directory).rglob('*')
             if p.is_file() and p.suffix in {'.py', '.html', '.js', '.css'}]
    files.append(ROOT / 'backend/manage.py')
    models = [ROOT / 'backend/vision_models' / name for name in (
        'face_detection_yunet_2023mar.onnx', 'face_recognition_sface_2021dec.onnx')]
    result['artifact_sizes'] = {'runtime_source_extensions': ['.py', '.html', '.js', '.css'],
                               'source_roots': ['backend/config', 'backend/school_app', 'backend/manage.py'],
                               'source_scope': 'Current production source, including new unstaged files; excludes tests, venv, generated outputs, private data and weights.',
                               'runtime_source_files': len(files),
                               'runtime_source_bytes': sum(p.stat().st_size for p in files),
                               'pinned_models': {p.name: p.stat().st_size for p in models},
                               'linux_dependency_prior_estimate_mib': 267.45,
                               'estimate_caveat': 'Prior Linux wheel dependency estimate only; not measured by this run, not deployed bundle or runtime RAM.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f'Wrote sanitized local benchmark: {args.output}')


if __name__ == '__main__':
    main()
