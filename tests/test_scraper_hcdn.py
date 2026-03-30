"""
Tests para scraper_hcdn.py — Monitor Legislativo Diputados
Cubre: _get_json, _get_csv, _buscar_resource_csv,
       obtener_proyectos_para_tmm, obtener_horas_comision,
       obtener_votaciones_para_iqp, obtener_datos_hcdn.
"""

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock


CSV_PROYECTOS = (
    "fecha_ingreso,fecha_dictamen,titulo\n"
    "01/03/2024,15/06/2024,Proyecto A\n"
    "10/04/2024,20/07/2024,Proyecto B\n"
    "05/01/2023,10/03/2023,Proyecto Viejo\n"
)

CSV_REUNIONES = (
    "tipo,duracion\n"
    "comision,90\n"
    "comision,120\n"
    "pleno,180\n"
)

CSV_VOTACIONES = (
    "sesion,presentes\n"
    "2024-05-01,210\n"
    "2024-06-15,198\n"
    "2024-09-10,220\n"
)

JSON_CKAN_OK = {
    "success": True,
    "result": {
        "resources": [
            {"url": "https://datos.hcdn.gob.ar/dataset/proyectos/download/proyectos2024.csv", "format": "CSV"},
        ]
    }
}

JSON_CKAN_FAIL = {"success": False, "result": {}}


def make_mock(text="", json_data=None, status=200):
    mock = MagicMock()
    mock.status_code = status
    mock.text = text
    mock.headers = {"content-type": "text/csv"}
    if json_data is not None:
        mock.json.return_value = json_data
    mock.raise_for_status.return_value = None
    return mock


# ══════════════════════════════════════════════════════════════════════════════
# _get_json
# ══════════════════════════════════════════════════════════════════════════════

class TestGetJson:

    @patch("requests.get")
    def test_retorna_json_cuando_ok(self, mock_get):
        mock_get.return_value = make_mock(json_data={"key": "value"})
        from scraper_hcdn import _get_json
        result = _get_json("http://ejemplo.com/api")
        assert result == {"key": "value"}

    @patch("requests.get")
    def test_retorna_none_si_falla(self, mock_get):
        mock_get.side_effect = Exception("Timeout")
        from scraper_hcdn import _get_json
        result = _get_json("http://ejemplo.com/api")
        assert result is None

    @patch("requests.get")
    def test_retorna_none_si_http_error(self, mock_get):
        mock = make_mock(status=500)
        mock.raise_for_status.side_effect = Exception("500 Server Error")
        mock_get.return_value = mock
        from scraper_hcdn import _get_json
        result = _get_json("http://ejemplo.com/api")
        assert result is None


# ══════════════════════════════════════════════════════════════════════════════
# _get_csv
# ══════════════════════════════════════════════════════════════════════════════

class TestGetCsv:

    @patch("requests.get")
    def test_retorna_dataframe_cuando_ok(self, mock_get):
        mock_get.return_value = make_mock(text="col1,col2\nA,B\nC,D\n")
        from scraper_hcdn import _get_csv
        df = _get_csv("http://ejemplo.com/data.csv")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2

    @patch("requests.get")
    def test_retorna_none_si_falla(self, mock_get):
        mock_get.side_effect = Exception("Connection error")
        from scraper_hcdn import _get_csv
        result = _get_csv("http://ejemplo.com/data.csv")
        assert result is None


# ══════════════════════════════════════════════════════════════════════════════
# _buscar_resource_csv
# ══════════════════════════════════════════════════════════════════════════════

class TestBuscarResourceCsv:

    @patch("scraper_hcdn._get_json")
    def test_retorna_url_csv_cuando_existe(self, mock_json):
        mock_json.return_value = JSON_CKAN_OK
        from scraper_hcdn import _buscar_resource_csv
        url = _buscar_resource_csv("proyectos", 2024)
        assert url is not None
        assert "csv" in url.lower() or "CSV" in url

    @patch("scraper_hcdn._get_json")
    def test_retorna_none_cuando_api_falla(self, mock_json):
        mock_json.return_value = None
        from scraper_hcdn import _buscar_resource_csv
        url = _buscar_resource_csv("proyectos", 2024)
        assert url is None

    @patch("scraper_hcdn._get_json")
    def test_retorna_none_cuando_success_false(self, mock_json):
        mock_json.return_value = JSON_CKAN_FAIL
        from scraper_hcdn import _buscar_resource_csv
        url = _buscar_resource_csv("proyectos", 2024)
        assert url is None


