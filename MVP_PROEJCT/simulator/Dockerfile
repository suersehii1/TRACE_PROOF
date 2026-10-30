FROM python:3.12-slim
WORKDIR /simulator
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY device.py .
RUN useradd --create-home simulator
USER simulator
EXPOSE 8001
CMD ["python", "device.py"]
