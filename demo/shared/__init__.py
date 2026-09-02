"""Shared demo components - reusable widgets and utilities for all demos."""

from .theme import DARK_QSS, apply_theme, fix_checkbox_width
from .dialogs import themed_confirm, themed_message, themed_notify
from .connect_bar import ConnectBar
from .project_image_loader import ProjectImageLoader
from .preset_tree import PresetTreeWidget
from .image_table import ImageTable
from .watch_config_panel import WatchConfigPanel
from .export_options_panel import ExportOptionsPanel
from .env_config import load_env, load_env_info, resolve_socket_path
from .phase2_widgets import Card, FieldLabel, Phase2DemoWindow

__all__ = [
    'DARK_QSS', 'apply_theme', 'fix_checkbox_width',
    'themed_confirm', 'themed_message', 'themed_notify',
    'ConnectBar',
    'ProjectImageLoader',
    'PresetTreeWidget',
    'ImageTable',
    'WatchConfigPanel',
    'ExportOptionsPanel',
    'load_env',
    'load_env_info',
    'resolve_socket_path',
    'Card',
    'FieldLabel',
    'Phase2DemoWindow',
]
