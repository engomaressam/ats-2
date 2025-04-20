from flask import Flask, jsonify, request, send_file, abort
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)  # Enable CORS for all domains

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "database": "postgres",
    "user": "postgres",
    "password": "PMO@1234"
}

# Directory containing PDFs
CVS_DIRECTORY = r"C:\cvs"

def get_db_connection():
    """Create a database connection"""
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)

@app.route('/api/search', methods=['GET'])
def search_cvs():
    """Search CVs by keywords in OCR text and other fields"""
    try:
        # Get search parameters
        keywords = request.args.get('keywords', '').strip()
        if not keywords:
            return jsonify({"error": "No search keywords provided"}), 400

        # Create keyword conditions for SQL
        keyword_list = [keyword.strip() for keyword in keywords.split(',')]
        keyword_conditions = " OR ".join([
            "LOWER(ocr_result) LIKE LOWER(%s)"
            for _ in keyword_list
        ])

        # Create parameter list for SQL query
        params = [f"%{keyword}%" for keyword in keyword_list]

        # Connect to database and execute search
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                query = f"""
                    SELECT id, pdf_filename, name, email
                    FROM pdf_extracted_data
                    WHERE {keyword_conditions}
                """
                cur.execute(query, params)
                results = cur.fetchall()

        # Convert results to list of dictionaries
        cvs = [dict(row) for row in results]
        return jsonify({
            "count": len(cvs),
            "results": cvs
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/cv/<filename>', methods=['GET'])
def get_cv_file(filename):
    """Serve CV PDF file"""
    try:
        # Sanitize filename to prevent directory traversal
        filename = os.path.basename(filename)
        file_path = os.path.join(CVS_DIRECTORY, filename)
        
        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404
            
        return send_file(
            file_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/cv/details/<int:cv_id>', methods=['GET'])
def get_cv_details(cv_id):
    """Get detailed information about a specific CV"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, pdf_filename, name, email
                    FROM pdf_extracted_data
                    WHERE id = %s
                """, (cv_id,))
                result = cur.fetchone()

                if not result:
                    return jsonify({"error": "CV not found"}), 404

                return jsonify(dict(result))

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 