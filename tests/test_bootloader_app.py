from types import SimpleNamespace

import bootloader_app


def make_app():
    app = bootloader_app.MotorolaBootloaderUtility.__new__(bootloader_app.MotorolaBootloaderUtility)
    app.root = SimpleNamespace(update_idletasks=lambda: None)
    app.console = SimpleNamespace(insert=lambda *args, **kwargs: None, see=lambda *args, **kwargs: None)
    app.status_var = SimpleNamespace(set=lambda *args, **kwargs: None)
    app.running = False
    return app


def test_run_generic_cmd_accepts_cwd(tmp_path):
    app = make_app()
    output, code = app._run_generic_cmd(
        ["python3", "-c", "import os; print(os.getcwd())"],
        cwd=str(tmp_path),
    )
    assert code == 0
    assert str(tmp_path) in output
