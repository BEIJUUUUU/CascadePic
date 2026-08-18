from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QSignalSpy

from waterfall_viewer.ui.jump_slider import JumpSlider


def test_slider_click_jumps_directly_to_position(qtbot) -> None:
    slider = JumpSlider(Qt.Orientation.Horizontal)
    slider.setRange(0, 100)
    slider.resize(200, 28)
    qtbot.addWidget(slider)
    slider.show()
    spy = QSignalSpy(slider.jumped)

    qtbot.mouseClick(slider, Qt.MouseButton.LeftButton, pos=QPoint(150, 14))

    assert 74 <= slider.value() <= 76
    assert spy.count() >= 1
