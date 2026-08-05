from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QPushButton, QRadioButton, QGroupBox, QLineEdit,
    QTabWidget, QWidget, QDoubleSpinBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QCursor
import audio_recorder

class SettingsDialog(QDialog):
    def __init__(self, config, parent=None, on_save_callback=None):
        super().__init__(parent)
        self.config = config
        self.on_save_callback = on_save_callback
        self.setWindowTitle("0xVoice2Text // SYSTEM CONFIGURATION")
        self.resize(480, 520)

        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0c0e12;
                color: #e2e8f0;
                font-family: 'Consolas', 'Segoe UI', sans-serif;
            }
            QTabWidget::pane {
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                background-color: #0c0e12;
                padding: 12px;
            }
            QTabBar::tab {
                background-color: #141720;
                color: #a0aec0;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 12px;
                font-size: 11px;
                font-weight: bold;
                letter-spacing: 0.5px;
                margin-right: 3px;
            }
            QTabBar::tab:selected {
                background-color: rgba(0, 240, 255, 0.18);
                color: #00f0ff;
                border-color: rgba(0, 240, 255, 0.45);
            }
            QTabBar::tab:hover:!selected {
                background-color: rgba(255, 255, 255, 0.08);
                color: #ffffff;
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
            QLineEdit, QDoubleSpinBox {
                background-color: #161a22;
                color: #00f0ff;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 4px;
                padding: 5px 8px;
                font-size: 12px;
                font-family: 'Consolas', sans-serif;
                font-weight: bold;
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

        main_layout = QVBoxLayout()
        main_layout.setSpacing(12)

        # Title Label
        title_label = QLabel("⚡ 0xVoice2Text // SYSTEM CONFIGURATION")
        title_label.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #00f0ff; padding-bottom: 2px;")
        main_layout.addWidget(title_label)

        # Tab Widget
        self.tabs = QTabWidget()

        # TAB 1: VOICE & WAKE WORD (⚡ Активация & VAD Пауза)
        tab_voice = QWidget()
        voice_main_layout = QVBoxLayout(tab_voice)
        voice_main_layout.setSpacing(12)

        voice_group = QGroupBox("АВТОМАТИЧЕСКАЯ АКТИВАЦИЯ И VAD ПАУЗА (VOSK)")
        voice_layout = QVBoxLayout()
        voice_layout.setSpacing(10)

        self.chk_wake_enabled = QCheckBox("Включить активацию голосом по кодовому слову")
        self.chk_wake_enabled.setChecked(self.config.get("wake_word_enabled", True))

        wake_h_layout = QHBoxLayout()
        lbl_wake = QLabel("Слово старта:")
        self.txt_wake_words = QLineEdit()
        self.txt_wake_words.setText(str(self.config.get("wake_words", "джарвис, джарвиз, жарвис")))
        self.txt_wake_words.setPlaceholderText("джарвис, джарвиз")
        wake_h_layout.addWidget(lbl_wake)
        wake_h_layout.addWidget(self.txt_wake_words)

        stop_h_layout = QHBoxLayout()
        lbl_stop = QLabel("Слово стоп:")
        self.txt_stop_words = QLineEdit()
        self.txt_stop_words.setText(str(self.config.get("stop_words", "стоп")))
        self.txt_stop_words.setPlaceholderText("стоп")
        stop_h_layout.addWidget(lbl_stop)
        stop_h_layout.addWidget(self.txt_stop_words)

        # VAD Pause Delay Timeout Setting
        pause_h_layout = QHBoxLayout()
        lbl_pause = QLabel("Задержка молчания (VAD пауза):")
        self.spin_silence_timeout = QDoubleSpinBox()
        self.spin_silence_timeout.setRange(0.5, 10.0)
        self.spin_silence_timeout.setSingleStep(0.5)
        self.spin_silence_timeout.setSuffix(" сек")
        self.spin_silence_timeout.setValue(float(self.config.get("silence_timeout", 3.0)))
        pause_h_layout.addWidget(lbl_pause)
        pause_h_layout.addWidget(self.spin_silence_timeout)

        lbl_pause_desc = QLabel("⏱️ Время в секундах, через которое пауза в речи автоматически останавливает запись.")
        lbl_pause_desc.setFont(QFont("Consolas", 8))
        lbl_pause_desc.setStyleSheet("color: #718096;")

        self.chk_macros_enabled = QCheckBox("Голосовые макросы («Папочка вернулся», «Играем в танки», «Открой ...»)")
        self.chk_macros_enabled.setChecked(self.config.get("voice_macros_enabled", True))

        voice_layout.addWidget(self.chk_wake_enabled)
        voice_layout.addLayout(wake_h_layout)
        voice_layout.addLayout(stop_h_layout)
        voice_layout.addLayout(pause_h_layout)
        voice_layout.addWidget(lbl_pause_desc)
        voice_layout.addWidget(self.chk_macros_enabled)

        voice_group.setLayout(voice_layout)
        voice_main_layout.addWidget(voice_group)
        voice_main_layout.addStretch()

        self.tabs.addTab(tab_voice, "⚡ ГОЛОС И ВАД")

        # TAB 2: AUDIO & STT ENGINE (🎙️ Микрофон & Groq API)
        tab_audio = QWidget()
        audio_main_layout = QVBoxLayout(tab_audio)
        audio_main_layout.setSpacing(12)

        # Microphone Group
        audio_group = QGroupBox("ИСТОЧНИК ВВОДА ЗВУКА")
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
        audio_main_layout.addWidget(audio_group)

        # Groq Cloud Engine Group
        model_group = QGroupBox("GROQ CLOUD API (WHISPER LARGE V3)")
        model_layout = QVBoxLayout()

        lbl_hw = QLabel("🚀 Движок: Groq Cloud LPU API (whisper-large-v3)")
        lbl_hw.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        lbl_hw.setStyleSheet("""
            background: rgba(0, 240, 255, 0.1);
            color: #00f0ff;
            border: 1px solid rgba(0, 240, 255, 0.25);
            border-radius: 4px;
            padding: 6px 10px;
        """)
        model_layout.addWidget(lbl_hw)

        lbl_env = QLabel("Ключ доступа: GROQ_API_KEY в файле .env")
        lbl_env.setFont(QFont("Consolas", 9))
        lbl_env.setStyleSheet("color: #a0aec0; margin-top: 2px;")
        model_layout.addWidget(lbl_env)

        lbl_lang = QLabel("Целевой язык распознавания:")
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
        audio_main_layout.addWidget(model_group)
        audio_main_layout.addStretch()

        self.tabs.addTab(tab_audio, "🎙️ ЗВУК И СТТ")

        # TAB 3: HOTKEYS & OPTIONS (⌨️ Клавиши & Опции)
        tab_options = QWidget()
        opts_main_layout = QVBoxLayout(tab_options)
        opts_main_layout.setSpacing(12)

        # Hotkey Group
        hk_group = QGroupBox("ГОРЯЧАЯ КЛАВИША И РЕЖИМ")
        hk_layout = QVBoxLayout()
        
        hk_h_layout = QHBoxLayout()
        hk_label = QLabel("Клавиша триггер:")
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
        self.radio_toggle = QRadioButton("Toggle Mode (Нажал -> Говоришь -> Нажал -> Завершил)")
        self.radio_ptt = QRadioButton("Push-to-Talk (Зажатие клавиши)")
        
        if curr_mode == "toggle":
            self.radio_toggle.setChecked(True)
        else:
            self.radio_ptt.setChecked(True)

        hk_layout.addWidget(self.radio_toggle)
        hk_layout.addWidget(self.radio_ptt)
        hk_group.setLayout(hk_layout)
        opts_main_layout.addWidget(hk_group)

        # Additional System Options Group
        sys_group = QGroupBox("ПОВЕДЕНИЕ И ИНТЕРФЕЙС")
        sys_layout = QVBoxLayout()

        self.chk_auto_paste = QCheckBox("Автоматически вставлять распознанный текст в активное окно")
        self.chk_auto_paste.setChecked(self.config.get("auto_paste", True))
        
        self.chk_trailing_space = QCheckBox("Добавлять пробел после вставки")
        self.chk_trailing_space.setChecked(self.config.get("add_trailing_space", True))

        self.chk_sound = QCheckBox("Звуковые эффекты старта / стопа записи")
        self.chk_sound.setChecked(self.config.get("sound_feedback", True))

        self.chk_ontop = QCheckBox("Поверх всех окон (Закрепить виджет)")
        self.chk_ontop.setChecked(self.config.get("always_on_top", True))

        sys_layout.addWidget(self.chk_auto_paste)
        sys_layout.addWidget(self.chk_trailing_space)
        sys_layout.addWidget(self.chk_sound)
        sys_layout.addWidget(self.chk_ontop)
        sys_group.setLayout(sys_layout)
        opts_main_layout.addWidget(sys_group)
        opts_main_layout.addStretch()

        self.tabs.addTab(tab_options, "⌨️ КЛАВИШИ И ПОВЕДЕНИЕ")

        main_layout.addWidget(self.tabs)

        # Buttons (SAVE / CANCEL)
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
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

    def save_settings(self):
        mic_id = self.combo_mic.currentData()
        lang = self.combo_lang.currentData()
        hk = self.combo_hk.currentData()
        mode = "toggle" if self.radio_toggle.isChecked() else "push_to_talk"

        self.config.set("audio_device", mic_id)
        self.config.set("language", lang)
        self.config.set("hotkey", hk)
        self.config.set("hotkey_mode", mode)
        self.config.set("wake_word_enabled", self.chk_wake_enabled.isChecked())
        self.config.set("wake_words", self.txt_wake_words.text())
        self.config.set("stop_words", self.txt_stop_words.text())
        self.config.set("silence_timeout", float(self.spin_silence_timeout.value()))
        self.config.set("voice_macros_enabled", self.chk_macros_enabled.isChecked())
        self.config.set("auto_paste", self.chk_auto_paste.isChecked())
        self.config.set("add_trailing_space", self.chk_trailing_space.isChecked())
        self.config.set("sound_feedback", self.chk_sound.isChecked())
        self.config.set("always_on_top", self.chk_ontop.isChecked())

        if self.on_save_callback:
            self.on_save_callback()

        self.accept()
