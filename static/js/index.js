const BACKEND = "neo4j"; // or "postgres"
const port = 5001;

const ROUTES = {
  postgres: {
    books: "/api/display_books",
    borrow: "/api/borrow_book",
    return: "/api/return_book",
    clear: "/api/clear_borrowing_data"
  },
  neo4j: {
    books: "/api/neo4j/display_books",
    borrow: "/api/neo4j/borrow_book",
    return: "/api/neo4j/return_book",
    clear: "/api/neo4j/clear_borrowing_data"
  }
};

window.onload = function () {
    loadBooks(port, ROUTES[BACKEND].books);
};

function loadBooks(port, route) {
        fetch(`http://127.0.0.1:${port}${route}`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(respone => respone.json())
    .then(books => {
        // Retrieve borrowing data from LocalStorage
        const borrowingData = JSON.parse(localStorage.getItem('borrowingData')) || {};
        const borrowBookSelect = document.getElementById('borrowBookId');
        const returnBookSelect = document.getElementById('returnBookId');

            // Clear existing options
            borrowBookSelect.innerHTML = '<option value="">Select a Book</option>';
            returnBookSelect.innerHTML = '<option value="">Select a Book</option>';

            const bookTable = document.getElementById("book-table")
            books.forEach(book => {
                const id = book.id
                const title = book.title
                const authorId = book.author_id
                const publisherId = book.publisher_id
                const genreId = book.genre_id
                const author = book.author
                const publisher = book.publisher
                const genre = book.genre    
                const state = book.state == 1 ? true : false

                // Create table row for each book
                const row = document.createElement('tr');
                row.setAttribute('data-id', id);

                // Check if book is borrowed
                const isBorrowed = borrowingData[id] ? true : false;

                row.innerHTML = `<td>${id}</td>
                             <td><a href="viewer.html?entity=Book&id=${id}" target="_blank">${title}</a></td>
                             <td><a href="viewer.html?entity=Author&id=${authorId}" target="_blank">${author}</a></td>
                             <td><a href="viewer.html?entity=Publisher&id=${publisherId}" target="_blank">${publisher}</a></td>
                             <td><a href="viewer.html?entity=Genre&id=${genreId}" target="_blank">${genre}</a></td>
                             <td>${isBorrowed ? borrowingData[id].borrowerName : ''}</td>
                             <td>${isBorrowed ? borrowingData[id].borrowDate : ''}</td>
                             <td>${isBorrowed ? borrowingData[id].returnDate : ''}</td>
                             <td>${isBorrowed ? 'Borrowed' : 'Present'}</td>`;
                bookTable.appendChild(row);


                // Populate the appropriate dropdown
                if (!isBorrowed) {
                    // Add book to Borrow dropdown
                    const option = document.createElement('option');
                    option.value = id;
                    option.textContent = `${id} - ${title}`;
                    borrowBookSelect.appendChild(option);
                } else {
                    // Add book to Return dropdown
                    const returnOption = document.createElement('option');
                    returnOption.value = id;
                    returnOption.textContent = `${id} - ${title}`;
                    returnBookSelect.appendChild(returnOption);
                }
            });

        }).catch(error => {
                console.error('Error fetching data:', error);
            });
        };

    function borrowBook(bookId, borrowerName, borrowDate) {
        fetch(`http://127.0.0.1:${port}${ROUTES[BACKEND].borrow}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                bookId: bookId,
                borrowerName: borrowerName,
                borrowDate: borrowDate
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(`Error: ${data.error}`);
            } else {
                alert(data.message);
            }
        })
        .catch(error => {
            console.error("Error:", error);
            alert("An error occurred while borrowing the book.");
        });
    }

    function returnBook(bookId, returnDate) {
        fetch(`http://127.0.0.1:${port}${ROUTES[BACKEND].return}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                bookId: bookId,
                returnDate: returnDate
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(`Error: ${data.error}`);
            } else {
                alert(data.message);
            }
        })
        .catch(error => {
            console.error("Error:", error);
            alert("An error occurred while returning the book.");
        });
    }
        
    function clearBorrowingData() {
        fetch(`http://127.0.0.1:${port}${ROUTES[BACKEND].clear}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(`Error: ${data.error}`);
            } else {
                alert(data.message);
            }
        })
        .catch(error => {
            console.error("Error:", error);
            alert("An error occurred while clearing all borrowing data.");
        });
    }
        


// Handle Borrow Form Submission
document.getElementById('borrowForm').addEventListener('submit', function (event) {
    event.preventDefault();
    const bookId = document.getElementById('borrowBookId').value;
    const borrowerName = document.getElementById('borrowerName').value.trim();
    const borrowDate = document.getElementById('borrowDate').value;

    if (!bookId || !borrowerName || !borrowDate) {
        alert('Please fill in all fields.');
        return;
    }

    // Confirmation Dialog
    if (!confirm(`Are you sure you want to borrow Book ID ${bookId}?`)) {
        return;
    }

    borrowBook(bookId, borrowerName, borrowDate);

    const row = document.querySelector(`#book-table tr[data-id="${bookId}"]`);
    if (row) {
        const currentState = row.cells[8].textContent;
        if (currentState === 'Borrowed') {
            alert('This book is already borrowed.');
            return;
        }

        const returnDate = new Date(borrowDate);
        returnDate.setMonth(returnDate.getMonth() + 3); // Set the return date 3 months later

        // Update the table
        row.cells[5].textContent = borrowerName;
        row.cells[6].textContent = borrowDate;
        row.cells[7].textContent = returnDate.toISOString().split('T')[0]; // Format the date as YYYY-MM-DD
        row.cells[8].textContent = 'Borrowed';
        row.classList.add('borrowed');

        // Save borrowing details to LocalStorage
        const borrowingData = JSON.parse(localStorage.getItem('borrowingData')) || {};
        borrowingData[bookId] = {
            borrowerName: borrowerName,
            borrowDate: borrowDate,
            returnDate: returnDate.toISOString().split('T')[0]
        };
        localStorage.setItem('borrowingData', JSON.stringify(borrowingData));

        // Remove the borrowed book from Borrow Form dropdown
        const borrowBookSelect = document.getElementById('borrowBookId');
        const optionToRemove = borrowBookSelect.querySelector(`option[value="${bookId}"]`);
        if (optionToRemove) {
            optionToRemove.remove();
        }

        // Add the borrowed book to Return Form dropdown
        const returnBookSelect = document.getElementById('returnBookId');
        const newReturnOption = document.createElement('option');
        newReturnOption.value = bookId;
        newReturnOption.textContent = `${bookId} - ${row.cells[1].textContent}`;
        returnBookSelect.appendChild(newReturnOption);

        // Clear the form
        document.getElementById('borrowForm').reset();

        alert(`Book ID ${bookId} has been successfully borrowed.`);
    } else {
        alert('No book found with that ID.');
    }
});

