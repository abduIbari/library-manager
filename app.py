from flask import Flask, render_template, jsonify, request
import configparser
import requests
import logging
from flask_cors import CORS
from sqlalchemy import select
from db.db_connection import init_db, db
from db.models import Author, Publisher, Genre, Book, Customer, customer_book
from neo4j import GraphDatabase


app = Flask(__name__, static_url_path='/static', static_folder='static')

init_db(app)

CORS(app)

# Configure logging to DEBUG level for detailed logs
logging.basicConfig(
    level=logging.DEBUG,  # Changed from INFO to DEBUG
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Load the configuration from the config.ini file
config = configparser.ConfigParser()
config.read('config.ini')

# Get the API key and URL from the configuration
try:
    GEMINI_API_KEY = config.get('API', 'GEMINI_API_KEY')
    GEMINI_API_URL = config.get('API', 'GEMINI_API_URL')
    logging.info("Gemini API configuration loaded successfully.")
except Exception as e:
    logging.error("Error reading config.ini: %s", e)
    GEMINI_API_KEY = None
    GEMINI_API_URL = None

# Route to serve the home page
@app.route('/')
def home():
    return render_template('index.html')

# Route to serve viewer.html
@app.route('/viewer.html')
def viewer():
    return render_template('viewer.html')

@app.route("/api/display_books", methods=["GET"])
def get_all_books():
    books = Book.query.all()
    return jsonify([book.to_dict() for book in books])

@app.route("/api/display_entity", methods=["POST"])
def get_entity():
    entity_data = request.json
    entity_id = entity_data.get("id")
    entity_type = entity_data.get("entity")

    if entity_type == "Author":
        author = Author.query.get(entity_id)
        author_name = author.author_name if author else "Author not found"
        return jsonify({"Author": author_name})

    elif entity_type == "Publisher":
        publisher = Publisher.query.get(entity_id)
        publisher_name = publisher.publisher_name if publisher else "Publisher not found"
        return jsonify({"Publisher":publisher_name})

    elif entity_type == "Genre":
        genre = Genre.query.get(entity_id)
        genre_name = genre.genre if genre else "Genre not found"
        return jsonify({"Genre": genre_name})
    
    elif entity_type == "Book":
        book = Book.query.get(entity_id)
        return jsonify({"Title":book.title,
                        "Author":book.author.author_name,
                        "Publisher":book.publisher.publisher_name,
                        "Genre":book.genre.genre,
                        "State":book.state})
    
    else:
        return jsonify({"error": "Invalid entity type"}), 400

@app.route('/api/borrow_book', methods=['POST'])
def borrow_book():
    book_id = request.json.get("bookId")
    book = Book.query.get(book_id)
    borrower_name = request.json.get("borrowerName")
    borrow_date = request.json.get("borrowDate")

    customer = Customer.query.filter_by(customer_name=borrower_name).first()
    if not customer:
        customer = Customer(customer_name=borrower_name)
        db.session.add(customer)
        db.session.commit()

    insert_stmt = customer_book.insert().values(
        customer_id=customer.id,
        book_id=book_id,
        date_borrowed=borrow_date
    )
    db.session.execute(insert_stmt)

    book.state = False
    db.session.commit()

    return jsonify({"message": f"Book ID {book_id} borrowed by {borrower_name} on {borrow_date}."})


@app.route('/api/return_book', methods=['POST'])
def return_book():
    book_id = request.json.get("bookId")
    return_date = request.json.get("returnDate")

    book = Book.query.get(book_id)

    result = db.session.execute(
        select(customer_book.c.customer_id).where(customer_book.c.book_id == book_id)
    ).first()
    if result is None:
        return jsonify({"error": f"No customer found borrowing book ID {book_id}."}), 404

    customer_id = result[0]
    customer = db.session.get(Customer, customer_id)
    if not customer:
        return jsonify({"error": "Customer not found."}), 404
    customer_name = customer.customer_name
    
    assoc_remove_stmt = customer_book.delete().where(customer_book.c.book_id == book_id)
    db.session.execute(assoc_remove_stmt)

    remaining_books = db.session.execute(
        select(customer_book.c.book_id).where(customer_book.c.customer_id == customer_id)
    ).fetchall()

    if not remaining_books:
        db.session.delete(customer)

    book.state = True
    db.session.commit()

    return jsonify({"message": f"Book ID {book_id} returned by {customer_name} on {return_date}."})


@app.route('/api/clear_borrowing_data', methods=['POST'])
def clear_borrrowing_data():
    db.session.execute(customer_book.delete())
    db.session.query(Customer).delete()
    db.session.commit()
    return jsonify({"message": "All borrowing data has been cleared."})


# API route to fetch description from Gemini API
@app.route('/api/description', methods=['GET'])
def get_description():
    entity_name = request.args.get('name')
    logging.debug(f"Received request for entity name: {entity_name}")  # Changed to DEBUG

    if not entity_name:
        logging.warning("Missing entity name in request.")
        return jsonify({'error': 'Missing entity name'}), 400

    if not GEMINI_API_URL or not GEMINI_API_KEY:
        logging.error("Gemini API configuration missing.")
        return jsonify({'error': 'Server configuration error'}), 500

    # Prepare the JSON payload with explicit instructions
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            f"Provide a detailed description of '{entity_name}'"
                            "If it is a book include information about the setting, characters, themes, key concepts, and its influence. "
                            "Do not include any concluding remarks or questions."
                            "Do not mention any Note at the end about not including concluding remarks or questions."
                        )
                    }
                ]
            }
        ]
    }

    # Construct the API URL with the API key as a query parameter
    api_url_with_key = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"

    headers = {
        "Content-Type": "application/json"
    }

    # Log the API URL and payload for debugging
    logging.debug(f"API URL: {api_url_with_key}")
    logging.debug(f"Payload: {payload}")

    try:
        # Make the POST request to the Gemini API
        response = requests.post(
            api_url_with_key,  # Include the API key in the URL
            headers=headers,
            json=payload,
            timeout=10  # seconds
        )
        logging.debug(f"Gemini API response status: {response.status_code}")  # Changed to DEBUG

        if response.status_code != 200:
            logging.error(f"Failed to fetch description from Gemini API. Status code: {response.status_code}")
            logging.error(f"Response content: {response.text}")
            return jsonify({
                'error': 'Failed to fetch description from Gemini API',
                'status_code': response.status_code,
                'response': response.text
            }), 500

        response_data = response.json()
        # Extract the description from the response
        description = response_data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'No description available.')
        logging.debug(f"Fetched description: {description}")  # Changed to DEBUG

        return jsonify({'description': description})

    except requests.exceptions.RequestException as e:
        logging.error(f"Exception during Gemini API request: {e}")
        return jsonify({'error': 'Failed to connect to Gemini API', 'message': str(e)}), 500
    except ValueError as e:
        logging.error(f"JSON decoding failed: {e}")
        return jsonify({'error': 'Invalid JSON response from Gemini API', 'message': str(e)}), 500
    except Exception as e:
        logging.exception(f"Unexpected error: {e}")
        return jsonify({'error': 'An unexpected error occurred', 'message': str(e)}), 500
    
