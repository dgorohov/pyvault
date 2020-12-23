from PyQt5 import uic, QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QPoint, pyqtProperty, QEasingCurve, QTimer
from PyQt5.QtWidgets import QDialog

from vault.prompt.qt import resource_path


class MFAUiPrompt:
    __app = None

    def __init__(self):
        self.__app = QtWidgets.QApplication([])

    def prompt(self, title="Enter MFA:"):
        assert self.__app is not None
        window = _Prompt()
        return window.value if window.prompt(title=title, validator_fn=lambda v: len(v) == 6 and v.isdigit()) else ''


class _Prompt(QDialog):
    __validator_fn = None

    def __init__(self):
        super(_Prompt, self).__init__()
        uic.loadUi(resource_path('prompt.ui'), self)
        self.__origin_point = QPoint(0, 0)
        self.__shake_diff = QPoint(20, 20)
        self.__total_shake_duration = 750
        self.__single_shake_duration = 25
        self.__animation = QtCore.QPropertyAnimation(
            self,
            propertyName=b'point',
            finished=self.__bounce_next_point
        )
        self.__animation_timer = QTimer()
        self.__animation_timer.timeout.connect(lambda: self.__animation.stop())

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if not event.modifiers():
            if event.key() == QtCore.Qt.Key_Return:
                self.accept()
            elif event.key() == QtCore.Qt.Key_Escape:
                self.reject()
        elif event.modifiers() == QtCore.Qt.KeypadModifier and event.key() == QtCore.Qt.Key_Enter:
            self.accept()
        else:
            super(QDialog, self).keyPressEvent(event)

    def prompt(self, title, validator_fn=None):
        self.adjustSize()
        self.__validator_fn = validator_fn
        self.prompt_label.setText(title)
        return self.exec_()

    @property
    def value(self):
        return self.prompt_value.text()

    @pyqtProperty(QPoint)
    def point(self):
        return self.pos()

    @point.setter
    def point(self, value):
        self.move(value)

    def __bounce_error(self):
        self.__origin_point = self.pos()
        self.__animation.setDuration(self.__single_shake_duration)
        self.__animation.setTargetObject(self)
        self.__animation.setStartValue(self.__origin_point)
        self.__animation.setEndValue(self.__origin_point + self.__shake_diff)
        self.__animation.setEasingCurve(QEasingCurve.OutBounce)
        self.__animation.start()
        self.__animation_timer.start(self.__total_shake_duration)

    def __bounce_next_point(self):
        _from = self.__animation.endValue()
        if self.__origin_point.x() > _from.x():
            _to = _from + self.__shake_diff
        else:
            _to = _from - self.__shake_diff
        self.__animation.setStartValue(_from)
        self.__animation.setEndValue(_to)
        self.__animation.start()

    def accept(self) -> None:
        if self.__validator_fn is None or self.__validator_fn(self.value):
            super(_Prompt, self).accept()
        else:
            self.__bounce_error()


if __name__ == '__main__':
    prompt = MFAUiPrompt()
    print(prompt.prompt())
