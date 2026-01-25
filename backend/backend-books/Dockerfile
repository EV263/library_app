FROM python:3.12-slim

WORKDIR /app

RUN pip install fastapi uvicorn sqlalchemy mysql-connector-python python-dotenv
COPY . .

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]