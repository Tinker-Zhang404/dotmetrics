__all__ = [
    "ImageLoader",
    "ParticleAnalyzer",
    "ResultExporter",
    "Visualizer",
    "logger",
    "resolve_model_path",
    "runtime_dir",
    "temp_dir",
    "user_data_dir",
]


def __getattr__(name):
    if name == "ImageLoader":
        from .image_loader import ImageLoader

        return ImageLoader
    if name == "ParticleAnalyzer":
        from .analyzer import ParticleAnalyzer

        return ParticleAnalyzer
    if name == "ResultExporter":
        from .exporter import ResultExporter

        return ResultExporter
    if name == "Visualizer":
        from .visualization import Visualizer

        return Visualizer
    if name == "logger":
        from .logging_utils import logger

        return logger
    if name in {"resolve_model_path", "runtime_dir", "temp_dir", "user_data_dir"}:
        from .runtime_paths import resolve_model_path, runtime_dir, temp_dir, user_data_dir

        return {
            "resolve_model_path": resolve_model_path,
            "runtime_dir": runtime_dir,
            "temp_dir": temp_dir,
            "user_data_dir": user_data_dir,
        }[name]
    raise AttributeError(name)
