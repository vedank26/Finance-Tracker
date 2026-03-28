from app import create_app, db

app = create_app()
with app.app_context():
    # Add new columns to user table using SQLAlchemy
    from sqlalchemy import text
    db.session.execute(text('ALTER TABLE user ADD COLUMN reset_token VARCHAR(32)'))
    db.session.execute(text('ALTER TABLE user ADD COLUMN reset_token_expiry INTEGER'))
    db.session.commit()
    print("Database updated successfully!")
