"""
Тесты для модуля диагностики дисплазии ТБС.
Запуск: pytest tests/ -v

Проверяют соответствие алгоритму рентгенолога (10 шагов).
"""

import io
import numpy as np
import pytest

from fastapi.testclient import TestClient
from PIL import Image


# ---------------------------------------------------------------------------
# Фикстуры
# ---------------------------------------------------------------------------

@pytest.fixture
def test_png_bytes() -> bytes:
    img = Image.fromarray(np.zeros((256, 256), dtype=np.uint8), mode="L")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def mock_models() -> dict:
    from app.core.model_registry import _MockYOLO, _MockMedSAM
    return {"yolo_hip": _MockYOLO(), "medsam": _MockMedSAM()}


@pytest.fixture
def app_client(mock_models):
    from app.main import create_app
    application = create_app()
    application.state.models = mock_models
    with TestClient(application, raise_server_exceptions=True) as client:
        yield client


def _make_masks(h=512, w=512) -> dict[str, np.ndarray]:
    """Синтетические маски обеих сторон для unit-тестов."""
    masks = {}
    masks["acetabulum_left"] = np.zeros((h, w), dtype=np.uint8)
    masks["acetabulum_left"][200:220, 80:160] = 1
    masks["acetabulum_right"] = np.zeros((h, w), dtype=np.uint8)
    masks["acetabulum_right"][200:220, 300:380] = 1
    masks["ilium_left"] = np.zeros((h, w), dtype=np.uint8)
    masks["ilium_left"][100:200, 60:180] = 1
    masks["ilium_right"] = np.zeros((h, w), dtype=np.uint8)
    masks["ilium_right"][100:200, 280:400] = 1
    masks["femoral_head_left"] = np.zeros((h, w), dtype=np.uint8)
    masks["femoral_head_left"][280:340, 80:140] = 1
    masks["femoral_head_right"] = np.zeros((h, w), dtype=np.uint8)
    masks["femoral_head_right"][280:340, 320:380] = 1
    masks["femoral_neck_left"] = np.zeros((h, w), dtype=np.uint8)
    masks["femoral_neck_left"][240:290, 90:130] = 1
    masks["femoral_neck_right"] = np.zeros((h, w), dtype=np.uint8)
    masks["femoral_neck_right"][240:290, 330:370] = 1
    masks["femoral_shaft_left"] = np.zeros((h, w), dtype=np.uint8)
    masks["femoral_shaft_left"][340:460, 95:115] = 1
    masks["femoral_shaft_right"] = np.zeros((h, w), dtype=np.uint8)
    masks["femoral_shaft_right"][340:460, 345:365] = 1
    masks["obturator_foramen_left"] = np.zeros((h, w), dtype=np.uint8)
    masks["obturator_foramen_left"][230:260, 60:100] = 1
    masks["obturator_foramen_right"] = np.zeros((h, w), dtype=np.uint8)
    masks["obturator_foramen_right"][230:260, 360:400] = 1
    for key in ["ossification_nucleus_left", "ossification_nucleus_right"]:
        masks[key] = np.zeros((h, w), dtype=np.uint8)
    return masks


# ---------------------------------------------------------------------------
# Шаг 4: Линия Хильгенрейнера
# ---------------------------------------------------------------------------

class TestGeometryStep4Hilgenreiner:

    def test_hilgenreiner_built_from_triradiate_cartilage(self):
        """Линия строится через Y-образные хрящи (дно вертлужных впадин)."""
        from app.modules.hip_dysplasia.geometry import GeometryEngine
        result = GeometryEngine().compute(_make_masks())
        assert result.hilgenreiner_line is not None
        assert len(result.hilgenreiner_points) == 2

    def test_hilgenreiner_approximately_horizontal(self):
        """При симметричных масках линия Хильгенрейнера должна быть почти горизонтальной."""
        from app.modules.hip_dysplasia.geometry import GeometryEngine
        result = GeometryEngine().compute(_make_masks())
        if result.hilgenreiner_line:
            # Горизонтальная прямая: |a| << |b|
            line = result.hilgenreiner_line
            assert abs(line.a) < abs(line.b) * 0.3


# ---------------------------------------------------------------------------
# Шаг 1: Симметричность
# ---------------------------------------------------------------------------

class TestGeometryStep1Quality:

    def test_symmetric_masks(self):
        from app.modules.hip_dysplasia.geometry import GeometryEngine
        result = GeometryEngine().compute(_make_masks())
        assert result.is_symmetric is True
        assert result.quality_note == ""

    def test_asymmetric_masks_trigger_warning(self):
        from app.modules.hip_dysplasia.geometry import GeometryEngine
        masks = _make_masks()
        masks["acetabulum_right"] = np.zeros((512, 512), dtype=np.uint8)
        masks["acetabulum_right"][280:300, 300:380] = 1  # сдвиг на 80px
        result = GeometryEngine().compute(masks)
        assert result.is_symmetric is False
        assert len(result.quality_note) > 0


