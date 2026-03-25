import logging
import os
from pathlib import Path

from click.testing import CliRunner

from sadie.app import airr, sadie
from tests.conftest import SadieFixture


def test_airr_cli(fixture_setup: SadieFixture):
    tmp_path = fixture_setup.tmp_path

    # Temporarily disable root logger StreamHandlers to prevent conflict between
    # pytest log_cli=True and Click CliRunner's stdout/stderr isolation
    root_logger = logging.getLogger()
    saved_handlers = root_logger.handlers[:]
    root_logger.handlers = [h for h in root_logger.handlers if not isinstance(h, logging.StreamHandler)]

    runner = CliRunner(mix_stderr=False)

    # check that sadie can be invoked alone (with --help)
    results = runner.invoke(sadie, ["--help"])
    assert results.exit_code == 0

    input_file = fixture_setup.get_catnap_heavy_nt()

    # this will be the default if we don't specify
    output_path = input_file.parent / Path(input_file.stem + ".tsv.gz")
    results = runner.invoke(airr, [str(input_file)])
    assert results.exit_code == 0
    os.remove(output_path)

    # explicitly specify the output file
    results = runner.invoke(airr, ["--skip-igl", "--skip-mutation", str(input_file), str(output_path)])
    assert results.exit_code == 0
    os.remove(output_path)

    # can we do feather
    tmp_out = tmp_path / "airr.feather"
    results = runner.invoke(airr, ["--skip-igl", "--skip-mutation", str(input_file), str(tmp_out)])
    assert Path(tmp_out).exists()
    assert results.exit_code == 0

    # can we do csv
    tmp_out = tmp_path / "airr.csv"
    results = runner.invoke(airr, ["--skip-igl", "--skip-mutation", str(input_file), str(tmp_out)])
    assert Path(tmp_out).exists()
    assert results.exit_code == 0

    # can we do gb
    tmp_out = tmp_path / "airr.gb"
    results = runner.invoke(airr, ["--skip-igl", "--skip-mutation", str(input_file), str(tmp_out)])
    assert Path(tmp_out).exists()
    assert results.exit_code == 0

    root_logger.handlers = saved_handlers
