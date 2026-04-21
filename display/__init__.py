# Public API của package display
# Import từ đây thay vì import trực tiếp vào các module con

from display.display_controller import trigger_sensor_display

__all__ = ["trigger_sensor_display"]