# neo4j routes
# Neo4j Connection
neo4j_driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "123456789"))

@app.route("/api/neo4j/display_books", methods=["GET"])
def get_all_books_neo4j():
    with neo4j_driver.session() as session:
        result = session.run("""
            MATCH (b:Book)
            OPTIONAL MATCH (b)-[:WRITTEN_BY]->(a:Author)
            OPTIONAL MATCH (b)-[:PUBLISHED_BY]->(p:Publisher)
            OPTIONAL MATCH (b)-[:IN_GENRE]->(g:Genre)
            RETURN 
                b.id AS id, 
                b.title AS title, 
                b.state AS state,
                a.id AS author_id,
                a.author_name AS author,
                p.id AS publisher_id,
                p.publisher_name AS publisher,
                g.id AS genre_id,
                g.genre AS genre
        """)
        books = [record.data() for record in result]
    return jsonify(books)

@app.route("/api/neo4j/display_entity", methods=["POST"])
def get_entity_neo4j():
    data = request.json
    entity = data.get("entity")
    entity_id = int(data.get("id"))

    with neo4j_driver.session() as session:
        if entity == "Book":
            result = session.run("""
                MATCH (b:Book {id: $id})
                OPTIONAL MATCH (b)-[:WRITTEN_BY]->(a:Author)
                OPTIONAL MATCH (b)-[:PUBLISHED_BY]->(p:Publisher)
                OPTIONAL MATCH (b)-[:IN_GENRE]->(g:Genre)
                RETURN b.title AS Title, b.state AS State,
                       a.author_name AS Author,
                       p.publisher_name AS Publisher,
                       g.genre AS Genre
            """, id=entity_id)
        elif entity == "Author":
            result = session.run("MATCH (a:Author {id: $id}) RETURN a.author_name AS Author", id=entity_id)
        elif entity == "Publisher":
            result = session.run("MATCH (p:Publisher {id: $id}) RETURN p.publisher_name AS Publisher", id=entity_id)
        elif entity == "Genre":
            result = session.run("MATCH (g:Genre {id: $id}) RETURN g.genre AS Genre", id=entity_id)
        else:
            return jsonify({"error": "Invalid entity type"}), 400

        record = result.single()
        if not record:
            return jsonify({"error": f"{entity} not found"}), 404
        return jsonify(record.data())

