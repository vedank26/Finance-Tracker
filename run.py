from app import create_app, db

app = create_app()

if __name__ == '__main__':
    import os
    with app.app_context():
        db.create_all()

        # Add fingerprint column if not exists (idempotent migration)
        try:
            from sqlalchemy import text
            db.session.execute(text(
                "ALTER TABLE transaction "
                "ADD COLUMN fingerprint "
                "VARCHAR(32)"
            ))
            db.session.commit()
            print("Fingerprint column added to transaction table")
        except Exception as e:
            db.session.rollback()
            print(f"Fingerprint column may already exist: {e}")

        print("Database tables created!")
        print("Starting Flask application...")
        print("Open http://localhost:5000 in your browser")

    # Read debug flag from environment; never enable in production
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)
