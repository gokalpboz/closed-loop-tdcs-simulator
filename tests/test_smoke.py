
def test_imports():
    import importlib
    for mod in [
        'src.app.closed_loop',
        'src.streaming.lsl_client',
        'src.processing.eeg_pipeline',
        'src.policy.bandpower_controller',
        'src.policy.ml_policy',
        'src.hardware.stimulator_api',
        'src.safety.safety_manager',
        'src.utils.signal',
    ]:
        importlib.import_module(mod)
