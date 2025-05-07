import psycopg2
import openai
import pandas as pd
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

DB_CONFIG = {
    "host": "localhost",
    "database": "postgres",
    "user": "postgres",
    "password": "PMO@1234"
}

def get_unique_universities():
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT university FROM pdf_extracted_data WHERE university IS NOT NULL")
            return [row[0] for row in cur.fetchall() if row[0]]

def add_university2_column():
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'pdf_extracted_data' AND column_name = 'university2'
            """)
            if not cur.fetchone():
                cur.execute("ALTER TABLE pdf_extracted_data ADD COLUMN university2 TEXT")
                print("Added university2 column.")
            else:
                print("university2 column already exists.")
            conn.commit()

def get_unified_university_mapping(universities):
    # Chunk the list to avoid token limits
    chunk_size = 40
    mapping = {}
    for i in range(0, len(universities), chunk_size):
        chunk = universities[i:i+chunk_size]
        prompt = (
            "You are a data cleaning assistant. Given this list of university names, group and unify similar ones. "
            "Return a JSON object where each original name is mapped to a unified, canonical university name. "
            "Example: {'Cairo University': 'Cairo University', 'Cairo Univ.': 'Cairo University', 'جامعة القاهرة': 'Cairo University'}\n"
            f"List: {chunk}"
        )
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=800
        )
        import json
        try:
            chunk_mapping = json.loads(response.choices[0].message.content)
            mapping.update(chunk_mapping)
        except Exception as e:
            print(f"Error parsing GPT response: {e}\nResponse: {response.choices[0].message.content}")
    return mapping

def update_university2(mapping):
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            for orig, unified in mapping.items():
                cur.execute("""
                    UPDATE pdf_extracted_data SET university2 = %s WHERE university = %s
                """, (unified, orig))
            conn.commit()
    print("university2 column updated.")

def main():
    universities = get_unique_universities()
    print(f"Found {len(universities)} unique university values.")
    add_university2_column()
    mapping = get_unified_university_mapping(universities)
    # Optionally, save mapping to Excel for review
    pd.DataFrame(list(mapping.items()), columns=['original', 'unified']).to_excel('university_mapping.xlsx', index=False)
    update_university2(mapping)
    print("Done.")

if __name__ == "__main__":
    main() 
 