@app.route("/api/neo4j/borrow_book", methods=["POST"])
def borrow_book_neo4j():
    data = request.json
    book_id = data.get("bookId")
    borrower_name = data.get("borrowerName")
    borrow_date = data.get("borrowDate")

    with neo4j_driver.session() as session:
        session.run("""
            MERGE (c:Customer {customer_name: $name})
            WITH c
            MATCH (b:Book {id: $book_id})
            MERGE (c)-[:BORROWED {date_borrowed: date($borrow_date)}]->(b)
            SET b.state = false
        """, name=borrower_name, book_id=int(book_id), borrow_date=borrow_date)

    return jsonify({"message": f"Book ID {book_id} borrowed by {borrower_name} on {borrow_date}."})

@app.route("/api/neo4j/return_book", methods=["POST"])
def return_book_neo4j():
    data = request.json
    book_id = data.get("bookId")
    return_date = data.get("returnDate")  # Not stored in Neo4j but accepted

    with neo4j_driver.session() as session:
        session.run("""
            MATCH (c:Customer)-[r:BORROWED]->(b:Book {id: $book_id})
            DELETE r
            SET b.state = true
        """, book_id=int(book_id))

    return jsonify({"message": f"Book ID {book_id} has been returned."})

@app.route("/api/neo4j/clear_borrowing_data", methods=["POST"])
def clear_borrowing_data_neo4j():
    with neo4j_driver.session() as session:
        # Delete all BORROWED relationships
        session.run("""
            MATCH (:Customer)-[r:BORROWED]->(:Book)
            DELETE r
        """)
        
        # Delete customers who no longer have any BORROWED edges
        session.run("""
            MATCH (c:Customer)
            WHERE NOT (c)-[:BORROWED]->()
            DELETE c
        """)
        
        # Reset all books to state=true (available)
        session.run("""
            MATCH (b:Book)
            SET b.state = true
        """)
    
    return jsonify({"message": "All Neo4j borrowing data has been cleared."})

# get all books by author name
@app.route("/api/neo4j/books/by_author/<author_name>", methods=["GET"])
def get_books_by_author_neo4j(author_name):
    result = neo4j_driver.session().run("""
        MATCH (a:Author {author_name: $name})<-[:WRITTEN_BY]-(b:Book)
        RETURN b.id AS id, b.title AS title, b.state AS state
        """, name=author_name)
    books = [record.data() for record in result]
    return jsonify(books)

# get books borrowed by customers
@app.route("/api/neo4j/borrowed_books/<customer_name>", methods=["GET"])
def get_borrowed_books_by_customer_neo4j(customer_name):
    result = neo4j_driver.session().run("""
        MATCH (c:Customer {customer_name: $name})-[:BORROWED]->(b:Book)
        RETURN b.id AS id, b.title AS title, b.state AS state
        """, name=customer_name)
    books = [record.data() for record in result]
    return jsonify(books)

# get book details 
@app.route("/api/neo4j/book_details/<int:book_id>", methods=["GET"])
def get_book_details_neo4j(book_id):
    result = neo4j_driver.session().run("""
        MATCH (b:Book {id: $id})
        OPTIONAL MATCH (b)-[:WRITTEN_BY]->(a:Author)
        OPTIONAL MATCH (b)-[:PUBLISHED_BY]->(p:Publisher)
        OPTIONAL MATCH (b)-[:IN_GENRE]->(g:Genre)
        RETURN b.title AS title, b.state AS state,
               a.author_name AS author,
               p.publisher_name AS publisher,
               g.genre AS genre
        """, id=book_id)
    return jsonify(result.single().data())

# End neo4j connection
@app.teardown_appcontext
def close_neo4j_driver(exception=None):
    if neo4j_driver is not None:
        neo4j_driver.close()


if __name__ == '__main__':
    app.run(debug=True, port=5001)