// Handle Return Form Submission
document.getElementById('returnForm').addEventListener('submit', function (event) {
    event.preventDefault();
    const bookId = document.getElementById('returnBookId').value;
    const returnDateInput = document.getElementById('returnDate').value;

    if (!bookId || !returnDateInput) {
        alert('Please fill in all fields.');
        return;
    }

    // Confirmation Dialog
    if (!confirm(`Are you sure you want to return Book ID ${bookId}?`)) {
        return;
    }

    returnBook(bookId, returnDateInput)

    const row = document.querySelector(`#book-table tr[data-id="${bookId}"]`);
    if (row) {
        const currentState = row.cells[8].textContent;
        if (currentState !== 'Borrowed') {
            alert('This book is not currently borrowed.');
            return;
        }

        // Update the table to clear borrowing details
        row.cells[5].textContent = '';
        row.cells[6].textContent = '';
        row.cells[7].textContent = '';
        row.cells[8].textContent = 'Present';
        row.classList.remove('borrowed');

        // Update LocalStorage
        const borrowingData = JSON.parse(localStorage.getItem('borrowingData')) || {};
        if (borrowingData[bookId]) {
            borrowingData[bookId].returnDate = returnDateInput; // Optionally update the return date
            // Remove the entry to indicate the book is returned
            delete borrowingData[bookId];
            localStorage.setItem('borrowingData', JSON.stringify(borrowingData));
        }

        // Remove the returned book from Return Form dropdown
        const returnBookSelect = document.getElementById('returnBookId');
        const optionToRemove = returnBookSelect.querySelector(`option[value="${bookId}"]`);
        if (optionToRemove) {
            optionToRemove.remove();
        }

        // Add the returned book back to Borrow Form dropdown
        const borrowBookSelect = document.getElementById('borrowBookId');
        const newBorrowOption = document.createElement('option');
        newBorrowOption.value = bookId;
        newBorrowOption.textContent = `${bookId} - ${row.cells[1].textContent}`;
        borrowBookSelect.appendChild(newBorrowOption);

        // Clear the form
        document.getElementById('returnForm').reset();

        alert(`Book ID ${bookId} has been successfully returned.`);
    } else {
        alert('No book found with that ID.');
    }
});

// Clear borrowing data from localStorage
document.getElementById('clearDataBtn').addEventListener('click', function () {
    if (confirm('Are you sure you want to clear all borrowing data? This action cannot be undone.')) {
        clearBorrowingData()
        localStorage.removeItem('borrowingData'); // Only remove borrowing data
        // location.reload(); // Reload the page after clearing the data
    }   
});
