FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY apps ./apps
COPY quant ./quant
COPY brokers ./brokers
COPY data ./data
COPY strategies ./strategies
COPY scanner ./scanner
COPY backtest ./backtest
COPY paper ./paper
COPY execution ./execution
COPY compliance ./compliance
COPY monitoring ./monitoring
RUN pip install --no-cache-dir uv && uv pip install --system -e '.[dev]'
EXPOSE 8000