# ══════════════════════════════════════════════════════════════════════════════
# obtener_proyectos_para_tmm
# ══════════════════════════════════════════════════════════════════════════════

class TestObtenerProyectosParaTmm:

    @patch("scraper_hcdn._buscar_resource_csv", return_value=None)
    @patch("scraper_hcdn._get_csv")
    def test_retorna_lista_de_proyectos(self, mock_csv, mock_buscar, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mock_csv.return_value = pd.read_csv(
            __import__("io").StringIO(CSV_PROYECTOS)
        )
        from scraper_hcdn import obtener_proyectos_para_tmm
        proyectos = obtener_proyectos_para_tmm(anio=2024)
        assert isinstance(proyectos, list)
        assert len(proyectos) > 0

    @patch("scraper_hcdn._buscar_resource_csv", return_value=None)
    @patch("scraper_hcdn._get_csv")
    def test_cada_proyecto_tiene_fechas(self, mock_csv, mock_buscar, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mock_csv.return_value = pd.read_csv(__import__("io").StringIO(CSV_PROYECTOS))
        from scraper_hcdn import obtener_proyectos_para_tmm
        proyectos = obtener_proyectos_para_tmm(anio=2024)
        for p in proyectos:
            assert "fecha_ingreso" in p
            assert "fecha_dictamen" in p

    @patch("scraper_hcdn._buscar_resource_csv", return_value=None)
    @patch("scraper_hcdn._get_csv", return_value=None)
    def test_retorna_lista_vacia_si_no_hay_datos(self, mock_csv, mock_buscar, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from scraper_hcdn import obtener_proyectos_para_tmm
        proyectos = obtener_proyectos_para_tmm(anio=2024)
        assert proyectos == []

    @patch("scraper_hcdn._buscar_resource_csv", return_value=None)
    @patch("scraper_hcdn._get_csv")
    def test_descarta_proyectos_de_otro_anio(self, mock_csv, mock_buscar, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mock_csv.return_value = pd.read_csv(__import__("io").StringIO(CSV_PROYECTOS))
        from scraper_hcdn import obtener_proyectos_para_tmm
        # El CSV tiene 1 proyecto de 2023 — no debe aparecer en 2024
        proyectos_2024 = obtener_proyectos_para_tmm(anio=2024)
        for p in proyectos_2024:
            assert "2024" in p["fecha_ingreso"] or "2024" in p["fecha_dictamen"]


# ══════════════════════════════════════════════════════════════════════════════
# obtener_horas_comision
# ══════════════════════════════════════════════════════════════════════════════

class TestObtenerHorasComision:

    @patch("scraper_hcdn._buscar_resource_csv", return_value=None)
    @patch("scraper_hcdn._get_csv")
    def test_retorna_dict_con_horas(self, mock_csv, mock_buscar, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mock_csv.return_value = pd.read_csv(__import__("io").StringIO(CSV_REUNIONES))
        from scraper_hcdn import obtener_horas_comision
        result = obtener_horas_comision(anio=2024)
        assert isinstance(result, dict)
        assert "horas_comision" in result
        assert "horas_pleno" in result

    @patch("scraper_hcdn._buscar_resource_csv", return_value=None)
    @patch("scraper_hcdn._get_csv", return_value=None)
    def test_retorna_dict_vacio_si_no_hay_datos(self, mock_csv, mock_buscar, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from scraper_hcdn import obtener_horas_comision
        result = obtener_horas_comision(anio=2024)
        assert result == {}

    @patch("scraper_hcdn._buscar_resource_csv", return_value=None)
    @patch("scraper_hcdn._get_csv")
    def test_horas_son_numeros_positivos(self, mock_csv, mock_buscar, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mock_csv.return_value = pd.read_csv(__import__("io").StringIO(CSV_REUNIONES))
        from scraper_hcdn import obtener_horas_comision
        result = obtener_horas_comision(anio=2024)
        if result:
            assert result.get("horas_comision", 0) >= 0
            assert result.get("horas_pleno", 0) >= 0


# ══════════════════════════════════════════════════════════════════════════════
# obtener_votaciones_para_iqp
# ══════════════════════════════════════════════════════════════════════════════

class TestObtenerVotacionesParaIqp:

    @patch("scraper_hcdn._buscar_resource_csv", return_value=None)
    @patch("scraper_hcdn._get_csv")
    def test_retorna_lista_de_votaciones(self, mock_csv, mock_buscar, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mock_csv.return_value = pd.read_csv(__import__("io").StringIO(CSV_VOTACIONES))
        from scraper_hcdn import obtener_votaciones_para_iqp
        votaciones = obtener_votaciones_para_iqp(anio=2024)
        assert isinstance(votaciones, list)
        assert len(votaciones) > 0

    @patch("scraper_hcdn._buscar_resource_csv", return_value=None)
    @patch("scraper_hcdn._get_csv")
    def test_cada_votacion_tiene_presentes(self, mock_csv, mock_buscar, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mock_csv.return_value = pd.read_csv(__import__("io").StringIO(CSV_VOTACIONES))
        from scraper_hcdn import obtener_votaciones_para_iqp
        votaciones = obtener_votaciones_para_iqp(anio=2024)
        for v in votaciones:
            assert "presentes" in v
            assert v["presentes"] > 0

    @patch("scraper_hcdn._buscar_resource_csv", return_value=None)
    @patch("scraper_hcdn._get_csv", return_value=None)
    def test_retorna_lista_vacia_si_no_hay_datos(self, mock_csv, mock_buscar, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from scraper_hcdn import obtener_votaciones_para_iqp
        result = obtener_votaciones_para_iqp(anio=2024)
        assert result == []


# ══════════════════════════════════════════════════════════════════════════════
# obtener_datos_hcdn (función principal)
# ══════════════════════════════════════════════════════════════════════════════

class TestObtenerDatosHcdn:

    @patch("scraper_hcdn.obtener_votaciones_para_iqp", return_value=[{"presentes": 210}])
    @patch("scraper_hcdn.obtener_horas_comision", return_value={"horas_comision": 100.0, "horas_pleno": 25.0})
    @patch("scraper_hcdn.obtener_proyectos_para_tmm", return_value=[{"fecha_ingreso": "2024-03-01", "fecha_dictamen": "2024-06-15"}])
    def test_retorna_dict_con_claves(self, mock_proy, mock_horas, mock_vot, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from scraper_hcdn import obtener_datos_hcdn
        result = obtener_datos_hcdn(anio=2024)
        assert isinstance(result, dict)
        assert "proyectos" in result
        assert "horas_comision" in result
        assert "votaciones" in result

    @patch("scraper_hcdn.obtener_votaciones_para_iqp", return_value=[])
    @patch("scraper_hcdn.obtener_horas_comision", return_value={})
    @patch("scraper_hcdn.obtener_proyectos_para_tmm", return_value=[])
    def test_retorna_dict_vacio_si_nada_disponible(self, mock_proy, mock_horas, mock_vot, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from scraper_hcdn import obtener_datos_hcdn
        result = obtener_datos_hcdn(anio=2024)
        assert isinstance(result, dict)

    @patch("scraper_hcdn.obtener_votaciones_para_iqp", return_value=[{"presentes": 210}])
    @patch("scraper_hcdn.obtener_horas_comision", return_value={"horas_comision": 100.0, "horas_pleno": 25.0})
    @patch("scraper_hcdn.obtener_proyectos_para_tmm", return_value=[{"fecha_ingreso": "2024-03-01", "fecha_dictamen": "2024-06-15"}])
    def test_guarda_json_resumen(self, mock_proy, mock_horas, mock_vot, tmp_path, monkeypatch):
        import scraper_hcdn as sh
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        monkeypatch.setattr(sh, "DATA_DIR", data_dir)
        sh.obtener_datos_hcdn(anio=2024)
        archivos = list(data_dir.glob("hcdn_resumen_*.json"))
        assert len(archivos) == 1