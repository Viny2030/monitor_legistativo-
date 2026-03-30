"""
Tests para obtener_datos.py — Monitor Legislativo Diputados
Cubre: nómina, DDJJ, presupuesto — sin llamadas reales a internet.
"""

import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock

HTML_HCDN_CON_TABLA = """
<html><body>
<table>
  <tr><th></th><th>Nombre</th><th>Distrito</th><th>Bloque</th></tr>
  <tr><td></td><td>GARCIA, Juan</td><td>Buenos Aires</td><td>UCR</td></tr>
  <tr><td></td><td>LOPEZ, Maria</td><td>Córdoba</td><td>PRO</td></tr>
  <tr><td></td><td>PEREZ, Carlos</td><td>Santa Fe</td><td>UxP</td></tr>
</table>
</body></html>
"""

HTML_SIN_TABLA = "<html><body><p>Sin datos</p></body></html>"
CSV_NOMINA = "Nombre,Distrito,Bloque\nGARCIA Juan,Buenos Aires,UCR\nLOPEZ Maria,Córdoba,PRO\n"


def make_mock(text="", json_data=None, status=200, content_type="text/csv"):
    mock = MagicMock()
    mock.status_code = status
    mock.text = text
    mock.content = text.encode() if text else b""
    mock.headers = {"content-type": content_type}
    if json_data is not None:
        mock.json.return_value = json_data
    mock.raise_for_status.return_value = None
    return mock


class TestObtenerNominaDiputados:

    @patch("requests.get")
    def test_retorna_dataframe_desde_csv(self, mock_get, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mock_get.return_value = make_mock(text=CSV_NOMINA)
        from obtener_datos import obtener_nomina_diputados
        df = obtener_nomina_diputados()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    @patch("obtener_datos._scraping_alternativo_diputados")
    @patch("requests.get")
    def test_usa_scraping_cuando_csv_falla(self, mock_get, mock_scraping, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mock_get.side_effect = Exception("Connection error")
        mock_scraping.return_value = pd.DataFrame([{"Nombre": "A", "Distrito": "B", "Bloque": "C"}])
        from obtener_datos import obtener_nomina_diputados
        obtener_nomina_diputados()
        mock_scraping.assert_called_once()

    @patch("requests.get")
    def test_guarda_csv_en_data_dir(self, mock_get, tmp_path, monkeypatch):
        import obtener_datos as od
        # DATA_DIR usa Path(__file__).parent, así que lo parcheamos directamente
        monkeypatch.setattr(od, "DATA_DIR", tmp_path / "data")
        (tmp_path / "data").mkdir()
        mock_get.return_value = make_mock(text=CSV_NOMINA)
        od.obtener_nomina_diputados()
        assert (tmp_path / "data" / "nomina_diputados.csv").exists()

    @patch("requests.get")
    def test_columnas_presentes(self, mock_get, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mock_get.return_value = make_mock(text=CSV_NOMINA)
        from obtener_datos import obtener_nomina_diputados
        df = obtener_nomina_diputados()
        for col in ["Nombre", "Distrito", "Bloque"]:
            assert col in df.columns


class TestScrapingAlternativo:

    @patch("requests.get")
    def test_extrae_diputados_de_tabla(self, mock_get, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mock_get.return_value = make_mock(text=HTML_HCDN_CON_TABLA, content_type="text/html")
        from obtener_datos import _scraping_alternativo_diputados
        df = _scraping_alternativo_diputados()
        assert isinstance(df, pd.DataFrame)

    @patch("requests.get")
    def test_devuelve_vacio_sin_tabla(self, mock_get, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mock_get.return_value = make_mock(text=HTML_SIN_TABLA, content_type="text/html")
        from obtener_datos import _scraping_alternativo_diputados
        df = _scraping_alternativo_diputados()
        assert df.empty

    @patch("requests.get")
    def test_maneja_error_de_red(self, mock_get, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mock_get.side_effect = Exception("Timeout")
        from obtener_datos import _scraping_alternativo_diputados
        df = _scraping_alternativo_diputados()
        assert df.empty


class TestIntentarDDJJ:

    @patch("requests.get")
    def test_retorna_ok_cuando_200(self, mock_get):
        mock_get.return_value = make_mock(status=200)
        from obtener_datos import intentar_ddjj
        result = intentar_ddjj()
        assert result["status"] == "ok"
        assert result["codigo_http"] == 200

    @patch("requests.get")
    def test_maneja_error_conexion(self, mock_get):
        mock_get.side_effect = Exception("Connection refused")
        from obtener_datos import intentar_ddjj
        result = intentar_ddjj()
        assert result["status"] == "sin_respuesta"
        assert "error" in result

    @patch("requests.get")
    def test_maneja_error_dns(self, mock_get, capsys):
        mock_get.side_effect = Exception("getaddrinfo failed")
        from obtener_datos import intentar_ddjj
        result = intentar_ddjj()
        assert result["status"] == "sin_respuesta"
        captured = capsys.readouterr()
        assert "DNS" in captured.out or "8.8.8.8" in captured.out

    @patch("requests.get")
    def test_retorna_dict_con_status(self, mock_get):
        mock_get.side_effect = Exception("Any error")
        from obtener_datos import intentar_ddjj
        result = intentar_ddjj()
        assert isinstance(result, dict)
        assert "status" in result


class TestCargarDDJJManual:

    def test_carga_csv_existente(self, tmp_path, monkeypatch):
        import obtener_datos as od
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        csv = data_dir / "ddjj_diputados.csv"
        csv.write_text("Nombre,DDJJ\nGARCIA Juan,2025\n", encoding="utf-8-sig")
        monkeypatch.setattr(od, "DATA_DIR", data_dir)
        df = od.cargar_ddjj_manual()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_devuelve_vacio_si_no_existe(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from obtener_datos import cargar_ddjj_manual
        df = cargar_ddjj_manual()
        assert df.empty

    def test_acepta_ruta_personalizada(self, tmp_path):
        csv = tmp_path / "mi_ddjj.csv"
        csv.write_text("Nombre,DDJJ\nLOPEZ Maria,2025\n", encoding="utf-8-sig")
        from obtener_datos import cargar_ddjj_manual
        df = cargar_ddjj_manual(str(csv))
        assert len(df) == 1
        assert df.iloc[0]["Nombre"] == "LOPEZ Maria"


class TestObtenerPresupuestoCongreso:

    @patch("requests.get")
    def test_devuelve_vacio_si_falla(self, mock_get, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mock_get.side_effect = Exception("Connection error")
        from obtener_datos import obtener_presupuesto_congreso
        df = obtener_presupuesto_congreso()
        assert df.empty

    @patch("requests.get")
    def test_imprime_instrucciones_si_falla(self, mock_get, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        mock_get.side_effect = Exception("Timeout")
        from obtener_datos import obtener_presupuesto_congreso
        obtener_presupuesto_congreso()
        captured = capsys.readouterr()
        assert "datos.gob.ar" in captured.out or "manual" in captured.out.lower()

    @patch("requests.get")
    def test_retorna_dataframe(self, mock_get, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        csv_content = "jurisdiccion,monto\n01,1000\n01,3000\n"
        mock_get.return_value = make_mock(text=csv_content)
        from obtener_datos import obtener_presupuesto_congreso
        df = obtener_presupuesto_congreso(anio=2024)
        assert isinstance(df, pd.DataFrame)