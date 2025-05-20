from neo4j import GraphDatabase
from db.db_connection import db
from db.models import Author, Publisher, Genre, Book, Customer, customer_book
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# create a session 
DATABASE_URL = "postgresql://admin:mysecretpassword@localhost:5432/pg-container"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j","123456789"))  # Connect to Neo4j

# clear any existing data
def clear_neo4j():
    driver.session().run("MATCH (n) DETACH DELETE n")

# insert author nodes
def insert_authors():
    for author in session.query(Author).all():
        driver.session().run("MERGE (:Author {id: $id, author_name: $name})", id=author.id, name=author.author_name)

# insert publisher nodes 
def insert_publishers():
    for publisher in session.query(Publisher).all():
        driver.session().run("MERGE (:Publisher {id: $id, publisher_name: $name})", id=publisher.id, name=publisher.publisher_name)

# insert genre nodes
def insert_genres():
    for genre in session.query(Genre).all():
        driver.session().run("MERGE (:Genre {id: $id, genre: $name})", id=genre.id, name=genre.genre)

# insert customer nodes
def insert_customers():
    for customer in session.query(Customer).all():
        driver.session().run("MERGE (:Customer {id: $id, customer_name: $name})", id=customer.id, name=customer.customer_name)

# insert book nodes and relationships (published by, written by)
def insert_books():
    for book in session.query(Book).all():
        driver.session().run("""
                MERGE (b:Book {id: $id})
                SET b.title = $title, b.state = $state
                WITH b
                MATCH (a:Author {id: $aid})
                MERGE (b)-[:WRITTEN_BY]->(a)
                WITH b
                MATCH (p:Publisher {id: $pid})
                MERGE (b)-[:PUBLISHED_BY]->(p)
                WITH b
                MATCH (g:Genre {id: $gid})
                MERGE (b)-[:IN_GENRE]->(g)""",
                id=book.id, title=book.title, state=book.state,
                aid=book.author_id, pid=book.publisher_id, gid=book.genre_id)

# insert borrowed relationships and add the borrowed date
def insert_borrows():
    for row in session.execute(customer_book.select()):
        driver.session().run("""
                MATCH (c:Customer {id: $cid}), (b:Book {id: $bid})
                MERGE (c)-[:BORROWED {date_borrowed: date($date)}]->(b)""",
                cid=row.customer_id, bid=row.book_id, date=str(row.date_borrowed))

# SQL to neo4j migration
def migrate():
    clear_neo4j()
    insert_authors()
    insert_publishers()
    insert_genres()
    insert_customers()
    insert_books()
    insert_borrows()
    print("Data sent to Neo4j successfully!")

if __name__ == "__main__":
    migrate()