# ---------------------------------------------------------------------------
# Шаг 5: Линия Перкина + квадранты Омбредана
# ---------------------------------------------------------------------------

class TestGeometryStep5Perkin:

    def test_perkin_is_vertical(self):
        from app.modules.hip_dysplasia.geometry import GeometryEngine
        result = GeometryEngine().compute(_make_masks())
        if result.left.perkin_line:
            assert abs(result.left.perkin_line.b) < 1e-6

    def test_ombredanne_quadrant_returned(self):
        from app.modules.hip_dysplasia.geometry import GeometryEngine
        masks = _make_masks()
        masks["ossification_nucleus_left"][290:310, 90:110] = 1
        result = GeometryEngine().compute(masks)
        valid = {"inner_lower", "outer_lower", "outer_upper", "inner_upper", None}
        assert result.left.ombredanne_quadrant in valid


# ---------------------------------------------------------------------------
# Шаги 7–9: измерения
# ---------------------------------------------------------------------------

class TestGeometryMeasurements:

    def test_acetabular_index_in_range(self):
        """Шаг 7: ацетабулярный угол между 0 и 90°."""
        from app.modules.hip_dysplasia.geometry import GeometryEngine
        result = GeometryEngine().compute(_make_masks())
        for side in (result.left, result.right):
            if side.acetabular_index is not None:
                assert 0.0 < side.acetabular_index < 90.0

    def test_no_crash_on_empty_masks(self):
        """Пустые маски не вызывают исключений."""
        from app.modules.hip_dysplasia.geometry import GeometryEngine
        empty = {k: np.zeros((512, 512), dtype=np.uint8) for k in [
            "ilium_left", "ilium_right", "femoral_head_left", "femoral_head_right",
            "femoral_neck_left", "femoral_neck_right", "femoral_shaft_left", "femoral_shaft_right",
            "acetabulum_left", "acetabulum_right", "obturator_foramen_left", "obturator_foramen_right",
            "ossification_nucleus_left", "ossification_nucleus_right",
        ]}
        result = GeometryEngine().compute(empty)
        assert result.hilgenreiner_line is None


# ---------------------------------------------------------------------------
# Классификатор (Шаги 7–10)
# ---------------------------------------------------------------------------

class TestClassifierStep7AcetabularNorms:

    def test_normal_newborn(self):
        """Угол 25° у новорождённого → норма (≈28°)."""
        from app.modules.hip_dysplasia.classifier import AgeBasedClassifier
        result = AgeBasedClassifier().classify(age_months=0, acetabular_left=25.0)
        assert result.has_pathology is False

    def test_5degree_excess_is_pathological(self):
        """Шаг 7: превышение нормы на ≥5° → патология."""
        from app.modules.hip_dysplasia.classifier import AgeBasedClassifier
        # Норма при рождении 28°, угол 34° = +6° ≥ 5°
        result = AgeBasedClassifier().classify(age_months=0, acetabular_left=34.0)
        assert result.left.acetabular_pathological is True
        assert result.has_pathology is True

    def test_1year_norm_18_22(self):
        """Шаг 7: в 1 год норма 18–22°."""
        from app.modules.hip_dysplasia.classifier import AgeBasedClassifier
        clf = AgeBasedClassifier()
        # 20° в норме (22° — верхняя граница нормы)
        assert not clf.classify(age_months=12, acetabular_left=20.0).has_pathology
        # 28° = превышение на 6° → патология
        assert clf.classify(age_months=12, acetabular_left=28.0).has_pathology


class TestClassifierStep8Distances:

    def test_h_below_8mm_pathological(self):
        """h < 8 мм → смещение головки вверх."""
        from app.modules.hip_dysplasia.classifier import AgeBasedClassifier
        result = AgeBasedClassifier().classify(age_months=6, h_left_mm=5.0)
        assert result.left.h_pathological is True
        assert any("h=" in n for n in result.clinical_notes)

    def test_h_in_normal_range(self):
        """h в норме → нет патологии по этому критерию."""
        from app.modules.hip_dysplasia.classifier import AgeBasedClassifier
        result = AgeBasedClassifier().classify(age_months=6, h_left_mm=10.0)
        assert result.left.h_pathological is False

    def test_d_above_15mm_pathological(self):
        """d > 15 мм → латеральное смещение."""
        from app.modules.hip_dysplasia.classifier import AgeBasedClassifier
        result = AgeBasedClassifier().classify(age_months=6, d_left_mm=20.0)
        assert result.left.d_pathological is True


class TestClassifierStep9NSA:

    def test_nsa_valgus(self):
        """Шаг 9: ШДУ > 150° → вальгусная деформация."""
        from app.modules.hip_dysplasia.classifier import AgeBasedClassifier
        result = AgeBasedClassifier().classify(age_months=24, nsa_left=165.0)
        assert result.left.nsa_pathological is True
        assert any("ШДУ" in n for n in result.clinical_notes)


