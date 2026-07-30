from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOGIN_PAGE = ROOT / "openharmony/entry/src/main/ets/pages/LoginPage.ets"
API_CLIENT = ROOT / "openharmony/entry/src/main/ets/common/ApiClient.ets"
SECURE_STORAGE = ROOT / "openharmony/entry/src/main/ets/common/SecureStorage.ets"
SERVER_CONFIG = ROOT / "openharmony/entry/src/main/ets/common/ServerConfig.ets"
MQTT_CLIENT = ROOT / "openharmony/entry/src/main/ets/common/MqttClient.ets"
FORM_ABILITY = ROOT / "openharmony/entry/src/main/ets/entryformability/EntryFormAbility.ets"
NETWORK_SECURITY = ROOT / "openharmony/entry/src/main/resources/rawfile/network_security_config.xml"


def test_server_connection_settings_live_in_a_dedicated_config_file():
    login_source = LOGIN_PAGE.read_text(encoding="utf-8")
    api_source = API_CLIENT.read_text(encoding="utf-8")
    storage_source = SECURE_STORAGE.read_text(encoding="utf-8")
    form_source = FORM_ABILITY.read_text(encoding="utf-8")
    mqtt_source = MQTT_CLIENT.read_text(encoding="utf-8")
    security_source = NETWORK_SECURITY.read_text(encoding="utf-8")

    assert SERVER_CONFIG.exists()
    config_source = SERVER_CONFIG.read_text(encoding="utf-8")
    assert "export const SERVER_PROTOCOL: string = 'http'" in config_source
    assert "export const SERVER_HOST: string = 'localhost'" in config_source
    assert "export const SERVER_PORT: number = 8000" in config_source
    assert "export const SERVER_BASE_URL" in config_source
    assert "8.162.10.179" not in config_source
    assert "8.162.10.179" not in login_source
    assert "8.162.10.179" not in api_source
    assert "8.162.10.179" not in storage_source
    assert "8.162.10.179" not in form_source
    assert "8.162.10.179" not in mqtt_source
    assert "8.162.10.179" not in security_source
    assert "SERVER_WEBSOCKET_URL" in mqtt_source


def test_login_page_does_not_expose_server_configuration():
    login_source = LOGIN_PAGE.read_text(encoding="utf-8")

    assert "setBaseUrl" not in login_source
    assert "showCfg" not in login_source
    assert "DEFAULT_SERVER_URL" not in login_source
    assert "getBaseUrl" not in login_source


def test_storage_and_api_client_wait_for_preferences_initialization():
    api_source = API_CLIENT.read_text(encoding="utf-8")
    storage_source = SECURE_STORAGE.read_text(encoding="utf-8")
    form_source = FORM_ABILITY.read_text(encoding="utf-8")

    assert "let prefsInitPromise: Promise<void> | null = null" in storage_source
    assert "async function ensurePreferencesReady(): Promise<void>" in storage_source
    assert "await ensurePreferencesReady()" in storage_source
    assert "await initPreferences(this.context)" in form_source
    assert "await loadServerUrl()" not in form_source
    assert "import { SERVER_BASE_URL" in api_source
    assert "loadServerUrl" not in api_source
    assert "saveServerUrl" not in api_source


def test_server_url_is_not_a_runtime_override():
    api_source = API_CLIENT.read_text(encoding="utf-8")
    storage_source = SECURE_STORAGE.read_text(encoding="utf-8")
    form_source = FORM_ABILITY.read_text(encoding="utf-8")

    assert "setBaseUrl" not in api_source
    assert "KEY_SERVER_URL" not in storage_source
    assert "saveServerUrl" not in storage_source
    assert "loadServerUrl" not in storage_source
    assert "SERVER_BASE_URL" in form_source
