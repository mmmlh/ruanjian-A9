FROM python:3.11-slim

WORKDIR /app

ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ARG PIP_TRUSTED_HOST=mirrors.aliyun.com
ARG PIP_DEFAULT_TIMEOUT=120

COPY requirements.txt .
RUN pip install --no-cache-dir \
    --index-url ${PIP_INDEX_URL} \
    --trusted-host ${PIP_TRUSTED_HOST} \
    --default-timeout ${PIP_DEFAULT_TIMEOUT} \
    -r requirements.txt

COPY . .

CMD ["python", "simulator_manager.py"]
