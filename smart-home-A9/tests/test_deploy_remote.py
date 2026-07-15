import deploy_remote


def test_build_remote_compose_uses_plain_mqtt_for_internal_backend_link():
    compose = deploy_remote.build_remote_compose("8.162.10.179")

    assert "- MQTT_BROKER=mqtt" in compose
    assert "- MQTT_PORT=1883" in compose
    assert "- MQTT_USE_TLS=false" in compose
    assert "- MQTT_TLS_PORT=8883" in compose
    assert "- MQTT_CA_CERTS=/certs/server.crt" in compose


def test_build_remote_compose_sets_public_base_url_to_server_https():
    compose = deploy_remote.build_remote_compose("8.162.10.179")

    assert "- PUBLIC_BASE_URL=https://8.162.10.179" in compose


def test_build_remote_compose_builds_backend_image_instead_of_installing_on_every_boot():
    compose = deploy_remote.build_remote_compose("8.162.10.179")

    assert "context: ./backend" in compose
    assert "image: python:3.11-slim" not in compose
    assert "pip install -r requirements.txt" not in compose


def test_build_remote_compose_builds_simulators_image_instead_of_runtime_pip_install():
    compose = deploy_remote.build_remote_compose("8.162.10.179")

    assert "context: ./simulators" in compose
    assert 'command: bash -c "pip install paho-mqtt==1.6.1 && python simulator_manager.py"' not in compose


def test_build_remote_compose_passes_pip_mirror_build_args():
    compose = deploy_remote.build_remote_compose("8.162.10.179")

    assert "PIP_INDEX_URL: https://mirrors.aliyun.com/pypi/simple/" in compose
    assert "PIP_TRUSTED_HOST: mirrors.aliyun.com" in compose
    assert "PIP_DEFAULT_TIMEOUT: 120" in compose