class TestClassifierStep3Nucleus:

    def test_nucleus_delayed_at_6_months(self):
        """Шаг 3: отсутствие ядра в 6 мес → третий признак Путти."""
        from app.modules.hip_dysplasia.classifier import AgeBasedClassifier
        result = AgeBasedClassifier().classify(
            age_months=6, nucleus_present_left=False, nucleus_present_right=False
        )
        assert result.putti_3_nucleus is True

    def test_nucleus_not_expected_before_3_months(self):
        """Шаг 3: до 3 мес ядро ещё не ожидается."""
        from app.modules.hip_dysplasia.classifier import AgeBasedClassifier
        result = AgeBasedClassifier().classify(
            age_months=1, nucleus_present_left=False, nucleus_present_right=False
        )
        assert result.putti_3_nucleus is False


class TestClassifierStep5Quadrants:

    def test_outer_upper_means_dislocation(self):
        """Шаг 5→10: внешний верхний квадрант → вывих."""
        from app.modules.hip_dysplasia.classifier import AgeBasedClassifier
        result = AgeBasedClassifier().classify(age_months=12, quadrant_left="outer_upper")
        assert result.diagnosis == "dislocation"
        assert result.severity == "severe"

    def test_outer_lower_means_subluxation(self):
        """Шаг 5→10: внешний нижний квадрант → подвывих."""
        from app.modules.hip_dysplasia.classifier import AgeBasedClassifier
        result = AgeBasedClassifier().classify(age_months=12, quadrant_right="outer_lower")
        assert result.diagnosis == "subluxation"


class TestClassifierStep10PuttiTriad:

    def test_all_three_signs(self):
        """Шаг 10: все три признака триады Путти → дисплазия."""
        from app.modules.hip_dysplasia.classifier import AgeBasedClassifier
        result = AgeBasedClassifier().classify(
            age_months=6,
            acetabular_left=35.0,       # признак 1 (норма 25°, превышение 10°)
            h_left_mm=5.0,              # признак 2
            nucleus_present_left=False, # признак 3
            nucleus_present_right=False,
        )
        assert result.putti_score == 3
        assert result.diagnosis == "dysplasia"

    def test_clinical_notes_reference_steps(self):
        """Шаг 10: заметки содержат ссылки на шаги алгоритма."""
        from app.modules.hip_dysplasia.classifier import AgeBasedClassifier
        result = AgeBasedClassifier().classify(age_months=6, acetabular_left=34.0, h_left_mm=5.0)
        assert any("Шаг" in note for note in result.clinical_notes)


# ---------------------------------------------------------------------------
# RLE
# ---------------------------------------------------------------------------

class TestMaskUtils:

    def test_rle_roundtrip(self):
        from app.modules.hip_dysplasia.mask_utils import mask_to_rle, rle_to_mask
        original = np.zeros((64, 64), dtype=np.uint8)
        original[10:20, 10:20] = 1
        rle = mask_to_rle(original)
        assert np.array_equal(original, rle_to_mask(rle, (64, 64)))

    def test_empty_mask_rle(self):
        from app.modules.hip_dysplasia.mask_utils import mask_to_rle
        assert mask_to_rle(np.zeros((128, 128), dtype=np.uint8)) == []


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

class TestAPI:

    def test_health(self, app_client):
        assert app_client.get("/api/v1/health").status_code == 200

    def test_info_has_10_algorithm_steps(self, app_client):
        data = app_client.get("/api/v1/hip-dysplasia/info").json()
        assert len(data["algorithm_steps"]) == 10

    def test_info_has_putti_triad(self, app_client):
        data = app_client.get("/api/v1/hip-dysplasia/info").json()
        assert len(data["putti_triad"]) == 3

    def test_analyze_response_structure(self, app_client, test_png_bytes):
        response = app_client.post(
            "/api/v1/hip-dysplasia/analyze",
            files={"file": ("test.png", test_png_bytes, "image/png")},
        )
        if response.status_code == 200:
            data = response.json()
            ed = data["educational_data"]
            # Все 10 шагов отражены в ответе
            assert "xray_quality" in ed           # Шаг 1
            assert "masks" in ed                  # Шаг 2
            assert "ossification_nucleus" in ed   # Шаг 3
            assert "lines" in ed                  # Шаги 4–6
            assert "measurements_left" in ed      # Шаги 7–9
            assert "putti_triad" in data["result"]  # Шаг 10

    def test_unsupported_format(self, app_client):
        response = app_client.post(
            "/api/v1/hip-dysplasia/analyze",
            files={"file": ("test.pdf", b"%PDF", "application/pdf")},
        )
        assert response.status_code == 415
