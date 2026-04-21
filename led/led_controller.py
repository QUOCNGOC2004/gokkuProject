from led.led_driver import set_color, turn_off, COLORS

# Thứ tự xoay vòng khi bấm nút 3
_CYCLE = ["RED", "GREEN", "BLUE", "OFF"]

# Con trỏ trạng thái hiện tại (bắt đầu từ OFF)
_state_index: int = len(_CYCLE) - 1   # → 3 (OFF)


def cycle_next() -> str:
    """
    Mỗi lần gọi sẽ chuyển sang màu tiếp theo trong vòng:
    RED → GREEN → BLUE → OFF → RED → ...
    Trả về tên trạng thái hiện tại để log.
    """
    global _state_index

    _state_index = (_state_index + 1) % len(_CYCLE)
    name = _CYCLE[_state_index]

    if name == "OFF":
        turn_off()
    else:
        r, g, b = COLORS[name]
        set_color(r, g, b)

    print(f"[LED] → {name}")
    return name


def get_state() -> str:
    """Trả về tên màu hiện tại."""
    return _CYCLE[_state_index]
