from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOGIN_PAGE = ROOT / "openharmony/entry/src/main/ets/pages/LoginPage.ets"
API_CLIENT = ROOT / "openharmony/entry/src/main/ets/common/ApiClient.ets"
SECURE_STORAGE = ROOT / "openharmony/entry/src/main/ets/common/SecureStorage.ets"
FORM_ABILITY = ROOT / "openharmony/entry/src/main/ets/entryformability/EntryFormAbility.ets"


def test_default_server_url_has_single_source_of_truth():
    login_source = LOGIN_PAGE.read_text(encoding="utf-8")
    api_source = API_CLIENT.read_text(encoding="utf-8")
    storage_source = SECURE_STORAGE.read_text(encoding="utf-8")
    form_source = FORM_ABILITY.read_text(encoding="utf-8")

    assert "8.162.10.179" not in login_source
    assert "8.162.10.179" not in api_source
    assert "8.162.10.179" not in form_source
    assert storage_source.count("8.162.10.179") == 1


def test_storage_and_api_client_wait_for_preferences_initialization():
    api_source = API_CLIENT.read_text(encoding="utf-8")
    storage_source = SECURE_STORAGE.read_text(encoding="utf-8")
    form_source = FORM_ABILITY.read_text(encoding="utf-8")

    assert "let prefsInitPromise: Promise<void> | null = null" in storage_source
    assert "async function ensurePreferencesReady(): Promise<void>" in storage_source
    assert "await ensurePreferencesReady()" in storage_source
    assert "await initPreferences(this.context)" in form_source
    assert "await loadServerUrl()" in form_source
    assert "import { DEFAULT_SERVER_URL" in api_source
