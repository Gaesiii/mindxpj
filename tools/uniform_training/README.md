# School-specific uniforms: offline tooling

D01 actual collection: **BLOCKED — no school garment photos supplied**.
D02 model/license investigation and offline tooling: **PARTIAL**. Actual training is
**BLOCKED — no school dataset**.
D03 real model evaluation/approval: **BLOCKED — no trained artifact or independent school-specific evaluation**.
Tooling is implemented; these statuses do not claim real model acceptance.

Supervisors upload original images with one face above an explicit garment ROI.
The original image is discarded; only the face-free garment crop is retained in a
private BinaryField, separate from FaceSample. The local detector must be available;
unavailable detection fails closed. Automatic detection is fallible: supervisors
must inspect every retained crop and delete any inappropriate image before export.
Never use student names/IDs for capture_group. Give all frames of the same person,
outfit, burst/location/session a single opaque group; groups never cross splits.
No endpoint exports student faces or trains/downloads models.

Export a class dataset ZIP as supervisor. Extract privately and run:

```powershell
python tools/uniform_training/pipeline.py validate PRIVATE_DATASET
python -m venv .venv-uniform-training
.venv-uniform-training/Scripts/python -m pip install -r tools/uniform_training/requirements-offline.txt
.venv-uniform-training/Scripts/python tools/uniform_training/pipeline.py train PRIVATE_DATASET --output PRIVATE_OUTPUT --epochs 20 --seed 2026 --threshold 0.95
```

The model is MobileNetV3 Small initialized without downloaded weights. Validation
loss chooses the checkpoint. Held-out evaluation reports per-class precision,
recall, confusion matrices, confidence coverage, bytes, OpenCV latency and ONNX
parity. This is a development baseline, not evidence that a school's logos or
garment shapes can be recognized. Use independent people/sessions/light/backgrounds,
both uniform types, similar colors with wrong logos/shapes and OTHER hard negatives.
Collect partially visible, jacket/hand/bag-covered logos and cropped torsos. Evaluate
those cases separately: classifier confidence alone cannot prove logo visibility.
No model may be approved until the supervisor substantiates UNKNOWN behavior for
occlusion, school logo/shape discrimination and acceptable precision/coverage on
held-out images. Retraining and a new immutable version are required for changes.
Random initialization is a baseline only. For fine-tuning, supply locally acquired
torchvision MobileNetV3 Small weights with `--initial-weights PRIVATE_WEIGHTS.pth
--weights-sha256 EXPECTED_SHA256`. The pipeline checks the hash and loads using
`weights_only=True` before replacing the final classifier. It never downloads.
Record the source, version, redistribution license and hash of those weights in the
private provenance record. Import requires at least 0.95 held-out precision for each
class, in addition to school-specific human review; low coverage remains visible.

After independent review, create private review.json containing report_sha256,
supervisor_id, approved:true, school_logo_shape_reviewed:true,
wrong_school_hard_negatives_reviewed:true, occlusion_unknown_behavior_reviewed:true,
and evidence_reference pointing to the private review record. These are operator
attestations, not cryptographic signatures or automatic proof. Import locally:

```powershell
$env:DJANGO_SECRET_KEY='YOUR_LOCAL_SECRET'
backend/.venv/Scripts/python tools/uniform_training/import_artifact.py --model PRIVATE_OUTPUT/uniform.onnx --report PRIVATE_OUTPUT/report.json --review PRIVATE_OUTPUT/review.json --classroom CLASS_UUID --supervisor USER_UUID
```

Select the returned version through the supervisor profile API. Import never
activates a version. The private artifact directory defaults to
backend/private_uniform_models; operators must exclude this and all dataset,
review and output directories from Git/public hosting. Runtime verifies SHA-256,
never downloads, serializes OpenCV DNN access and returns NOT_CHECKED on failure.
No PyTorch dependency is added to Django. Missing/insufficient body/uncertain
predictions return UNKNOWN/NOT_CHECKED. Two consistent high-confidence predictions
are required; matching the frozen session requirement suggests COMPLIANT, a
confident mismatch suggests REVIEW_REQUIRED and requires staff reason/confirmation.
Compliant scans may be recorded automatically under the approved attendance flow;
manual fallback remains available when evidence is insufficient.

Licensing/provenance: school owns or authorizes all garment photos; document consent
and retention locally. Do not scrape student photos. PyTorch and torchvision use
BSD-style licenses; ONNX uses Apache-2.0; OpenCV uses Apache-2.0; Pillow uses its
HPND-style license; NumPy uses BSD. Preserve exact installed package license notices
when redistributing. No pretrained model/image corpus is downloaded or included.
