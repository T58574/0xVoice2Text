from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QPushButton, QRadioButton, QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QCursor
import audio_recorder

class SettingsDialog(QDialog):
    def __init__(self, config, parent=None, on_save_callback=None):
        super().__init__(parent)
        self.config = config
        self.on_save_callback = on_save_callback
        self.setWindowTitle("0xVoice2Text // SETTINGS")
        self.resize(440, 500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0c0e12;
                color: #e2e8f0;
                font-family: 'Consolas', 'Segoe UI', sans-serif;
            }
            QGroupBox {
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 15px;
                font-weight: bold;
                font-size: 11px;
                color: #00f0ff;
                letter-spacing: 1px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLabel {
                color: #a0aec0;
                font-size: 12px;
            }
            QComboBox {
                background-color: #161a22;
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #161a22;
                color: #ffffff;
                selection-background-color: #00f0ff;
                selection-color: #000000;
            }
            QCheckBox, QRadioButton {
                color: #e2e8f0;
                font-size: 12px;
                spacing: 8px;
            }
            QCheckBox::indicator, QRadioButton::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 3px;
                background: #161a22;
            }
            QCheckBox::indicator:checked, QRadioButton::indicator:checked {
                background: #00f0ff;
                border-color: #00f0ff;
            }
            QPushButton {
                background: rgba(0, 240, 255, 0.15);
                color: #00f0ff;
                font-weight: bold;
                border: 1px solid #00f0ff;
                border-radius: 4px;
                padding: 8px 18px;
                font-size: 12px;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: #00f0ff;
                color: #000000;
            }
            QPushButton#btnCancel {
                background-color: transparent;
                color: #718096;
                border: 1px solid #4a5568;
            }
            QPushButton#btnCancel:hover {
                background-color: rgba(255, 255, 255, 0.05);
                color: #ffffff;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)

        title_label = QLabel("⚡ 0xVoice2Text // SYSTEM CONFIGURATION")
        title_label.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #00f0ff; padding-bottom: 2px;")
        layout.addWidget(title_label)

        # 1. Microphone Group
        audio_group = QGroupBox("AUDIO INPUT SOURCE")
        audio_layout = QVBoxLayout()
        self.combo_mic = QComboBox()
        self.devices = audio_recorder.get_input_devices()
        
        self.combo_mic.addItem("DEFAULT SYSTEM MICROPHONE", None)
        current_device = self.config.get("audio_device")
        selected_idx = 0

        for idx, dev in enumerate(self.devices):
            self.combo_mic.addItem(f"{dev['name']}", dev['id'])
            if current_device is not None and dev['id'] == current_device:
                selected_idx = idx + 1

        self.combo_mic.setCurrentIndex(selected_idx)
        audio_layout.addWidget(self.combo_mic)
        audio_group.setLayout(audio_layout)
        layout.addWidget(audio_group)

        # 2. Groq Cloud Engine Group
        model_group = QGroupBox("GROQ CLOUD API (WHISPER LARGE V3)")
        model_layout = QVBoxLayout()

        lbl_hw = QLabel("🚀 Engine: Groq Cloud LPU API (whisper-large-v3)")
        lbl_hw.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        lbl_hw.setStyleSheet("""
            background: rgba(0, 240, 255, 0.1);
            color: #00f0ff;
            border: 1px solid rgba(0, 240, 255, 0.25);
            border-radius: 4px;
            padding: 4px 8px;
        """)
        model_layout.addWidget(lbl_hw)

        lbl_env = QLabel("Key setup: Specify GROQ_API_KEY in .env file")
        lbl_env.setFont(QFont("Consolas", 9))
        lbl_env.setStyleSheet("color: #a0aec0; margin-top: 2px;")
        model_layout.addWidget(lbl_env)

        lbl_lang = QLabel("Target Language:")
        self.combo_lang = QComboBox()
        langs = [("Russian (ru)", "ru"), ("English (en)", "en"), ("Auto-Detect", "auto")]
        curr_lang = self.config.get("language", "ru")
        lang_select_idx = 0
        for i, (label, val) in enumerate(langs):
            self.combo_lang.addItem(label, val)
            if val == curr_lang:
                lang_select_idx = i
        self.combo_lang.setCurrentIndex(lang_select_idx)

        model_layout.addWidget(lbl_lang)
        model_layout.addWidget(self.combo_lang)
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)

        # 3. Hotkey Group
        hk_group = QGroupBox("HOTKEY TRIGGER & MODE")
        hk_layout = QVBoxLayout()
        
        hk_h_layout = QHBoxLayout()
        hk_label = QLabel("Trigger Key:")
        self.combo_hk = QComboBox()
        hk_options = [
            ("Ctrl + Space (Рекомендуется)", "ctrl+space"),
            ("Alt + 3", "alt+3"),
            ("Caps Lock", "caps_lock"),
            ("F8", "f8"),
            ("F9", "f9"),
            ("F10", "f10"),
            ("Scroll Lock", "scroll_lock")
        ]
        curr_hk = self.config.get("hotkey", "ctrl+space")
        hk_select_idx = 0
        for i, (label, val) in enumerate(hk_options):
            self.combo_hk.addItem(label, val)
            if val == curr_hk:
                hk_select_idx = i
        self.combo_hk.setCurrentIndex(hk_select_idx)
        
        hk_h_layout.addWidget(hk_label)
        hk_h_layout.addWidget(self.combo_hk)
        hk_layout.addLayout(hk_h_layout)

        curr_mode = self.config.get("hotkey_mode", "toggle")
        self.radio_toggle = QRadioButton("Toggle Mode (Нажал Alt-3 -> Говоришь -> Нажал Alt-3 -> Готово)")
        self.radio_ptt = QRadioButton("Hold Key (Push-to-Talk: Зажатие)")
        
        if curr_mode == "toggle":
            self.radio_toggle.setChecked(True)
        else:
            self.radio_ptt.setChecked(True)

        hk_layout.addWidget(self.radio_toggle)
        hk_layout.addWidget(self.radio_ptt)
        hk_group.setLayout(hk_layout)
        layout.addWidget(hk_group)

        # 4. Toggles
        opts_layout = QVBoxLayout()
        self.chk_auto_paste = QCheckBox("Auto-paste text into active focus window")
        self.chk_auto_paste.setChecked(self.config.get("auto_paste", True))
        
        self.chk_trailing_space = QCheckBox("Add trailing space after insertion")
        self.chk_trailing_space.setChecked(self.config.get("add_trailing_space", True))

        self.chk_sound = QCheckBox("Audio feedback beep on record start/stop")
        self.chk_sound.setChecked(self.config.get("sound_feedback", True))

        self.chk_ontop = QCheckBox("Always on top (Pin widget above windows)")
        self.chk_ontop.setChecked(self.config.get("always_on_top", True))

        opts_layout.addWidget(self.chk_auto_paste)
        opts_layout.addWidget(self.chk_trailing_space)
        opts_layout.addWidget(self.chk_sound)
        opts_layout.addWidget(self.chk_ontop)
        layout.addLayout(opts_layout)

        # 5. Buttons
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("SAVE CONFIG")
        btn_cancel = QPushButton("CANCEL")
        btn_cancel.setObjectName("btnCancel")

        btn_save.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_cancel.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        btn_save.clicked.connect(self.save_settings)
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def save_settings(self):
        mic_id = self.combo_mic.currentData()
        lang = self.combo_lang.currentData()
        hk = self.combo_hk.currentData()
        mode = "toggle" if self.radio_toggle.isChecked() else "push_to_talk"

        self.config.set("audio_device", mic_id)
        self.config.set("language", lang)
        self.config.set("hotkey", hk)
        self.config.set("hotkey_mode", mode)
        self.config.set("auto_paste", self.chk_auto_paste.isChecked())
        self.config.set("add_trailing_space", self.chk_trailing_space.isChecked())
        self.config.set("sound_feedback", self.chk_sound.isChecked())
        self.config.set("always_on_top", self.chk_ontop.isChecked())

        if self.on_save_callback:
            self.on_save_callback()

        self.accept()
