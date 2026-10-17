FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN pip install --no-cache-dir boto3==1.43.114
COPY server.py index.html app.js style.css /app/
USER 10001:10001
EXPOSE 8080
CMD ["python", "server.py"]
