FROM python:3.10

WORKDIR /app

COPY . /app

RUN pip install --upgrade pip && pip install -r requirements.txt

# Create few-shot examples directory
RUN mkdir -p /app/few_shot_examples

EXPOSE 8000

# Mount few_shot_examples as a volume to persist curator examples
VOLUME ["/app/few_shot_examples"]

CMD ["uvicorn", "query:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
