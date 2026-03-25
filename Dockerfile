# משתמשים בתמונה קלה של פייתון (מבוססת אלפיין או סלים)
FROM python:3.12-slim

# הגדרת תיקיית העבודה בתוך הקונטיינר
WORKDIR /app

# התקנת כלים בסיסיים אם נצטרך (אופציונלי)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# העתקת קובץ הדרישות והתקנה
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# העתקת שאר קבצי הפרויקט (כולל תיקיית static)
COPY . .

# חשיפת הפורט שה-FastAPI רץ עליו
EXPOSE 8000

# פקודת ההרצה של השרת
CMD ["python", "main.py"]