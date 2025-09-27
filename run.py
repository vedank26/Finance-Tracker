from app import app, db

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("Database tables created!")
        print("Starting Flask application...")
        print("Open http://localhost:5000 in your browser")
    app.run(debug=True, host='0.0.0.0', port=5000)