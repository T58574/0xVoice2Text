from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QPushButton, QRadioButton, QGroupBox, QLineEdit,
    QTabWidget, QWidget, QDoubleSpinBox, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QCursor
from src.core.audio_recorder import get_input_devices
from src.core.logger import logger

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
                background-color: #000000;
                color: #ffffff;
                font-family: 'Consolas', 'Segoe UI', sans-serif;
            }
            QTabWidget::pane {
                border: 1px solid #27272a;
                border-radius: 6px;
                background-color: #000000;
                padding: 12px;
            }
            QTabBar::tab {
                background-color: #09090b;
                color: #a1a1aa;
                border: 1px solid #27272a;
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
                background-color: #ffffff;
                color: #000000;
                border-color: #ffffff;
                border-bottom: 1px solid #ffffff;
            }
            QTabBar::tab:hover:!selected {
                background-color: #18181b;
                color: #ffffff;
            }
            QGroupBox {
                border: 1px solid #27272a;
                border-radius: 6px;
                background-color: #000000;
                margin-top: 10px;
                padding-top: 15px;
                font-weight: bold;
                font-size: 11px;
                color: #ffffff;
                letter-spacing: 1px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                background-color: #000000;
            }
            QLabel {
                color: #a1a1aa;
                font-size: 12px;
            }
            QComboBox {
                background-color: #09090b;
                color: #ffffff;
                border: 1px solid #27272a;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #09090b;
                color: #ffffff;
                selection-background-color: #ffffff;
                selection-color: #000000;
            }
            QLineEdit, QDoubleSpinBox {
                background-color: #09090b;
                color: #ffffff;
                border: 1px solid #27272a;
                border-radius: 4px;
                padding: 5px 8px;
                font-size: 12px;
                font-family: 'Consolas', sans-serif;
                font-weight: bold;
            }
            QCheckBox, QRadioButton {
                color: #ffffff;
                font-size: 12px;
                spacing: 8px;
            }
            QCheckBox::indicator, QRadioButton::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #3f3f46;
                border-radius: 3px;
                background: #09090b;
            }
            QCheckBox::indicator:checked, QRadioButton::indicator:checked {
                background: #ffffff;
                border-color: #ffffff;
            }
            QPushButton {
                background: #000000;
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #ffffff;
                border-radius: 4px;
                padding: 8px 18px;
                font-size: 12px;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: #ffffff;
                color: #000000;
            }
            QPushButton#btnCancel {
                background-color: #000000;
                color: #71717a;
                border: 1px solid #27272a;
            }
            QPushButton#btnCancel:hover {
                background-color: #18181b;
                color: #ffffff;
            }
        """)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(12)

        # Title Label
        title_label = QLabel("[SYS] 0xVoice2Text // SYSTEM CONFIGURATION")
        title_label.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #ffffff; padding-bottom: 2px;")
        main_layout.addWidget(title_label)

        # Tab Widget
        self.tabs = QTabWidget()

        # TAB 1: VOICE & WAKE WORD
        tab_voice = QWidget()
        voice_main_layout = QVBoxLayout(tab_voice)
        voice_main_layout.setSpacing(12)

        voice_group = QGroupBox("НЕЙРОСЕТЕВОЙ VAD И АКТИВАЦИЯ ГОЛОСОМ (SILERO VAD + VOSK)")
        voice_layout = QVBoxLayout()
        voice_layout.setSpacing(10)

        self.chk_vad_enabled = QCheckBox("Использовать нейросетевой VAD (Silero VAD v5 ONNX)")
        self.chk_vad_enabled.setChecked(self.config.get("vad_enabled", True))

        vad_thresh_layout = QHBoxLayout()
        lbl_vad_thresh = QLabel("Порог чувствительности VAD:")
        self.spin_vad_threshold = QDoubleSpinBox()
        self.spin_vad_threshold.setRange(0.1, 0.95)
        self.spin_vad_threshold.setSingleStep(0.05)
        self.spin_vad_threshold.setValue(float(self.config.get("vad_threshold", 0.5)))
        vad_thresh_layout.addWidget(lbl_vad_thresh)
        vad_thresh_layout.addWidget(self.spin_vad_threshold)

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

        # VAD Pause Delay Timeout Setting (Range extended to 60 seconds!)
        pause_h_layout = QHBoxLayout()
        lbl_pause = QLabel("Задержка молчания (VAD пауза):")
        self.spin_silence_timeout = QDoubleSpinBox()
        self.spin_silence_timeout.setRange(0.5, 60.0)
        self.spin_silence_timeout.setSingleStep(0.5)
        self.spin_silence_timeout.setSuffix(" сек")
        self.spin_silence_timeout.setValue(float(self.config.get("silence_timeout", 3.0)))
        pause_h_layout.addWidget(lbl_pause)
        pause_h_layout.addWidget(self.spin_silence_timeout)

        lbl_pause_desc = QLabel("[VAD] Время в секундах (0.5 - 60.0 сек), через которое пауза в речи завершает запись.")
        lbl_pause_desc.setFont(QFont("Consolas", 8))
        lbl_pause_desc.setStyleSheet("color: #71717a;")

        self.chk_macros_enabled = QCheckBox("Голосовые макросы («Папочка вернулся», «Играем в танки», «Открой ...»)")
        self.chk_macros_enabled.setChecked(self.config.get("voice_macros_enabled", True))

        voice_layout.addWidget(self.chk_vad_enabled)
        voice_layout.addLayout(vad_thresh_layout)
        voice_layout.addWidget(self.chk_wake_enabled)
        voice_layout.addLayout(wake_h_layout)
        voice_layout.addLayout(stop_h_layout)
        voice_layout.addLayout(pause_h_layout)
        voice_layout.addWidget(lbl_pause_desc)
        voice_layout.addWidget(self.chk_macros_enabled)

        voice_group.setLayout(voice_layout)
        voice_main_layout.addWidget(voice_group)
        voice_main_layout.addStretch()

        self.tabs.addTab(tab_voice, "[VAD] ГОЛОС И ВАД")

        # TAB 2: AUDIO & STT ENGINE (🎙️ Микрофон & Groq API)
        tab_audio = QWidget()
        audio_main_layout = QVBoxLayout(tab_audio)
        audio_main_layout.setSpacing(12)

        # Microphone Group
        audio_group = QGroupBox("ИСТОЧНИК ВВОДА ЗВУКА")
        audio_layout = QVBoxLayout()
        self.combo_mic = QComboBox()
        self.devices = get_input_devices()
        
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

        # STT Engine Selection Group
        model_group = QGroupBox("ДВИЖОК РАСПОЗНАВАНИЯ РЕЧИ (STT)")
        model_layout = QVBoxLayout()
        model_layout.setSpacing(8)

        lbl_engine = QLabel("STT Провайдер / Архитектура:")
        self.combo_stt_engine = QComboBox()
        engines = [
            ("[LOCAL] Qwen3-ASR (Local SOTA 2026, GPU DirectML / AVX2)", "qwen3"),
            ("[CLOUD] Groq Cloud API (Whisper-Large-v3)", "groq")
        ]
        curr_engine = self.config.get("stt_engine", "qwen3")
        engine_idx = 0
        for i, (lbl, val) in enumerate(engines):
            self.combo_stt_engine.addItem(lbl, val)
            if val == curr_engine:
                engine_idx = i
        self.combo_stt_engine.setCurrentIndex(engine_idx)
        model_layout.addWidget(lbl_engine)
        model_layout.addWidget(self.combo_stt_engine)

        lbl_qwen_m = QLabel("Модель Qwen3-ASR:")
        self.combo_qwen_model = QComboBox()
        qwen_models = [
            ("Qwen3-ASR-1.7B ONNX (DirectML GPU / RX 7800 XT 16GB)", "andrewleech/qwen3-asr-1.7b-onnx"),
            ("Qwen3-ASR-1.7B PyTorch (CPU AVX2)", "Qwen/Qwen3-ASR-1.7B-hf"),
        ]
        curr_qwen_m = self.config.get("qwen_model", "andrewleech/qwen3-asr-1.7b-onnx")
        qwen_idx = 0
        for i, (lbl, val) in enumerate(qwen_models):
            self.combo_qwen_model.addItem(lbl, val)
            if val == curr_qwen_m:
                qwen_idx = i
        self.combo_qwen_model.setCurrentIndex(qwen_idx)
        model_layout.addWidget(lbl_qwen_m)
        model_layout.addWidget(self.combo_qwen_model)

        lbl_device = QLabel("Вычислительное устройство (Hardware Target):")
        self.combo_stt_device = QComboBox()
        devices_list = [
            ("DirectML GPU (AMD Radeon RX 7800 XT / DirectX 12)", "directml"),
            ("Auto (DirectML RX 7800 XT / CUDA / CPU AVX2)", "auto"),
            ("CPU (Intel Core i7-14700KF 20 Cores / AVX2)", "cpu"),
            ("NVIDIA CUDA (при наличии)", "cuda"),
        ]
        curr_dev = self.config.get("stt_device", "auto")
        dev_idx = 0
        for i, (lbl, val) in enumerate(devices_list):
            self.combo_stt_device.addItem(lbl, val)
            if val == curr_dev:
                dev_idx = i
        self.combo_stt_device.setCurrentIndex(dev_idx)
        model_layout.addWidget(lbl_device)
        model_layout.addWidget(self.combo_stt_device)

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

        self.tabs.addTab(tab_audio, "[STT] ЗВУК И СТТ")

        # TAB 3: HOTKEYS & OPTIONS
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

        # TTS Engine & Voice Configuration Group
        tts_group = QGroupBox("СИНТЕЗ РЕЧИ ДЖАРВИСА (TTS)")
        tts_layout = QVBoxLayout()
        tts_layout.setSpacing(8)

        self.chk_tts_voice = QCheckBox("Включить голосовые ответы ассистента")
        self.chk_tts_voice.setChecked(self.config.get("tts_voice_enabled", True))
        tts_layout.addWidget(self.chk_tts_voice)

        lbl_tts_engine = QLabel("Движок TTS:")
        self.combo_tts_engine = QComboBox()
        tts_engines = [
            ("[LOCAL] Qwen3-TTS-12Hz (Local SOTA 2026 / Zero-Shot Cloning)", "qwen3"),
            ("[CLOUD] Edge-TTS (Microsoft Cloud)", "edge")
        ]
        curr_tts_engine = self.config.get("tts_engine", "qwen3")
        tts_eng_idx = 0
        for i, (lbl, val) in enumerate(tts_engines):
            self.combo_tts_engine.addItem(lbl, val)
            if val == curr_tts_engine:
                tts_eng_idx = i
        self.combo_tts_engine.setCurrentIndex(tts_eng_idx)
        tts_layout.addWidget(lbl_tts_engine)
        tts_layout.addWidget(self.combo_tts_engine)

        lbl_qwen_tts_m = QLabel("Модель Qwen3-TTS:")
        self.combo_qwen_tts_model = QComboBox()
        qwen_tts_models = [
            ("Qwen3-TTS-12Hz-0.6B-Base (Сверхбыстрая / Минимальная задержка)", "Qwen/Qwen3-TTS-12Hz-0.6B-Base"),
            ("Qwen3-TTS-12Hz-1.7B-CustomVoice (Zero-Shot клонирование тембра)", "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice")
        ]
        curr_qwen_tts_m = self.config.get("qwen_tts_model", "Qwen/Qwen3-TTS-12Hz-0.6B-Base")
        qwen_tts_idx = 0
        for i, (lbl, val) in enumerate(qwen_tts_models):
            self.combo_qwen_tts_model.addItem(lbl, val)
            if val == curr_qwen_tts_m:
                qwen_tts_idx = i
        self.combo_qwen_tts_model.setCurrentIndex(qwen_tts_idx)
        tts_layout.addWidget(lbl_qwen_tts_m)
        tts_layout.addWidget(self.combo_qwen_tts_model)

        tts_h_layout = QHBoxLayout()
        lbl_tts_voice = QLabel("Облачный голос (Edge):")
        self.combo_tts_voice = QComboBox()
        self.combo_tts_voice.addItem("Светлана (Женский)", "ru-RU-SvetlanaNeural")
        self.combo_tts_voice.addItem("Дмитрий (Мужской)", "ru-RU-DmitryNeural")
        curr_tts_v = self.config.get("tts_voice", "ru-RU-SvetlanaNeural")
        self.combo_tts_voice.setCurrentIndex(1 if "Dmitry" in str(curr_tts_v) else 0)

        lbl_tts_rate = QLabel("Скорость:")
        self.combo_tts_rate = QComboBox()
        self.combo_tts_rate.addItem("Нормальная (0%)", "+0%")
        self.combo_tts_rate.addItem("Быстрая (+20%)", "+20%")
        self.combo_tts_rate.addItem("Очень быстрая (+35%)", "+35%")
        curr_tts_r = self.config.get("tts_rate", "+20%")
        r_idx = 1 if curr_tts_r == "+20%" else (2 if curr_tts_r == "+35%" else 0)
        self.combo_tts_rate.setCurrentIndex(r_idx)

        tts_h_layout.addWidget(lbl_tts_voice)
        tts_h_layout.addWidget(self.combo_tts_voice)
        tts_h_layout.addWidget(lbl_tts_rate)
        tts_h_layout.addWidget(self.combo_tts_rate)
        tts_layout.addLayout(tts_h_layout)

        tts_group.setLayout(tts_layout)
        opts_main_layout.addWidget(tts_group)

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

        self.tabs.addTab(tab_options, "[CFG] КЛАВИШИ И ПОВЕДЕНИЕ")

        # TAB 4: AI POST-PROCESSING
        tab_ai = QWidget()
        ai_main_layout = QVBoxLayout(tab_ai)
        ai_main_layout.setSpacing(10)

        ai_mode_group = QGroupBox("РЕЖИМ ОБРАБОТКИ ИИ")
        ai_mode_layout = QVBoxLayout()
        ai_mode_layout.setSpacing(8)

        self.combo_ai_mode = QComboBox()
        self.combo_ai_mode.addItem("[DIRECT] Прямой ввод STT без ИИ", "direct")
        self.combo_ai_mode.addItem("[CLEAN] Чистка устной речи (Gemma 4 / Flash Lite)", "clean")
        self.combo_ai_mode.addItem("[SMART] Умная команда / Рерайт (Gemini Flash)", "smart")
        
        curr_ai_mode = self.config.get("ai_mode", "direct")
        mode_idx = 0 if curr_ai_mode == "direct" else (1 if curr_ai_mode == "clean" else 2)
        self.combo_ai_mode.setCurrentIndex(mode_idx)
        ai_mode_layout.addWidget(self.combo_ai_mode)
        ai_mode_group.setLayout(ai_mode_layout)
        ai_main_layout.addWidget(ai_mode_group)

        # API Key Group
        api_group = QGroupBox("GOOGLE GEMINI API KEY")
        api_layout = QVBoxLayout()
        self.txt_gemini_key = QLineEdit()
        self.txt_gemini_key.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.txt_gemini_key.setText(self.config.get("gemini_api_key", ""))
        self.txt_gemini_key.setPlaceholderText("Ключ из Google AI Studio (или добавьте GEMINI_API_KEY в .env)")
        lbl_api_hint = QLabel("[INFO] Ключ также автоматически подхватывается из файла .env (GEMINI_API_KEY)")
        lbl_api_hint.setFont(QFont("Consolas", 8))
        lbl_api_hint.setStyleSheet("color: #71717a;")
        api_layout.addWidget(self.txt_gemini_key)
        api_layout.addWidget(lbl_api_hint)
        api_group.setLayout(api_layout)
        ai_main_layout.addWidget(api_group)

        # Models Group
        models_group = QGroupBox("ВЫБОР МОДЕЛЕЙ ИИ")
        models_layout = QVBoxLayout()
        models_layout.setSpacing(8)

        clean_m_layout = QHBoxLayout()
        lbl_clean_m = QLabel("Clean модель (Gemma/Lite):")
        self.combo_clean_model = QComboBox()
        self.combo_clean_model.addItem("Gemma 4 31B (14.4k RPD / 30 RPM)", "gemma-4-31b-it")
        self.combo_clean_model.addItem("Gemma 4 26B (14.4k RPD / 30 RPM)", "gemma-4-26b-a4b-it")
        self.combo_clean_model.addItem("Gemini 3.5 Flash Lite (500 RPD / 15 RPM)", "gemini-3.5-flash-lite")
        self.combo_clean_model.addItem("Gemini 3.1 Flash Lite (500 RPD / 15 RPM)", "gemini-3.1-flash-lite")
        
        curr_gemma = self.config.get("gemma_model", "gemma-4-31b-it")
        gemma_idx = 0
        for i in range(self.combo_clean_model.count()):
            if self.combo_clean_model.itemData(i) == curr_gemma:
                gemma_idx = i
                break
        self.combo_clean_model.setCurrentIndex(gemma_idx)
        clean_m_layout.addWidget(lbl_clean_m)
        clean_m_layout.addWidget(self.combo_clean_model)

        smart_m_layout = QHBoxLayout()
        lbl_smart_m = QLabel("Smart модель (Gemini Flash):")
        self.combo_smart_model = QComboBox()
        self.combo_smart_model.addItem("Gemini 3.6 Flash (20 RPD / 5 RPM)", "gemini-3.6-flash")
        self.combo_smart_model.addItem("Gemini 3.5 Flash (20 RPD / 5 RPM)", "gemini-3.5-flash")
        self.combo_smart_model.addItem("Gemini 3.5 Flash Lite (500 RPD / 15 RPM)", "gemini-3.5-flash-lite")
        self.combo_smart_model.addItem("Gemma 4 31B (14.4k RPD / 30 RPM)", "gemma-4-31b-it")

        curr_gemini = self.config.get("gemini_model", "gemini-3.6-flash")
        gemini_idx = 0
        for i in range(self.combo_smart_model.count()):
            if self.combo_smart_model.itemData(i) == curr_gemini:
                gemini_idx = i
                break
        self.combo_smart_model.setCurrentIndex(gemini_idx)
        smart_m_layout.addWidget(lbl_smart_m)
        smart_m_layout.addWidget(self.combo_smart_model)

        models_layout.addLayout(clean_m_layout)
        models_layout.addLayout(smart_m_layout)
        models_group.setLayout(models_layout)
        ai_main_layout.addWidget(models_group)
        ai_main_layout.addStretch()

        self.tabs.addTab(tab_ai, "[AI] ИИ (GEMINI / GEMMA)")

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
        try:
            # Collect all settings into a single dict for batch-write (1 disk I/O)
            updates = {
                "audio_device": self.combo_mic.currentData(),
                "stt_engine": self.combo_stt_engine.currentData(),
                "qwen_model": self.combo_qwen_model.currentData(),
                "stt_device": self.combo_stt_device.currentData(),
                "language": self.combo_lang.currentData(),
                "hotkey": self.combo_hk.currentData(),
                "hotkey_mode": "toggle" if self.radio_toggle.isChecked() else "push_to_talk",
                "vad_enabled": self.chk_vad_enabled.isChecked(),
                "vad_threshold": float(self.spin_vad_threshold.value()),
                "wake_word_enabled": self.chk_wake_enabled.isChecked(),
                "wake_words": self.txt_wake_words.text(),
                "stop_words": self.txt_stop_words.text(),
                "silence_timeout": float(self.spin_silence_timeout.value()),
                "voice_macros_enabled": self.chk_macros_enabled.isChecked(),
                "auto_paste": self.chk_auto_paste.isChecked(),
                "add_trailing_space": self.chk_trailing_space.isChecked(),
                "sound_feedback": self.chk_sound.isChecked(),
                "tts_voice_enabled": self.chk_tts_voice.isChecked(),
                "tts_engine": self.combo_tts_engine.currentData(),
                "qwen_tts_model": self.combo_qwen_tts_model.currentData(),
                "tts_voice": self.combo_tts_voice.currentData(),
                "tts_rate": self.combo_tts_rate.currentData(),
                "always_on_top": self.chk_ontop.isChecked(),
                "ai_mode": self.combo_ai_mode.currentData(),
                "gemini_api_key": self.txt_gemini_key.text().strip(),
                "gemma_model": self.combo_clean_model.currentData(),
                "gemini_model": self.combo_smart_model.currentData(),
            }

            # Single atomic write to disk
            ok, err_msg = self.config.set_many(updates)
            if not ok:
                logger.error(f"[Settings] Config save failed: {err_msg}")
                QMessageBox.critical(
                    self,
                    "[FAIL] Config Save Error",
                    f"[SYS] Failed to save configuration to disk.\n\nError: {err_msg}\n\n"
                    "Check write permissions for data/config.json and available disk space.",
                    QMessageBox.StandardButton.Ok
                )
                return

            logger.info("[Settings] Configuration saved successfully.")

        except Exception as e:
            logger.error(f"[Settings] Unexpected error collecting settings: {e}")
            QMessageBox.critical(
                self,
                "[CRIT] Settings Error",
                f"[SYS] Unexpected error while saving settings.\n\nDetails: {e}",
                QMessageBox.StandardButton.Ok
            )
            return

        # Invoke the post-save callback in a separate try/except
        # so config persistence is never lost due to callback failures
        if self.on_save_callback:
            try:
                self.on_save_callback()
            except Exception as e:
                logger.error(f"[Settings] Error applying config changes: {e}")
                QMessageBox.warning(
                    self,
                    "[WARN] Apply Error",
                    f"[SYS] Configuration was saved, but applying changes failed.\n\n"
                    f"Details: {e}\n\nRestart the application to apply changes manually.",
                    QMessageBox.StandardButton.Ok
                )

        self.accept()
