ARG PYTHON_BASE=docker.1ms.run/library/python:3.12-slim
FROM ${PYTHON_BASE}

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /sandbox

RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple backtrader==1.9.78.123 pandas==2.2.3

COPY run_strategy.py /sandbox/run_strategy.py

ENTRYPOINT ["python", "/sandbox/run_strategy.py"]
