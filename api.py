from flask import Flask, jsonify, request, send_file, abort
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
import json

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
    """Search CVs by keywords in OCR text and other fields, with pagination"""
    try:
        # Get search parameters
        keywords = request.args.get('keywords', '').strip()
        department = request.args.get('department', '').strip()
        job_title = request.args.get('job_title', '').strip()
        search_type = request.args.get('search_type', 'AND').strip().upper()  # AND or OR
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))

        conditions = []
        params = []

        # Add keyword search if provided
        if keywords:
            keyword_list = [keyword.strip() for keyword in keywords.split(',')]
            keyword_conditions = []
            for keyword in keyword_list:
                keyword_conditions.append("LOWER(ocr_result) LIKE LOWER(%s)")
                params.append(f"%{keyword}%")
            operator = " AND " if search_type == "AND" else " OR "
            conditions.append(f"({operator.join(keyword_conditions)})")

        # Add department filter if provided
        if department:
            conditions.append("LOWER(department) = LOWER(%s)")
            params.append(department)

        # Add job title filter if provided
        if job_title:
            conditions.append("LOWER(job_title) = LOWER(%s)")
            params.append(job_title)

        # Combine all conditions with AND
        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Connect to database and execute search
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get total count
                count_query = f"SELECT COUNT(*) FROM pdf_extracted_data WHERE {where_clause}"
                cur.execute(count_query, params)
                total_count = cur.fetchone()['count']

                # Get paginated results
                offset = (page - 1) * per_page
                query = f"""
                    SELECT id, pdf_filename, name, email, department, job_title, 
                           years_of_experience, current_company, location
                    FROM pdf_extracted_data
                    WHERE {where_clause}
                    ORDER BY id DESC
                    LIMIT %s OFFSET %s
                """
                cur.execute(query, params + [per_page, offset])
                results = cur.fetchall()

        cvs = [dict(row) for row in results]
        return jsonify({
            "count": total_count,
            "results": cvs,
            "page": page,
            "per_page": per_page
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/search/skills', methods=['GET'])
def search_skills():
    """Search CVs by keywords in skills field only"""
    try:
        keywords = request.args.get('keywords', '').strip()
        search_type = request.args.get('search_type', 'AND').strip().upper()  # AND or OR
        department = request.args.get('department', '').strip()
        job_title = request.args.get('job_title', '').strip()
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        offset = (page - 1) * per_page

        conditions = []
        params = []

        # Add skills keyword search if provided
        if keywords:
            keyword_list = [keyword.strip() for keyword in keywords.split(',')]
            keyword_conditions = []
            for keyword in keyword_list:
                keyword_conditions.append("LOWER(skills) LIKE LOWER(%s)")
                params.append(f"%{keyword}%")
            
            # Combine keywords with AND or OR
            operator = " AND " if search_type == "AND" else " OR "
            conditions.append(f"({operator.join(keyword_conditions)})")

        # Add department filter if provided
        if department:
            conditions.append("LOWER(department) = LOWER(%s)")
            params.append(department)

        # Add job title filter if provided
        if job_title:
            conditions.append("LOWER(job_title) = LOWER(%s)")
            params.append(job_title)

        # Combine all conditions with AND
        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get total count
                count_query = f"SELECT COUNT(*) FROM pdf_extracted_data WHERE {where_clause}"
                cur.execute(count_query, params)
                total_count = cur.fetchone()['count']

                # Get paginated results
                query = f"""
                    SELECT id, pdf_filename, name, email, department, job_title, 
                           years_of_experience, current_company, location, skills
                    FROM pdf_extracted_data
                    WHERE {where_clause}
                    ORDER BY id DESC
                    LIMIT %s OFFSET %s
                """
                cur.execute(query, params + [per_page, offset])
                results = cur.fetchall()

        cvs = [dict(row) for row in results]
        return jsonify({
            "count": total_count,
            "results": cvs,
            "page": page,
            "per_page": per_page
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/search/advanced', methods=['GET'])
def advanced_search():
    """Advanced search with multiple field-specific filters, supporting all columns including new CRM columns."""
    try:
        # Get all possible search parameters
        params = {}
        conditions = []
        query_params = []
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        offset = (page - 1) * per_page

        # List all columns to support as filters and in results
        all_columns = [
            'id', 'pdf_filename', 'name', 'email', 'department', 'job_title',
            'years_of_experience', 'current_company', 'location', 'skills',
            'languages', 'certifications', 'project_types', 'university',
            'graduation_year',
            'status_1', 'status_2', 'status_3',
            'modified_by_1', 'modified_by_2', 'modified_by_3',
            'last_attempt', 'confidence',
            'linkedin',
            'current_job', 'ocr_result',
            # CRM columns
            'crm_applicationid', 'crm_fullname', 'crm_contactphone', 'crm_telephonenumber',
            'crm_gender', 'crm_position', 'crm_employmenttype', 'crm_expectedsalary',
            'crm_dateavailableforemployment', 'crm_currentsalary', 'crm_company',
            'crm_graduationyear', 'crm_qualitiesattributes', 'crm_careergoals',
            'crm_additionalinformation', 'crm_appstatus', 'crm_hrinterviewstatus',
            'crm_technicalrating', 'crm_technicalinterviewcomments', 'crm_hrcomment',
            'crm_createdon', 'crm_modifiedon', 'crm_howdidyouhearaboutrowad',
            'crm_extrasocialactivities', 'crm_pleasesepcify'
        ]

        # Add filter for each column if present in query string
        for col in all_columns:
            value = request.args.get(col, '').strip()
            if value:
                # Numeric columns (id, years_of_experience, graduation_year, confidence, crm_expectedsalary)
                if col in ['id', 'years_of_experience', 'graduation_year', 'confidence', 'crm_expectedsalary']:
                    conditions.append(f"{col} = %s")
                    query_params.append(value)
                elif col == 'ocr_result':
                    # Support multiple keywords and AND/OR logic
                    search_type = request.args.get('ocr_result_search_type', 'AND').strip().upper()
                    keywords = [v.strip() for v in value.split(',') if v.strip()]
                    if keywords:
                        like_conditions = []
                        for kw in keywords:
                            like_conditions.append("LOWER(ocr_result) LIKE LOWER(%s)")
                            query_params.append(f"%{kw}%")
                        operator = ' AND ' if search_type == 'AND' else ' OR '
                        conditions.append(f"({operator.join(like_conditions)})")
                else:
                    conditions.append(f"LOWER(CAST({col} AS TEXT)) = LOWER(%s)")
                    query_params.append(value)

        # Combine all conditions with AND
        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get total count
                count_query = f"SELECT COUNT(*) FROM pdf_extracted_data WHERE {where_clause}"
                cur.execute(count_query, query_params)
                total_count = cur.fetchone()['count']

                # Get paginated results
                query = f"""
                    SELECT {', '.join(all_columns)}
                    FROM pdf_extracted_data
                    WHERE {where_clause}
                    ORDER BY id DESC
                    LIMIT %s OFFSET %s
                """
                print(f"Executing query: {query} with params: {query_params + [per_page, offset]}")
                cur.execute(query, query_params + [per_page, offset])
                results = cur.fetchall()
                print(f"Query returned {len(results)} results. Sample result: {results[0] if results else 'No results'}")

        cvs = [dict(row) for row in results]
        return jsonify({
            "count": total_count,
            "results": cvs,
            "page": page,
            "per_page": per_page
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

@app.route('/api/departments', methods=['GET'])
def get_departments():
    """Get list of all departments"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT department 
                    FROM pdf_extracted_data 
                    WHERE department IS NOT NULL 
                    ORDER BY department
                """)
                results = cur.fetchall()
                departments = [row['department'] for row in results]
                return jsonify(departments)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/job-titles', methods=['GET'])
def get_job_titles():
    """Get list of all job titles"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT job_title 
                    FROM pdf_extracted_data 
                    WHERE job_title IS NOT NULL 
                    ORDER BY job_title
                """)
                results = cur.fetchall()
                job_titles = [row['job_title'] for row in results]
                return jsonify(job_titles)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/cv/details/<int:cv_id>', methods=['GET'])
def get_cv_details(cv_id):
    """Get detailed information about a specific CV"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, pdf_filename, name, email, department, job_title,
                           years_of_experience, current_company, location, languages,
                           certifications, project_types, skills, graduation_year,
                           university, linkedin
                    FROM pdf_extracted_data
                    WHERE id = %s
                """, (cv_id,))
                result = cur.fetchone()

                if not result:
                    return jsonify({"error": "CV not found"}), 404

                return jsonify(dict(result))

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/cv/update_status/<int:cv_id>', methods=['POST'])
def update_cv_status(cv_id):
    """
    Update status and modified_by columns for a CV.
    Expects JSON like:
    {
        "status_1": "...", "status_2": "...", "status_3": "...",
        "modified_by_1": "...", "modified_by_2": "...", "modified_by_3": "..."
    }
    """
    data = request.json
    fields = ['status_1', 'status_2', 'status_3', 'modified_by_1', 'modified_by_2', 'modified_by_3']
    updates = []
    values = []
    for field in fields:
        if field in data:
            updates.append(f"{field} = %s")
            values.append(data[field])
    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400
    values.append(cv_id)
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE pdf_extracted_data SET {', '.join(updates)} WHERE id = %s",
                    values
                )
                conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/cv/update_audit_log/<int:cv_id>', methods=['POST'])
def update_audit_log(cv_id):
    """
    Update the audit_log column for a CV.
    Expects JSON like:
    {
        "audit_log": ...   # array, object, or value
    }
    """
    data = request.json
    if 'audit_log' not in data:
        return jsonify({"error": "Missing 'audit_log' in request body"}), 400
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE pdf_extracted_data SET audit_log = %s WHERE id = %s",
                    [json.dumps(data['audit_log']), cv_id]
                )
                conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/cv/audit_log/<int:cv_id>', methods=['GET'])
def get_audit_log(cv_id):
    """
    Retrieve the audit_log column for a specific CV.
    Returns the audit_log as JSON, or an error if not found.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT audit_log FROM pdf_extracted_data WHERE id = %s",
                    (cv_id,)
                )
                result = cur.fetchone()
                if not result or result['audit_log'] is None:
                    return jsonify({"error": "No audit_log found for this CV"}), 404
                return jsonify({"audit_log": result['audit_log']})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 