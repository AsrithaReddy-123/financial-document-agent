FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY app ./app
COPY evaluation ./evaluation
COPY tests ./tests
RUN pip install --no-cache-dir .
ENV CORPUS_SIZE=500
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
